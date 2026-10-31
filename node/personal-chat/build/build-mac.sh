#!/usr/bin/env bash
# build-mac.sh - build the Personal Chat Mac app and disk image, UNSIGNED.
#
#   UNTESTED. Written on a Windows PC (2026-10-30) with no Mac to run it on. Not one line of it
#   has executed. Treat the first run on a Mac as the test, and expect to fix it.
#
#   ./build-mac.sh --version 0.1.0 --ladder /path/to/ladder.json
#   ./build-mac.sh --version 0.1.0 --nodespec /path/to/NodeSpec.ps1     (needs pwsh)
#
# The ladder: NodeSpec.ps1 holds the ONLY copy. This script never restates it. Give it either
# a ladder.json exported by Export-Ladder.ps1 (the Windows build leaves one in dist/stage), or
# NodeSpec.ps1 plus pwsh so it can export one itself. With neither, it refuses.
#
# The tier on a Mac: NodeSpec.ps1 is Windows-only (master checklist C12, open), so a Mac
# install has no measured tier. The app then uses the ladder's CPU-only row and says
# "tier: unknown". Mapping Apple-silicon unified memory onto the ladder is a decision that
# belongs to NodeSpec.ps1, not to this script.
#
# HARD GATES: never signs, never notarises, never uploads. A Developer ID certificate and
# notarisation need an Apple Developer account (an owner spend, card V7). Until then Gatekeeper
# blocks the app on other Macs and it must not be distributed.
set -euo pipefail

VERSION="0.1.0"
LADDER=""
NODESPEC=""
PYTHON="${PYTHON:-python3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
APP="$ROOT/app"
OUT="$ROOT/dist-mac"

while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --ladder) LADDER="$2"; shift 2 ;;
    --nodespec) NODESPEC="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[ "$(uname -s)" = "Darwin" ] || { echo "build-mac.sh runs on macOS only" >&2; exit 2; }
echo "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || { echo "version must be x.y.z" >&2; exit 2; }

STAGE="$OUT/stage"; WORK="$OUT/work"; FINAL="$OUT/out"
rm -rf "$STAGE" "$WORK" "$FINAL"
mkdir -p "$STAGE" "$WORK" "$FINAL"

echo "== 1. ladder"
if [ -n "$LADDER" ]; then
  [ -f "$LADDER" ] || { echo "no ladder.json at $LADDER" >&2; exit 2; }
  cp "$LADDER" "$STAGE/ladder.json"
elif [ -n "$NODESPEC" ] && command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -File "$HERE/Export-Ladder.ps1" -NodeSpec "$NODESPEC" -Out "$STAGE/ladder.json"
else
  echo "need --ladder ladder.json, or --nodespec NodeSpec.ps1 with pwsh installed" >&2
  exit 2
fi
LADDER_SHA="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8-sig"))["sha256"])' "$STAGE/ladder.json")"

echo "== 2. build_info.json (preview: store not configured, unsigned)"
"$PYTHON" - "$STAGE/build_info.json" "$VERSION" "$LADDER_SHA" <<'PY'
import json, sys, datetime
path, version, sha = sys.argv[1:4]
json.dump({"version": version, "platform": "mac", "signed": False,
           "sale_enabled": False, "store_org_id": None, "store_host": "api.polar.sh",
           "store_hosts_allowed": ["api.polar.sh"], "max_seats": 3, "ladder_sha256": sha,
           "builtAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
          open(path, "w", encoding="utf-8"), indent=2)
PY

echo "== 3. PyInstaller freeze (.app)"
"$PYTHON" -c "import PyInstaller" || { echo "PyInstaller is not installed for $PYTHON" >&2; exit 2; }
"$PYTHON" -m PyInstaller --noconfirm --clean --onedir --windowed \
  --name "Personal Chat" --osx-bundle-identifier ai.etg.personalchat \
  --distpath "$STAGE" --workpath "$WORK" --specpath "$WORK" \
  --paths "$APP" \
  --add-data "$APP/static:static" \
  --add-data "$STAGE/ladder.json:." \
  --add-data "$STAGE/build_info.json:." \
  "$APP/personal_chat.py"
BUNDLE="$STAGE/Personal Chat.app"
[ -d "$BUNDLE" ] || { echo "PyInstaller reported success but $BUNDLE does not exist" >&2; exit 1; }

echo "== 4. disk image"
DMG="$FINAL/PersonalChat-$VERSION-UNSIGNED.dmg"
hdiutil create -volname "Personal Chat" -srcfolder "$BUNDLE" -ov -format UDZO "$DMG"

echo "== 5. result"
shasum -a 256 "$DMG"
echo "UNSIGNED PREVIEW. Not for distribution: signing and notarisation are card V7, selling is the Polar card."
