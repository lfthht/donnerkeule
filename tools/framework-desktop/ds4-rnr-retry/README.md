# Preserve receiver readiness within the existing deadline

The adapter previously configured `rnr_retry=3`. On the tested software transport,
three receiver-not-ready retries were exhausted in about 10 ms, even though the
application allowed 750 ms by default. A short receiver delay can therefore fail
a request unnecessarily. The overlay selects the verbs value **7**, meaning
unlimited receiver-not-ready retries while the operation remains alive. The
existing application deadline, cancellation and QP teardown still bound failure;
existing per-gate grace is retained. ACK retry count 3 and timeout exponent 14
stay unchanged.

Apply after the page-aligned gate overlay:

```sh
python3 tools/framework-desktop/ds4-rnr-retry/apply.py /path/to/ds4/source
python3 tools/framework-desktop/ds4-rnr-retry/apply.py /path/to/ds4/source --apply
```

Source hashes are checked before and after patching. Only the initial local QP
receiver-ready retry field changes. Wire formats, peer negotiation, precision,
GPU numerical code, payload/header checks and completion validation are unchanged.
The policy can differ across peers without changing the protocol, but both
sending directions benefit from the new setting. The runtime recipe packages
the five qualified binaries into the preceding image; binaries are not included.

A two-node test deliberately withheld the receive WQE for 50 ms. Value 3 failed
with WC status 13 (`RNR_RETRY_EXC_ERR`) after 10.06 ms. Value 7 delivered every
byte correctly after 52.25 ms, with guards intact. When the receiver never posted,
the test stopped at its 750 ms application deadline and closed the QP in about
858 ms total. Thus the change tolerates a valid short pause without creating an
unbounded application wait.

`test_receiver_delay.c` is the hardware fixture. Compile it with section garbage
collection against the qualified TP source and matching libibverbs development
headers. In a temporary test-only copy of the adapter, replace the initial
`a.rnr_retry=7;` assignment with:

```c
a.rnr_retry = (uint8_t)atoi(getenv("TEST_RNR_RETRY") ? getenv("TEST_RNR_RETRY") : "3");
```

The fixture selects 3 or 7 before QP creation; it does not change an active QP.
Run both ranks against the same host/port, with packed gates and RC logits
explicitly disabled and gate alignment 65536 for this raw-SEND test:

```sh
export DS4_TP_ROCE_PACKED_GATES=0 DS4_TP_ROCE_LOGITS=0
export DS4_TP_ROCE_GATE_ALIGN=65536 DS4_TP_GATE_TIMEOUT_MS=750
TEST_RNR_RETRY=3 ./test_receiver_delay RANK LEADER PORT 3 50 0
TEST_RNR_RETRY=7 ./test_receiver_delay RANK LEADER PORT 7 50 0
TEST_RNR_RETRY=7 ./test_receiver_delay RANK LEADER PORT 7 0 1
```

RANK is 0 on the leader and 1 on the worker. The first case expects the old early
failure; the second expects exact data; the third expects bounded cancellation.
Return to the qualified packed-gate/RC-logits settings for model use.

Rollback stops both model ranks and restores the preceding runtime. No kernel,
provider, model preference or stock-clock service change is needed. The
[qualification report](../../../bench/results/2026-10-24-deepseek-rnr-retry/README.md)
records model validation and the original unclassified I/O abort that prompted
this investigation. The controlled test proves a retry weakness; it does not
prove that the original abort had that exact completion status.
