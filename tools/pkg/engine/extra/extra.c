/*
 * EXTRA.PRX — production engine module, v1.0 (Phase 1, P1.4). docs/ENGINE.md has the plain-English story.
 *
 * What it does at boot (module_start, called once by the EBOOT loader stub, see patches/engine-loader.json):
 *   1. sets up the status block g_extra (signature 'XTRA' + self pointer; found by tools/pkg/engine/find_status.py)
 *   2. loads disc0:/PSP_GAME/USRDIR/DATA/EXTRA.IDX (our extra file index, format in docs/ENGINE.md) and checks it
 *      (header, strictly sorted hashes, 20-bit sector, install flag 0, checksum, every row inside PACKAGE.BIN)
 *   3. collision check: every row whose hash is also in the disc's own PACKAGE_INFO.BIN must be flagged
 *      "override" in the index's override bitmap; unflagged ones are dropped (counted in g_extra.rejected)
 *   4. if rows are left: RAM-patches ONE game word, 0x08871420 `jal 0x08871288` -> `jal xidx_tramp`, behind the
 *      JIT-safe guard from P0.7 (so our rows are searched first, then the game's PACKAGE_INFO)
 * Anything wrong -> no hook, the game runs as vanilla, the reason is in g_extra.state. It never writes any other
 * game word (Phase 0's fixed words 0x089A8B14.. are NOT used any more), creates no thread, never frees the rows
 * (the game keeps row pointers for the whole session).
 * Phase 2 API skeleton: g_api ('XAPI') = registry pointer (NULL) + find_row + feature (always 0). No behaviour.
 *
 * Build: tools/dlc/pspenv.sh make -C tools/pkg/engine/extra   -> extra.prx + extra.layout
 *        then python3 -I tools/pkg/engine/make_manifest.py   (engine.json + patches/engine-loader.json)
 */
#ifdef HOST_TEST
#include "../test/host_mock.h"      /* host unit test: tools/pkg/engine/test/run_host_test.sh */
#else
#include <pspkernel.h>
#include <pspsysmem.h>
#include <pspiofilemgr.h>
#include <psputils.h>

PSP_MODULE_INFO("ExtraEngine", 0, 1, 0);
#define HOOK_AT   ((volatile unsigned int *)0x08871420)
#endif

#define ENGINE_VERSION 0x00010000u      /* 1.0.0 = major << 16 | minor << 8 | patch */
#define STATUS_LAYOUT  1
#define MAGIC_STATUS   0x41525458u      /* bytes "XTRA" */
#define MAGIC_TAIL     (~MAGIC_STATUS)  /* last word of the block */
#define MAGIC_API      0x49504158u      /* bytes "XAPI" */
#define MAGIC_IDX      0x58444958u      /* bytes "XIDX" */

#define HOOK_ORIG 0x0E21C4A2u           /* jal 0x08871288 (name hash) in lookup FUN_088713e4 */
#define HOOK_LINE 0x08871400u           /* 64-byte line around the hook */
#define PKG_ISO_SECTOR 186624u          /* PACKAGE.BIN's ISO sector (sanity field of EXTRA.IDX) */
#define MAX_ROWS  16384u
#define INFO_MAX  11253u                /* game's PACKAGE_INFO buffer 0x20F8C B = 16 + 12 * 11253 */
#define CHUNK_ROWS 340u                 /* PACKAGE_INFO scan: 340 rows = 4080 B per read */

#define IDX_PATH  "disc0:/PSP_GAME/USRDIR/DATA/EXTRA.IDX"
#define INFO_PATH "disc0:/PSP_GAME/USRDIR/DATA/PACKAGE_INFO.BIN"
#define PKG_PATH  "disc0:/PSP_GAME/USRDIR/DATA/PACKAGE.BIN"

