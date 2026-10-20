/* Host (x86-64) stand-ins for the PSP SDK calls EXTRA.PRX uses — unit test only (run_host_test.sh). */
#include <stddef.h>
typedef int SceUID;
typedef unsigned int SceSize;
typedef long long SceOff;
typedef struct { unsigned int st_mode, st_attr; SceOff st_size; } SceIoStat;
#define PSP_O_RDONLY 1
#define PSP_SEEK_SET 0
#define PSP_SMEM_Low 0
#define PSP_SMEM_High 1
SceUID sceIoOpen(const char *path, int flags, int mode);
int sceIoRead(SceUID fd, void *buf, SceSize n);
int sceIoClose(SceUID fd);
int sceIoLseek32(SceUID fd, int off, int whence);
int sceIoGetstat(const char *path, SceIoStat *st);
SceUID sceKernelAllocPartitionMemory(SceUID part, const char *name, int type, SceSize size, void *addr);
int sceKernelFreePartitionMemory(SceUID blk);
void *sceKernelGetBlockHeadAddr(SceUID blk);
SceSize sceKernelMaxFreeMemSize(void);
SceSize sceKernelTotalFreeMemSize(void);
void sceKernelDcacheWritebackInvalidateRange(const void *p, unsigned int n);
void sceKernelIcacheInvalidateRange(const void *p, unsigned int n);
extern volatile unsigned int host_code[32];   /* stands for 0x08871400.. */
#define HOOK_AT (&host_code[8])
void xidx_tramp(void);
