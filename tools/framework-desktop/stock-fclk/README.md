# Qualified stock fabric-clock and CQ profile

The paired Framework Desktop deployment measured a modest further gain from
**two settings together**: `DS4_TP_ROCE_CQ_YIELD=8` and manual AMD DPM with the
stock **2000 MHz fabric entry** selected. The six-request
[comparison](../../../bench/results/2026-10-24-deepseek-stock-profile/README.md)
measured 17.50 → 17.79 generation tok/s and 436.62 → 444.25 prefill tok/s.
Standalone screens do not establish the separate contribution of each setting.

Model weights, precision, DSpark acceptance rules, kernel driver, HSA runtime
and verbs provider remain unchanged. The new image has exactly the same
filesystem layers as the preceding qualified image; only its CQ environment
default changes. There is no engine recompilation or new GPU computation.

## Runtime

Use a qualified image containing the full-precision RDMA-score overlay and its
matching native provider. This Containerfile adds only the environment default:

```sh
podman build --pull=never --network=none \
  --build-arg DS4_BASE_IMAGE=YOUR_QUALIFIED_BASE_IMAGE \
  -t localhost/deepseek1017-ds4:usb4-cq8 \
  -f tools/framework-desktop/stock-fclk/Containerfile.runtime \
  tools/framework-desktop/stock-fclk
```

Use identical image bytes on both hosts. The measured parent and child hashes
are recorded in the result manifest. Both retain packed gates, full-precision
RC scores and the 64 KiB direct-host minimum. The CQ parser's source default
and accepted values are unchanged; this profile sets its environment default.

## Stock clock service

This helper is qualified for AMD device `0x1586` on the tested Framework hosts.
It requires an automatic-mode baseline and a unique stock 2000 MHz fabric
entry on every detected AMD GPU. It validates all devices before any power
write, captures the baseline first, then requests manual mode and that stock
index. Unsupported GPUs, missing entries and mismatched tables fail before
power changes. The frequency is a **requested stock entry**; firmware telemetry
does not consistently report a current fabric-clock marker on these hosts.
No voltage, overclock, power limit or memory-timing control is changed.

Stop model work before installation or removal. From this directory:

```sh
sudo install -d -m 0755 /usr/local/libexec/framework-desktop-fclk
sudo install -m 0644 stock_fclk.py comparison_power.py /usr/local/libexec/framework-desktop-fclk/
sudo install -m 0644 framework-desktop-fclk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now framework-desktop-fclk.service
```

The manual policy stays active while the service is enabled and running,
including idle periods. Stopping it restores the captured automatic mode.
Recovery state is root-owned under `/var/lib/framework-desktop-fclk` and tracks
whether this profile still owns the setting; repeated cleanup does not rewrite
an already released baseline. Startup and stop recovery were exercised on both
hosts. Tests also cover failure restoration and unsupported-device/table cases.

To restore automatic power and the preceding CQ default:

```sh
sudo systemctl disable --now framework-desktop-fclk.service
```

Select the preceding qualified runtime, or set `DS4_TP_ROCE_CQ_YIELD=64` on both
ranks. No kernel/provider rollback or model conversion is required. The named
service and recovery directory must be inspected before replacing an existing
installation. Preserve existing local power policies rather than overwriting
them with this profile.
