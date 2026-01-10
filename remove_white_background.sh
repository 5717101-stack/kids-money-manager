#!/bin/bash

# Script to remove white background from app icon
# Uses sips to create a version with transparent background

ICON_FILE="app-icon.png"
OUTPUT_FILE="app-icon-transparent.png"

if [ ! -f "$ICON_FILE" ]; then
    echo "Error: $ICON_FILE not found"
    exit 1
fi

echo "Removing white background from $ICON_FILE..."

# Check if ImageMagick is available
if command -v convert &> /dev/null; then
    echo "Using ImageMagick to remove white background..."
    # Remove white background and make it transparent
    convert "$ICON_FILE" -fuzz 10% -transparent white "$OUTPUT_FILE"
    echo "✓ Created $OUTPUT_FILE with transparent background"
elif command -v magick &> /dev/null; then
    echo "Using ImageMagick (magick) to remove white background..."
    magick "$ICON_FILE" -fuzz 10% -transparent white "$OUTPUT_FILE"
    echo "✓ Created $OUTPUT_FILE with transparent background"
else
    echo "⚠ ImageMagick not found. Trying alternative method with sips..."
    # sips doesn't support removing backgrounds directly, but we can try to create a version
    # For now, just copy and note that manual editing might be needed
    cp "$ICON_FILE" "$OUTPUT_FILE"
    echo "⚠ Please use an image editor to remove the white background from $OUTPUT_FILE"
    echo "   Or install ImageMagick: brew install imagemagick"
fi
