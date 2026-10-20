# Linux build/test box for the Tauri app (keeps WebKit/GTK dev packages off the host).
#   docker build -t sorapatch-build tools/installer/app
#   see docs/INSTALLER-TECH.md "Build" for the run command (host rustup + cargo mounted read-only).
FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential pkg-config ca-certificates curl file \
      libwebkit2gtk-4.1-dev libgtk-3-dev libsoup-3.0-dev libjavascriptcoregtk-4.1-dev librsvg2-dev libxdo-dev libssl-dev \
      xvfb xauth x11-apps imagemagick dbus-x11 fonts-noto-core \
 && rm -rf /var/lib/apt/lists/*