/* g_extra.state */
enum {
	ST_STARTING = 0,        /* module_start running (or died in it: see .step) */
	ST_NO_ROWS = 1,         /* index valid, but no row left (empty, or all rejected) -> no hook */
	ST_LIVE = 2,            /* rows loaded + hook word written */
	ST_NO_INDEX = -1,       /* EXTRA.IDX not on the disc -> vanilla (normal for an engine-only disc) */
	ST_BAD_HEADER = -2,     /* magic/version/size/count/flags/PACKAGE.BIN sector */
	ST_ALLOC = -3,          /* not enough memory for the rows */
	ST_SHORT_READ = -4,     /* file shorter than the header says */
	ST_BAD_ROW = -5,        /* not strictly sorted / sector > 20 bits / install flag != 0 / size 0 */
	ST_BAD_SUM = -6,        /* checksum */
	ST_HOOK_TAKEN = -7,     /* 0x08871420 is not the vanilla jal (someone else patched it) */
	ST_OUT_OF_PKG = -8,     /* a row points past the end of PACKAGE.BIN */
	ST_BAD_OVR = -9,        /* override bitmap offset/size invalid */
};
/* g_extra.warn bits */
#define W_INFO_SKIPPED  1u      /* PACKAGE_INFO.BIN unreadable -> collision check skipped */
#define W_PKG_SKIPPED   2u      /* PACKAGE.BIN size unknown -> bounds check skipped */
#define W_JIT_MARKER    4u      /* hook guard accepted a PPSSPP JIT block marker (neighbour words vanilla) */
#define W_HOOK_READBACK 8u      /* hook word read back != the word we wrote (JIT marker over it is fine) */

typedef struct { unsigned int hash, sector, size; } Row;
typedef struct {
	unsigned int magic;             /* "XIDX" */
	unsigned short version, hdr;    /* 1, >= 32 */
	unsigned int count, flags, pkg_sector, sum, ovr_off, r1;
} Hdr;
#define IDX_F_OVERRIDES 1u          /* flags bit 0: override bitmap at ovr_off */

/* ---- status block: layout v1, 0x80 bytes, frozen (append-only in later layouts) ---- */
struct extra_status {
	unsigned int magic;             /* +0x00 "XTRA" */
	unsigned short layout, size;    /* +0x04 1, +0x06 0x80 */
	unsigned int self;              /* +0x08 address of this block (search signature: magic + self) */
	unsigned int base;              /* +0x0C &module_start */
	unsigned int version;           /* +0x10 ENGINE_VERSION */
	int state;                      /* +0x14 ST_* */
	unsigned int warn;              /* +0x18 W_* */
	Row *rows;                      /* +0x1C live rows (sorted) */
	unsigned int count;             /* +0x20 live rows */
	unsigned int file_rows;         /* +0x24 rows in EXTRA.IDX */
	unsigned int rejected;          /* +0x28 rows dropped by the collision check */
	unsigned int overrides;         /* +0x2C live rows that shadow a disc PACKAGE_INFO row (flagged) */
	unsigned int lookups;           /* +0x30 xidx_find calls (non-cached game lookups) */
	unsigned int hits;              /* +0x34 */
	unsigned int last_hit;          /* +0x38 hash */
	unsigned int last_hash;         /* +0x3C last looked-up hash */
	unsigned int hook_at;           /* +0x40 0x08871420 */
	unsigned int hook_word;         /* +0x44 word read back after the patch (0 = no hook) */
	unsigned int guard_seen;        /* +0x48 word at the hook after the cache sync, before patching */
	unsigned int guard_mode;        /* +0x4C 1 vanilla, 2 JIT marker accepted, 0 refused / not reached */
	unsigned int boot_max;          /* +0x50 MaxFreeMemSize at module_start */
	unsigned int boot_total;        /* +0x54 TotalFreeMemSize at module_start */
	void *api;                      /* +0x58 &g_api (Phase 2) */
	unsigned int info_rows;         /* +0x5C disc PACKAGE_INFO rows scanned by the collision check */
	unsigned int first_rejected;    /* +0x60 hash of the first dropped row */
	unsigned int pkg_size;          /* +0x64 PACKAGE.BIN size seen (bounds check) */
	unsigned int row_hits[4];       /* +0x68 hits on live rows 0..3 */
	unsigned int step;              /* +0x78 last module_start step reached (1..8) */
	unsigned int tail;              /* +0x7C ~"XTRA" */
};
struct extra_status g_extra __attribute__((aligned(16)));

