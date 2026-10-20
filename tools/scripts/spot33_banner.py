"""Put #33's name banner ("Sora", 128x32, made with name_banner.py from the game's own letters) into every menu
pack that has p_sev120_name (Aerith's old banner): Customization and Shop. In place (same size), via pkg_put.py.

  python3 -I spot33_banner.py ISO BANNER.png
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, package_entry, read_at  # noqa: E402
from gim_put import put  # noqa: E402
from name_banner import banners  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402

PACKS = ['menu/EN/menu_lpk_customize_gim_0.bin', 'menu/EN/menu_lpk_shop_gim_0.bin']
NAME = 'p_sev120_name'


def main():
    iso, png = sys.argv[1:3]
    img = Image.open(png)
    for path in PACKS:
        with open(iso, 'rb') as f:
            info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
            off, size = package_entry(info, path)
            d = bytearray(read_at(f, PACKAGE_ISO_SECTOR * SECTOR + off, size))
        at = banners(bytes(d))[NAME]
        gsize = int.from_bytes(d[at + 0x14:at + 0x18], 'little') + 0x10
        d[at:at + gsize] = put(bytes(d[at:at + gsize]), img)
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, os.path.basename(path))
            open(p, 'wb').write(bytes(d))
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                               check=True, capture_output=True, text=True)
            print(r.stdout.strip())


if __name__ == '__main__':
    main()
