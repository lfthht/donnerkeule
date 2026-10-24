# Optional page-aligned DeepSeek gate slots

This overlay reduces transport padding without changing numerical operations.
It applies after the packed-gate, cooperative-polling and RC-logits overlays.
The adapter source is hash checked before and after patching:

```sh
python3 tools/framework-desktop/ds4-gate-alignment/apply.py /path/to/ds4/source
python3 tools/framework-desktop/ds4-gate-alignment/apply.py /path/to/ds4/source --apply
```

Rebuild the host TP code against the same numerical object and runtime. Set
`DS4_TP_ROCE_GATE_ALIGN=4096` identically on both ranks, with
`DS4_TP_ROCE_PACKED_GATES=1`, `DS4_TP_ROCE_LOGITS=1` and the qualified CQ interval
8. The qualified kernel must also have `dmabuf_host_direct=1`,
`dmabuf_host_credits=1` and `dmabuf_host_direct_min_bytes=4096` on both hosts.
The [runtime recipe](Containerfile.runtime) packages the five qualified host
executables into the preceding runtime; it does not distribute those files.

The unset adapter default stays 65,536 bytes. Only the exact values 4096, 8192,
16384, 32768 and 65536 are accepted. Smaller units require packed gates and RC
logits. The bootstrap capability includes the selected unit; an older or
differently configured peer fails negotiation before model payload DMA.

The logical gate limit remains 65,536 minus the complete 40-byte header. Wire
length rounds the header and payload up to the negotiated unit. A scalar
20,480-byte gate therefore sends 24,576 bytes instead of 65,536. Float bits,
header validation, completion checks, timeouts, cancellation, receive ownership
and the larger-window fallback are preserved. Padding is still zeroed. The
kernel parameter defaults to 65,536; invalid thresholds disable direct-host
eligibility, and short/unaligned or unsupported requests retain staging. All
existing MR, device, access and lifetime checks remain.

Portable tests execute the actual adapter helpers from the patch, covering all
five units, boundary lengths, payload bits, guards, every header byte, bad or
duplicate/stale completions, timeouts and cancellation. Separate tests execute
the real kernel eligibility/map helpers. The two-node hardware checks include
mixed gate/full-float score lengths, tails, canaries and peer mismatch failure.

The [qualified comparison](../../../bench/results/2026-10-24-deepseek-small-gates/README.md)
records the measured gain, output variation, accuracy checks and Gufo regression.
This is a joint runtime/kernel profile: changing just the runtime while keeping
a 64 KiB direct-host threshold would stage the shorter packets and does not
reproduce the measured path.

For rollback, stop both ranks, restore the preceding runtime, and restore the
64 KiB kernel threshold (or preceding module) on both hosts together. Keep the
existing stock-clock service and unrelated model preferences. Do not mix gate
units across ranks.
