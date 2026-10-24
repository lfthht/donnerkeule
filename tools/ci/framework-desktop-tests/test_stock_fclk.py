# SPDX-License-Identifier: GPL-2.0-only
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
FEATURE=ROOT/'tools/framework-desktop/stock-fclk'
sys.path.insert(0,str(FEATURE))
spec=importlib.util.spec_from_file_location('stock_fclk_tested',FEATURE/'stock_fclk.py')
profile=importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class Backend:
    def __init__(self):
        self.value={'gpu':{'vendor':'0x1002','device':'0x1586','mode':'auto',
                          'clocks':{'pp_dpm_fclk':'0: 400Mhz\n7: 2000Mhz\n'}}}
        self.calls=[]
        self.fail=False
    def snapshot(self):
        if any(v['mode']!='auto' for v in self.value.values()):raise RuntimeError('Expected auto baseline')
        return deepcopy(self.value)
    def apply(self,before,mode,fclk=None):
        self.calls.append(('apply',mode,fclk))
        for v in self.value.values():v['mode']=mode
        if self.fail:raise RuntimeError('Injected write failure')
        return deepcopy(self.value)
    def restore(self,before):
        self.calls.append(('restore',))
        self.value=deepcopy(before)
        return deepcopy(self.value)


class StockFabricTests(unittest.TestCase):
    def test_capture_select_restore_and_release_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'state.json';b=Backend()
            profile.apply_profile(state,b)
            self.assertEqual(b.calls,[('apply','manual',7)])
            self.assertTrue(json.loads(state.read_text())['armed'])
            self.assertEqual(state.stat().st_mode&0o777,0o600)
            profile.restore_profile(state,b)
            self.assertEqual(b.value['gpu']['mode'],'auto')
            self.assertFalse(json.loads(state.read_text())['armed'])
            profile.restore_profile(state,b)
            self.assertEqual(b.calls,[('apply','manual',7),('restore',)])
            b.value['gpu']['mode']='high'
            with self.assertRaises(RuntimeError):profile.apply_profile(state,b)
            profile.restore_profile(state,b)
            self.assertEqual(b.value['gpu']['mode'],'high')
    def test_prevalidate_all_devices_and_stock_frequency_before_writes(self):
        for kind in ('missing','ambiguous','wrong_device','different_index'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                state=Path(directory)/'state.json';b=Backend()
                if kind=='missing':b.value['gpu']['clocks']['pp_dpm_fclk']='0: 400Mhz\n'
                if kind=='ambiguous':b.value['gpu']['clocks']['pp_dpm_fclk']+='8: 2000Mhz\n'
                if kind=='wrong_device':b.value['gpu']['device']='0xffff'
                if kind=='different_index':
                    b.value['gpu2']=deepcopy(b.value['gpu'])
                    b.value['gpu2']['clocks']['pp_dpm_fclk']='6: 2000Mhz\n'
                with self.assertRaises(ValueError):profile.apply_profile(state,b)
                self.assertEqual(b.calls,[])
                self.assertFalse(state.exists())
    def test_write_failure_recovers_and_absent_state_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'state.json';b=Backend();b.fail=True
            self.assertFalse(profile.restore_profile(state,b)['restored'])
            with self.assertRaises(RuntimeError):profile.apply_profile(state,b)
            self.assertEqual(b.calls,[('apply','manual',7),('restore',)])
            self.assertEqual(b.value['gpu']['mode'],'auto')
            self.assertFalse(json.loads(state.read_text())['armed'])


if __name__=='__main__':unittest.main()
