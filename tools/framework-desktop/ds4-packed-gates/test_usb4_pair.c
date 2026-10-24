/* Actual model-free transport, including the production RC and TCP adapters. */
#define DS4_ROCM_BUILD 1
#include "ds4_tp.c"
#include <assert.h>
void ds4_vision_embedding_free(ds4_vision_embedding *e){if(e){free(e->data);memset(e,0,sizeof(*e));}}
int main(int argc,char **argv) {
 if(argc!=5)return 2;
 int rank=atoi(argv[1]),port=atoi(argv[3]);const char *mode=argv[4];
 ds4_tp_options opt={.role=rank?DS4_TP_WORKER:DS4_TP_LEADER,
  .listen_host=argv[2],.leader_host=argv[2],.listen_port=port,.leader_port=port,
  .transport=DS4_TP_TRANSPORT_RDMA,.rdma_device="usb4_rdma0",.rdma_port=1,
  .rdma_gid_index=1,.rdma_gid_index_set=true};
 ds4_tp_identity id={.gguf_bytes=1,.model_id=41,.n_layer=40,.n_embd=5120,
  .n_vocab=129280,.quant_bits=2,.ctx_size=65536};
 ds4_tp *tp=NULL;char err[512]={0};
 if(!ds4_tp_create(&tp,&opt,&id,err,sizeof(err))){fprintf(stderr,"create failed: %s\n",err);return !strcmp(mode,"negotiation-mismatch")?0:1;}
 if(!strcmp(mode,"negotiation-mismatch")){ds4_tp_free(tp);return 1;}
 const size_t sizes[]={1,3,31,4095,4096,20480,40960,65496,65497,65536,131072,2097151,2097152,2097153,8388611,41635840};
 const size_t cap=41635840;unsigned char *out=malloc(cap),*storage=malloc(cap+2);assert(out&&storage);
 int ok=1;double start=tp_now_sec();
 if(!tp->roce->packed_gates && !strcmp(mode,"normal")) {
  /* Match inference's initial bulk prefill before measuring small gates. */
  memset(out,rank?0x73:0x41,2097152);memset(storage,0xa5,2097154);
  ok=tp_linux_gate(tp,3,39,0,10000,out,storage+1,2097152,0);
  if(ok)for(size_t j=0;j<2097152;j++)assert(storage[j+1]==(rank?0x41:0x73));
  assert(ok && storage[0]==0xa5 && storage[2097153]==0xa5);
 }

 for(unsigned n=0;ok && n<sizeof(sizes)/sizeof(*sizes);n++) {
  size_t bytes=sizes[n];if(!tp->roce->packed_gates && bytes<20480)continue;memset(storage,0xa5,cap+2);
  for(size_t j=0;j<bytes;j++)out[j]=(unsigned char)(j*31+rank*73+n*7);
  uint64_t seq=n+1;if(!strcmp(mode,"header-mismatch")&&rank)seq++;
  ok=tp_linux_gate(tp,3,39,0,seq,out,storage+1,bytes,0);
  if(!strcmp(mode,"header-mismatch")) {
   assert(!ok && ds4_tp_failed(tp));for(size_t j=0;j<cap+2;j++)assert(storage[j]==0xa5);
   puts("PASS mismatched gate rejected before model output copy");ok=1;break;
  }
  if(ok)for(size_t j=0;j<bytes;j++)if(storage[j+1]!=(unsigned char)(j*31+(1-rank)*73+n*7)){ok=0;break;}
  if(ok)ok=storage[0]==0xa5&&storage[bytes+1]==0xa5;
  printf("rank=%d bytes=%zu payload_canaries=%s\n",rank,bytes,ok?"PASS":"FAIL");fflush(stdout);
 }
 if(ok && !strcmp(mode,"normal")) {
  double t=tp_now_sec();const size_t bytes=20480;
  for(unsigned n=0;ok&&n<100;n++) {
   memset(out,rank?0x73:0x41,bytes);memset(storage,0xa5,bytes+2);
   ok=tp_linux_gate(tp,1,39,0,n+1000,out,storage+1,bytes,0);
   if(ok)for(size_t j=0;j<bytes;j++)if(storage[j+1]!=(rank?0x41:0x73)){ok=0;break;}
   if(ok)ok=storage[0]==0xa5&&storage[bytes+1]==0xa5;
  }
  printf("rank=%d repeated_20k_gates=100 mean_us=%.2f %s\n",rank,(tp_now_sec()-t)*1e6/100,ok?"PASS":"FAIL");
 }
 free(out);free(storage);ds4_tp_free(tp);
 printf("rank=%d total_seconds=%.3f result=%s\n",rank,tp_now_sec()-start,ok?"PASS":"FAIL");return ok?0:1;
}
