/*
 * XIDX — Phase-0 P0.7 PROTOTYPE (build-only; not on any disc yet): extra file index for files that are not in
 * PACKAGE_INFO.BIN. notes/dlc-phase0.md "P0.7". Meant to be merged into EXTRA.PRX in Phase 2.
 *
 * Data lives in PACKAGE.BIN's appended tail (like tools/scripts/pkg_add.py: appended at the ISO end, PACKAGE.BIN's
 * directory size stretched), so the game's own read code serves it unchanged; only the INDEX is ours:
 *   disc0:/PSP_GAME/USRDIR/DATA/EXTRA.IDX = header (32 B) + N rows of 12 B {hash, sector, size} sorted by hash,
 *   exactly the PACKAGE_INFO row layout (the game's readers only look at row+4 & 0xFFFFF and row+8 & 0x0FFFFFFF).
 *
 * Hook (one word, written at module_start, checked first):
 *   0x08871420 inside lookup FUN_088713e4: `jal 0x08871288` (name hash, delay slot `move a0,s1`) -> `jal xidx_tramp`.
 *   xidx_tramp calls the real hash, then xidx_find(hash): hit -> s2 = our row, return to 0x088714BC (the game's own
 *   hit path: caches the name + pointer at obj+8/+0x58, returns s2); miss -> return the hash to 0x08871428 and the
 *   game's bsearch runs as before. So EXTRA.IDX rows OVERRIDE disc rows with the same hash, and because our rows
 *   live outside the PACKAGE_INFO buffer (and carry flag 0), Data Install (FUN_0886fb98) never serves them.
 */
#include <pspkernel.h>
#include <pspiofilemgr.h>
#include <pspsysmem.h>
#include <psputils.h>

PSP_MODULE_INFO("SoraExtraIdx", 0, 1, 0);

#define HOOK_AT   ((volatile unsigned int *)0x08871420)
#define HOOK_ORIG 0x0E21C4A2u           /* jal 0x08871288 */
#define PKG_ISO_SECTOR 186624u
#define MAX_ROWS  16384u

typedef struct { unsigned int hash, sector, size; } Row;
typedef struct {
	char magic[4];                  /* "XIDX" */
	unsigned short version, hdr;    /* 1, 32 */
	unsigned int count, flags, pkg_sector, sum, r0, r1;
} Hdr;

Row *g_rows;
unsigned int g_count;
int g_state;                            /* >0 hooked (= rows), <0 = step that failed */

Row *xidx_find(unsigned int h)
{
	int lo = 0, hi = (int)g_count - 1;
	while (lo <= hi) {
		int mid = (lo + hi) >> 1;
		unsigned int v = g_rows[mid].hash;
		if (v == h)
			return &g_rows[mid];
		if (v < h)
			lo = mid + 1;
		else
			hi = mid - 1;
	}
	return 0;
}

/* Called instead of the hash; a0 = name. Absolute game addresses via lui/ori (no relocations). */
__asm__(
	".set push\n.set noreorder\n"
	".globl xidx_tramp\n"
	"xidx_tramp:\n"
	"  addiu $sp, $sp, -16\n"
	"  sw    $ra, 0($sp)\n"
	"  lui   $t9, 0x0887\n"
	"  ori   $t9, $t9, 0x1288\n"
	"  jalr  $t9\n"                 /* v0 = FUN_08871288(name) */
	"  nop\n"
	"  sw    $v0, 4($sp)\n"
	"  jal   xidx_find\n"
	"  move  $a0, $v0\n"
	"  lw    $ra, 0($sp)\n"
	"  beqz  $v0, 1f\n"
	"  nop\n"
	"  move  $s2, $v0\n"            /* hit: game hit path uses s2 */
	"  lui   $ra, 0x0887\n"
	"  ori   $ra, $ra, 0x14BC\n"
	"1:\n"
	"  lw    $v0, 4($sp)\n"         /* miss: hash for the game's bsearch */
	"  jr    $ra\n"
	"  addiu $sp, $sp, 16\n"
	".set pop\n");
extern void xidx_tramp(void);

static int load(void)
{
	Hdr h;
	unsigned int i, n;
	SceUID fd = sceIoOpen("disc0:/PSP_GAME/USRDIR/DATA/EXTRA.IDX", PSP_O_RDONLY, 0);
	if (fd < 0)
		return -1;
	if (sceIoRead(fd, &h, sizeof h) != (int)sizeof h || h.magic[0] != 'X' || h.magic[1] != 'I' ||
	    h.magic[2] != 'D' || h.magic[3] != 'X' || h.version != 1 || h.hdr < sizeof h ||
	    h.count == 0 || h.count > MAX_ROWS || h.pkg_sector != PKG_ISO_SECTOR) {
		sceIoClose(fd);
		return -2;
	}
	n = h.count;
	SceUID blk = sceKernelAllocPartitionMemory(2, "xidx", PSP_SMEM_High, n * sizeof(Row), 0);
	if (blk < 0) {
		sceIoClose(fd);
		return -3;
	}
	g_rows = sceKernelGetBlockHeadAddr(blk);
	sceIoLseek32(fd, h.hdr, PSP_SEEK_SET);
	i = sceIoRead(fd, g_rows, n * sizeof(Row));
	sceIoClose(fd);
	if (i != n * sizeof(Row))
		return -4;
	unsigned int sum = 0;
	for (i = 0; i < n; i++) {
		Row *r = &g_rows[i];
		sum += r->hash ^ r->sector ^ r->size;
		if ((i && r->hash <= g_rows[i - 1].hash) || r->sector > 0xFFFFF || (r->size >> 28))
			return -5;      /* must be strictly sorted, 20-bit sector, flag 0 */
	}
	if (sum != h.sum)
		return -6;
	g_count = n;
	return n;
}

int module_start(SceSize args, void *argp)
{
	(void)args; (void)argp;
	g_state = load();
	if (g_state > 0) {
		if (*HOOK_AT != HOOK_ORIG) {
			g_state = -7;           /* someone else patched the call: stay out */
			return 0;
		}
		*HOOK_AT = 0x0C000000u | (((unsigned int)xidx_tramp >> 2) & 0x03FFFFFFu); /* one aligned store */
		sceKernelDcacheWritebackRange((void *)HOOK_AT, 4);
		sceKernelIcacheInvalidateRange((void *)HOOK_AT, 4);
	}
	return 0;
}

int module_stop(SceSize args, void *argp)
{
	(void)args; (void)argp;
	if (g_state > 0) {
		*HOOK_AT = HOOK_ORIG;
		sceKernelDcacheWritebackRange((void *)HOOK_AT, 4);
		sceKernelIcacheInvalidateRange((void *)HOOK_AT, 4);
	}
	return 0;
}
