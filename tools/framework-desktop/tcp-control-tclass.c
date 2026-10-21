/* SPDX-License-Identifier: GPL-2.0-only */
/* Keep TCP bootstrap/control in the existing priority-3 class during RDMA load.
 * This shim changes socket setup only; it never intercepts the verbs data path.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <sys/socket.h>
#include <unistd.h>

static pthread_once_t initialized=PTHREAD_ONCE_INIT;
static int (*real_socket)(int,int,int);
static void initialize(void) { real_socket=dlsym(RTLD_NEXT,"socket"); }

int socket(int domain,int type,int protocol) {
    pthread_once(&initialized,initialize);
    if(!real_socket) { errno=ENOSYS;return -1; }
    int fd=real_socket(domain,type,protocol);
    if(fd>=0 && (type&15)==SOCK_STREAM && (domain==AF_INET||domain==AF_INET6)) {
        int tos=96,ret;
        if(domain==AF_INET)ret=setsockopt(fd,IPPROTO_IP,IP_TOS,&tos,sizeof(tos));
        else ret=setsockopt(fd,IPPROTO_IPV6,IPV6_TCLASS,&tos,sizeof(tos));
        if(ret) { int saved=errno;close(fd);errno=saved;return -1; }
    }
    return fd;
}
