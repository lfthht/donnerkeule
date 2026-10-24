# DS4: cooperative completion polling on native USB4

This optional engine-side patch follows Gufo's cooperative `CpuRelax` /
`SpinPause` approach. It applies **after the qualified UBG3 overlay**, to the
exact `ds4_tp_roce.h` recorded in `source-manifest.json`. It changes neither
GPU computation nor the Donnerkeule kernel driver or verbs provider.

The existing DS4 loop continuously polled its completion queue. Unlike a
hardware RDMA NIC, the native USB4 path depends on scheduled kernel work to
advance descriptor/completion processing. A user thread polling continuously
can delay that work. Gufo already pauses and periodically yields its polling
thread; DS4 did not.

The patch applies the same policy to DS4's two empty-CQ wait loops: CPU pause
on most empty polls, `sched_yield()` every 64. All status, WR ID, opcode,
length, cancellation, sequence, header, DMA lifetime and deadline checks stay
in place. A nonempty completion is processed immediately. There is no new
sleep, buffer reuse rule, wire protocol or approximation.

## Application

Use the [UBG3 source instructions](../ds4-packed-gates/README.md) first. Then:

```sh
python3 /path/to/donnerkeule/tools/framework-desktop/ds4-cq-polling/apply.py /path/to/qualified/ds4
python3 /path/to/donnerkeule/tools/framework-desktop/ds4-cq-polling/apply.py /path/to/qualified/ds4 --apply
```

The helper verifies exact input/output hashes. Build once in the same locked
ROCm environment and install identical binaries on both hosts. For the tested
native USB4 runtime, set inside **both** containers:

```sh
DS4_TP_ROCE_PACKED_GATES=1
DS4_TP_ROCE_CQ_YIELD=64
```

The polling setting defaults to `0` (the original policy). Supported nonzero
intervals are powers of two up to 4096; only 64 was qualified for this result.
Set it to `0`, or select the preceding UBG3 image, to roll back. There is no
quality, DSpark, quantization, model or clock-setting change. This source and
its patch retain the licensing of the corresponding DS4/Gufo code.

## Validation

The actual helper code added by the patch is compiled by
`tools/ci/framework-desktop-tests/test_ds4_cq_poll.py`, covering valid/invalid
configuration, yield cadence, disabled behavior and counter wraparound.
The complete patched adapter also passed actual-source completion fault,
header/guard, timeout/cancellation and Linux TP protocol tests. Model-free
hardware tests passed on both hosts across mixed sizes, repeated gates and
protocol mismatches. These retain the earlier UBG3 test harness and enable
the polling interval.

The [measured comparison and its limits](../../../bench/results/2026-10-24-deepseek-cq-polling/README.md)
include repeated native 16K inference, actual both-cable payload counters,
output parity, and text/vision qualification. GPU computation object bytes and
the ROCm/HSA runtime remained unchanged. Profiling runs are separate from the
scored requests.
