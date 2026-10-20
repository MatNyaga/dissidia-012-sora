# EXTRA.PRX — production engine module v1 (P1.4). Build inside the pspdev container:
#   tools/dlc/pspenv.sh make -C tools/pkg/engine/extra      -> extra.prx + extra.layout (symbol offsets)
#   python3 -I tools/pkg/engine/make_manifest.py            -> engine.json + patches/engine-loader.json
TARGET = extra
OBJS = extra.o exports.o

INCDIR =
CFLAGS = -Os -G0 -Wall -Wextra -fno-builtin -fno-pic
ASFLAGS = $(CFLAGS)

BUILD_PRX = 1
PRX_EXPORTS = exports.exp

# no crt0/newlib: our own module_start, no thread, only syscall stubs
USE_KERNEL_LIBS = 0
LDFLAGS = -nostartfiles -nostdlib
LIBS = -lpspuser -lpspmodinfo

EXTRA_TARGETS = extra.layout
EXTRA_CLEAN = extra.layout

PSPSDK = $(shell psp-config --pspsdk-path)
include $(PSPSDK)/lib/build.mak

extra.layout: extra.prx
	psp-nm -n extra.elf | grep -E ' (module_start|module_stop|module_info|g_extra|g_api|xidx_tramp|xidx_find|extra_get_api|extra_find_row|extra_feature)$$' > $@
	psp-size -A extra.elf | grep -E '^\.(text|rodata|data|bss|sceStub\.text|lib\.ent|lib\.stub|rodata\.sceModuleInfo)' >> $@
