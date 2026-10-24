# DS4: full-precision vocabulary scores over native RC

The Linux engine sent layer partials over RDMA but still sent complete worker
vocabulary-score vectors over its TCP control socket. After Mellanox removal,
that socket used a 1 Gb/s ordinary LAN. Each scalar score vector is 258,560
bytes for the tested 129,280-token vocabulary; speculative verification sends
all of its score rows too.

This optional host-transport overlay moves every score float to the existing
RC queue. It keeps the original control-frame type/length, then exchanges a
page-aligned, zero-padded message through the qualified completion checks. The
worker sends the complete payload; the coordinator sends zeros in the reverse
direction so both receive-ahead windows drain with matching WR IDs. Only the
requested data bytes reach the caller. There is no quantization, top-k filter,
argmax substitution, sampling change or target-verification shortcut.

The layer service and main-thread score caller serialize adapter ownership
with a mutex. The GPU graph drains before its scores are returned. Scratch
capacity is bounded by the existing four 2 MiB RC windows and reused between
calls. Payload failures mark the transport failed; they cannot fall back to a
different frame layout or publish partial caller output.

## Apply and enable

Apply the qualified [UBG3](../ds4-packed-gates/README.md) and
[cooperative-polling](../ds4-cq-polling/README.md) overlays first. Then:

```sh
python3 /path/to/donnerkeule/tools/framework-desktop/ds4-rdma-logits/apply.py /path/to/qualified/ds4
python3 /path/to/donnerkeule/tools/framework-desktop/ds4-rdma-logits/apply.py /path/to/qualified/ds4 --apply
```

The helper checks exact input/output source hashes. Rebuild in the same locked
ROCm environment and use identical binaries on both hosts. Set on both ranks:

```text
DS4_TP_ROCE_PACKED_GATES=1
DS4_TP_ROCE_CQ_YIELD=64
DS4_TP_ROCE_LOGITS=1
```

The new switch defaults to off and requires packed-gate mode. Its negotiated
capability identifier is UBG4; gate framing remains UBG3. A peer with a different
setting fails setup before gate DMA. TCP mode and source-default behavior stay
on the existing path. Roll back by disabling the switch on both ranks or
selecting the preceding qualified runtime.

## Evidence

The complete GPU object remains byte-identical. Hardware tests compared every
bit, including arbitrary NaN encodings, at scalar, speculative and multi-window
sizes, alternating scores with layer gates. Mode mismatch, invalid count and
bad-header cases passed. Automated tests execute the actual added helper and
serialization wrapper, including allocation/prepare/transfer failures, frame
validation, canaries and concurrent ownership.

The six-request [comparison](../../../bench/results/2026-10-24-deepseek-rdma-logits/README.md)
and its limits record throughput, output parity and both-cable counters. Model
weights, precision, DSpark policy, HSA runtime, verbs provider and kernel driver
are unchanged. This overlay retains the licensing of the corresponding DS4
source. Model and container binaries are not distributed here.
