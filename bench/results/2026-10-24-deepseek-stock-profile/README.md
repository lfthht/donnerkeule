# DeepSeek polling and stock-clock profile — 24 October 2026

The combination of CQ yield interval **8** and manual AMD DPM selecting the
stock **2000 MHz fabric entry** improved median DeepSeek generation from
**17.50 to 17.79 tok/s (+1.66%)** and prefill from **436.62 to 444.25 tok/s
(+1.75%)** in six alternating full requests. Every candidate generation sample
exceeded every control sample. Both settings are selected on both hosts after
paired accuracy checks, a Gufo regression check and startup/recovery validation.

The kernel, provider, HSA runtime, model, precision, DSpark policy and all five
engine executable files are unchanged. The new image has the same 16 filesystem
layers as its predecessor; only its CQ environment default changes. The stock
clock request is provided by a separate reversible system service.

## Full comparison

Two Framework Desktop Strix Halo hosts, two 40 Gb/s USB4 cables and four native
rails. Same Q2 target, matching DSpark model, tile4/down-rgroup4, 16,127 uncached
input tokens, 256 generated tokens, 16,384 allocation and concurrency one.
Loading is excluded. Both arms use full-precision RC score transport and the
same aligned-host receive-credit driver, with the 64 KiB minimum unchanged.
The optional `--quality` flag remains false in both arms; no quality, precision
or target-verification setting is relaxed.

Controls use the saved runtime with CQ interval 64 and automatic GPU power.
Candidates use interval 8 and manual DPM with stock FCLK index 7 requested.
The native driver is reloaded on both hosts before each request; both unload
before either loads, and live domain reciprocity is checked before inference.
Native speculative/prefill logging is unchanged, with no added stage profiler.

| Run | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Control 0 | 436.62 | 17.50 |
| Candidate 1 | 443.82 | 17.70 |
| Candidate 2 | 444.86 | 17.83 |
| Control 3 | 436.18 | 17.59 |
| Control 4 | 436.93 | 17.50 |
| Candidate 5 | 444.25 | 17.79 |
| **Control median** | **436.62** | **17.50** |
| **Candidate median** | **444.25** | **17.79** |

All six decoded outputs have canonical SHA-256
`674754a8c7c6d8483f492302becda923d3bb1f279e31dfd9bdc0faff429787f6`.
All available speculative trace checkpoint counts also match, through call
224. Full final speculative totals are not claimed from those checkpoints.
See [deepseek.csv](deepseek.csv), [summary.json](summary.json),
[output-parity.json](output-parity.json) and [deepseek-proof.json](deepseek-proof.json).
The proof files omit zero counters except for explicitly retained error deltas.

This measures the combination. The standalone screens below do not isolate a
repeat-qualified contribution from each setting. It is one continuation fixture,
not a general speed or accuracy guarantee. Relative to the historical single
Mellanox result of 420.98 prefill / 18.27 generation tok/s, these medians are
about **+5.53% / -2.63%**. The Mellanox NICs were removed, so no fresh interconnect
A/B is available. The generation target remains open.

## Validation and selected runtime

The child image is
`55d3551404f5129dba6cf91671ff2f085bf6079b40e49e0ae255cb958f236ab2`;
its measured parent is
`df68ad19223d5413fc1dc00cd9cd7fc4512f8e87f1126a560992997eee87404a`.
Both hosts have identical child image bytes. Filesystem-layer equality proves
that the model computation binaries and container libraries are unchanged.
The complete GPU object remains
`0064b49c10b3437464e15004f0fe3e610cc44a8f4689f5393a2bf951d9840dfe`.
The selected driver remains SHA-256
`4b42271eedab95ba196dd6b668673c1e4e3021eb46ad641340c87731f898233f`,
srcversion `BAF45670669940EC5C9C0CA`.

Eleven identical known-answer request payloads pass for both the baseline and
candidate: arithmetic, factorial, ordering logic, factual answers, translation,
JSON, code evaluation, vision and a 15,788-token engineering-record prompt.
Actual answers were also checked exactly, with JSON parsed structurally. All
paired answers match. The API checks use DSpark, temperature zero, seed 1017,
thinking off and 16,384 context capacity. See [accuracy.json](accuracy.json) and
[quality-fixtures.json](quality-fixtures.json). These checks supplement unchanged
computation/precision evidence; they are not a broad model-accuracy evaluation.

