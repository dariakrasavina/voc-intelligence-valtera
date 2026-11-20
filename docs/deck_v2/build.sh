#!/bin/sh
# Render docs/deck_v2/deck.html -> docs/Valtera_VOC_Intelligence_deck.pdf with headless Chrome
cd "$(dirname "$0")"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=15000 --print-to-pdf="../Valtera_VOC_Intelligence_deck.pdf" "file://$PWD/deck.html" 2>/dev/null
echo "wrote docs/Valtera_VOC_Intelligence_deck.pdf"