/* ---- Phase 2 API skeleton (v1: no behaviour) ---- */
const Row *extra_find_row(unsigned int hash);
int extra_feature(unsigned int id);
struct extra_api {
	unsigned int magic;             /* +0x00 "XAPI" */
	unsigned short version, size;   /* +0x04 1, sizeof */
	void *registry;                 /* +0x08 Phase 2: owner registry table (owner_tables.json ids) — NULL in v1 */
	unsigned int registry_count;    /* +0x0C 0 */
	const Row *(*find_row)(unsigned int hash);  /* +0x10 read-only lookup in our index (no counters) */
	int (*feature)(unsigned int id);            /* +0x14 feature switch; v1 always 0 (= vanilla behaviour) */
	struct extra_status *status;    /* +0x18 &g_extra */
	unsigned int reserved[5];       /* +0x1C */
};
struct extra_api g_api = {MAGIC_API, 1, sizeof(struct extra_api), 0, 0, extra_find_row, extra_feature, &g_extra,
			  {0, 0, 0, 0, 0}};

struct extra_api *extra_get_api(void) { return &g_api; }
int extra_feature(unsigned int id) { (void)id; return 0; }

static int find_index(unsigned int h)
{
	int lo = 0, hi = (int)g_extra.count - 1;
	while (lo <= hi) {
		int mid = (lo + hi) >> 1;
		unsigned int v = g_extra.rows[mid].hash;
		if (v == h)
			return mid;
		if (v < h)
			lo = mid + 1;
		else
			hi = mid - 1;
	}
	return -1;
}

const Row *extra_find_row(unsigned int hash)
{
	int i = find_index(hash);
	return i < 0 ? 0 : &g_extra.rows[i];
}

/* called by xidx_tramp on every non-cached game lookup */
Row *xidx_find(unsigned int h)
{
	int i;
	g_extra.lookups++;
	g_extra.last_hash = h;
	i = find_index(h);
	if (i < 0)
		return 0;
	g_extra.hits++;
	g_extra.last_hit = h;
	if (i < 4)
		g_extra.row_hits[i]++;
	return &g_extra.rows[i];
}

#ifndef HOST_TEST
/* Replaces the hash call at 0x08871420; a0 = name. Absolute game addresses via lui/ori (no relocations).
 * hit -> s2 = our row, return to the game's hit path 0x088714BC; miss -> return the hash to 0x08871428. */
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
	"  move  $s2, $v0\n"
	"  lui   $ra, 0x0887\n"
	"  ori   $ra, $ra, 0x14BC\n"
	"1:\n"
	"  lw    $v0, 4($sp)\n"
	"  jr    $ra\n"
	"  addiu $sp, $sp, 16\n"
	".set pop\n");
extern void xidx_tramp(void);
#endif

static int read_full(SceUID fd, void *buf, unsigned int n)
{
	return sceIoRead(fd, buf, n) == (int)n;
}

/* Load + check EXTRA.IDX. Returns the row count (>= 0) or ST_*. On success g_extra.rows/count are set and *ovr
 * holds a temporary block with the override bitmap (or < 0 if none). */
