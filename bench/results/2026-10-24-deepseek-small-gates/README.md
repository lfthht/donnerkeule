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

## Nonselected receive-ahead limit follow-up

A separate six-request off/on/on/off/off/on comparison tested the existing
`dmabuf_credit_max=65536` parameter against its 1,048,576-byte default, with the
new selected gate profile identical in both arms. The hypothesis was to avoid
large speculative receive buffers when gate and score sizes alternate. Median
prefill was 444.05 vs 445.72 tok/s, and generation **17.92 vs 17.88 tok/s
(-0.22%)**. The shared-output group gives 17.92 vs 17.885 tok/s. Five outputs
were canonical; the final candidate produced the previously observed alternate
variant. Both cables carried payload in every request; all ten preceding
transport integrity cases passed. This provides no evidence of a useful gain.
The default 1 MiB limit is restored and retained. See
[raw measurements](credit-limit-followup.csv) and
[summary/work counts](credit-limit-followup.json).

## Nonselected empty reciprocal score-message follow-up

A transport-only prototype sent full vocabulary scores in the required
direction and replaced the reverse zero-filled payload with empty SENDs. Exact
zero-byte receive completions still drained all prepared WQEs, and private score
copy-out preceded receive prearming. A distinct bootstrap capability rejected
mixed peers. The complete GPU object and model settings were unchanged.

All five two-node integrity cases passed, including mixed score/gate sizes,
float bits, tails, guards, peer mismatch and malformed frame/count failure.
Portable tests exercised the actual helpers with 1..4 WQEs, eager next DMA,
completion errors, stale/duplicate IDs, timeouts and shared-queue serialization.
Both candidate logs confirmed the feature active. Nevertheless, six alternating
full requests measured **17.93 vs 17.88 generation tok/s (-0.28%)**, and 445.97
vs 445.03 prefill tok/s. The canonical-output subgroup gives 17.935 vs 17.88;
the first control produced the known alternate variant. Both cables carried
payload in every request. The prototype establishes no useful performance gain
and is not selected or recommended. The qualified runtime is restored. See
[raw measurements](empty-ack-followup.csv) and
[summary and prototype provenance](empty-ack-followup.json).

## Further CPU scheduling screens

Eight single full-request screens compared CQ intervals 4/2/1 with the current
8, per-process nice values 5/10 with 0, and the driver's progress interval 10
microseconds with 25. The same selected image, stock clock, model, DSpark policy
and numerical binaries were used throughout. Both drivers were reloaded before
every request; global parameters were restored afterward. Actual priorities of
all model threads were checked on both hosts. All outputs were canonical and
both cables carried payload.

| Setting | Prefill tok/s | Generation tok/s | Score transfers |
|---|---:|---:|---:|
| Control A: CQ8, nice0, 25 us | 442.06 | 17.85 | 236 |
| CQ4 | 444.87 | 18.31 | 230 |
| CQ2 | 446.20 | 17.92 | 236 |
| CQ1 | 445.70 | 18.01 | 236 |
| Nice5 | 442.08 | 17.99 | 236 |
| Nice10 | 443.13 | 17.85 | 236 |
| Driver progress 10 us | 444.02 | 18.12 | 230 |
| Control B: CQ8, nice0, 25 us | 445.19 | 18.06 | 236 |

The isolated 18.31 sample exceeds the historical Mellanox figure, but it also
has a different speculative-work pattern. Identical text does not prove
identical draft work. No parity or optimization claim is established by that
single sample. Lower model process priority does not establish a gain. See
[raw screens](scheduling-followup.csv) and [work, priority and cable evidence](scheduling-followup.json).

## Nonselected page-sized reciprocal score-message follow-up

