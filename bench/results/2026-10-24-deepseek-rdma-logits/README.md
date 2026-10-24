# DeepSeek full-precision scores over native USB4 — 24 October 2026

Moving complete vocabulary-score vectors from the TCP control socket to native
RC improved median DeepSeek generation from **16.23 to 16.99 tok/s (+4.68%)**
in six alternating full requests. All decoded outputs match. This engine-only
change is selected on both hosts; model precision, GPU computation, DSpark
policy, provider, HSA runtime and kernel driver are unchanged.

## Matched comparison

Two Framework Desktop Strix Halo hosts, two 40 Gb/s USB4 cables, four active
native rails, Q2 target with the same matching DSpark model, tile4/down-rgroup4,
16,127 uncached prompt tokens, 256 generated tokens, 16,384 allocation,
concurrency one. Loading is excluded. The sequence is control / candidate /
candidate / control / control / candidate. Both use cooperative polling at 64.
The optional `--quality` mode remains at the same false setting in both arms;
no model-quality setting or verification rule is relaxed.

| Run | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Control 0 | 431.09 | 16.18 |
| Candidate 1 | 435.48 | 17.12 |
| Candidate 2 | 436.84 | 16.96 |
| Control 3 | 434.68 | 16.52 |
| Control 4 | 433.68 | 16.23 |
| Candidate 5 | 433.11 | 16.99 |
| **Control median** | **433.68** | **16.23** |
| **Candidate median** | **435.48** | **16.99** |

Candidate generation exceeds every control sample. Prefill changes by +0.42%.
These are measurements for one matched continuation fixture, not a broad
accuracy or speed guarantee. The historical Mellanox generation result is
18.27 tok/s: this candidate is still **7.01% below it**. The NICs have been
removed, so that historical single run is not a fresh interconnect A/B.

Native `DS4_BENCH_SPEC_TRACE=1` and
`DS4_METAL_GRAPH_PREFILL_PROFILE=1` logging matches preceding results. No added
stage profiler, affinity shim or DSpark diagnostic logging is active in these
six scored requests. [results.csv](results.csv) retains every measurement.

## Why this helps

The existing RDMA path carried layer partials, while
`ds4_tp_send_logits_half` / `ds4_tp_recv_logits_half` still transferred every
full-float vocabulary-score vector over TCP. That control connection was
verified at 1,000 Mb/s after Mellanox removal. A scalar half-vocabulary vector
has 64,640 float32 values: 258,560 bytes, with multiple rows for speculative
verification. Prior descriptions of RDMA model traffic covered the layer
partials and did not establish this separate score path.

The [optional overlay](../../../tools/framework-desktop/ds4-rdma-logits/README.md)
keeps the TCP frame header and moves the complete score payload through the
qualified RC exchange. It preserves every score bit and the target verification
policy. A 128-output-token off/on/off screen measured 16.09 / 16.89 / 16.15
tok/s with identical output. Coordinator LAN receive bytes dropped from
36,706,395 to 498,440 for the first control versus candidate request. The
candidate reported 117 score exchanges and 34,647,040 received score bytes
over RC. Interface counters cover the whole request lifetime, including
control/startup traffic; they are not payload-only bandwidth measurements.
The six full-request [LAN counters](lan-counters.json) and actual
[score counters](logits-counters.json) are provided separately.

## Quality and correctness

The complete GPU object is byte-identical, SHA-256
`0064b49c10b3437464e15004f0fe3e610cc44a8f4689f5393a2bf951d9840dfe`.
Only host transport source changes. There is no quantization, top-k pruning,
argmax shortcut, altered sampling or speculative acceptance rule.
All six decoded outputs have canonical UTF-8 SHA-256
`674754a8c7c6d8483f492302becda923d3bb1f279e31dfd9bdc0faff429787f6`,
excluding logger quotes and final newline. See [output-parity.json](output-parity.json).

Hardware integrity tests compare arbitrary float bit patterns, including NaNs,
with guard canaries at 1, 2, 5,120, 64,640, 129,280, 387,840, 516,160, 900,001
and 2,096,128 values, alternating with layer gates. Enabled, disabled,
negotiation-mismatch, invalid-count and bad-header cases pass. Portable tests
execute the actual added helper and serialization wrapper with injected
allocation, receive preparation, frame and transfer failures, plus concurrent
score/gate ownership. The existing actual-source Linux TP suite passes.

The final identical image on both hosts passes real text, vision and long-prompt
inference with DSpark. Both-cable proof passes for every scored request and all
three functional fixtures. Saved model, precision and Gufo preferences are
preserved. Final checks pass native startup, HIP_RESULT=42, automatic GPU power,
zero remaining model containers/QPs/host mappings, and Nodebool's three services
and backend/Compute health. See [validation.json](validation.json),
[transport-proof.json](transport-proof.json) and
[runtime-manifest.json](runtime-manifest.json).

## Other screened paths

Eleven GPU/CPU handshake screens found no repeatable gain from changing host
spin budgets, pause counts or reduction block size. The initially fast pause-8
sample did not repeat. A separate opt-in host receive-credit kernel passed 32
host/GPU hardware correctness cases and a preliminary off/on/off screen, but
is not selected or distributed as an improvement here. Original kernel and
host policy were restored before all six scored requests above.

The preceding [CPU/DSpark follow-up](../2026-10-24-deepseek-cpu-dspark/README.md)
remains a record of its own controls and rejected policies. Its 5% gate was for
promoting a global IRQ/CPU-placement policy. The lossless score-routing change
here has a consistent smaller gain and leaves host scheduling defaults alone.
The Mellanox target remains outstanding; further trials are separate from
this qualified result.

Source/output hashes and rollback instructions accompany the overlay. Raw logs,
commands and private recovery material remain local. Credentials, model files,
container binaries and private recovery paths are not distributed.
