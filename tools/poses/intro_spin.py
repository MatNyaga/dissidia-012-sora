"""Sora's intro (_900A) = Codex "B — slow flourish" (Mat 2026-10-15: "add the intro file sent by chat gpt slow
flourish"). Thin wrapper so the build needs no env var: tools/poses/intro_codex.py with VARIANT=spin.
Alternatives kept: intro_codex.py VARIANT=arc (shoulder sweep), intro_a.py (Claude v5), intro_opts.py."""
import importlib.util
import os

os.environ['VARIANT'] = 'spin'
_spec = importlib.util.spec_from_file_location('intro_codex', os.path.join(os.path.dirname(__file__), 'intro_codex.py'))
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
LOOP = getattr(_m, 'LOOP', 6)
build = _m.build
