#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Select a tested stock fabric-clock entry; restore the captured auto policy."""
import argparse
import json
import os
from pathlib import Path
import re
import comparison_power


def save(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w') as stream:
        os.chmod(temp,0o600)
        stream.write(json.dumps(value,indent=2)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def apply_profile(state, backend=comparison_power):
    before=backend.snapshot()
    indices=[]
    for device,item in before.items():
        if (item['vendor'],item['device'])!=('0x1002','0x1586'):
            raise ValueError('This profile was qualified only on the tested Strix Halo GPU')
        rows=re.findall(r'^\s*(\d+):\s*(\d+)Mhz\b',item['clocks'].get('pp_dpm_fclk',''),re.M|re.I)
        matches=[int(index) for index,mhz in rows if int(mhz)==2000]
        if len(matches)!=1:
            raise ValueError('A unique stock 2000 MHz fabric entry is required')
        indices.append(matches[0])
    if not indices or len(set(indices))!=1:
        raise ValueError('The stock fabric-clock tables differ across GPUs')
    save(state,{'before':before,'requested_fclk_mhz':2000,'stock_index':indices[0],'armed':True})
    try:
        after=backend.apply(before,'manual',fclk=indices[0])
        if any(item['mode']!='manual' for item in after.values()):
            raise RuntimeError('Manual power-mode acknowledgement differs')
    except BaseException:
        backend.restore(before)
        value=json.loads(state.read_text());value['armed']=False;save(state,value)
        raise
    return {'applied':True,'requested_fclk_mhz':2000,'stock_index':indices[0],'after':after}


def restore_profile(state, backend=comparison_power):
    if not state.exists():
        return {'restored':False,'reason':'No captured baseline; no device writes'}
    value=json.loads(state.read_text())
    if not value.get('armed'):
        return {'restored':False,'reason':'This captured baseline is already released; no device writes'}
    after=backend.restore(value['before'])
    value['armed']=False
    save(state,value)
    return {'restored':True,'after':after}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('apply','restore'))
    parser.add_argument('--state',type=Path,required=True)
    args=parser.parse_args()
    if os.geteuid()!=0:
        raise SystemExit('Applying or restoring this profile requires root')
    result=apply_profile(args.state) if args.action=='apply' else restore_profile(args.state)
    print(json.dumps(result))


if __name__=='__main__':main()
