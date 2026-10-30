#!/bin/bash
# Build the site's images from the app's own artwork and App Store screenshots.
#
#   assets/img/art/<key>.webp        800x1000 portrait (bottom 4:5 of the e-card art)
#   assets/img/art/<key>-thumb.webp  160x200
#   assets/img/og/<key>.jpg          1200x630 share image
#   assets/img/shots/<name>.webp     iPhone App Store screenshots, 600 wide
#   assets/img/ladoo-*.png           brand mark and icons
#
# Usage: tools/prep_images.sh [path/to/laddo-this]   (default ~/laddo-this). Needs ImageMagick 7.
set -euo pipefail
APP="${1:-$HOME/laddo-this}"
XC="$APP/LaddoThis/Assets.xcassets"
SITE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$SITE/assets/img"
mkdir -p "$OUT/art" "$OUT/og" "$OUT/shots"

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

# iPhone screenshots from the App Store listing (the app's own marketing images).
SHOTS=(
  "planner:PurpleSource211/v4/0e/e6/6a/0ee66ab5-4cc2-6825-833d-878314adaee5/complete_wedding_planner.png"
  "culture:PurpleSource221/v4/68/64/f8/6864f83b-602f-1f49-1cb8-8e4e3d6221a9/customized_culture.png"
  "ceremony:PurpleSource221/v4/8f/66/0c/8f660c3f-20cc-fcaf-aaa3-2fd47f33e314/ceremony_culture.png"
  "ecards:PurpleSource211/v4/89/62/01/896201ae-b294-f98d-41a8-01adba33fc0e/e-card_generator.png"
  "moodboard:PurpleSource221/v4/ea/23/24/ea232473-fc73-5755-8af4-a9de35810bde/mood_board.png"
  "budget:PurpleSource221/v4/4e/d5/c3/4ed5c366-144f-e5a3-cc60-f87865ac2afb/budget.png"
  "playlist:PurpleSource211/v4/c1/bd/ca/c1bdca1a-bb39-e253-4f21-f5590ab5dd59/playlist.png"
)
for pair in "${SHOTS[@]}"; do
  name="${pair%%:*}"; path="${pair#*:}"
  curl -sf "https://is1-ssl.mzstatic.com/image/thumb/$path/600x1300bb.webp" -o "$OUT/shots/$name.webp"
done

LADOO="$XC/LadooOnboarding.imageset/ladoo.png"
magick "$LADOO" -trim +repage -resize 64x64 -background none -gravity center -extent 64x64 "$OUT/ladoo-64.png"
magick "$LADOO" -trim +repage -resize 160x160 -background none -gravity center -extent 160x160 "$OUT/ladoo-160.png"
magick "$XC/AppIcon.appiconset/AppIcon.png" -resize 180x180 "$OUT/apple-touch-icon.png"
magick "$XC/AppIcon.appiconset/AppIcon.png" -resize 32x32 "$OUT/favicon-32.png"
du -sh "$OUT"
