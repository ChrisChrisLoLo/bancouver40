#!/bin/sh
# sheets.html -> bancouver40_pb2_drawings.pdf (headless Chrome) -> per-page PNG previews (pdftoppm or sips)
set -e
cd "$(dirname "$0")"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --no-pdf-header-footer \
  --allow-file-access-from-files --print-to-pdf="$PWD/../bancouver40_pb2_drawings.pdf" "file://$PWD/sheets.html" 2>/dev/null
