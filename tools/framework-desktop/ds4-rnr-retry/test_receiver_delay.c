#define DS4_ROCM_BUILD 1
#include "ds4_tp.c"
#include <assert.h>
#include <poll.h>
void ds4_vision_embedding_free(ds4_vision_embedding *e){if(e){free(e->data);memset(e,0,sizeof(*e));}}
int main(int argc,char **argv){
 if(argc!=7)return 2;int rank=atoi(argv[1]),port=atoi(argv[3]),retry=atoi(argv[4]),delay=atoi(argv[5]),never=atoi(argv[6]);
 ds4_tp_options opt={.role=rank?DS4_TP_WORKER:DS4_TP_LEADER,.listen_host=argv[2],.leader_host=argv[2],.listen_port=port,.leader_port=port,.transport=DS4_TP_TRANSPORT_RDMA,.rdma_device="usb4_rdma0",.rdma_port=1,.rdma_gid_index=1,.rdma_gid_index_set=true};
 ds4_tp_identity id={.gguf_bytes=1,.model_id=41,.n_layer=40,.n_embd=5120,.n_vocab=129280,.quant_bits=2,.ctx_size=16384};setenv("TEST_RNR_RETRY",argv[4],1);ds4_tp *tp=NULL;char err[512]={0};assert(ds4_tp_create(&tp,&opt,&id,err,sizeof(err)));struct ds4_tp_roce *r=tp->roce;assert(!r->posted&&!r->prearmed);

 const uint32_t bytes=24576;memset(r->tx,0x73,bytes);memset(r->rx,0xa5,bytes+8192);uint64_t marker=0x524e5254455354u,peer=0;assert(ds4_tp_io_exchange(tp->control_fd,&marker,&peer,8,5000,&tp->failed)&&marker==peer);
 double start=tp_now_sec();uint32_t status=UINT32_MAX;int ok=0;
 if(rank){
  struct ibv_sge sg={.addr=(uintptr_t)r->tx,.length=bytes,.lkey=r->tx_mr->lkey};struct ibv_send_wr wr={.wr_id=101,.sg_list=&sg,.num_sge=1,.opcode=IBV_WR_SEND,.send_flags=IBV_SEND_SIGNALED},*bad=NULL;assert(!ibv_post_send(r->qp,&wr,&bad));
  while(tp_now_sec()-start<(never?.750:2.0)){struct ibv_wc wc[2];int n=ibv_poll_cq(r->cq,2,wc);assert(n>=0);if(n){status=wc[0].status;printf("SEND_WC status=%u vendor=%u elapsed_ms=%.3f\n",status,wc[0].vendor_err,(tp_now_sec()-start)*1000);break;}sched_yield();}
  if(never&&status==UINT32_MAX){printf("APPLICATION_DEADLINE elapsed_ms=%.3f\n",(tp_now_sec()-start)*1000);ds4_tp_mark_failed(tp);status=UINT32_MAX-1;}
  assert(tp_write_full(tp->control_fd,&status,4));ok=never?status==UINT32_MAX-1:(retry==3?status!=IBV_WC_SUCCESS:status==IBV_WC_SUCCESS);
 }else{
  usleep((unsigned)delay*1000);struct pollfd p={.fd=tp->control_fd,.events=POLLIN};int early=poll(&p,1,0);assert(early>=0);
  if(!early&&!never){
   struct ibv_sge sg={.addr=(uintptr_t)(r->rx+4096),.length=bytes,.lkey=r->rx_mr->lkey};struct ibv_recv_wr wr={.wr_id=202,.sg_list=&sg,.num_sge=1},*bad=NULL;assert(!ibv_post_recv(r->qp,&wr,&bad));
   while(tp_now_sec()-start<2){struct ibv_wc wc[2];int n=ibv_poll_cq(r->cq,2,wc);assert(n>=0);if(n){assert(wc[0].status==IBV_WC_SUCCESS&&wc[0].opcode==IBV_WC_RECV&&wc[0].byte_len==bytes);ok=1;break;}sched_yield();}
   if(ok){for(unsigned j=0;j<bytes;j++)assert(r->rx[4096+j]==0x73);assert(r->rx[4095]==0xa5&&r->rx[4096+bytes]==0xa5);}
  }
  assert(tp_read_full(tp->control_fd,&status,4));if(never)ok=status==UINT32_MAX-1;else if(retry==3)ok=status!=IBV_WC_SUCCESS;else ok=ok&&status==IBV_WC_SUCCESS;
 }
 ds4_tp_free(tp);printf("RESULT=%s retry=%d delay_ms=%d never=%d total_ms=%.3f\n",ok?"PASS":"FAIL",retry,delay,never,(tp_now_sec()-start)*1000);return ok?0:1;
}
