# DeepSeek page-aligned gate slots — 24 October 2026

A joint runtime/kernel profile improved median generation from **17.63 to
18.10 tok/s (+2.67%)** in six alternating full requests. Prefill was essentially
unchanged, **445.50 vs 445.46 tok/s**. Restricting the comparison to the shared
output variant gives **17.705 vs 18.10 tok/s (+2.23%)**. All three candidate
generation samples exceeded all three controls. The profile is saved on both
hosts after hardware integrity, known-answer and Gufo regression checks.

The change removes transport padding. A 20,480-byte scalar gate with its complete
40-byte header now travels in a 24,576-byte slot, rather than a 65,536-byte slot.
The accompanying opt-in kernel threshold lets those smaller page-aligned host
buffers keep direct DMA and receive-ahead credits. The model, quantization,
DSpark policy, target verification, float payloads, GPU numerical object,
provider and HSA library are unchanged. No quality control is relaxed.

## Matched full requests

Two Framework Desktop Strix Halo Max+395 hosts, each with 128 GB unified memory;
two physical 40 Gb/s USB4 cables, four native rails and one pooled QP. Both arms
use CQ yield interval 8 and the same requested stock FCLK entry 2000 MHz. This
is a requested stock table entry, not a measured live clock frequency. CPU
placement remains unrestricted. The previous CPU and DSpark screens did not
establish an additional improvement worth selecting.

Same Q2 target, matching DSpark support model, tile4/down-rgroup4, 16,127 uncached
input tokens, 256 generated tokens, 16,384 allocation and concurrency one.
Loading is excluded; native timing and speculative logging remain unchanged.
No extra stage profiler is enabled. The native driver is reloaded on both hosts
before every request, with both unloaded before either is loaded and reciprocal
controller domains checked before inference.

| Run | Profile | Prefill tok/s | Generation tok/s |
|---|---|---:|---:|
| 0 | Control, 64 KiB slots | 446.46 | 17.63 |
| 1 | Candidate, 4 KiB alignment | 445.46 | 18.18 |
| 2 | Candidate, 4 KiB alignment | 445.99 | 17.83 |
| 3 | Control, 64 KiB slots | 443.71 | 17.78 |
| 4 | Control, 64 KiB slots | 445.50 | 17.63 |
| 5 | Candidate, 4 KiB alignment | 441.22 | 18.10 |
| **Control median** | | **445.50** | **17.63** |
| **Candidate median** | | **445.46** | **18.10** |

The first control produced SHA-256
`2d923d794b5d891864051f9e1e6f826ac9fb4ef2e93eeb0ef36944aebe7ad260`.
The other five requests produced the canonical output
`674754a8c7c6d8483f492302becda923d3bb1f279e31dfd9bdc0faff429787f6`.
The shared-output comparison therefore contains two controls and three candidates.
Their available speculative-work checkpoint counts match through call 224.
Identical text alone does not establish identical draft work; the differing
control also has different available work counts. This known variation is
retained in [output parity](deepseek-output-parity.json), rather than excluded
from the overall median. Full final speculative totals are not inferred from
intermediate checkpoints.

See [deepseek.csv](deepseek.csv), [summary.json](summary.json) and
[per-request cable proofs](deepseek-proof.json). Native counters show payload
movement on all four rails in both physical controller domains, on both ranks,
and receive-credit reuse in every candidate. Zero counters are omitted except
for explicitly retained error deltas.

Compared with the **historical single Mellanox request** at 420.98 prefill /
18.27 generation tok/s, this candidate median is **+5.81% / -0.93%**. The Mellanox
NICs have been removed, so this is not a fresh matched interconnect A/B. It is
one continuation fixture with three samples per profile, not a general model
speed guarantee. The historical generation target has not yet been reached.

## Gufo regression

Four alternating requests use the unchanged Gufo image, 16,384 uncached input
tokens, 256 output tokens, 262,144 context capacity, MTP ceiling 7, thinking off,
concurrency one and an excluded eight-token warmup. Only the native kernel
changes; the same stock-clock service and model settings are used throughout.

| Profile | Median prefill tok/s | Median generation tok/s |
|---|---:|---:|
| Previous driver | 2075.83 | 59.05 |
| Candidate driver | 2074.22 | 59.02 |

Differences below 0.1% do not establish a speed change. All outputs match, with
226 proposed and 150 accepted draft tokens in each request. Both cables carry
payload. See [gufo.csv](gufo.csv), [work/output parity](gufo-output-parity.json),
[summary](gufo-summary.json) and [cable proofs](gufo-proof.json).

## Integrity, quality and saved state

Ten two-node transport cases pass under the current CQ8/stock-clock profile:
all five gate alignments, RC-logits disabled on both peers, old/new logits peer
mismatch, different alignment mismatch, malformed gate header and invalid score
count. Successful cases compare full float bits, guards, tails, mixed gate and
score traffic, repeated windows and large bounded transfers. Failure cases
verify bounded failure without exposing invalid output. See
[hardware-integrity.json](hardware-integrity.json). Hardware tests use the exact
qualified source; portable fault tests execute actual adapter helpers.

Eleven known-answer cases pass on both the preceding selected image and the
final candidate image: arithmetic, factorial, ordering logic, factual answers,
translation, JSON, code evaluation, vision and a 15,788-token record prompt.
Actual payload hashes and answers match for every pair. JSON is parsed
structurally. See [accuracy.json](accuracy.json) and the
[fixture definitions](quality-fixtures.json). These are targeted regressions,
not a broad accuracy evaluation. Quality preservation also rests on unchanged
numerical code, model precision and transport payload bits.

The final saved image is
`842787d6dc6e34f0cf6f76816aa901217643e76738dbbd8801fdc7c02fa28eaf`.
Both hosts have the same image and five executable hashes. It copies the
qualified host binaries into the previous runtime
`55d3551404f5129dba6cf91671ff2f085bf6079b40e49e0ae255cb958f236ab2`
and adds the 4096 alignment default. The complete GPU object stays
`0064b49c10b3437464e15004f0fe3e610cc44a8f4689f5393a2bf951d9840dfe`.
The selected kernel is SHA-256
`2a3d4bea358ba71ae90615111ff50cb4e2927ca9a99f456f0ae41dca3047357d`,
srcversion `6034C2FBE3EF9C733BA8B4C`. The previous control kernel is retained
in [runtime-manifest.json](runtime-manifest.json) and source provenance.

The [overlay and rollback instructions](../../../tools/framework-desktop/ds4-gate-alignment/README.md)
record the paired settings and unchanged defaults. Kernel source changes only
`verbs_mr.c` relative to the selected receive-credit driver. Invalid thresholds
fall back from direct-host eligibility; original access/bounds/lifetime checks
and GPU DMA-BUF eligibility stay intact. The adapter requires identical peer
alignment during bootstrap, before payload DMA.

Gufo text, vision and long-prompt checks pass. Saved quality/model/Gufo preferences
are unchanged. Both saved launch roles resolve the selected image and native
HCA. Both startup services are enabled; stock-clock policy remains manual as
before. Both GPUs pass HIP_RESULT=42; owned model containers, QPs and active
host mappings are zero. Nodebool services and backend/Compute health pass.
Promotion recovery transactions are disarmed after verification; no scoped new
GPU fault or QP1/open-port messages are found. The complete smoke suite and all
15 Framework tests pass. See [validation.json](validation.json).

Raw commands, private recovery journals and full logs remain local. Credentials,
private paths, models and engine/module binaries are not distributed.
