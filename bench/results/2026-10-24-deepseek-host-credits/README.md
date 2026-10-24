# DeepSeek aligned-host receive credits — 24 October 2026

Extending the existing receive-credit mechanism to eligible pinned host MRs
improved DeepSeek generation from **17.00 to 17.54 tok/s (+3.18%)** in six
alternating full requests. All outputs match; prefill changes by -0.12%.
The qualified driver is selected on both Framework hosts. The score-routing
runtime, model, GPU object, precision, DSpark policy, HSA runtime and userspace
provider are unchanged.

## Full matched comparison

Two Framework Desktop Strix Halo hosts, two 40 Gb/s USB4 cables, four native
rails, 16,127 uncached input tokens, 256 generated tokens, 16,384 allocation,
concurrency one. Loading is excluded. Q2 target and the same matching DSpark
model, tile4/down-rgroup4, normal math and target verification remain unchanged.
The optional `--quality` flag remains false in both arms, matching the preceding
qualified baseline. No quality or precision setting is reduced.

Both arms use the exact same full-precision score-routing image
`df68ad19223d5413fc1dc00cd9cd7fc4512f8e87f1126a560992997eee87404a`,
UBG4, 64 KiB packed layer slots and `DS4_TP_ROCE_CQ_YIELD=64`.
Controls reload the actual previously selected driver, SHA-256
`0c62484437a192e83d8a8a9cb1ab3169bc9a44ec6feb4b016166cf0677407764`.
Candidates load the qualified receive-credit driver with
`dmabuf_host_credits=1`. Both hosts unload before either loads; live domain
reciprocity and rail selection are checked before each request.

| Run | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Control 0 | 437.52 | 16.92 |
| Candidate 1 | 436.39 | 17.54 |
| Candidate 2 | 432.65 | 17.37 |
| Control 3 | 436.93 | 17.01 |
| Control 4 | 435.04 | 17.00 |
| Candidate 5 | 436.72 | 17.61 |
| **Control median** | **436.93** | **17.00** |
| **Candidate median** | **436.39** | **17.54** |

Every candidate generation sample exceeds every control sample. This is one
matched continuation fixture, not a broad speed or accuracy guarantee. Native
speculative trace and prefill logging match the preceding benchmark; no added
stage profiler, diagnostic DSpark logging or CPU-affinity shim is active.
See [deepseek.csv](deepseek.csv) and [summary.json](summary.json).

The preceding [score-routing change](../2026-10-24-deepseek-rdma-logits/README.md)
separately measured 16.23 → 16.99 tok/s. The fresh 17.00 control above is the
proper denominator for this driver experiment. The historical Mellanox
reference is 420.98 prefill / 18.27 generation tok/s: current candidate medians
are +3.66% / -4.00% relative to that old single run. The NICs were removed, so
this is not a fresh Mellanox A/B, and the generation target is still open.

## Mechanism and bounds

The driver already pre-armed receive descriptors for eligible GPU SEND streams.
DeepSeek's host transport uses ordinary pinned, page-aligned MRs. An opt-in
extension now allows those MRs to use the same existing credit protocol.
Repeated layer transfers can consume a ready receive window without another
receiver-preparation exchange. The scored candidate requests require nonzero
credit reuse on both ranks; [deepseek-proof.json](deepseek-proof.json) records
those counters together with traffic on both physical cables and all four rails.

This changes two kernel files. `tbv_ibdev_dmabuf_peek` retains RC/QP state,
endpoint, PD, lkey, local-write permission, receive length, MR bounds and page
alignment checks. Host pages must also pass the existing direct-host eligibility
check. The minimum remains **64 KiB**, page size 4 KiB, maximum MR size 256 MiB.
Receive ownership, PSN/WQE validation, finish callbacks and cancellation retain
the existing lifetime rules. Staged, short and unaligned host transfers are not
speculatively armed. GPU eligibility and the wire format remain unchanged.

`dmabuf_host_credits` defaults to false. Reproduce the tested configuration by
loading the same qualified module on both hosts with `dmabuf_host_credits=1`,
`dmabuf_host_direct=1` and the preceding native profile parameters. Stop model
work before changing modules. Roll back with the preceding capability-corrected
module and its original parameters; retain matching installed and selected
module copies and startup metadata. No provider replacement or model rebuild
is required. The deployment keeps private recovery copies of those files.

## Quality and validation

