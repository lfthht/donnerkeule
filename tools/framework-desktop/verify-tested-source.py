#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check that the fork's driver/provider sources match the measured candidate."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
manifest = json.loads((root/'docs/framework-desktop-tested-source.json').read_text())
expected = dict(manifest['source_sha256'])
expected['userspace/usb4_rdma/usb4_rdma.c'] = manifest['provider_source_sha256']
changed = []
for name, digest in expected.items():
    file = root/name
    actual = hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None
    if actual != digest:
        changed.append(name)
if changed:
    raise SystemExit('Source differs from the recorded measurement: '+', '.join(changed))
print(f'PASS: {len(expected)} source files match the measured driver/provider.')
