# Optional DS4 Linux RC packed gates (UBG3)

This is an **engine-side transport overlay**, separate from the Donnerkeule
kernel driver. It was tested with DeepSeek V4.1 Flash 1017 Q2 plus DSpark MXFP4
on two Framework Desktop 128 GB hosts and the unchanged selected driver.
It changes neither quality flags nor GPU computations.

[The six-request comparison](../../../bench/results/2026-10-24-deepseek-usb4/README.md)
measured 9.02 → 9.61 median generation tokens/s (+6.54%) and essentially unchanged
prefill. All six outputs and speculative-work distributions matched. This is a
modest gain in one matched comparison; it does not recover the historical
18.27 tokens/s Mellanox reference or establish a general speedup.

## What changes

Small gates carry the complete 40-byte validated control header and payload in
one aligned 64 KiB RC SEND/RECV, using the existing direct-host DMA path. A
full-capacity receive is posted ahead after the previous payload has been copied
out. This preserves readiness without a per-gate TCP barrier. Both exact
completion IDs/types/lengths and magic, kind, layer, gate, epoch, sequence and
logical length validate before model input is written. Bootstrap exchanges the
UBG3 tag; mismatched peers fail before gate DMA. Large transfers keep their
bounded four-WR windows and TCP readiness barriers. Registered staging remains
16 MiB. The receive-ahead WQE remains bounded by the existing registered buffer.

Without `DS4_TP_ROCE_PACKED_GATES=1`, the original wire path remains selected.
Set the variable on **both ranks**, inside their containers. Both executable
versions and the UBG3 protocol settings must match. Stop the ranks before
changing them. Set the variable to `0` on both ranks to use the original path.

## Measured source and application

The input was the locally qualified DS4 source based on
`kyuz0/ds4@f46631e483e19d13f23d3c4bced7ade0d086a3ad`, its recorded ROCm/V4.1
and vision overlays, and the existing explicit RoCE traffic-class overlay.
This is not a patch against arbitrary upstream HEAD. The exact two input and
output hashes are in `source-manifest.json`; the helper refuses other inputs.
No engine source, model weights or container binary is distributed here.

```sh
python3 /path/to/donnerkeule/tools/framework-desktop/ds4-packed-gates/apply.py /path/to/qualified/ds4
python3 /path/to/donnerkeule/tools/framework-desktop/ds4-packed-gates/apply.py /path/to/qualified/ds4 --apply
```

Build in the same locked ROCm environment as the qualified engine, with its
original flags and matching provider ABI. Build once and copy identical
executables to both hosts. The measured GPU object was byte-identical to the
qualified base (`ds4_rocm.o`, SHA-256
`0064b49c10b3437464e15004f0fe3e610cc44a8f4689f5393a2bf951d9840dfe`).
The patch and tests retain the licensing of the corresponding DS4 source.

## Actual-source tests

In the patched, qualified Linux source directory, with libibverbs headers:

```sh
cp /path/to/donnerkeule/tools/framework-desktop/ds4-packed-gates/test_packed_gate.c .
cc -O2 -D_GNU_SOURCE -ffunction-sections -fdata-sections -I. test_packed_gate.c \
  -Wl,--gc-sections -lm -pthread -ldl -o test-packed-gate
./test-packed-gate
cc -O2 -D_GNU_SOURCE -ffunction-sections -fdata-sections tests/test_tp_linux.c \
  -Wl,--gc-sections -lm -pthread -ldl -o test-linux
./test-linux
```

The first harness executes the actual adapter against explicit verbs faults:
all 40 header bytes, payload tails and guards, duplicate/stale completions,
wrong completion length/status, timeout and cancellation. The second is the
existing Linux protocol regression suite. These engine tests require the
separately obtained qualified DS4 source; they are not part of this driver's CI.

`test_usb4_pair.c` includes that same source for model-free two-host testing.
Build it with the same options. It selects `usb4_rdma0`, port 1, GID 1, 40 layers
and 5120-wide vectors, as measured. Its arguments are rank (`0`/`1`), coordinator
address, TCP port, and `normal`, `negotiation-mismatch` or `header-mismatch`.
Run it in the engine's matching provider environment. `normal` checks payloads
and guards across mixed transfer sizes up to 41.6 MB and 100 repeated 20 KiB
gates. The original-path comparison starts with a bulk warmup and tests sizes
at least 20 KiB; UBG3 additionally tests payloads down to one byte. For the two
negative modes, configure the two flags differently, or use the same enabled
flag with deliberately differing sequence headers, respectively.

Before hardware tests after any driver reload, confirm reciprocal peer
**generation identities**, all four active rails and both cable domains.
Sequential restoration can leave a stale remote identity; active device names
alone are insufficient. In this run, a simultaneous stop/start of both selected
drivers restored reciprocity. Never interrupt unrelated active QPs or workloads.
