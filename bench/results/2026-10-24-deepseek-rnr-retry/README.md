# Receiver readiness retry correction — 24 October 2026

The selected DeepSeek runtime now uses verbs **RNR value 7**, allowing
receiver-not-ready retries until the existing application deadline. The old
value 3 could fail a valid short receiver pause in about 10 ms. This is a
reliability correction; no separate throughput gain is claimed. Model weights,
precision, DSpark acceptance/rollback rules and GPU numerical code are unchanged.

## Controlled reproduction and bounded failure

A two-node fixture withheld the receive WQE, then checked every payload byte
and both guards. It configured the retry value during initial QP creation;
the provider did not accept a later attribute-only change on an active QP.
The expected early failure is a test success in row 1.

| Setting | Receiver behavior | Observed result |
|---|---|---|
| Previous RNR value 3 | Posts after 50 ms | Sender WC status 13, RNR retry exhaustion, after 10.06 ms |
| RNR value 7 | Posts after 50 ms | Exact payload after 52.25 ms; guards intact |
| RNR value 7 | Never posts | Application stops at 750 ms; sender QP closes by about 858 ms total |

Value 7 means unlimited receiver-readiness retries at the verbs layer, rather
than seven attempts. The default 750 ms application deadline, existing explicit
per-gate grace, cancellation and QP teardown remain in force. ACK retry count 3
and timeout exponent 14 stay unchanged. No completion, header, bounds or payload
validation is relaxed. See [the source-checked overlay and fixture](../../../tools/framework-desktop/ds4-rnr-retry/README.md)
and [actual receiver-delay logs](receiver-delay.json).

## Original event and attribution limits

The first baseline control of a later scheduling repeat aborted on both ranks
with an I/O completion error at layer 2, position 16186, sequence 4731, before
CQ4 was tried. The request is excluded from timing results. The saved profile
recovered; both GPUs passed HIP_RESULT=42, and scoped kernel logs contained no
GPU fault or QP1/open-port messages. Its prompt hash matched a successful control.

The original WC status was not captured. An error-instrumented baseline repeat
subsequently passed. A three-round transport-only stress also passed 63,360
gates and 768 score transfers, including large prefill-shaped windows,
decode-shaped transitions, exact bits and guards on both cables. Thus neither
silent data corruption nor the exact cause of the original abort is established.
The controlled test independently proves a retry weakness that can explain
this class of failure. See [original-abort.json](original-abort.json) and
[preceding-bit-stress.json](preceding-bit-stress.json).

## Qualified runtime and quality

The final image is
`e1ad6c23388e0e0b1c40773d6d2d3e326375ffc34d34c85ae1a9225fbe91ab41`,
identical on both hosts. Its parent is the preceding selected gate image
`842787d6dc6e34f0cf6f76816aa901217643e76738dbbd8801fdc7c02fa28eaf`.
Only the initial local QP RNR field changes in host transport source. All five
executables use the qualified numerical objects. The complete GPU object stays
`0064b49c10b3437464e15004f0fe3e610cc44a8f4689f5393a2bf951d9840dfe`.
Provider and HSA libraries are inherited unchanged. See
[runtime-manifest.json](runtime-manifest.json).

Ten two-node transport cases pass: all five gate units, logits-disabled
compatibility, logits/alignment peer mismatch, malformed header and invalid
score count. Successful connections query the actual QP and verify RNR value 7,
ACK retry 3 and timeout exponent 14. Float bits, tails, guards, mixed traffic
and repeated bounded windows pass. Actual-adapter completion faults, header
corruption, timeout/cancellation and Linux TP tests pass. See
[hardware-integrity.json](hardware-integrity.json) and
[source-fault-tests.json](source-fault-tests.json).

Eleven identical known-answer requests pass against the preceding selected
image. Answers and request hashes match exactly, including vision and a
15,788-token record prompt; JSON is checked structurally. DSpark stays enabled,
with temperature zero, seed 1017, unchanged precision and target verification.
These are targeted regressions, not a broad accuracy evaluation. See
[accuracy.json](accuracy.json) and [fixture definitions](quality-fixtures.json).

A full native 16,127-input / 256-output completion check passes at 444.97 prefill
and 17.83 generation tok/s, with canonical output and both-cable payload. This
single check is not a matched speedup claim. Gufo text, vision and long-context
checks pass. The kernel, provider, Gufo image, requested stock fabric policy,
saved model/quality preferences and all global parameters are unchanged. The
driver remains `6034C2FBE3EF9C733BA8B4C`, with host threshold 4096 and progress
interval 25 us; CQ interval remains 8. Both saved launch roles resolve the final
image and native HCA. Startup services are enabled; both GPUs, Nodebool services,
backend and Compute health pass, with owned model containers stopped. See
[native-check.json](native-check.json) and [validation.json](validation.json).

The earlier [matched smaller-gate improvement](../2026-10-24-deepseek-small-gates/README.md)
is retained. The subsequent CQ4 repeat measured only 17.92 vs 17.97 generation tok/s
with overlap, so CQ8 is retained. No Mellanox parity is claimed. Raw commands, private recovery paths,
full model logs, credentials, models and engine/module binaries are not distributed.

Final post-test checks confirm the selected image on both hosts, unchanged model,
quality and Gufo preferences, no owned model containers, both GPU smoke checks,
healthy Nodebool/backend/Compute, and all eleven checked recovery transactions
disarmed on each host. No scoped new GPU fault or QP1 messages appear. The
further fixed-threshold and target-only DSpark screens establish no additional
speed gain, so adaptive DSpark remains selected. See
[final verification](final-verification.json) and
[policy screens](../2026-10-24-deepseek-small-gates/dspark-final-followup.csv).
