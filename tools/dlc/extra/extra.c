/*
 * EXTRA.PRX — Phase-0 module = P0.2/P0.3 probe (tools/dlc/probe/probe.c, unchanged behaviour, same g_probe layout)
 *             + P0.7 extra file index (tools/dlc/xidx/xidx.c, plus diagnostics in g_xidx).
 * notes/dlc-phase0.md "P0.7 runtime check". Disc: tools/dlc/p07_xidx_disc.py.
 * Build: tools/dlc/pspenv.sh make -C tools/dlc/extra   -> extra.prx + extra.layout (symbol offsets from module_start)
 *
 * g_xidx (address = &module_start + offset in extra.layout; &module_start is also in fixed word 0x089A8B18):
 *   +0x00 'XIDX' magic (bytes 58 49 44 58)   +0x04 state: >0 = rows loaded AND hook word written; <0 = failed step
 *         (-1 no EXTRA.IDX, -2 bad header, -3 alloc, -4 short read, -5 row not sorted/20-bit/flag0, -6 bad sum,
 *          -7 hook word was not the vanilla jal 0x08871288)
 *   +0x08 rows address   +0x0C row count   +0x10 lookups seen (xidx_find calls = non-cached game lookups)
 *   +0x14 hits   +0x18 last hit hash   +0x1C last looked-up hash   +0x20 hook word written (jal xidx_tramp)
 *   +0x24 hook address (0x08871420)   +0x28..+0x47 hits per row 0..7
 *   +0x48 word seen at 0x08871420 after the cache sync (before patching)   +0x4C guard mode: 1 = vanilla word,
 *         2 = PPSSPP JIT marker 0x68xxxxxx accepted (neighbour delay-slot words vanilla), 0 = refused (-7)
 */
#include <pspkernel.h>
#include <pspsysmem.h>
#include <pspthreadman.h>
#include <pspiofilemgr.h>
#include <psputils.h>

PSP_MODULE_INFO("SoraExtraProbe", 0, 1, 1);

#define FIXED ((volatile unsigned int *)0x089A8B14)
#define MAGIC_FIXED 0x50524F42u /* 'PROB' */
#define MAGIC_STRUCT 0x32425250u /* 'PRB2' little-endian bytes "PRB2" */

#ifndef EXTRA_THREAD
#define EXTRA_THREAD 1
#endif

struct probe {
	unsigned int magic;      /* +0x00 'PRB2' */
	unsigned int version;    /* +0x04 1 */
	unsigned int base;       /* +0x08 &module_start */
	unsigned int boot_max;   /* +0x0C MaxFree at module_start */
	unsigned int boot_total; /* +0x10 TotalFree at module_start */
	unsigned int ticks;      /* +0x14 sampler loop count (250 ms each) */
	unsigned int cur_max;    /* +0x18 latest MaxFree */
	unsigned int cur_total;  /* +0x1C latest TotalFree */
	unsigned int min_max;    /* +0x20 smallest MaxFree seen since boot */
	unsigned int min_total;  /* +0x24 smallest TotalFree seen since boot */
	int thid;                /* +0x28 sampler thread id (<0 = create failed, 0 = disabled) */
	unsigned int tick_calls; /* +0x2C probe_tick() calls */
	unsigned int last_where; /* +0x30 probe_tick() argument */
	unsigned int last_max;   /* +0x34 MaxFree at last probe_tick */
	unsigned int last_total; /* +0x38 TotalFree at last probe_tick */
	unsigned int stop;       /* +0x3C set by module_stop */
};

struct probe g_probe __attribute__((aligned(16)));

#define HOOK_AT   ((volatile unsigned int *)0x08871420)
#define HOOK_ORIG 0x0E21C4A2u           /* jal 0x08871288 */
#define HOOK_LINE 0x08871400u           /* 64-byte line(s) around the hook */
#define PKG_ISO_SECTOR 186624u
#define MAX_ROWS  16384u

typedef struct { unsigned int hash, sector, size; } Row;
typedef struct {
	char magic[4];                  /* "XIDX" */
	unsigned short version, hdr;    /* 1, 32 */
	unsigned int count, flags, pkg_sector, sum, r0, r1;
} Hdr;

struct xidx_stat {
	unsigned int magic, state;
	Row *rows;
	unsigned int count, lookups, hits, last_hit, last_hash, hook_word, hook_at;
	unsigned int row_hits[8];
	unsigned int guard_seen, guard_mode;
};
struct xidx_stat g_xidx __attribute__((aligned(16)));
#define g_rows (g_xidx.rows)
#define g_count (g_xidx.count)

