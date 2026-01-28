#!/bin/bash

# Script to process iPad screenshots to required resolutions
# Usage: ./process_ipad_screenshots.sh

set -e

IPAD_DIR="$HOME/Desktop/App_Store_Screenshots/iPad"

# iPad screenshot sizes
IPAD_SIZES=(
    "2048x2732"  # iPad Pro 12.9" Portrait
    "2732x2048"  # iPad Pro 12.9" Landscape
    "1668x2388"  # iPad Pro 11" Portrait
    "2388x1668"  # iPad Pro 11" Landscape
    "1536x2048"  # iPad 9.7" Portrait
    "2048x1536"  # iPad 9.7" Landscape
)

echo "📐 מעבד קבצים בתיקיית iPad..."
echo ""

# Find all image files that are not already processed
for img in "$IPAD_DIR"/*.png "$IPAD_DIR"/*.jpg "$IPAD_DIR"/*.jpeg "$IPAD_DIR"/*.PNG "$IPAD_DIR"/*.JPG "$IPAD_DIR"/*.JPEG; do
    if [ ! -f "$img" ]; then
        continue
    fi
    
    # Skip already processed files
    if [[ "$(basename "$img")" =~ _iPad_ ]]; then
        continue
    fi
    
    base_name=$(basename "$img")
    name_without_ext="${base_name%.*}"
    ext="${base_name##*.}"
    
    echo "📐 מעבד: $base_name"
    
    # Get original dimensions
    WIDTH=$(sips -g pixelWidth "$img" 2>/dev/null | grep pixelWidth | awk '{print $2}')
    HEIGHT=$(sips -g pixelHeight "$img" 2>/dev/null | grep pixelHeight | awk '{print $2}')
    
    if [ -z "$WIDTH" ] || [ -z "$HEIGHT" ]; then
        echo "   ⚠️  לא הצלחתי לקרוא את הגדלים, מדלג..."
        continue
    fi
    
    echo "   📏 גודל מקורי: ${WIDTH}x${HEIGHT}"
    echo "   📱 יוצר צילומי מסך לאייפד..."
    
    # Create iPad screenshots for each size
    for size in "${IPAD_SIZES[@]}"; do
        IFS='x' read -r TARGET_WIDTH TARGET_HEIGHT <<< "$size"
        
        # Determine orientation
        if [ "$TARGET_HEIGHT" -gt "$TARGET_WIDTH" ]; then
            ORIENTATION="Portrait"
        else
            ORIENTATION="Landscape"
        fi
        
        output_file="$IPAD_DIR/${name_without_ext}_iPad_${TARGET_WIDTH}x${TARGET_HEIGHT}_${ORIENTATION}.${ext}"
        
        # Resize maintaining aspect ratio
        sips -z "$TARGET_HEIGHT" "$TARGET_WIDTH" "$img" --out "$output_file" 2>&1 > /dev/null
        
        # Crop to exact dimensions if needed
        CURRENT_W=$(sips -g pixelWidth "$output_file" 2>/dev/null | grep pixelWidth | awk '{print $2}')
        CURRENT_H=$(sips -g pixelHeight "$output_file" 2>/dev/null | grep pixelHeight | awk '{print $2}')
        
        if [ "$CURRENT_W" != "$TARGET_WIDTH" ] || [ "$CURRENT_H" != "$TARGET_HEIGHT" ]; then
            # Crop to center
            sips -c "$TARGET_HEIGHT" "$TARGET_WIDTH" "$output_file" --out "$output_file" 2>&1 > /dev/null
        fi
        
        echo "      ✅ iPad ${TARGET_WIDTH}x${TARGET_HEIGHT} (${ORIENTATION})"
    done
    
    echo ""
done

echo "✅ סיום!"
echo ""
echo "📁 הצילומים נמצאים ב: $IPAD_DIR"
echo ""
echo "📋 קבצים שנוצרו:"
ls -lh "$IPAD_DIR"/*_iPad_*.{png,jpg,jpeg} 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}' || echo "   אין קבצים"
