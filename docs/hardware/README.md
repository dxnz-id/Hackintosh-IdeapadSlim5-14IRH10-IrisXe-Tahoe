# Hardware reports and USB map

Source of truth for the IdeaPad Slim 5 14IRH10 hardware probes, taken from Windows on 2026-10-29.

| File | What it is |
|---|---|
| `opcore-report.json` | OpCore-Simplify `SysReport` output: CPU, GPU, audio, network, USB controllers, input, storage |
| `usbmap.json` | USBToolBox map with the selected ports. Device serials are replaced with `<redacted>` |
| `usbmap-settings.json` | USBToolBox options used for the map |

## USB map

The map is in `EFI/OC/Kexts/UTBMap.kext`. It covers 10 ports across two controllers, below the macOS 15-port limit per controller. `XhciPortLimit` stays off.

PCH XHCI `00:14.0` (`8086:51ed`, `\_SB.PC00.XHCI`):

| Map name | Port | Connector | Use |
|---|---|---|---|
| `HS01` | 2 | 3 (USB-A) | USB-A 2.0 |
| `HS02` | 3 | 3 (USB-A) | USB-A 2.0 |
| `HS03` | 6 | 255 (internal) | Camera |
| `HS04` | 7 | 9 (USB-C) | USB-C 2.0 |
| `HS05` | 8 | 9 (USB-C) | USB-C 2.0 |
| `HS06` | 10 | 255 (internal) | Bluetooth |
| `SS01` | 14 | 3 (USB-A) | USB-A 3.x |
| `SS02` | 15 | 3 (USB-A) | USB-A 3.x |

Thunderbolt XHCI `00:0d.0` (`8086:a71e`, `\_SB.PC00.TXHC`):

| Map name | Port | Connector | Use |
|---|---|---|---|
| `SS01` | 3 | 9 (USB-C) | USB-C 3.x |
| `SS02` | 4 | 9 (USB-C) | USB-C 3.x |

Ports not listed are disabled in macOS. The map keeps both USB-A ports, both USB-C ports, the camera and Bluetooth. `SS04` (port 16) is unused.

The PCH controller needs `XHCI-unsupported.kext` (`0x51ed8086`). The Thunderbolt controller (`0xa71e8086`) is not in that kext, so macOS may not attach a driver to it; USB-C then works at USB 2.0 through `HS04`/`HS05` only. Test after the first boot before patching anything.
