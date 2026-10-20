# P0.7 extra-index PROTOTYPE (build-only, measures code size; not on any disc). Build in the pspdev container:
#   tools/dlc/pspenv.sh make -C tools/dlc/xidx      -> xidx.prx
TARGET = xidx
OBJS = xidx.o exports.o
INCDIR =
CFLAGS = -Os -G0 -Wall -Wextra -fno-builtin -fno-pic
ASFLAGS = $(CFLAGS)
BUILD_PRX = 1
PRX_EXPORTS = exports.exp
USE_KERNEL_LIBS = 0
LDFLAGS = -nostartfiles -nostdlib
LIBS = -lpspuser -lpspmodinfo
PSPSDK = $(shell psp-config --pspsdk-path)
include $(PSPSDK)/lib/build.mak
