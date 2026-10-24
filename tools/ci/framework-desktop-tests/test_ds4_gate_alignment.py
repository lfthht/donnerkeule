# SPDX-License-Identifier: GPL-2.0-only
"""Execute qualified gate helpers with malformed completions and payload guards."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
FEATURE=ROOT/'tools/framework-desktop/ds4-gate-alignment'

def qualified_header():
    patch=(FEATURE/'ds4-gate-alignment.patch').read_text()
    return '\n'.join(line[1:] for line in patch.splitlines()
                     if line.startswith(' ') or (line.startswith('+') and not line.startswith('+++')))+'\n'

def actual(source,name):
    m=re.search(r'^static [^\n]*\b'+name+r'\([^;{]*\{[\s\S]*?^\}',source,re.MULTILINE)
    if not m:raise AssertionError(name)
    return m[0]+'\n'

class Ds4GateAlignmentTests(unittest.TestCase):
    def execute(self,files):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            for name,text in files.items():(p/name).write_text(text)
            r=subprocess.run([shutil.which('cc'),'-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(p/'test')],capture_output=True,text=True,timeout=10)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_payload_bits_padding_completion_faults_canaries_timeout_and_cancel(self):
        source=qualified_header()
        helpers=''.join(actual(source,n) for n in ('tp_roce_cq_pause','tp_roce_prepare','tp_roce_prearm','tp_roce_packed_gate'))
        self.execute({'test.c':(FEATURE/'test_packed_gate.c').read_text(),
                      'test-adapter.h':(FEATURE/'test-adapter-types.h').read_text()+'\n'+helpers})

    def test_strict_units_prerequisites_and_peer_capabilities(self):
        source=qualified_header()
        start=source.index('    const char *alignment=getenv(')
        end=source.index('    if(!tp_roce_parse_cq_yield(',start)
        block=source[start:end]
        cap=re.search(r'mine\.reserved=([^;]+);',source)[1]
        program=r'''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
struct ds4_tp_roce { uint32_t gate_alignment; bool logits,packed_gates; };
#define tp_set_err(...) ((void)0)
static int parse(struct ds4_tp_roce *r) { BODY return 1;fail:return 0; }
static uint32_t capability(struct ds4_tp_roce *r) { return CAPABILITY; }
int main(void) {
 const char *valid[]={"4096","8192","16384","32768","65536"};
 uint32_t codes[5];
 for(unsigned i=0;i<5;i++) {
  setenv("DS4_TP_ROCE_GATE_ALIGN",valid[i],1);
  for(unsigned flags=0;flags<4;flags++) {
   struct ds4_tp_roce r={.packed_gates=!!(flags&1),.logits=!!(flags&2)};
   assert(parse(&r)==(i==4 || flags==3));
   if(flags==3) {assert(r.gate_alignment==(4096u<<i));codes[i]=capability(&r);}
  }
 }
 for(unsigned i=0;i<5;i++)for(unsigned j=0;j<i;j++)assert(codes[i]!=codes[j]);
 assert(codes[0]==0x55424751u && codes[4]==0x55424734u);
 const char *bad[]={"","0","4095","4097","8193","65537","-4096"," 4096","4096 ","0x1000","4096x"};
 for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++) {
  setenv("DS4_TP_ROCE_GATE_ALIGN",bad[i],1);struct ds4_tp_roce r={.logits=true,.packed_gates=true};assert(!parse(&r));
 }
 unsetenv("DS4_TP_ROCE_GATE_ALIGN");
 struct ds4_tp_roce r={0};assert(parse(&r)&&r.gate_alignment==65536&&capability(&r)==0);
 r.packed_gates=true;assert(capability(&r)==0x55424733u);
 return 0;
}'''.replace('BODY',block).replace('CAPABILITY',cap)
        self.execute({'test.c':program})

if __name__=='__main__':unittest.main()