static int load_index(SceUID *ovr_blk, unsigned int **ovr)
{
	Hdr h;
	unsigned int i, n, sum = 0, words = 0;
	SceUID fd, blk;

	*ovr_blk = -1;
	*ovr = 0;
	fd = sceIoOpen(IDX_PATH, PSP_O_RDONLY, 0);
	if (fd < 0)
		return ST_NO_INDEX;
	g_extra.step = 2;
	if (!read_full(fd, &h, sizeof h) || h.magic != MAGIC_IDX || h.version != 1 || h.hdr < sizeof h ||
	    (h.hdr & 3) || h.count > MAX_ROWS || h.pkg_sector != PKG_ISO_SECTOR || (h.flags & ~IDX_F_OVERRIDES)) {
		sceIoClose(fd);
		return ST_BAD_HEADER;
	}
	n = h.count;
	g_extra.file_rows = n;
	if (h.flags & IDX_F_OVERRIDES) {
		words = (n + 31) >> 5;
		if (!n || (h.ovr_off & 3) || h.ovr_off < h.hdr + n * sizeof(Row)) {
			sceIoClose(fd);
			return ST_BAD_OVR;
		}
	}
	if (!n) {
		sceIoClose(fd);
		return h.sum == 0 ? 0 : ST_BAD_SUM;
	}
	blk = sceKernelAllocPartitionMemory(2, "xtra_rows", PSP_SMEM_High, n * sizeof(Row), 0);
	if (blk < 0) {
		sceIoClose(fd);
		return ST_ALLOC;
	}
	g_extra.rows = sceKernelGetBlockHeadAddr(blk);
	g_extra.step = 3;
	if (sceIoLseek32(fd, h.hdr, PSP_SEEK_SET) != (int)h.hdr || !read_full(fd, g_extra.rows, n * sizeof(Row))) {
		sceIoClose(fd);
		sceKernelFreePartitionMemory(blk);
		g_extra.rows = 0;
		return ST_SHORT_READ;
	}
	if (words) {
		*ovr_blk = sceKernelAllocPartitionMemory(2, "xtra_tmp", PSP_SMEM_Low, words * 4, 0);
		if (*ovr_blk < 0) {
			sceIoClose(fd);
			sceKernelFreePartitionMemory(blk);
			g_extra.rows = 0;
			return ST_ALLOC;
		}
		*ovr = sceKernelGetBlockHeadAddr(*ovr_blk);
		if (sceIoLseek32(fd, h.ovr_off, PSP_SEEK_SET) != (int)h.ovr_off || !read_full(fd, *ovr, words * 4)) {
			sceIoClose(fd);
			return ST_SHORT_READ;   /* caller frees both blocks */
		}
		for (i = 0; i < words; i++)
			sum += (*ovr)[i];
		if (n & 31)
			if ((*ovr)[words - 1] >> (n & 31))
				return sceIoClose(fd), ST_BAD_OVR;  /* bits past the last row must be 0 */
	}
	sceIoClose(fd);
	for (i = 0; i < n; i++) {
		Row *r = &g_extra.rows[i];
		sum += r->hash ^ r->sector ^ r->size;
		if ((i && r->hash <= g_extra.rows[i - 1].hash) || r->sector > 0xFFFFFu || (r->size >> 28) || !r->size)
			return ST_BAD_ROW;
	}
	if (sum != h.sum)
		return ST_BAD_SUM;
	return (int)n;
}

/* every row must lie inside PACKAGE.BIN (the game reads all rows through the PACKAGE.BIN handle) */
static int check_bounds(unsigned int n)
{
	SceIoStat st;
	unsigned int i;
	if (sceIoGetstat(PKG_PATH, &st) < 0 || st.st_size <= 0 || st.st_size > 0x7FFFFFFFLL) {
		g_extra.warn |= W_PKG_SKIPPED;
		return 0;
	}
	g_extra.pkg_size = (unsigned int)st.st_size;
	for (i = 0; i < n; i++) {
		Row *r = &g_extra.rows[i];
		if ((r->sector << 11) + r->size > g_extra.pkg_size)     /* sector < 2^20, size < 2^28: no overflow */
			return ST_OUT_OF_PKG;
	}
	return 0;
}

/* rows that shadow a row of the disc's own PACKAGE_INFO.BIN need their override bit; others are dropped */
static void check_collisions(const unsigned int *ovr)
{
	unsigned int head[4], left, i, k, n = g_extra.count;
	SceUID fd = sceIoOpen(INFO_PATH, PSP_O_RDONLY, 0), blk;
	Row *buf;
	if (fd < 0) {
		g_extra.warn |= W_INFO_SKIPPED;
		return;
	}
	blk = sceKernelAllocPartitionMemory(2, "xtra_tmp2", PSP_SMEM_Low, CHUNK_ROWS * sizeof(Row), 0);
	if (blk < 0 || !read_full(fd, head, sizeof head) || head[1] != 0x6B636170u /* "pack" */ ||
	    head[2] > INFO_MAX) {
		if (blk >= 0)
			sceKernelFreePartitionMemory(blk);
		sceIoClose(fd);
		g_extra.warn |= W_INFO_SKIPPED;
		return;
	}
	buf = sceKernelGetBlockHeadAddr(blk);
	for (left = head[2]; left; left -= k) {
		k = left < CHUNK_ROWS ? left : CHUNK_ROWS;
		if (!read_full(fd, buf, k * sizeof(Row))) {
			g_extra.warn |= W_INFO_SKIPPED;     /* rows marked so far stay marked: still safe */
			break;
		}
		g_extra.info_rows += k;
		for (i = 0; i < k; i++) {
			int j = find_index(buf[i].hash);
			if (j < 0)
				continue;
			if (ovr && (ovr[j >> 5] >> (j & 31) & 1))
				g_extra.overrides++;
			else
				g_extra.rows[j].size |= 0x80000000u;    /* mark: drop (bit 31 is 0 in valid rows) */
		}
	}
	sceKernelFreePartitionMemory(blk);
	sceIoClose(fd);
	for (i = k = 0; i < n; i++) {             /* compact, order kept -> still sorted */
		if (g_extra.rows[i].size & 0x80000000u) {
			if (!g_extra.rejected++)
				g_extra.first_rejected = g_extra.rows[i].hash;
			continue;
		}
		g_extra.rows[k++] = g_extra.rows[i];
	}
	g_extra.count = k;
}

