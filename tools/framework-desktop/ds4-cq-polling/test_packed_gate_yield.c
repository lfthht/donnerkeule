/* Execute the real candidate adapter against explicit verbs completion faults. */
#define DS4_ROCM_BUILD 1
#include "ds4_tp.c"
#include <assert.h>
static struct ds4_tp_roce *rr;
static unsigned mode, polls, send_calls, recv_calls, corrupt_byte;
static uint64_t send_id, recv_id;
static uint32_t wire;
static unsigned char expected[65536];
static int fake_recv(struct ibv_qp *qp,struct ibv_recv_wr *wr,struct ibv_recv_wr **bad) {
    (void)qp;(void)bad;++recv_calls;
    assert(wr->num_sge==1 && wr->sg_list->length<=TP_RC_CHUNK && !(wr->sg_list->length%4096));
    recv_id=wr->wr_id;
    assert(wr->sg_list->addr==(uintptr_t)rr->rx);
    return mode==1?EIO:0;
}
static int fake_send(struct ibv_qp *qp,struct ibv_send_wr *wr,struct ibv_send_wr **bad) {
    (void)qp;(void)bad;++send_calls;send_id=wr->wr_id;
    wire=wr->sg_list->length;assert(wr->num_sge==1 && wire==65536);
    assert(!memcmp(rr->tx,expected,wire));
    memcpy(rr->rx,expected,wire);
    for(unsigned i=40;i<wire;i++)rr->rx[i]^=0x73;
    if(mode==2)rr->rx[corrupt_byte]^=1;
    return mode==3?EIO:0;
}
static int fake_poll(struct ibv_cq *cq,int nr,struct ibv_wc *wc) {
    (void)cq;assert(nr==2);++polls;
    if(mode==4)return -1;
    if(mode==5)return 0;
    wc[0]=(struct ibv_wc){.wr_id=recv_id,.status=IBV_WC_SUCCESS,.opcode=IBV_WC_RECV,.byte_len=wire};
    wc[1]=(struct ibv_wc){.wr_id=send_id,.status=IBV_WC_SUCCESS,.opcode=IBV_WC_SEND};
    if(mode==6)wc[0].status=IBV_WC_GENERAL_ERR;
    if(mode==7)wc[0].wr_id+=16;
    if(mode==8)wc[0].byte_len--;
    if(mode==9)wc[1]=wc[0];
    return 2;
}
static void one(size_t bytes,unsigned fault,unsigned corrupt) {
    mode=fault;corrupt_byte=corrupt;polls=send_calls=recv_calls=0;
    struct ibv_context context={.ops={.post_recv=fake_recv,.post_send=fake_send,.poll_cq=fake_poll}};
    struct ibv_qp qp={.context=&context};struct ibv_cq cq={.context=&context};
    struct ibv_mr mr={.lkey=17};unsigned char tx[65536],rx[65536],out[65536],storage[65538];
    memset(storage,0xa5,sizeof(storage));memset(expected,0,sizeof(expected));
    struct ds4_tp_roce r={.qp=&qp,.cq=&cq,.tx_mr=&mr,.rx_mr=&mr,.tx=tx,.rx=rx,.packed_gates=true,.cq_yield_interval=64};rr=&r;
    ds4_tp tp={.roce=&r,.gate_timeout_ms=1};atomic_init(&tp.failed,false);
    ds4_tp_linux_gate_header h={DS4_TP_MAGIC,1,39,1,123,7,bytes};
    memcpy(expected,&h,sizeof(h));
    for(size_t i=0;i<bytes;i++)out[i]=(unsigned char)(i*31+7);
    memcpy(expected+sizeof(h),out,bytes);
    if(fault==10)ds4_tp_mark_failed(&tp);
    if(fault==11)r.posted=1;
    if(fault==12)r.window_id=UINT64_MAX/16;
    int ok=tp_roce_packed_gate(&tp,&h,sizeof(h),out,storage+1,bytes,0);
    assert(ok==(fault==0));
    if(ok) {
        assert(r.posted==1 && r.prearmed && send_calls==1 && recv_calls==2);
        for(size_t i=0;i<bytes;i++)assert(storage[i+1]==(unsigned char)(out[i]^0x73));
        assert(storage[0]==0xa5 && storage[bytes+1]==0xa5);
    } else {
        for(unsigned i=0;i<sizeof(storage);i++)assert(storage[i]==0xa5);
        if(fault==10 || fault==11 || fault==12)assert(!send_calls && !recv_calls);
    }
}
int main(void) {
    const size_t sizes[]={1,3,4096,20480,40960,65496};
    for(unsigned i=0;i<sizeof(sizes)/sizeof(*sizes);i++)one(sizes[i],0,0);
    for(unsigned i=1;i<=12;i++)one(20480,i,0);
    for(unsigned i=0;i<40;i++)one(20480,2,i);
    puts("PASS real packed-gate adapter: payloads, tails, all 40 header bytes, canaries, completion errors, duplicate/stale IDs, timeout and cancellation");
}
