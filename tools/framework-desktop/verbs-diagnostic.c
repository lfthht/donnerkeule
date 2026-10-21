/* SPDX-License-Identifier: GPL-2.0-only */
/* Diagnostic provider logging; optional pre-registration host cache eviction.
 * The opt-in eviction writes back cache lines without changing payload bytes.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <infiniband/verbs.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#undef ibv_reg_mr

static pthread_once_t once = PTHREAD_ONCE_INIT;
static int (*next_post)(struct ibv_qp *, struct ibv_send_wr *, struct ibv_send_wr **);
static struct ibv_mr *(*next_reg)(struct ibv_pd *, void *, size_t, int);
static struct ibv_mr *(*next_reg_iova2)(struct ibv_pd *, void *, size_t, uint64_t, unsigned int);
static _Thread_local unsigned int reg_depth;
static void initialize(void)
{
    next_post = dlsym(RTLD_NEXT, "ibv_cmd_post_send");
    next_reg = dlsym(RTLD_NEXT, "ibv_reg_mr");
    next_reg_iova2 = dlsym(RTLD_NEXT, "ibv_reg_mr_iova2");
}

static void evict_host_cache(void *address, size_t length)
{
    const char *enabled = getenv("TBV_DIAG_FLUSH_MR");
    uintptr_t begin = (uintptr_t)address;
    int saved = errno;
    struct timespec a, b;
    if (!enabled || strcmp(enabled, "1") || !length || length > 268435456U ||
        !begin || begin > UINTPTR_MAX - length)
        return;
#if defined(__x86_64__)
    clock_gettime(CLOCK_MONOTONIC, &a);
    __asm__ volatile("mfence" ::: "memory");
    uintptr_t last = (begin + length - 1) & ~(uintptr_t)63;
    for (uintptr_t p = begin & ~(uintptr_t)63; ; p += 64) {
        __asm__ volatile("clflush (%0)" :: "r" (p) : "memory");
        if (p == last)
            break;
    }
    __asm__ volatile("mfence" ::: "memory");
    clock_gettime(CLOCK_MONOTONIC, &b);
    fprintf(stderr, "RDMA_MR_CACHE_FLUSH bytes=%zu duration_ns=%lld before_registration=1\n", length,
            (long long)(b.tv_sec-a.tv_sec)*1000000000LL + b.tv_nsec-a.tv_nsec);
#else
    fprintf(stderr, "RDMA_MR_CACHE_FLUSH_UNSUPPORTED\n");
#endif
    errno = saved;
}

struct ibv_mr *ibv_reg_mr(struct ibv_pd *pd, void *address, size_t length, int access)
{
    struct ibv_mr *result;
    pthread_once(&once, initialize);
    if (!next_reg) { errno = ENOSYS; return NULL; }
    if (!reg_depth++) evict_host_cache(address, length);
    result = next_reg(pd, address, length, access);
    reg_depth--;
    return result;
}

struct ibv_mr *ibv_reg_mr_iova2(struct ibv_pd *pd, void *address, size_t length,
                             uint64_t iova, unsigned int access)
{
    struct ibv_mr *result;
    pthread_once(&once, initialize);
    if (!next_reg_iova2) { errno = ENOSYS; return NULL; }
    if (!reg_depth++) evict_host_cache(address, length);
    result = next_reg_iova2(pd, address, length, iova, access);
    reg_depth--;
    return result;
}

int ibv_cmd_post_send(struct ibv_qp *qp, struct ibv_send_wr *wr, struct ibv_send_wr **bad)
{
    pthread_once(&once, initialize);
    if (!next_post) return ENOSYS;
    int result = next_post(qp, wr, bad), saved = errno;
    if (result) {
        struct ibv_send_wr *failed = bad && *bad ? *bad : wr;
        fprintf(stderr, "RDMA_POST_ERROR return=%d errno=%d qp=%u wr_id=%llu opcode=%d\n",
                result, saved, qp->qp_num, (unsigned long long)failed->wr_id, failed->opcode);
    }
    errno = saved;
    return result;
}
