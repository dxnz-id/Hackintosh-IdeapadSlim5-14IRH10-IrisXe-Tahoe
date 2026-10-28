# Iris Xe acceleration on macOS Tahoe — Lenovo IdeaPad Slim 5 14IRH10

Fork of [JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe](https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe)
adapted for the **Lenovo IdeaPad Slim 5 14IRH10** (i5-13420H, UHD Graphics A7A8, 48 EU). The NootedGreen/Metal stack is
upstream's; this fork replaces the Dell-specific EFI (ACPI, kexts, boot-args) and documents what is known and unknown
for this laptop.

> ⚠️ **Experimental, and unproven on this exact GPU.** Upstream has confirmed the stack on Iris Xe 96 EU parts
> (A7A0/46A8) and on 80 EU parts with `ngreen-eu=80 ngreen-l3=6`. This laptop's UHD Graphics is **A7A8, 48 EU, 6 L3
> banks**; the topology boot-args are set from the fuses, but nobody has booted macOS on this model yet. Keep a second
> bootable USB and expect debugging. Read [docs/STATUS.md](docs/STATUS.md) before installing.

## This machine (probed from Linux)

| Part | Model |
|---|---|
| CPU | Intel Core i5-13420H — 4 P-cores + 4 E-cores, 12 threads |
| GPU | Intel UHD Graphics (Alder Lake-P, `8086:A7A8`), 48 EU, 6 L3 banks |
| Panel | 1920×1200 60 Hz (SDC ATNA40CT03-0), eDP, GPU PWM backlight |
| Audio | Conexant CX8070 / SN6140 (HDA) |
| Wi-Fi / Bluetooth | Intel AX210 |
| Touchpad | ELAN06FA, I2C HID |
| Camera | internal UVC |
| Storage | WD SN740 NVMe |
| BIOS | Q5CN27WW |

## What this fork changes

- **ACPI.** Keeps `SSDT-EC`, `SSDT-MCHC`, `SSDT-PLUG-ALT`, `SSDT-PNLF`, `SSDT-SBUS`, `SSDT-USB-Reset`, `SSDT-USBX`,
  `SSDT-XOSI` — all verified against this DSDT. Drops the Dell tables (`SSDT-ALS0`, `SSDT-GPI0`, `SSDT-RTCAWAC`,
  `SSDT-XPS-I2C`) from the config; the files stay in the repo for upstream. Only the `_OSI` → `XOSI` patch remains
  enabled, so `TPD0._CRS` returns `I2cSerialBusV2 + GpioInt(\_SB.GPI0)` and the touchpad can run on interrupts.
- **GPU.** `ngreen-eu=48 ngreen-l3=6` from the fuse read (`0x9118 = 0x88`); `-ngreenpm` keeps the BIOS PL1 instead of
  the XPS's 22 W cap. `ngreenblmax=17777` is removed: it is an XPS-panel value and this panel reports a different PWM
  period (400 on Linux). Everything else in the NootedGreen boot-args is upstream's tested set.
- **Audio.** AppleALC 1.9.8 with layout **15** (`alcid=15`; fallback 21). The codec is a Conexant **SN6140**
  (`0x14F11F87`), but AppleALC 1.9.8 only lists the CX8070 (`0x14F11F86`), so the layout may not be selected; if
  there is no sound, the fallback is a patched AppleALC or VoodooHDA. The XPS's AudShim/XeSpeakers SoundWire stack
  does not apply to this HDA codec.
- **Kexts.** `SMCDellSensors` entry removed (file kept, XPS-only). USB stays on default enumeration
  (`USBToolBox.kext` + `UTBDefault.kext`); a real map is deferred until Windows. `XHCI-unsupported` stays because it
  matches the PCH XHCI (`0x51ed8086`); it does not cover the Thunderbolt XHCI (`0xa71e8086`), so USB-C USB3 may be
  missing until a USB map is made.
- **Drivers.** `OpenHfsPlus.efi` enabled (open-source HFS+ driver bundled with OpenCore, no Apple binary needed).
- **SMBIOS.** MacBookPro16,2 stays (Tahoe-supported; board-id `Mac-5F9802EFE386AA28`). Serials are generated locally
  by `make-efi-linux.py` and written only to `dist/` (gitignored).

## Expected status

