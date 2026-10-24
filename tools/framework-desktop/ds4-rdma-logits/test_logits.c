#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define TP_RC_WINDOW 4u
#define TP_RC_CHUNK (2u*1024u*1024u)
#define DS4_TP_MAGIC 1234u
#define DS4_TP_FRAME_LOGITS 8u
#define DS4_TP_HAVE_ROCE 1
typedef struct {uint32_t magic,type,bytes;} ds4_tp_frame_header;
struct ds4_tp_roce {bool logits;pthread_mutex_t io_lock;uint8_t *logits_tx,*logits_rx;size_t logits_capacity;uint64_t logits_calls,logits_tx_bytes,logits_rx_bytes;};
typedef struct {struct ds4_tp_roce *roce;bool rdma_active;atomic_bool failed;int control_fd;} ds4_tp;
static unsigned mode,prepares,exchanges,headers,expected_bytes;
static atomic_uint in_flight;
static bool sending,delay_exchange;
static uint32_t *pattern;
static bool fail_allocation;
static void *allocate(size_t n){return fail_allocation?NULL:malloc(n);}
static void *allocate_zero(size_t n,size_t s){return fail_allocation?NULL:calloc(n,s);}
static bool ds4_tp_failed(ds4_tp *t){return atomic_load(&t->failed);}
static void ds4_tp_mark_failed(ds4_tp *t){atomic_store(&t->failed,true);}
static int tp_roce_prepare(ds4_tp *t,uint64_t bytes){(void)t;assert(bytes%4096==0);prepares++;return mode!=1;}
static int tp_write_full(int fd,const void *data,size_t n){(void)fd;assert(n==sizeof(ds4_tp_frame_header));const ds4_tp_frame_header *h=data;assert(h->magic==DS4_TP_MAGIC&&h->type==DS4_TP_FRAME_LOGITS&&h->bytes==expected_bytes);headers++;return mode!=2;}
static int tp_read_frame_header(int fd,uint32_t *type,uint32_t *bytes){(void)fd;headers++;*type=mode==2?999:DS4_TP_FRAME_LOGITS;*bytes=expected_bytes+(mode==5?4:0);return 1;}
static int tp_roce_exchange(ds4_tp *t,const void *out,void *in,uint64_t bytes){
 assert(++in_flight==1);exchanges++;
 if(sending)assert(!memcmp(out,pattern,expected_bytes));
 else for(unsigned i=0;i<bytes;i++)assert(!((const unsigned char*)out)[i]);
 for(unsigned i=expected_bytes;i<bytes;i++)assert(!((const unsigned char*)out)[i]);
 if(delay_exchange){struct timespec d={0,200000};nanosleep(&d,NULL);}
 memset(in,0,(size_t)bytes);memcpy(in,pattern,expected_bytes);
 --in_flight;(void)t;return mode!=3;
}
static int tp_linux_gate_unlocked(ds4_tp *t,uint32_t k,uint32_t l,uint32_t g,uint64_t s,const void *o,void *i,uint64_t n,uint64_t grace){
 (void)t;(void)k;(void)l;(void)g;(void)s;(void)o;(void)i;(void)n;(void)grace;
 assert(++in_flight==1);struct timespec d={0,200000};nanosleep(&d,NULL);--in_flight;return 1;
}
#define malloc allocate
#define calloc allocate_zero
#include "logits-helper.c"
#undef malloc
#undef calloc
#include "gate-wrapper.c"

static void one(uint32_t count,bool send,unsigned fault){
 struct ds4_tp_roce r={.logits=true};assert(!pthread_mutex_init(&r.io_lock,NULL));ds4_tp t={.roce=&r,.rdma_active=true};atomic_init(&t.failed,false);
 unsigned char output[258568];memset(output,0xa5,sizeof(output));mode=fault;sending=send;prepares=exchanges=headers=0;expected_bytes=count*4;fail_allocation=fault==4;
 int ok=tp_roce_logits_transfer(&t,send?(float*)pattern:NULL,send?NULL:(float*)(output+4),count);
 assert(ok==(fault==0));assert(ds4_tp_failed(&t)==(fault!=0));
 if(ok){if(!send)assert(!memcmp(output+4,pattern,expected_bytes));assert(r.logits_calls==1&&r.logits_tx_bytes==(send?expected_bytes:0)&&r.logits_rx_bytes==(send?0:expected_bytes));}
 else for(unsigned i=0;i<sizeof(output);i++)assert(output[i]==0xa5);
 assert(!pthread_mutex_trylock(&r.io_lock));pthread_mutex_unlock(&r.io_lock);
 free(r.logits_tx);free(r.logits_rx);pthread_mutex_destroy(&r.io_lock);fail_allocation=false;
}
static void *transfer_thread(void *ptr){ds4_tp *t=ptr;for(unsigned i=0;i<40;i++)assert(tp_roce_logits_transfer(t,(float*)pattern,NULL,8));return NULL;}
static void *gate_thread(void *ptr){ds4_tp *t=ptr;for(unsigned i=0;i<40;i++)assert(tp_linux_gate(t,1,0,0,i,NULL,NULL,32,0));return NULL;}
int main(void){
 pattern=malloc(258560);assert(pattern);for(unsigned i=0;i<64640;i++)pattern[i]=0x7fc00001u^(i*2654435761u);
 for(unsigned n=1;n<=64640;n=n==1?2:n==2?5120:n==5120?64640:64641)for(unsigned send=0;send<2;send++)one(n,send,0);
 for(unsigned fault=1;fault<=5;fault++)for(unsigned send=0;send<2;send++)if(fault!=5||!send)one(64640,send,fault);
 struct ds4_tp_roce r={.logits=true};pthread_mutex_init(&r.io_lock,NULL);ds4_tp t={.roce=&r,.rdma_active=true};atomic_init(&t.failed,false);
 assert(!tp_roce_logits_transfer(&t,(float*)pattern,NULL,0));assert(!tp_roce_logits_transfer(&t,(float*)pattern,NULL,UINT32_MAX));
 assert(!tp_roce_logits_transfer(&t,NULL,NULL,1));assert(!tp_roce_logits_transfer(&t,(float*)pattern,(float*)pattern,1));
 atomic_store(&t.failed,false);mode=0;sending=true;expected_bytes=32;delay_exchange=true;pthread_t a,b;assert(!pthread_create(&a,NULL,transfer_thread,&t));assert(!pthread_create(&b,NULL,gate_thread,&t));pthread_join(a,NULL);pthread_join(b,NULL);
 assert(r.logits_calls==40&&!in_flight);free(r.logits_tx);free(r.logits_rx);pthread_mutex_destroy(&r.io_lock);free(pattern);return 0;
}
