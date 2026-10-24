# DeepSeek dual USB4: cooperative completion polling — 24 October 2026

DeepSeek's CPU completion loop was polling continuously while native USB4
needed scheduled kernel work to advance completion processing. Gufo already
uses CPU pause plus periodic yield. Applying that policy to DeepSeek recovers
most of the remaining generation slowdown. No quality or precision setting,
model, DSpark setting, GPU kernel, driver, provider or HSA runtime was changed.

## Six-request comparison

Same candidate executable, 16,127 input tokens, 256 outputs, 16,384 allocation,
DSpark enabled, normal optimized tile4/down-rgroup=4 settings, original selected
native driver, automatic GPU power and CPU performance governors. The sequence
was OFF/ON/ON/OFF/OFF/ON. The only scored switch was
`DS4_TP_ROCE_CQ_YIELD=0` or `64`. Loading is excluded; no external profiler or added host-stage diagnostic
instrumentation was enabled. The native benchmark/speculative trace logging
matches the historical commands. Both ranks use UBG3 throughout.

| Policy | Median prefill tok/s | Median generation tok/s |
|---|---:|---:|
| Continuous polling, interval 0 | 430.29 | 9.58 |
| Cooperative polling, interval 64 | 437.05 | 16.23 |

Generation improved **69.42%**. Individual controls were 9.10, 9.58 and 9.80;
candidates were 16.23, 16.33 and 15.94 tok/s. All six outputs were byte-identical
(SHA-256 `fc5c31afceefc4c4fba835c87cac5345c0c5ca9e5fc1da6ac9559376b18ad2f8`).
Reported DSpark grouping differed in one candidate run; the median includes all
six requests, with none filtered. The first pair's output and reported grouping
matched exactly and improved 9.10 → 16.23. Its reported one-token call average
fell from 116.8 to 63.9 ms. Thus the gain does not depend on generating easier
text or changing speculation settings. Raw rows, grouping and proofs are in
`measurements.csv`, `summary.json` and `transport-proof.json`.

The **older single-run Mellanox reference** is 420.98 prefill / 18.27 generation
tok/s. The new USB4 median is about **11.17% below** that generation reference,
versus about 47% below in the initial USB4 series. Mellanox NICs were removed
before this investigation; no fresh matched Mellanox A/B was possible, and its
older continuation/speculative grouping differs. The remaining 11% cannot be
assigned entirely to the physical USB4 link from this comparison.

## Why Gufo lost a smaller percentage

The engines have different execution/transport paths. Gufo already has
cooperative completion polling, GPU DMA-BUF windows and overlapping window
lifetimes. DeepSeek's original tight poll loop was particularly costly for the
software-driven USB4 completion path. The tested Gufo source's polling behavior
was verified against its retained baseline source snapshot.

Speculative work also differs by model and prompt: one measured Gufo 16K
request produced 256 tokens in 93 draft rounds, accepting 162 of 260 drafted
tokens. DeepSeek's repeated fixture mostly emitted one token per reported
round. That changes how much coordination is amortized per generated token;
it does not imply a universal interconnect penalty or a quality difference.
DSpark remains enabled in all DeepSeek tests and in the selected runtime.

## Separate diagnostics

In two diagnostic 16K/64-output requests, each with 4,560 scalar gates:

| Coordinator stage, mean microseconds | Original polling | Cooperative polling |
|---|---:|---:|
| GPU ready wait | 353.21 | 352.90 |
| TX copy/padding | 0.98 | 0.92 |
| Completion wait | 704.09 | 136.73 |
| RX copy/check | 0.85 | 0.88 |

The GPU-ready time stayed constant while the completion wait fell about 81%.
The copies themselves total less than 2 microseconds and were not the main
cause. Around 80 small gates per ordinary decode call multiply the avoided
wait into tens of milliseconds per token. These are local stage timings,
including peer waiting, not measurements of pure USB4 wire latency. The
`service_wakeup` diagnostic is queued-job age, including backlog; do not add it
to the other spans as an independent scheduler delay. Diagnostic runs are
excluded from the scored comparison; see `stage-profiles.json`.

## Selected fix and verification

[The small additive source patch](../../../tools/framework-desktop/ds4-cq-polling/README.md)
changes only empty-CQ polling. Complete status, ID/type/length, sequence/header,
timeout/cancellation and DMA lifetime checks are retained. It adds no sleep or
wire change. `0` remains the source default; the selected native-USB4 runtime
sets `64` on both hosts. All GPU computation object bytes match the previous
qualified build exactly; its SHA-256 and the unchanged HSA/provider hashes are
recorded in `summary.json`.

Actual-source helper and completion-fault tests, the Linux TP regression suite,
and two-host mixed-size payload/canary and protocol mismatch tests passed. Real
text, vision and long-prompt fixtures passed on the identical final image;
both physical cables and all four payload rails were verified with no new
transport errors. See `model-qualification.json`. Both saved launch paths now
select that image; model/quality/Gufo preferences were protected by exact hashes.
Both GPUs passed HIP_RESULT=42; native startup stays active/enabled, power stays
automatic, and test containers, QPs and host mappings were cleaned up.

A separate container-only transplant of Gufo's HSA runtime passed a tiny HIP
probe but failed a full DeepSeek request and was excluded. No host runtime
library or kernel was changed. A prepared host-credit driver candidate was
not loaded; the effective fix required no driver change.

Rollback is the preceding UBG3 image on both hosts, or the new runtime with
`DS4_TP_ROCE_CQ_YIELD=0` in both containers. Exact previous catalog/network bytes
were retained privately. Container/model binaries are not distributed here.

The later [CPU/DSpark follow-up](../2026-10-24-deepseek-cpu-dspark/README.md)
kept this runtime selected: placement added only 0.97% in its full comparison,
and the tested DSpark alternatives regressed. No additional change was promoted.
