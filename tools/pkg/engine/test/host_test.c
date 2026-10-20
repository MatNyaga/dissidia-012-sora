/* Host unit test of EXTRA.PRX's boot logic (extra.c compiled with -DHOST_TEST). Disc files come from directory
 * $XDIR: EXTRA.IDX, PACKAGE_INFO.BIN and PACKAGE.BIN.size (decimal text). Prints the status block as key=value,
 * then the result of xidx_find for each hex hash given on the command line.
 * $HOOK: "vanilla" (default) | "jit" (PPSSPP marker, neighbours vanilla) | "taken" (someone else's jal). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#pragma GCC diagnostic ignored "-Wpointer-to-int-cast"
#pragma GCC diagnostic ignored "-Wint-to-pointer-cast"
#include "../extra/extra.c"

volatile unsigned int host_code[32];
void xidx_tramp(void) {}
static FILE *fds[8];
static void *blks[8];
static int nblk, freed;
static const char *dir(void) { const char *d = getenv("XDIR"); return d ? d : "."; }
static void map(const char *path, char *out) { const char *b = strrchr(path, '/'); sprintf(out, "%s/%s", dir(), b + 1); }
SceUID sceIoOpen(const char *path, int flags, int mode)
{
	char p[512]; (void)flags; (void)mode; map(path, p);
	for (int i = 1; i < 8; i++) if (!fds[i]) { fds[i] = fopen(p, "rb"); return fds[i] ? i : (int)0x80010002u; }
	return -1;
}
int sceIoRead(SceUID fd, void *buf, SceSize n) { return (int)fread(buf, 1, n, fds[fd]); }
int sceIoClose(SceUID fd) { fclose(fds[fd]); fds[fd] = 0; return 0; }
int sceIoLseek32(SceUID fd, int off, int whence) { (void)whence; fseek(fds[fd], off, SEEK_SET); return (int)ftell(fds[fd]); }
int sceIoGetstat(const char *path, SceIoStat *st)
{
	char p[512]; map(path, p); strcat(p, ".size");
	FILE *f = fopen(p, "r"); if (!f) return (int)0x80010002u;
	if (fscanf(f, "%lld", &st->st_size) != 1) st->st_size = 0;
	fclose(f); return 0;
}
SceUID sceKernelAllocPartitionMemory(SceUID part, const char *name, int type, SceSize size, void *addr)
{
	(void)part; (void)name; (void)type; (void)addr;
	if (getenv("NOMEM")) return (int)0x800200D9u;
	blks[++nblk] = calloc(1, size); return nblk;
}
int sceKernelFreePartitionMemory(SceUID blk) { free(blks[blk]); blks[blk] = 0; freed++; return 0; }
void *sceKernelGetBlockHeadAddr(SceUID blk) { return blks[blk]; }
SceSize sceKernelMaxFreeMemSize(void) { return 247040; }
SceSize sceKernelTotalFreeMemSize(void) { return 445440; }
void sceKernelDcacheWritebackInvalidateRange(const void *p, unsigned int n) { (void)p; (void)n; }
void sceKernelIcacheInvalidateRange(const void *p, unsigned int n) { (void)p; (void)n; }

int main(int argc, char **argv)
{
	const char *h = getenv("HOOK");
	host_code[5] = 0x34060050u; host_code[8] = 0x0E21C4A2u; host_code[9] = 0x02202025u;
	if (h && !strcmp(h, "jit")) host_code[8] = 0x6800D5CAu;
	if (h && !strcmp(h, "taken")) host_code[8] = 0x0E000000u;
	module_start(0, 0);
	struct extra_status *s = &g_extra;
	printf("magic=%08x layout=%u size=0x%x self_ok=%d version=%08x state=%d warn=%u count=%u file_rows=%u "
	       "rejected=%u overrides=%u first_rejected=%08x info_rows=%u pkg_size=%u guard_seen=%08x guard_mode=%u "
	       "hook_word=%s step=%u tail=%08x api_magic=%08x api_status_ok=%d blocks=%d freed=%d\n",
	       s->magic, s->layout, s->size, s->self == (unsigned int)s, s->version, s->state, s->warn, s->count,
	       s->file_rows, s->rejected, s->overrides, s->first_rejected, s->info_rows, s->pkg_size, s->guard_seen,
	       s->guard_mode, host_code[8] == hook_word() ? "ours" : "vanilla", s->step, s->tail,
	       ((struct extra_api *)s->api)->magic, ((struct extra_api *)s->api)->status == s, nblk, freed);
	for (int i = 1; i < argc; i++) {
		unsigned int q = (unsigned int)strtoul(argv[i], 0, 16);
		Row *r = xidx_find(q);
		printf("find %08x -> %s", q, r ? "" : "miss\n");
		if (r) printf("sector %u size %u\n", r->sector, r->size);
	}
	printf("lookups=%u hits=%u row_hits0=%u feature=%d\n", s->lookups, s->hits, s->row_hits[0], extra_feature(1));
	return 0;
}