/* Flush + invalidate the hook's cache line. On PPSSPP this also drops JIT blocks there, which puts the real
 * instruction back where the JIT had left its 0x68xxxxxx "emuhack" block marker (P0.7 runtime #1). */
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
	g_extra.guard_seen = w;
	if (w == HOOK_ORIG)
		return 1;
	/* still a JIT block marker (opcode 0x1A): accept only if the two delay-slot words around it (never block
	 * entries, so never markers) are the vanilla ones */
	if ((w >> 26) == 0x1A && HOOK_AT[-3] == 0x34060050u && HOOK_AT[1] == 0x02202025u)
		return 2;
	return 0;
}

static unsigned int hook_word(void)
{
	return 0x0C000000u | (((unsigned int)xidx_tramp >> 2) & 0x03FFFFFFu);
}

static int engine_start(void)
{
	SceUID ovr_blk;
	unsigned int *ovr;
	int st, mode;

	st = load_index(&ovr_blk, &ovr);
	if (st <= 0) {
		if (ovr_blk >= 0)
			sceKernelFreePartitionMemory(ovr_blk);
		/* rows block (if any) is kept: freeing it is not worth the code; it is at most 192 KB and only on a
		 * broken disc. */
		g_extra.count = 0;
		return st == 0 ? ST_NO_ROWS : st;
	}
	g_extra.count = (unsigned int)st;
	g_extra.step = 4;
	st = check_bounds(g_extra.count);
	g_extra.step = 5;
	if (st == 0) {
		check_collisions(ovr);
		g_extra.step = 6;
	}
	if (ovr_blk >= 0)
		sceKernelFreePartitionMemory(ovr_blk);
	if (st < 0) {
		g_extra.count = 0;
		return st;
	}
	if (!g_extra.count)
		return ST_NO_ROWS;
	mode = hook_ok();
	g_extra.guard_mode = (unsigned int)mode;
	g_extra.step = 7;
	if (!mode) {
		g_extra.count = 0;
		return ST_HOOK_TAKEN;   /* someone else patched the call: stay out */
	}
	if (mode == 2)
		g_extra.warn |= W_JIT_MARKER;
	*HOOK_AT = hook_word();         /* one aligned store; rows + count are visible before it */
	code_sync();
	g_extra.hook_word = *HOOK_AT;
	if (g_extra.hook_word != hook_word())
		g_extra.warn |= W_HOOK_READBACK;
	return ST_LIVE;
}

int module_start(SceSize args, void *argp)
{
	(void)args;
	(void)argp;
	g_extra.layout = STATUS_LAYOUT;
	g_extra.size = sizeof g_extra;
	g_extra.self = (unsigned int)&g_extra;
	g_extra.base = (unsigned int)&module_start;
	g_extra.version = ENGINE_VERSION;
	g_extra.state = ST_STARTING;
	g_extra.hook_at = (unsigned int)HOOK_AT;
	g_extra.api = &g_api;
	g_extra.tail = MAGIC_TAIL;
	g_extra.step = 1;
	g_extra.magic = MAGIC_STATUS;       /* signature visible from here on */
	g_extra.boot_max = (unsigned int)sceKernelMaxFreeMemSize();
	g_extra.boot_total = (unsigned int)sceKernelTotalFreeMemSize();
	g_extra.state = engine_start();
	g_extra.step = 8;
	return 0;                           /* always stay resident (status block + rows live here) */
}

int module_stop(SceSize args, void *argp)
{
	(void)args;
	(void)argp;
	if (g_extra.state == ST_LIVE && *HOOK_AT == hook_word()) {
		*HOOK_AT = HOOK_ORIG;
		code_sync();
	}
	return 0;
}
