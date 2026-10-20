# EXTRA.PRX = P0.2/P0.3 probe + P0.7 extra index (Phase 0). Build inside the pspdev container:
#   tools/dlc/pspenv.sh make -C tools/dlc/extra            -> extra.prx + extra.layout (symbol offsets)
#   tools/dlc/pspenv.sh make -C tools/dlc/extra EXTRA_THREAD=0   (no sampler thread)
TARGET = extra
OBJS = extra.o exports.o

EXTRA_THREAD ?= 1
INCDIR =
CFLAGS = -Os -G0 -Wall -Wextra -fno-builtin -fno-pic -DEXTRA_THREAD=$(EXTRA_THREAD)
ASFLAGS = $(CFLAGS)

BUILD_PRX = 1
PRX_EXPORTS = exports.exp

# no crt0/newlib: our own module_start, no main thread, only syscall stubs
USE_KERNEL_LIBS = 0
LDFLAGS = -nostartfiles -nostdlib
LIBS = -lpspuser -lpspmodinfo

EXTRA_TARGETS = extra.layout
EXTRA_CLEAN = extra.layout

PSPSDK = $(shell psp-config --pspsdk-path)
include $(PSPSDK)/lib/build.mak

# build.mak appends -lpspdebug -lpspdisplay ... to LIBS; with -nostdlib and no references they add nothing.

extra.layout: extra.prx
	psp-nm -n extra.elf | grep -E ' (module_start|module_stop|probe_tick|g_probe|g_xidx|xidx_tramp|xidx_find|module_info)$$' > $@
