#!/usr/bin/env python3
"""Static evidence only: never import project modules or read external inputs."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
SUFFIX = re.compile(r'\.(?:iso|gmo|objx|gim|bin|elf|wav|scd|at3|vag|tex|png|dds|glb|gltf|mdlx|mset|mag|json|txt|dll|ttf|py)\b', re.I)
files = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
evidence = []
for rel in files:
    p = ROOT / rel
    if p.suffix not in {'.py', '.sh', '.cs', '.csproj', '.toml'} or rel.startswith('tools/repository/'):
        continue
    s = p.read_text()
    if p.suffix == '.py':
        tree = ast.parse(s)
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and '\n' not in n.value and SUFFIX.search(n.value):
                evidence.append({'consumer': rel, 'line': n.lineno, 'kind': 'literal; may be input, output, or game-internal member', 'expression': n.value})
            if isinstance(n, ast.Call) and (ast.unparse(n.func).endswith(('.read_bytes', '.read_text', '.open', '.load', '.join')) or ast.unparse(n.func) == 'open'):
                expr = ast.unparse(n)
                if len(expr) < 500:
                    evidence.append({'consumer': rel, 'line': n.lineno, 'kind': 'IO/join expression; runtime values unresolved', 'expression': expr})
    else:
        for num, line in enumerate(s.splitlines(), 1):
            if not line.lstrip().startswith(('#', '//')) and SUFFIX.search(line):
                evidence.append({'consumer': rel, 'line': num, 'kind': 'build expression', 'expression': line.strip()})
result = {'scope': 'All tracked Python/shell/C#/project/Cargo source, not execution reachability. Read with docs/REPRODUCIBILITY.md.', 'limitations': 'Superset includes outputs and ISO member names. Dynamic manifests, environment alternatives, imported omitted helpers and glTF external URIs require local expansion; no claim of complete resolved runtime dependency closure.', 'evidence': evidence}
out = json.dumps(result, indent=2) + '\n'
if len(sys.argv) == 2:
    Path(sys.argv[1]).write_text(out)
else:
    print(out, end='')
