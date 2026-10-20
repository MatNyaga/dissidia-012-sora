/*
 * EXTRA.PRX — Phase-0 probe module (P0.2 "our code loads at boot" + P0.3 "free RAM").
 * docs/PHASE0-DLC-PLAN.md, notes/dlc-phase0.md (P0.2/P0.3 build).
 *
 * Loaded and started once at boot by the patched EBOOT (tools/dlc/p02_module_disc.py):
 *   FUN_0893354c (boot init) -> jal STUB 0x0886EF60 -> loader 0x0886EEBC(mode 2 = one try) -> sceKernelStartModule.
 *
 * module_start (returns 0, no main thread):
 *   fixed words (EBOOT dead function, never executed, unreferenced — notes/ex-equipment.md row 0x089a8b14):
 *     0x089A8B14 = 0x50524F42 'PROB' (written LAST, so magic present => the other 3 are valid)
 *     0x089A8B18 = &module_start      (module load address of the entry point)
 *     0x089A8B1C = sceKernelMaxFreeMemSize()   at module start (largest free block, bytes)
 *     0x089A8B20 = sceKernelTotalFreeMemSize() at module start (all free user memory, bytes)
 *   g_probe (module .bss/.data, address = &module_start + PROBE_OFS printed by the build) gets the same plus
 *   a low-priority sampler thread that refreshes free memory every 250 ms (keeps the minimum seen) and counts
 *   ticks — a rising tick count in a battle proves the module is still resident and running there.
 * probe_tick(where) (exported, not hooked yet): a later battle hook can jal here to log a sample at a known point.
 *
 * Build: tools/dlc/pspenv.sh make -C tools/dlc/probe   (EXTRA_THREAD=0 to build without the sampler thread)
 */
#include <pspkernel.h>
#include <pspsysmem.h>
#include <pspthreadman.h>

PSP_MODULE_INFO("SoraExtraProbe", 0, 1, 0);

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
	return 0;
}
