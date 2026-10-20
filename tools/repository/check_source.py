#!/usr/bin/env python3
"""Asset-free syntax/content check. Does not import project code or touch game files."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SKIP = {'.git', 'target', 'node_modules', '.venv', '__pycache__', 'testdata', 'dumps', 'kh2_export'}
SECRET = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
errors = []
counts = {'python': 0, 'shell': 0, 'json': 0, 'files': 0}
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or set(p.relative_to(ROOT).parts) & SKIP:
        continue
    rel = str(p.relative_to(ROOT))
    counts['files'] += 1
    if p.is_symlink():
        errors.append([rel, 'symlink requires review'])
        continue
    if p.stat().st_size > 1_000_000:
        errors.append([rel, 'file exceeds 1 MB source-review threshold'])
    try:
        s = p.read_text()
    except UnicodeError:
        errors.append([rel, 'binary excluded from source export'])
        continue
    if SECRET.search(s):
        errors.append([rel, 'credential pattern; value suppressed'])
    # A generic path-shape check; no real account names appear in this tool.
    if re.search(r'(?<![\w/])/(?:home|Users|data)/[A-Za-z][A-Za-z0-9_-]*/', s):
        errors.append([rel, 'machine-specific path requires review'])
    try:
        if p.suffix == '.py':
            ast.parse(s, filename=rel)
            counts['python'] += 1
        elif p.suffix == '.sh':
            result = subprocess.run(['bash', '-n', str(p)], capture_output=True, text=True)
            if result.returncode:
                errors.append([rel, 'bash syntax failed'])
            counts['shell'] += 1
        elif p.suffix == '.json':
            json.loads(s)
            counts['json'] += 1
    except (SyntaxError, ValueError) as e:
        errors.append([rel, type(e).__name__])
print(json.dumps({'counts': counts, 'errors': errors, 'limits': 'Heuristic scan; not a legal/provenance guarantee or runtime test'}, indent=2))
sys.exit(bool(errors))
