#!/usr/bin/env python3
"""Validate the measured DS4 transport source and optionally apply UBG3."""
import argparse,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=pathlib.Path);p.add_argument('--apply',action='store_true');a=p.parse_args();here=pathlib.Path(__file__).resolve().parent;manifest=json.loads((here/'source-manifest.json').read_text());root=a.source.resolve()
for name,expected in manifest['files'].items():
 actual=hashlib.sha256((root/name).read_bytes()).hexdigest()
 if actual!=expected['before_sha256']:raise SystemExit('Source differs from the measured pre-patch input: '+name)
patch=str(here/'ds4-ubg3.patch');subprocess.run(['git','apply','--check',patch],cwd=root,check=True)
if a.apply:
 subprocess.run(['git','apply',patch],cwd=root,check=True)
 for name,expected in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected['after_sha256']
 print('UBG3 applied. Keep both ranks on matching binaries and protocol settings.')
else:print('Measured source hashes and patch check pass; no source files changed.')
