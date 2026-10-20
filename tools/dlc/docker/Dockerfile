# Small build box for the pspdev toolchain (host is Ubuntu 22.04; pspdev v20261001 needs glibc >= 2.38).
# The toolchain itself lives on the host at the PSPDEV_HOST directory and is mounted read-only at /usr/local/pspdev.
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends make cmake python3 ca-certificates file \
    libmpc3 libmpfr6 libgmp10 libisl23 zlib1g libzstd1 libreadline8 && rm -rf /var/lib/apt/lists/*
ENV PSPDEV=/usr/local/pspdev PATH=/usr/local/pspdev/bin:$PATH
WORKDIR /work
