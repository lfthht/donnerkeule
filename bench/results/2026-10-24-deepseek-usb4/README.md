# DeepSeek 1017 over dual USB4 — 24 October 2026

The quality setting was already correct: no `--quality` flag, normal MXFP4 tile4
and down-rgroup=4 settings, no bounded SWA replay. The original executables on
both hosts matched the previous Mellanox runtime. Gufo settings were unchanged.

The original five-request USB4 series measured 427.98 prefill / 9.72 generation
tokens/s. The historical Mellanox reference was 420.98 / 18.27 from **one** native
16K request. NICs were removed before this follow-up; it is not a new Mellanox
A/B. Different continuations make these historical series unsuitable for
pairing with individual new requests.

## Matched engine transport comparison

Six native requests, OFF/ON/ON/OFF/OFF/ON, concurrency one. Same executable,
model files, 16,127 input tokens, 256 outputs, 16,384 context allocation, DSpark,
original selected Donnerkeule driver, automatic GPU power and CPU performance
governors. Model loading is excluded. No external tracer or added host-stage profiling
was used; native benchmark/speculative logging matched the historical commands.
The only switch is the optional UBG3 control transport. All six decoded outputs
and speculative-work distributions match exactly. Both physical cables and all
four rails carry actual payload; no new transport errors were observed.

| Path | Median prefill tok/s | Median generation tok/s |
|---|---:|---:|
| Original TCP gate header + USB4 payload | 429.20 | 9.02 |
| UBG3 packed validated gates | 430.57 | 9.61 |

Generation improved **6.54%** in this small matched comparison. Individual
controls were 9.32, 9.02 and 8.54; candidates were 9.54, 9.61 and 9.63 tok/s.
The three adjacent paired gains were +2.36%, +6.54% and +12.76%. This is a
**partial improvement**, not recovery of Mellanox speed or a claim that 9.61
beats the different earlier 9.72-token/s series. See `measurements.csv`,
`summary.json` and `transport-proof.json`.

## Findings and retained change

DeepSeek uses 16 MiB of registered host staging; Gufo uses GPU DMA-BUF windows.
The original DeepSeek path exchanges and validates a complete 40-byte control
header over ordinary 1 Gbit/s LAN at each gate, then transfers the model payload
over USB4. In a separate profiled 16K/64-output request, 4,560 scalar gates
averaged 703.65 microseconds: 176.46 in the TCP header and 524.91 in RDMA/staging.
Those spans include peer waiting; they do not measure pure USB4 wire latency.
Profiling points to this synchronization/staging path; the experiment does not
assign all remaining time to LAN. The full historical gap remains unresolved.

[The optional engine overlay](../../../tools/framework-desktop/ds4-packed-gates/README.md)
places the full validated header and small payload in a fixed aligned RC
message, with the next receive posted ahead. It preserves completion, sequence,
length, epoch and payload guards, leaves GPU math unchanged, and rejects
protocol mismatches. The GPU object hash matched the qualified base exactly.
Large transfers keep bounded windows and TCP readiness barriers.

The first no-barrier prototype was rejected after a receive-readiness failure.
The retained receive-ahead version passed actual-source fault tests and the
existing Linux protocol regression suite, then two-host mixed-size payload,
canary, repeated gate and protocol mismatch tests. Real text, vision and long
fixtures passed on both cables. See `model-qualification.json`.

The identical final image was selected on both servers, preserving the saved
model/quality/Gufo preferences. The original kernel driver remains selected;
no experimental kernel module or power policy was promoted. Rollback is the
previous image, or the same new executable with
`DS4_TP_ROCE_PACKED_GATES=0` on both ranks. Image/model binaries are not hosted
in this repository.

Other trials did not establish a reliable gain: reducing the direct-host DMA
threshold, enabling host receive credits, and pinning the stock fabric clock.
A stock high-power GPU mode measured 9.48 versus automatic controls 9.50/9.41
on the original 16K/128-output case and was restored. No quality or clock change
was needed. Invalid early probes after sequential driver restoration revealed
stale remote generation identities; both hosts were reconnected together and
reciprocity was checked before subsequent tests.

A [later completion-polling follow-up](../2026-10-24-deepseek-cq-polling/README.md)
recovered most of the remaining slowdown with DSpark and GPU math unchanged.