Gufo text, vision and long-prompt checks pass. Both-cable traffic is proven in
all full DeepSeek requests, accuracy fixtures and Gufo measurements. Saved
quality/model/Gufo preferences are preserved. Both saved launch roles resolve
the new image and native HCA, while retaining DSpark and the existing math.
HIP_RESULT=42, zero remaining containers/QPs/host mappings, native startup,
Nodebool services and backend/Compute health pass. No new GPU fault or QP1
messages are found in the scoped kernel journal. See [validation.json](validation.json)
and [runtime-manifest.json](runtime-manifest.json).

The [stock-clock helper and service](../../../tools/framework-desktop/stock-fclk/README.md)
validate the tested GPU identity and stock table, capture automatic mode before
writes, and restore it when stopped. Start/stop recovery was exercised on both
hosts. The manual policy also stays active during idle periods while the
service is running. Firmware does not consistently show a live FCLK marker;
2000 MHz describes the requested stock table entry. No voltage, overclock,
power-limit or memory-timing control is changed.

## Gufo regression check

Four alternating requests use the unchanged Gufo image, 16,384 uncached prompt
tokens, 256 output tokens, 262,144 context capacity, MTP ceiling 7, thinking off,
concurrency one and an excluded eight-token warmup. Controls use automatic GPU
power and candidates the requested stock fabric profile. Loading is excluded.

| Run | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Control 0 | 2070.23 | 59.41 |
| Candidate 1 | 2072.60 | 59.42 |
| Candidate 2 | 2065.87 | 59.72 |
| Control 3 | 2072.04 | 58.89 |
| **Control median** | **2071.14** | **59.15** |
| **Candidate median** | **2069.23** | **59.57** |

These small differences do not establish a Gufo speedup or substantial
regression. Every output matches, with 226 proposed and 150 accepted draft
tokens each. See [gufo.csv](gufo.csv), [gufo-output-parity.json](gufo-output-parity.json)
and [gufo-proof.json](gufo-proof.json).

## Screens and a control-variation finding

All screens below use 128 output tokens and their own controls, rather than
the full comparison's 256 tokens. They are retained in [screens.json](screens.json).

| CQ interval | Generation tok/s |
|---|---:|
| 64, control A | 17.23 |
| 8 | 17.55 |
| 16 | 17.34 |
| 32 | 17.16 |
| 128 | 17.43 |
| 256 | 17.28 |
| 0, no cooperative yield | 16.08 |
| 64, control B | 17.32 |

All outputs match. The two CPU-mask screens then measured 17.27 and 17.45 tok/s,
versus an unrestricted initial control at 17.36. Their output matches that
control. The closing **unrestricted** control reached 18.17 and produced the
same output variant as the earlier apparent fast CPU-mask result. Available
trace counts show more speculative work in that variant. This demonstrates
that the earlier fast branch cannot reliably be attributed to CPU placement;
it is not evidence of a CPU-induced quality reduction either. CPU defaults are
retained. No claim of Mellanox parity is made from this isolated shorter screen.

| Stock power screen | Prefill tok/s | Generation tok/s |
|---|---:|---:|
| Automatic A | 435.75 | 17.16 |
| High | 445.60 | 17.49 |
| Manual, FCLK entry 2000 MHz | 444.39 | 17.74 |
| Peak profile | 405.97 | 16.63 |
| Automatic B | 435.73 | 17.47 |

All outputs match and automatic mode was restored after screening. Peak mode
regressed and is not selected. The retained full comparison uses the manual
stock entry together with CQ interval 8.

The original Mellanox 256-token output was independently compared with the
qualified USB4 output and matches exactly. Its speculative checkpoint counts
differ, however: identical text alone does not prove identical draft work.
Historical interconnect comparisons retain that limitation.

Raw logs, commands and private recovery journals remain local. Credentials,
private recovery paths, model files and engine/module binaries are not distributed.
