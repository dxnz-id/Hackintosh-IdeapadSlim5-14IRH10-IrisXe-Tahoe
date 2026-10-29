#!/bin/zsh
# Builds a ready-to-use OpenCore EFI for the Lenovo IdeaPad Slim 5 14IRH10 (i5-13420H) with YOUR OWN serial numbers.
#
#   zsh make-efi.sh                 -> dist/EFI and dist/EFI-IdeaPad-Slim5-14IRH10.zip (reuses saved SMBIOS)
#   zsh make-efi.sh --new-smbios   -> generate new serial, save, rebuild (use when changing machines)
#
# Every machine needs unique SMBIOS data (serial, MLB, UUID, ROM): sharing one set between machines breaks iCloud /
# iMessage and can get Apple IDs flagged. This script downloads Apple-compatible serial tooling (macserial, from the
# official OpenCore release that matches the EFI) and fills both config files:
#   EFI/OC/config.plist          accelerated (NootedGreen on)
#   EFI/OC/config-install.plist  for installing macOS (NootedGreen off, verbose boot)
# SMBIOS is saved to dist/smbios.json on first run and reused on every subsequent run so rebuilding never burns
# the serial. Use --new-smbios only when setting up a second machine.
# Works on macOS (uses the macOS macserial binary). On Linux, use python3 make-efi-linux.py instead.
set -e
ROOT=${0:A:h}
OC_VER=1.0.8
DEPS=$ROOT/build/deps; DIST=$ROOT/dist
SMBIOS=$DIST/smbios.json
mkdir -p $DEPS $DIST
MS=$DEPS/OpenCore-$OC_VER/Utilities/macserial/macserial
if [[ ! -x $MS ]]; then
  echo "== downloading OpenCore $OC_VER (macserial)"
  curl -fL -o $DEPS/oc.zip https://github.com/acidanthera/OpenCorePkg/releases/download/$OC_VER/OpenCore-$OC_VER-RELEASE.zip
  mkdir -p $DEPS/OpenCore-$OC_VER && (cd $DEPS/OpenCore-$OC_VER && unzip -q -o ../oc.zip 'Utilities/macserial/*')
  chmod +x $MS
fi

if [[ "$1" == "--new-smbios" || ! -f $SMBIOS ]]; then
  line=$($MS -m MacBookPro16,2 -g -n 1)
  SERIAL=${${line%% |*}// /}; MLB=${${line##*| }// /}
  UUID=$(uuidgen)
  ROM=$(openssl rand -base64 6)          # 6 random bytes (plist <data> is base64)
  printf '{"serial":"%s","mlb":"%s","uuid":"%s","rom":"%s"}\n' "$SERIAL" "$MLB" "$UUID" "$ROM" > $SMBIOS
  [[ "$1" == "--new-smbios" ]] && echo "Generated new SMBIOS and saved to dist/smbios.json" \
                               || echo "Generated SMBIOS and saved to dist/smbios.json"
else
  echo "Reusing saved SMBIOS from dist/smbios.json"
  SERIAL=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['serial'])" $SMBIOS)
  MLB=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['mlb'])" $SMBIOS)
  UUID=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['uuid'])" $SMBIOS)
  ROM=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['rom'])" $SMBIOS)
fi

rm -rf $DIST/EFI; ditto $ROOT/EFI $DIST/EFI
for c in $DIST/EFI/OC/config.plist $DIST/EFI/OC/config-install.plist; do
  plutil -replace PlatformInfo.Generic.SystemProductName -string MacBookPro16,2 $c
  plutil -replace PlatformInfo.Generic.SystemSerialNumber -string $SERIAL $c
  plutil -replace PlatformInfo.Generic.MLB -string $MLB $c
  plutil -replace PlatformInfo.Generic.SystemUUID -string $UUID $c
  plutil -replace PlatformInfo.Generic.ROM -data $ROM $c
  plutil -lint $c > /dev/null
done
rm -f $DIST/EFI-IdeaPad-Slim5-14IRH10.zip
(cd $DIST && ditto -c -k --keepParent EFI EFI-IdeaPad-Slim5-14IRH10.zip)
cat <<EOF

EFI ready: $DIST/EFI   (zip: $DIST/EFI-IdeaPad-Slim5-14IRH10.zip)
  Serial: $SERIAL   MLB: $MLB   UUID: $UUID
  SMBIOS saved: $SMBIOS
  Keep dist/ private: it contains this machine's identity. Do not publish it.

Next steps:
  1. Copy dist/EFI to a FAT32 USB EFI partition.
  2. To INSTALL macOS: rename EFI/OC/config-install.plist to config.plist (keep the original).
  3. After installing: restore the accelerated config.plist and run  zsh install.sh
  4. To regenerate serial numbers (new machine): zsh make-efi.sh --new-smbios
EOF