A second, separately negotiated prototype used 4096-byte zero acknowledgements
instead of empty reciprocal SENDs, retaining the ordinary direct-DMA path. Five
hardware integrity cases and portable helper/fault tests passed; GPU numerical
code and all quality settings stayed unchanged. Six alternating full requests
measured **17.92 vs 17.97 generation tok/s (+0.28%)**, with overlapping samples,
identical output and 236 score transfers each. This does not establish a useful
generation gain. Prefill medians were 440.56 vs 445.89 tok/s, but later unchanged
controls reached 445.19. A durable prefill gain has not been confirmed. The
prototype stays unselected and the qualified runtime is restored. See
[measurements](page-ack-followup.csv) and [work/prototype provenance](page-ack-followup.json).

## Later baseline abort and retry correction

The first control of a later CQ4 repeat comparison aborted on both ranks with
an I/O completion failure at layer 2, position 16186, before the candidate was
tried. It is excluded from timing results. The saved profile recovered, both
GPUs passed health checks, and no GPU fault or QP1 kernel messages were found.
An error-instrumented repeat then passed. A controlled receiver-delay test
separately reproduced an overly short RNR retry budget; the subsequently
qualified [retry correction](../2026-10-24-deepseek-rnr-retry/README.md) is now
selected on both hosts. The original event did not record its precise WC
status, so that specific cause is not claimed as proven.

## Completed CQ4 repeat qualification

After the receiver-ready correction, six fresh off/on/on/off/off/on full requests
compared CQ8 with CQ4 on the same retry-corrected image, kernel, stock clock and
CPU placement. Median prefill was **443.73 vs 445.26 tok/s (+0.34%)** and generation
**17.92 vs 17.97 tok/s (+0.28%)**, with overlapping samples. Every output was
canonical. Both cables carried payload and all requests completed without a
transport error. This does not reproduce the isolated 18.31 result. CQ8 is retained.

All three controls had 236 score transfers and 68,001,280 score bytes. Only one
candidate had exactly matching available checkpoint counts, final score-transfer
count and score bytes; it measured 18.02 tok/s. Other candidates differed in the
final score work, despite identical text. The work-matched subgroup is too small
to establish an improvement. No Mellanox parity claim is made. See
[measurements](cq4-repeat.csv), [work groups and medians](cq4-repeat.json) and
[cable proofs](cq4-repeat-proof.json).

## Final DSpark policy screens

The retry-corrected runtime was also tested with explicit confidence thresholds
0.5, 0.8 and 0.95, plus pure target decoding without the draft support model.
An explicit threshold selects the engine's fixed-threshold proposal policy,
retaining coarse adaptive backoff instead of its default cost scheduler. It
changes which drafts are proposed, never the target verification criterion.
The target-only case removes both `--dspark` and `--mtp-model`; the initial
setup attempt left the support-model argument and was rejected before loading,
then corrected. It is not included as a performance result.

All scored requests use the same target, precision, numerical binaries, 16,127
input tokens, 256 outputs, context allocation 16,384, CQ8, nice0, progress 25 us,
stock fabric request and both cables. The driver is reloaded before each.

| Policy | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Adaptive control A | 446.03 | 17.90 |
| Target only | 441.73 | 17.94 |
| Fixed confidence 0.5 | 445.77 | 17.74 |
| Fixed confidence 0.8 | 444.20 | 17.94 |
| Fixed confidence 0.95 | 446.37 | 17.86 |
| Adaptive control B | 446.47 | 17.87 |

No single alternative establishes a repeatable generation improvement against
the observed control variation. The 0.8 and 0.95 outputs also differ from the
canonical response; the latter is the previously observed alternate variant.
Both controls, target-only and threshold 0.5 are canonical. All transfer/quality
settings are unchanged and all requests complete with both-cable payload.
Adaptive DSpark is retained. See [measurements](dspark-final-followup.csv) and
[work counts and cable proofs](dspark-final-followup.json).

No further reliable generation gain was found in the tested CPU placement,
priority, CQ cadence, driver progress, credit limit, score acknowledgement or
DSpark policy families. The verified smaller-gate improvement and receiver-ready
retry correction remain selected. The historical single Mellanox generation
reference is still not matched by a repeat-qualified new profile.
