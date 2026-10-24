# SPDX-License-Identifier: GPL-2.0-only
"""Execute the actual optional transport helper and queue ownership wrapper."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


class Ds4LogitsTests(unittest.TestCase):
    def test_bits_padding_failures_and_transport_serialization(self):
        root=Path(__file__).resolve().parents[3]
        feature=root/'tools/framework-desktop/ds4-rdma-logits'
        patch=(feature/'ds4-rdma-logits.patch').read_text()
        target_hunks='\n'.join(line[1:] for line in patch.splitlines()
                               if (line.startswith('+') and not line.startswith('+++'))
                               or line.startswith(' '))
        def actual(name):
            match=re.search(r'^static int '+name+r'\([^\n]*[\s\S]*?^\}',target_hunks,re.MULTILINE)
            self.assertIsNotNone(match,name)
            return match[0]+'\n'
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            (folder/'logits-helper.c').write_text(actual('tp_roce_logits_transfer'))
            (folder/'gate-wrapper.c').write_text(actual('tp_linux_gate'))
            shutil.copy2(feature/'test_logits.c',folder/'test.c')
            built=subprocess.run([shutil.which('cc'),'-std=gnu11','-O2','-Wall','-Wextra','-Werror',
                                  '-pthread',str(folder/'test.c'),'-o',str(folder/'test')],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(folder/'test')],capture_output=True,text=True)
            self.assertEqual(ran.returncode,0,ran.stderr)


if __name__=='__main__':unittest.main()
