/* Diagnostic host timings only; one writer per translation unit. */
#include <stdint.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
struct tpdiag_stat { uint64_t count,ns,bytes,max; };
static struct tpdiag_stat tpdiag_stats[4][10];
static const char *tpdiag_names[]={"service_wakeup","gpu_ready_wait","transport_callback","tx_copy_pad","receive_prepare_send","completion_wait","rx_copy_check","next_receive","large_tx_copy","large_rx_copy"};
static uint64_t tpdiag_clock(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000ull+t.tv_nsec; }
static uint64_t tpdiag_begin(void) { return getenv("DS4_TP_DIAGNOSTIC")?tpdiag_clock():0; }
static void tpdiag_add(unsigned kind,unsigned stage,uint64_t start,uint64_t bytes) {
 if(!start || kind>3 || stage>=10)return;
 uint64_t dt=tpdiag_clock()-start;struct tpdiag_stat *s=&tpdiag_stats[kind][stage];++s->count;s->ns+=dt;s->bytes+=bytes;if(dt>s->max)s->max=dt;
}
__attribute__((destructor)) static void tpdiag_report(void) {
 for(unsigned k=0;k<4;k++)for(unsigned i=0;i<10;i++) { struct tpdiag_stat *s=&tpdiag_stats[k][i];if(s->count)fprintf(stderr,"DS4_TP_STAGE unit=%s kind=%u stage=%s count=%llu total_ms=%.3f mean_us=%.3f max_us=%.3f bytes=%llu\n",TPDIAG_UNIT,k,tpdiag_names[i],(unsigned long long)s->count,s->ns/1e6,s->ns/(1e3*s->count),s->max/1e3,(unsigned long long)s->bytes); }
}