The entire DeepSeek GPU object is unchanged, SHA-256
`0064b49c10b3437464e15004f0fe3e610cc44a8f4689f5393a2bf951d9840dfe`.
All six canonical decoded output hashes are
`674754a8c7c6d8483f492302becda923d3bb1f279e31dfd9bdc0faff429787f6`.
No quantization, sampler, proposal policy or target acceptance rule changes.
See [output-parity.json](output-parity.json) and
[runtime-manifest.json](runtime-manifest.json).

Hardware verification passed 32 host/GPU SEND and WRITE cases, both directions,
with canaries, tails, two rounds and MR/QP recreation. Mixed full-float scores
and layer gates, arbitrary score bits including NaNs, multi-window payloads,
mode mismatch, invalid count and wrong-frame rejection also pass under the
candidate driver. See [hardware-integrity.json](hardware-integrity.json).
An initial test-controller assertion incorrectly required credit reuse in an
alternating-size sequence. All hardware payload checks had passed, with credits
safely returned/cancelled. The controller was corrected to check grant activity;
scored real-model requests separately require actual reuse on both ranks.
The previous driver was restored after that interrupted controller run.

Automated tests execute the actual kernel peek function with host opt-in and
GPU cases, PD/access rejection, bounds, allocation failure, unavailable or
closing queues, endpoint mismatch, overflow and reference cleanup. The full
receive-state suite now runs for both GPU and direct-host buffers, covering
credit cancellation, retries, cached results, disconnect and ownership.
The complete protocol, provider, DMA wait/posting, lifetime, profiling and
Framework test suite passes.

Final real Gufo and DeepSeek text, vision and long-prompt fixtures pass after
installation. Saved model, quality and Gufo preferences are preserved. Both
saved launch paths, module integrity metadata and automatic startup are checked.
HIP_RESULT=42, automatic GPU power, zero remaining containers/QPs/host mappings,
and Nodebool's services and backend/Compute health pass. Trial recovery leases
are disarmed. See [validation.json](validation.json).

## Gufo regression check

Four alternating requests use the unchanged Gufo image, 16,384 uncached prompt
tokens, 256 output tokens, 262,144 context capacity, MTP ceiling 7, thinking off,
concurrency one and an excluded eight-token warmup. Both arms retain automatic
GPU power and unrestricted CPU affinity. Loading is excluded.

| Run | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Control 0 | 2071.18 | 57.50 |
| Candidate 1 | 2063.28 | 58.81 |
| Candidate 2 | 2046.81 | 59.06 |
| Control 3 | 2070.73 | 58.71 |
| **Control median** | **2070.95** | **58.10** |
| **Candidate median** | **2055.05** | **58.94** |

Prefill is -0.77%, generation +1.44% in this small check. No substantial
regression is observed; this does not establish a separate Gufo speedup. All
four outputs match and each proposes 226 draft tokens, accepting 150.
[gufo.csv](gufo.csv), [gufo-output-parity.json](gufo-output-parity.json) and
[gufo-proof.json](gufo-proof.json) retain the request and both-cable evidence.

## Other screens retained without promotion

All rates below use 128 output tokens and must be compared with their own
controls. No additional host policy or smaller-slot runtime is selected.

| CPU wake-up limit | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Existing 99 microseconds, A | 436.84 | 16.85 |
| Temporary 10 microseconds | 437.06 | 16.81 |
| Temporary 0 microseconds | 414.02 | 16.80 |
| Existing 99 microseconds, B | 433.72 | 16.74 |

All outputs match. The temporary requests use file-descriptor lifetime bounds;
99 microseconds is verified before and after. Lower wake-up latency does not
improve generation, and forcing 0 regresses prefill.

A separate smaller-slot runtime used page-aligned wire units with a kernel
supporting a lower direct-host threshold. Its 64 KiB controls measured 17.39
and 17.24 tok/s, 4 KiB alignment 17.53, 16 KiB alignment 17.37. All outputs match;
ten mixed-payload/protocol hardware cases and actual-adapter fault tests pass.
The small apparent difference has not been repeat-qualified, so that runtime
and lower threshold are not selected or represented by the source change here.
The retained kernel minimum remains 64 KiB.

Eleven earlier handshake screens found no repeatable gain from host spin/pause
budgets or reduction block size; the fast initial pause-8 sample did not repeat.
Their GPU executable/constant sections were checked separately from changed
non-executable build metadata. [screens.json](screens.json) retains these
screen rates, CPU latency trials, smaller-slot trials and the four preliminary
host-credit screens. The [earlier CPU/DSpark comparison](../2026-10-24-deepseek-cpu-dspark/README.md)
retains the rejected affinity, IRQ-placement and aggressive-drafting policies.

Raw logs, commands and recovery journals remain local. Credentials, private
recovery paths, model files and container/module binaries are not distributed.
