# SPDX-License-Identifier: GPL-2.0-only
"""Compile the actual cooperative-poll helpers added by the DS4 overlay."""
from pathlib import Path
import re,subprocess,tempfile,shutil,unittest
ROOT=Path(__file__).resolve().parents[3]

class Ds4CqPollTests(unittest.TestCase):
    def test_configuration_yield_cadence_disabled_behavior_and_wraparound(self):
        patch=(ROOT/'tools/framework-desktop/ds4-cq-polling/ds4-cq-yield.patch').read_text()
        additions='\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))+'\n'
        selected=[]
        for name in ('tp_roce_parse_cq_yield','tp_roce_cq_pause'):
            matches=re.findall(r'^static [^\n]*\b'+name+r'\([^\n]*\)\s*\{[\s\S]*?^\}',additions,re.MULTILINE)
            self.assertEqual(len(matches),1,name)
            selected.append(matches[0])
        helpers='\n'.join(selected)+'\n'
        program=r'''#include <assert.h>
        #include <errno.h>
        #include <stdlib.h>
        #include <limits.h>
        static unsigned yielded;
        static int mock_yield(void){++yielded;return 0;}
        #define sched_yield mock_yield
        #include "helpers.h"
        int main(void){
         const char *valid[]={NULL,"0","1","2","16","64","256","4096"};
         unsigned expected[]={0,0,1,2,16,64,256,4096};
         for(unsigned i=0;i<sizeof(expected)/sizeof(*expected);i++){unsigned n=9000;assert(tp_roce_parse_cq_yield(valid[i],&n)&&n==expected[i]);unsigned spins=0;yielded=0;for(unsigned j=0;j<8192;j++)tp_roce_cq_pause(n,&spins);assert(yielded==(n?8192/n:0));assert(spins==(n?8192:0));}
         const char *bad[]={"","x","3","4097","4294967296","64x","-1","16.0","18446744073709551616"};
         for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++){unsigned n=2;assert(!tp_roce_parse_cq_yield(bad[i],&n)&&errno==EINVAL&&n==0);}
         unsigned spins=UINT_MAX;yielded=0;tp_roce_cq_pause(64,&spins);assert(spins==0&&yielded==1);
         return 0;
        }'''
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'helpers.h').write_text(helpers)
            (root/'test.c').write_text(program)
            r=subprocess.run([shutil.which('cc'),'-O2','-Wall','-Wextra','-Werror',str(root/'test.c'),'-o',str(root/'test')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(root/'test')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)

if __name__=='__main__':unittest.main()