Row *xidx_find(unsigned int h)
{
	int lo = 0, hi = (int)g_count - 1;
	g_xidx.lookups++;
	g_xidx.last_hash = h;
	while (lo <= hi) {
		int mid = (lo + hi) >> 1;
		unsigned int v = g_rows[mid].hash;
		if (v == h) {
			g_xidx.hits++;
			g_xidx.last_hit = h;
			if (mid < 8)
				g_xidx.row_hits[mid]++;
			return &g_rows[mid];
		}
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
	g_count = 0;
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
	return n;
}

/* Flush + invalidate the hook's cache lines. On PPSSPP this also drops JIT blocks there, which puts the real
 * instruction back where the JIT had left its 0x68xxxxxx "emuhack" block marker (seen in p07 runtime: state -7). */
static void code_sync(void)
{
	sceKernelDcacheWritebackInvalidateRange((void *)HOOK_LINE, 64);
	sceKernelIcacheInvalidateRange((void *)HOOK_LINE, 64);
}

static int hook_ok(void)
{
	unsigned int w;
	code_sync();
	w = *HOOK_AT;
	g_xidx.guard_seen = w;
	if (w == HOOK_ORIG)
		return 1;
	/* still a JIT block marker (opcode 0x1A): accept only if the two delay-slot words around it (never block
	 * entries, so never markers) are the vanilla ones */
	if ((w >> 26) == 0x1A && HOOK_AT[-3] == 0x34060050u && HOOK_AT[1] == 0x02202025u)
		return 2;
	return 0;
}

static void xidx_start(void)
{
	int st = load();
	g_xidx.hook_at = (unsigned int)HOOK_AT;
	if (st > 0) {
		int mode = hook_ok();
		g_xidx.guard_mode = (unsigned int)mode;
		if (!mode) {
			st = -7;        /* someone else patched the call: stay out */
		} else {
			unsigned int w = 0x0C000000u | (((unsigned int)xidx_tramp >> 2) & 0x03FFFFFFu);
			g_count = (unsigned int)st;   /* rows visible before the hook goes live */
			*HOOK_AT = w;                 /* one aligned store */
			code_sync();
			g_xidx.hook_word = *HOOK_AT;  /* read back after the sync */
		}
	}
	g_xidx.state = (unsigned int)st;
	g_xidx.magic = 0x58444958u;          /* "XIDX" */
}

static void xidx_stop(void)
{
	if ((int)g_xidx.state > 0) {
		*HOOK_AT = HOOK_ORIG;
		code_sync();
	}
}

int module_start(SceSize args, void *argp);

static void sample(unsigned int *mx, unsigned int *tot)
{
	*mx = (unsigned int)sceKernelMaxFreeMemSize();
	*tot = (unsigned int)sceKernelTotalFreeMemSize();
	if (*mx < g_probe.min_max)
		g_probe.min_max = *mx;
	if (*tot < g_probe.min_total)
		g_probe.min_total = *tot;
}

void probe_tick(unsigned int where)
{
	unsigned int mx, tot;
	sample(&mx, &tot);
	g_probe.last_where = where;
	g_probe.last_max = mx;
	g_probe.last_total = tot;
	g_probe.tick_calls++;
}

#if EXTRA_THREAD
static int sampler(SceSize args, void *argp)
{
	(void)args;
	(void)argp;
	while (!g_probe.stop) {
		unsigned int mx, tot;
		sample(&mx, &tot);
		g_probe.cur_max = mx;
		g_probe.cur_total = tot;
		g_probe.ticks++;
		sceKernelDelayThread(250000);
	}
	return 0;
}
#endif

int module_start(SceSize args, void *argp)
{
	unsigned int mx, tot;
	(void)args;
	(void)argp;
	mx = (unsigned int)sceKernelMaxFreeMemSize();
	tot = (unsigned int)sceKernelTotalFreeMemSize();

	xidx_start();                   /* P0.7: load EXTRA.IDX + hook (free-memory numbers above are before it) */

	g_probe.version = 1;
	g_probe.base = (unsigned int)&module_start;
	g_probe.boot_max = g_probe.cur_max = g_probe.min_max = mx;
	g_probe.boot_total = g_probe.cur_total = g_probe.min_total = tot;
	g_probe.magic = MAGIC_STRUCT;

	FIXED[1] = (unsigned int)&module_start;
	FIXED[2] = mx;
	FIXED[3] = tot;
	FIXED[0] = MAGIC_FIXED;

#if EXTRA_THREAD
	/* low priority (0x6F; game threads are higher), 2 KB stack, user thread */
	g_probe.thid = sceKernelCreateThread("sora_probe", sampler, 0x6F, 0x800, PSP_THREAD_ATTR_USER, NULL);
	if (g_probe.thid >= 0)
		sceKernelStartThread(g_probe.thid, 0, NULL);
#endif
	return 0;
}

int module_stop(SceSize args, void *argp)
{
	(void)args;
	(void)argp;
	g_probe.stop = 1;
	xidx_stop();
	return 0;
}
