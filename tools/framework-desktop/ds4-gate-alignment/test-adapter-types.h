/* SPDX-License-Identifier: GPL-2.0-only */
/* Minimal verbs dispatch mocks; production helpers are extracted from the patch. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sched.h>
#define TP_RC_WINDOW 4u
#define TP_RC_CHUNK (2u * 1024u * 1024u)
#define DS4_TP_MAGIC UINT32_C(0x44533454)
#define IBV_WC_SUCCESS 0
#define IBV_WC_GENERAL_ERR 1
#define IBV_WC_RECV 2
#define IBV_WC_SEND 3
#define IBV_WR_SEND 0
#define IBV_SEND_SIGNALED 1
struct ibv_qp; struct ibv_cq; struct ibv_recv_wr; struct ibv_send_wr; struct ibv_wc;
struct ibv_context {
    struct {
        int (*post_recv)(struct ibv_qp *,struct ibv_recv_wr *,struct ibv_recv_wr **);
        int (*post_send)(struct ibv_qp *,struct ibv_send_wr *,struct ibv_send_wr **);
        int (*poll_cq)(struct ibv_cq *,int,struct ibv_wc *);
    } ops;
};
struct ibv_qp { struct ibv_context *context; };
struct ibv_cq { struct ibv_context *context; };
struct ibv_mr { uint32_t lkey; };
struct ibv_sge { uintptr_t addr; uint32_t length,lkey; };
struct ibv_recv_wr { uint64_t wr_id; struct ibv_sge *sg_list; int num_sge; };
struct ibv_send_wr { uint64_t wr_id; struct ibv_sge *sg_list; int num_sge,opcode,send_flags; };
struct ibv_wc { uint64_t wr_id; int status,opcode; uint32_t byte_len; };
struct ds4_tp_roce {
    struct ibv_qp *qp; struct ibv_cq *cq; struct ibv_mr *tx_mr,*rx_mr;
    uint8_t *tx,*rx; uint32_t lengths[TP_RC_WINDOW];
    uint64_t window_id; unsigned posted,cq_yield_interval;
    bool packed_gates,prearmed,logits; uint32_t gate_alignment;
};
typedef struct { struct ds4_tp_roce *roce; uint64_t gate_timeout_ms; atomic_bool failed; } ds4_tp;
typedef struct { uint32_t magic,kind,layer,gate; uint64_t elements,seq,bytes; } ds4_tp_linux_gate_header;
static bool ds4_tp_failed(ds4_tp *tp){return atomic_load(&tp->failed);}
static void ds4_tp_mark_failed(ds4_tp *tp){atomic_store(&tp->failed,true);}
static double tp_now_sec(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
#define ibv_post_recv(q,w,b) ((q)->context->ops.post_recv(q,w,b))
#define ibv_post_send(q,w,b) ((q)->context->ops.post_send(q,w,b))
#define ibv_poll_cq(q,n,w) ((q)->context->ops.poll_cq(q,n,w))
