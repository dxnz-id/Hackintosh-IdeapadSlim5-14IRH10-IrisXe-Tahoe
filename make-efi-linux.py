#!/usr/bin/env python3
"""Build dist/EFI with unique SMBIOS data, from Linux.

    python3 make-efi-linux.py            -> reuse saved SMBIOS, rebuild dist/EFI and zip
    python3 make-efi-linux.py --new-smbios -> generate new serial/MLB/UUID/ROM, save and rebuild

Every machine needs its own serial, MLB, UUID and ROM. This fills both config files:
  EFI/OC/config.plist          accelerated (NootedGreen on)
  EFI/OC/config-install.plist  for installing macOS (NootedGreen off, verbose)

SMBIOS data is saved to dist/smbios.json on first run (or with --new-smbios).
Keep dist/ private and never commit it.

The macOS-only make-efi.sh uses ditto/plutil; this script uses only the Python standard library and
macserial.linux from the matching OpenCore release.
"""
import base64
import json
import plistlib
import secrets
import shutil
import subprocess
import sys
import urllib.request
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OC_VER = "1.0.8"
DEPS = ROOT / "build" / "deps"
DIST = ROOT / "dist"
OC_DIR = DEPS / f"OpenCore-{OC_VER}"
MS = OC_DIR / "Utilities" / "macserial" / "macserial.linux"
ZIP_NAME = "EFI-IdeaPad-Slim5-14IRH10.zip"
SMBIOS_FILE = DIST / "smbios.json"


def ensure_macserial() -> None:
    if MS.exists():
        MS.chmod(0o755)
        return
    DEPS.mkdir(parents=True, exist_ok=True)
    archive = DEPS / "oc.zip"
    if not archive.exists():
        url = (
            f"https://github.com/acidanthera/OpenCorePkg/releases/download/{OC_VER}/"
            f"OpenCore-{OC_VER}-RELEASE.zip"
        )
        print(f"Downloading OpenCore {OC_VER} (macserial)...")
        urllib.request.urlretrieve(url, archive)
    print("Extracting macserial.linux...")
    with zipfile.ZipFile(archive) as zf:
        zf.extract("Utilities/macserial/macserial.linux", OC_DIR)
    MS.chmod(0o755)


def generate_smbios() -> tuple[str, str]:
    # stderr carries "arc4random is not available", so only parse stdout.
    out = subprocess.run(
        [str(MS), "-m", "MacBookPro16,2", "-g", "-n", "1"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    serial, mlb = (part.strip() for part in out.split("|", 1))
    if not serial or not mlb:
        sys.exit(f"Could not parse macserial output: {out!r}")
    return serial, mlb


def load_smbios() -> tuple[str, str, str, bytes] | None:
    """Return (serial, mlb, system_uuid, rom) from saved file, or None if missing."""
    if not SMBIOS_FILE.exists():
        return None
    data = json.loads(SMBIOS_FILE.read_text())
    return data["serial"], data["mlb"], data["uuid"], base64.b64decode(data["rom"])


def save_smbios(serial: str, mlb: str, system_uuid: str, rom: bytes) -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    SMBIOS_FILE.write_text(json.dumps({
        "serial": serial,
        "mlb": mlb,
        "uuid": system_uuid,
        "rom": base64.b64encode(rom).decode(),
    }, indent=2))


def main() -> None:
    new_smbios = "--new-smbios" in sys.argv

    ensure_macserial()

    saved = load_smbios()
    if new_smbios or saved is None:
        serial, mlb = generate_smbios()
        system_uuid = str(uuid.uuid4()).upper()
        rom = secrets.token_bytes(6)  # 6 random bytes; plist <data> is base64
        save_smbios(serial, mlb, system_uuid, rom)
        if new_smbios:
            print("Generated new SMBIOS data and saved to dist/smbios.json")
    else:
        serial, mlb, system_uuid, rom = saved
        print("Reusing saved SMBIOS from dist/smbios.json")

    out_efi = DIST / "EFI"
    if out_efi.exists():
        shutil.rmtree(out_efi)
    DIST.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "EFI", out_efi)

    for cfg in (out_efi / "OC" / "config.plist", out_efi / "OC" / "config-install.plist"):
        with open(cfg, "rb") as f:
            p = plistlib.load(f)
        generic = p["PlatformInfo"]["Generic"]
        generic["SystemProductName"] = "MacBookPro16,2"
        generic["SystemSerialNumber"] = serial
        generic["MLB"] = mlb
        generic["SystemUUID"] = system_uuid
        generic["ROM"] = rom
        with open(cfg, "wb") as f:
            plistlib.dump(p, f, sort_keys=False)
        with open(cfg, "rb") as f:
            plistlib.load(f)  # sanity check

    archive = DIST / ZIP_NAME
    archive.unlink(missing_ok=True)
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=DIST, base_dir="EFI")

    print(f"""
EFI ready: {out_efi}  (zip: {archive})
  Serial: {serial}
  MLB:    {mlb}
  UUID:   {system_uuid}

SMBIOS backup: {SMBIOS_FILE}
Keep dist/ private: it contains this machine's identity. Do not publish it.

Next steps:
  1. Copy dist/EFI to a FAT32 USB EFI partition.
  2. To INSTALL macOS: rename EFI/OC/config-install.plist to config.plist (keep the accelerated one).
  3. After installing: restore the accelerated config.plist and run install.sh from macOS.
  4. To regenerate serial numbers (new machine): python3 make-efi-linux.py --new-smbios
""")


if __name__ == "__main__":
    main()
