# Optional diagnostic source overlays

Use a separate copy of the qualified UBG3 + cooperative-poll source, never the
production runtime. Copy `ds4_tp_diag.h` to the DS4 source root, then apply
`adapter-timings.patch` and `cpu-service-timings.patch` with `git apply --check`
and `git apply`. Build with the locked engine environment and original flags.

Set `DS4_TP_DIAGNOSTIC=1` on both ranks. Compare
`DS4_TP_ROCE_CQ_YIELD=0` and `64` with the same fixture. `DS4_TP_STAGE` lines
aggregate host monotonic durations by gate kind: 1 scalar, 2 batch, 3 big/prefill.
They include peer waiting and are not pure wire measurements. The
`service_wakeup` label is job age since publication, including queued backlog.
Do not add overlapping spans as independent costs. Use uninstrumented binaries
for scored inference and never infer cross-host ordering from local clocks.
These host-only diagnostics do not change model arithmetic or GPU kernels.
