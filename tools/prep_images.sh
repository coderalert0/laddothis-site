#!/bin/bash
# Build the site's images from the app's own artwork and screens.
#
#   assets/img/art/<key>.webp        800x1000 portrait (bottom 4:5 of the e-card art)
#   assets/img/art/<key>-thumb.webp  180x180, cropped around the people
#   assets/img/og/<key>.jpg          1200x630 share image, heads kept in
#   assets/img/screens/<name>.webp   app screens, 600 wide (the page draws the phone frame)
#   assets/img/ladoo-*.png           brand mark and icons
#
# Screens are raw iPhone 17 Pro simulator screenshots (1206x2622, no captions or
# backgrounds), taken with the app launched in demo mode:
#   xcrun simctl status_bar <udid> override --time 9:41 --batteryState charged --batteryLevel 100 --wifiBars 3 --cellularBars 4
#   xcrun simctl launch <udid> com.laddothis.app -uitesting -resetData -community "Sikh Punjabi" -side Bride \
#     -brideName Simran -groomName Arjun -weddingDate <~90 days out> -premium -marketingDemo -mockWeather
# then, inside the app: total budget set to $175,000 (the demo default of $50,000 shows every
# category over budget) and the Anand Karaj e-card given parents "Harjit & Manjit Gill" and venue
# "Gurdwara Sahib, Sacramento, CA". Save them as timeline, checklist (Maiyan), checklists,
# ecard, budget and gifts .png in SCREENS_SRC.
#
# Usage: [SCREENS_SRC=dir] tools/prep_images.sh [path/to/laddo-this]   (default ~/laddo-this). Needs ImageMagick 7.
set -euo pipefail
APP="${1:-$HOME/laddo-this}"
XC="$APP/LaddoThis/Assets.xcassets"
SITE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$SITE/assets/img"
mkdir -p "$OUT/art" "$OUT/og"

# Crops come from tools/art.json: per image, where the people's heads are (top) and how wide
# the group is (x). One "key set w h x y" line per output, computed here so every crop keeps heads in.
python3 - "$SITE/tools/art.json" > "$OUT/.crops" <<'PY'
import json, sys
art = {k: v for k, v in json.load(open(sys.argv[1])).items() if not k.startswith("_")}
W, H, MARGIN = 1024, 1536, 70
for key, a in art.items():
    top, (x1, x2) = a["top"], a["x"]
    # header art: bottom 4:5 of the image (1024x1280 from y=256); every top value is below 256
    print(key, a["set"], "art", 1024, 1280, 0, 256)
    # thumbnail: square wide enough for the group and tall enough to reach from the heads to the bottom
    side = min(W, max(x2 - x1 + 2 * MARGIN, H - (top - MARGIN)))
    x = max(0, min(W - side, (x1 + x2) // 2 - side // 2))
    y = max(0, min(top - MARGIN, H - side))
    print(key, a["set"], "thumb", side, side, x, y)
    # share image: 1200x630 ratio across the full width, heads plus margin inside
    h = round(W * 630 / 1200)
    print(key, a["set"], "og", W, h, 0, max(0, min(top - MARGIN, H - h)))
PY
while read -r key set_name kind w h x y; do
  src="$(find "$XC/$set_name.imageset" -type f ! -name Contents.json | head -1)"
  crop=(-crop "${w}x${h}+${x}+${y}" +repage)
  case "$kind" in
    art)   magick "$src" "${crop[@]}" -resize 800x1000 -quality 72 "$OUT/art/$key.webp" ;;
    thumb) magick "$src" "${crop[@]}" -resize 180x180 -quality 74 "$OUT/art/$key-thumb.webp" ;;
    og)    magick "$src" "${crop[@]}" -resize 1200x630 -quality 78 "$OUT/og/$key.jpg" ;;
  esac
done < "$OUT/.crops"
rm -f -- "$OUT/.crops"

if [ -n "${SCREENS_SRC:-}" ]; then
  mkdir -p "$OUT/screens"
  for f in "$SCREENS_SRC"/*.png; do
    magick "$f" -resize 600x -quality 80 "$OUT/screens/$(basename "${f%.png}").webp"
  done
fi

LADOO="$XC/LadooOnboarding.imageset/ladoo.png"
magick "$LADOO" -trim +repage -resize 64x64 -background none -gravity center -extent 64x64 "$OUT/ladoo-64.png"
magick "$LADOO" -trim +repage -resize 160x160 -background none -gravity center -extent 160x160 "$OUT/ladoo-160.png"
magick "$XC/AppIcon.appiconset/AppIcon.png" -resize 180x180 "$OUT/apple-touch-icon.png"
magick "$XC/AppIcon.appiconset/AppIcon.png" -resize 32x32 "$OUT/favicon-32.png"
du -sh "$OUT"