| Area | Expectation |
|---|---|
| Installer (no acceleration) | should boot on the firmware framebuffer; wired network needed (see below) |
| Metal desktop | unproven on A7A8: upstream issue [#8](https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe/issues/8) (HDMI `probePortState` panic) and [#17](https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe/issues/17) (eDP VBL timeout) |
| Internal panel / brightness | `SSDT-PNLF` targets `\_SB.PC00.GFX0`; 60 Hz may avoid the VBL timeout; untested |
| Audio | AppleALC layout 15, fallback 21; codec ID mismatch may prevent it loading |
| Touchpad / keyboard | VoodooI2C + VoodooI2CHID; keyboard on VoodooPS2 |
| Wi-Fi / Bluetooth | AirportItlwm after install; IntelBluetoothFirmware |
| Battery / NVMe | SMCBatteryManager, NVMeFix |
| Camera | UVC, should work with the built-in driver |
| Sleep | likely broken (Modern Standby only; use display sleep) |
| HDMI | untested and risky on A7A8 |
| Fingerprint / haptics / touchscreen | XPS-only tools; this model's hardware is not adapted |

## Build the EFI (Linux)

No Mac needed. Python 3 is enough; the script downloads `macserial.linux` from the matching OpenCore release:

```sh
git clone https://github.com/dxnz-id/Hackintosh-IdeapadSlim5-14IRH10-IrisXe-Tahoe.git
cd Hackintosh-IdeapadSlim5-14IRH10-IrisXe-Tahoe
python3 make-efi-linux.py        # -> dist/EFI + dist/EFI-IdeaPad-Slim5-14IRH10.zip
```

`dist/` contains **your** serial, MLB, UUID and ROM. Keep it private and never commit it. The macOS-only
`make-efi.sh` still exists for upstream; on this branch use the Python script.

## Installer USB (recovery via OpenCore, no Mac/VM)

1. Make a GPT USB with two FAT32 partitions: `EFI` (200 MB+) and `DATA` (the rest, 16 GB is plenty).
2. Download the Tahoe recovery with the board-id of **MacBookPro16,2** and the `latest` OS type. The script is in the
   OpenCore release (`Utilities/macrecovery/`):
   ```sh
   python3 macrecovery.py -b Mac-5F9802EFE386AA28 -m 00000000000000000 -os latest download
   ```
   It creates `com.apple.recovery.boot/` in the current directory. (`-os latest` is required; the default OS type can
   return an older release.)
3. Copy `dist/EFI/` (the `EFI` folder itself) to the `EFI` partition and `com.apple.recovery.boot/` to the root of
   `DATA`.
4. On the USB, swap the configs: rename `config.plist` to `config-accelerated.plist`, then `config-install.plist` to
   `config.plist`. OpenCore only reads `config.plist`.
5. **Network:** the install config uses `itlwm.kext`, which has no UI in Recovery. Connect a **USB-C Ethernet adapter**
   (Realtek RTL8153/RTL8156 or ASIX AX88179 work with macOS's built-in drivers) or use iPhone USB tethering. The
   installer downloads the full OS from Apple. AirportItlwm's native Wi-Fi is for the installed system; never enable
   `itlwm` and `AirportItlwm` together.
6. BIOS: Secure Boot **off**, VMD/Intel RST **off** (NVMe/AHCI), VT-d **on**, Fast Startup **off**, UEFI only, CSM
   off, USB boot enabled.
7. Boot the USB → OpenCore → **macOS Base System** → Disk Utility → erase the external SSD as APFS/GUID → install.
8. After the first boot, mount the USB EFI and restore the accelerated config: `config.plist` → `config-install.plist`,
   `config-accelerated.plist` → `config.plist`. Reboot.

## After installation

```sh
xcode-select --install          # Command Line Tools
git clone <this repo> ~/Ideapad-Tahoe && cd ~/Ideapad-Tahoe
zsh install.sh                  # builds NootedGreen, HookCase, Metal driver, libxedrv, shader compiler
```

Copy `build/NootedGreen.kext` to `EFI/OC/Kexts/` on the EFI, approve the extension if macOS asks, reboot, then check:

```sh
kmutil showloaded | grep NootedGreen
system_profiler SPDisplaysDataType | grep -i metal
ioreg -rc IntelAccelerator -d1 | grep xe-topo    # expect 48 EU, 6 L3
```

`install.sh` checks for macOS 26.7.1 build **25G241**. A newer recovery build only produces a warning, but the
NootedGreen byte patches (especially `-ngreenpm`) were verified on 25G241; if the boot hangs, use the install config
and remove `-ngreenpm` first.

After switching from `itlwm` to `AirportItlwm`, remove the old Ethernet service in System Settings › Network and add
Wi-Fi, so `en0` is the built-in Wi-Fi port (iMessage/FaceTime expect that).

## XPS-only tools (kept for upstream, not adapted here)

| Tool | Why it does not apply |
|---|---|
| `tools/AudShim`, `tools/XeSpeakers`, `tools/audio/` | XPS uses SoundWire + RT1316 amps; this laptop's CX8070 is driven by AppleALC |
| `tools/fingerprint/` | XPS Goodix 27C6:63BC; this model's reader (if fitted) is not adapted |
| `tools/xe-haptic`, `tools/xe-hapticbar` | XPS haptic touchpad; not applicable |
| `tools/xe-toque` | XPS touchscreen; this model has no touchscreen (check your SKU) |
| `tools/xe-pblock`, `tools/sleep/` | XPS power/lid behaviour; untested here and sleep is likely broken anyway |
| `tools/xe-brilho`, `tools/xe-temp`, `tools/xe-res`, `tools/xe-perfil` | generic XeShim/NootedGreen tools; **may** work on this panel, but untested |

Do not delete those directories: they are upstream work and keep the fork mergeable.

## Upstream documentation

The deep technical docs still describe the XPS 13 Plus and the shared NootedGreen stack:
[INSTALL](docs/INSTALL.md) · [STATUS](docs/STATUS.md) · [KERNEL-PATCHES](docs/KERNEL-PATCHES.md) ·
[METAL](docs/METAL.md) · [DEBUGGING](docs/DEBUGGING.md) · [HISTORY](docs/HISTORY.md) ·
[EXPERIMENTS](docs/EXPERIMENTS.md) · [CATALOG](docs/CATALOG.md).
`README.pt-BR.md` is the upstream Portuguese README; it is not machine-adapted.

## Credits and license

Upstream project by JulioNectar (Dell XPS 13 Plus 9320). NootedGreen by StezzaPilot, WhateverXe/OCLP by b00t0x and
jkbuha, BlackHole by Existential Audio, SOF/SoundWire work from Intel and the Linux `sound/soc/sof` drivers, itlwm by
laobamac/OpenIntelWireless, and the acidanthera kexts. See the upstream README and [NOTICE.md](NOTICE.md).

[Thou Shalt Not Profit License 1.0](LICENSE), the license of NootedGreen. Third-party kexts in `EFI/` keep their own
licenses. No Apple binaries are included.
