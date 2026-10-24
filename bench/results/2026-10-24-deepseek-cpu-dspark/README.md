# DeepSeek CPU placement and DSpark follow-up — 24 October 2026

The current cooperative-polling runtime remains selected. The best CPU
placement measured **16.60 versus 16.44 generation tok/s (+0.97%)** across six
alternating full requests, with identical decoded output. It did not meet the
preselected 5% gate for replacing defaults. The tested DSpark alternatives
regressed. No additional performance change was promoted.

## Full matched comparison

Two Framework Desktop Strix Halo hosts, the same native dual-USB4 driver and
provider, same Q2 target and matching DSpark model, 16,127 uncached input tokens,
256 generated tokens, 16,384 allocation, concurrency one. Loading is excluded.
DSpark stays enabled on both ranks. Tile4/down-rgroup=4, precision, normal math,
context, power policy and target verification are unchanged.

The sequence was baseline / placement / placement / baseline / baseline /
placement. Both arms use image
`9e10a9bfa49112ee02508fb9d6b12433ed4ab7b409b03019306bed1593bc087b`,
UBG3 and `DS4_TP_ROCE_CQ_YIELD=64`. Baseline has unrestricted model CPU affinity
and the original requested USB4 IRQ masks. Placement puts the CPU transport
service on CPU 10 and the two USB4 controllers' IRQs on CPUs 8 and 9. No other
inference thread is pinned in this candidate. These are distinct physical
cores on the measured 16-core/32-thread hosts.

| Run | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Baseline 0 | 437.31 | 16.46 |
| Placement 1 | 434.97 | 16.60 |
| Placement 2 | 436.09 | 16.65 |
| Baseline 3 | 435.76 | 16.36 |
| Baseline 4 | 437.52 | 16.44 |
| Placement 5 | 437.82 | 16.57 |
| **Baseline median** | **437.31** | **16.44** |
| **Placement median** | **436.09** | **16.60** |

This is a small measured difference on one continuation fixture, not an
established general speedup. All samples are retained. The earlier 16.23
tok/s result uses this same selected runtime; the fresh control above is the
appropriate denominator for this experiment. The older Mellanox result is
still a historical single run, not a new matched interconnect comparison.

Native `DS4_BENCH_SPEC_TRACE=1` and
`DS4_METAL_GRAPH_PREFILL_PROFILE=1` logging matches the preceding benchmark.
There is no added stage profiler or DSpark diagnostic logging in these six
scored requests. The placement shim acts at thread startup, outside timed
inference. GPU object bytes, executable bytes and numerical kernels are
unchanged; see [runtime-manifest.json](runtime-manifest.json).

## Screening results

Separate screens use 128 output tokens at the same 16,127-token frontier, so
their rates must be compared with their own controls. These are single screens,
not repeat-qualified gains.

| CPU screen | Prefill tok/s | Generation tok/s | Output/decision |
|---|---:|---:|---|
| Baseline A | 435.08 | 15.87 | Reference |
| CQ yield 16 | 432.30 | 15.88 | Identical; no meaningful gain |
| CQ yield 256 | 436.27 | 15.93 | Identical; no meaningful gain |
| All model threads on CPUs 0–15 | 431.24 | 17.14 | Output differs; rejected |
| All model threads on CPUs 8–15 | — | — | Native gate EIO at sequence 4500; rejected |
| Baseline B after rejection | 436.54 | 15.86 | Reference reproduced |
| Transport service on CPU 2 | 438.38 | 16.11 | Identical; small screen difference |
| Transport service on CPU 10 | 437.56 | 16.27 | Identical; small screen difference |
| IRQs 0/1, service CPU 2 | 439.90 | 16.40 | Identical; screen only |
| IRQs 8/9, service CPU 10 | 439.18 | 16.47 | Identical; selected for the full comparison above |

An initial attempt using Podman's cpuset controller could not start because
that controller is unavailable to the rootless user. Process-affinity screens
then used `taskset`; no cgroup delegation or host CPU settings were changed.
The EIO screen is retained as a failure, with no throughput assigned. Subsequent
unrestricted requests and final health checks passed. Output differences are a
failure of this experiment's strict parity gate; no claim of reduced model
accuracy is inferred from those differences alone.

## DSpark diagnostics

All five screens below enable the same additional `DS4_DSPARK_STATS=1` and
`DS4_DSPARK_SPEC_LOG=1` diagnostic logging. They are excluded from the full
scored comparison. Target-model draft acceptance and rollback code are
unchanged. Confidence overrides affect which drafts are proposed, not the
target verification test.

| Policy | Generation tok/s | Decoded output matches baseline |
|---|---:|---|
| Current adaptive policy | 15.91 | Yes |
| Disable adaptive drafting backoff | 15.12 | No |
| Always propose width 1 | 11.49 | No |
| Always propose width 3 | 13.31 | Yes |
| Always propose width 5 | 11.40 | Yes |

The always-propose screens use `--dspark-confidence 0`,
`DS4_DSPARK_DISABLE_ADAPTIVE_DRAFTING=1` and
`DS4_DSPARK_FIXED_WIDTH=1`, `3` or `5`, on both ranks. The no-backoff screen
changes only that environment switch from the diagnostic control.

The control accepted 12 draft tokens in this 128-token request, spending
146.722 ms in proposals and 946.358 ms in verification. Always proposing five
accepted 82 draft tokens but spent 847.393 ms in proposals and 10,360.571 ms in
verification. More accepted drafts did not repay their verification cost.
The retained source's TCP-derived cost annotations were a hypothesis to
investigate; these tests do not establish that replacing those constants would
improve USB4 throughput. No speculative verification shortcut or cost-table
replacement was installed. Full counters are in
[dspark-profiles.json](dspark-profiles.json).

## Output, transport and restoration

All six full-request decoded texts are identical, including when compared
directly with the previous qualified raw log. Their canonical UTF-8 hash,
excluding the logger's quotes and final newline, is
`674754a8c7c6d8483f492302becda923d3bb1f279e31dfd9bdc0faff429787f6`.
This framing differs from the preceding report's output-hash representation.
[output-parity.json](output-parity.json) retains every screen result separately.

Native payload-counter deltas prove traffic on both physical USB4 domains and
all four rails in every completed request; see
[transport-proof.json](transport-proof.json). The host-side IRQ trial used
bounded independent recovery timers. Requested IRQ masks were restored after
each trial and checked against the original masks at the end. Effective IRQ
vector choices remain kernel-managed under the restored broad masks; exact
restoration of those transient choices is not claimed. Candidate confirmation
also checked actual effective placement for IRQs whose counters advanced.

The service-affinity diagnostic used a temporary `pthread_create` startup shim
targeting the exact executable symbols listed in [runtime-manifest.json](runtime-manifest.json).
It changed no model computation or transport callback. Neither that shim nor
the experimental IRQ placement is selected in the saved runtime.

Both hosts retain the same saved image and quality/model/Gufo preferences.
Final checks passed native startup, HIP_RESULT=42, automatic GPU power,
zero remaining QPs/host mappings and no active model containers. Nodebool's
three services and backend/Compute health passed. All trial timers and
temporary authenticated sessions were closed. See
[validation.json](validation.json).

Raw request logs, commands, IRQ snapshots and recovery journals are retained
locally. No credentials, model files, private recovery files or container
binaries are distributed in this result.
