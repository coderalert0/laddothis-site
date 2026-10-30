#!/bin/bash
# Build the site's images from the app's own artwork and screens.
#
#   assets/img/art/<key>.webp        800x1000 portrait (bottom 4:5 of the e-card art)
#   assets/img/art/<key>-thumb.webp  160x200
#   assets/img/og/<key>.jpg          1200x630 share image
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

# site key -> e-card image set in the app
ART=(
  "anand-karaj:ECardSikhPunjabiAnandKarajRed"
  "golden-temple:ECardSikhPunjabi"
  "jaggo:ECardPunjabiJaggo"
  "hindu-punjabi:ECardHinduPunjabiWedding"
  "pakistani-mehndi:ECardPakistaniPunjabiMehndi"
  "nikah:ECardPakistaniPunjabiNikah"
  "sindhi-nikah:ECardSindhiMuslimNikah"
  "white-gown:ECardPakistaniPunjabiWalima"
  "garba:ECardGujaratiHinduSangeet"
  "south-indian:ECardSouthIndianWedding"
  "bengali:ECardBengaliHinduWedding"
  "marathi:ECardMaharashtriHinduWedding"
  "palace-lake:ECardHinduPunjabiReception"
  "sangeet:ECardHinduSangeet"
  "illustrated:ECardIllustratedWedding"
  "illustrated-night:ECardNightReception"
  "indo-caribbean:ECardIndoCaribbeanWedding"
  "first-dance:ECardReceptionFirstDanceTwirl"
)
for pair in "${ART[@]}"; do
  key="${pair%%:*}"; set_name="${pair#*:}"
  src="$(find "$XC/$set_name.imageset" -type f ! -name Contents.json | head -1)"
  # The art is 1024x1536 with empty sky at the top for invitation text; keep the bottom.
  magick "$src" -gravity south -crop 1024x1280+0+0 +repage -resize 800x1000 -quality 72 "$OUT/art/$key.webp"
  magick "$src" -gravity south -crop 560x700+0+0 +repage -resize 160x200 -quality 72 "$OUT/art/$key-thumb.webp"
  magick "$src" -gravity south -crop 1024x538+0+40 +repage -resize 1200x630 -quality 78 "$OUT/og/$key.jpg"
done

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
