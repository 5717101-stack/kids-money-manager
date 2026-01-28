#!/bin/bash

# Script to create iPad screenshots from iPhone screenshots
# Usage: ./create_ipad_screenshots.sh [path_to_iphone_screenshots]

set -e

IPHONE_DIR="${1:-ios/screenshots/iphone}"
IPAD_DIR="ios/screenshots/ipad"

echo "📱 יוצר צילומי מסך לאייפד מצילומי מסך לאייפון"
echo ""

# Create iPad directory if it doesn't exist
mkdir -p "$IPAD_DIR"

# Check if iPhone directory exists and has files
if [ ! -d "$IPHONE_DIR" ] || [ -z "$(ls -A "$IPHONE_DIR"/*.png "$IPHONE_DIR"/*.jpg 2>/dev/null)" ]; then
    echo "❌ לא נמצאו צילומי מסך לאייפון בתיקייה: $IPHONE_DIR"
    echo ""
    echo "💡 הוראות:"
    echo "   1. העתק את צילומי המסך לאייפון לתיקייה: $IPHONE_DIR"
    echo "   2. הרץ שוב: ./create_ipad_screenshots.sh"
    exit 1
fi

echo "✅ נמצאו צילומי מסך לאייפון ב: $IPHONE_DIR"
echo ""

# iPad screenshot sizes (Portrait and Landscape)
# iPad Pro 12.9" is the most common requirement
IPAD_SIZES=(
    "2048x2732"  # iPad Pro 12.9" Portrait
    "2732x2048"  # iPad Pro 12.9" Landscape
    "1668x2388"  # iPad Pro 11" Portrait
    "2388x1668"  # iPad Pro 11" Landscape
    "1536x2048"  # iPad 9.7" Portrait
    "2048x1536"  # iPad 9.7" Landscape
)

# Process each iPhone screenshot
for iphone_file in "$IPHONE_DIR"/*.{png,jpg,PNG,JPG} 2>/dev/null; do
    if [ ! -f "$iphone_file" ]; then
        continue
    fi
    
    filename=$(basename "$iphone_file")
    name_without_ext="${filename%.*}"
    ext="${filename##*.}"
    
    echo "📐 מעבד: $filename"
    
    # Get iPhone screenshot dimensions
    WIDTH=$(sips -g pixelWidth "$iphone_file" 2>/dev/null | grep pixelWidth | awk '{print $2}')
    HEIGHT=$(sips -g pixelHeight "$iphone_file" 2>/dev/null | grep pixelHeight | awk '{print $2}')
    
    if [ -z "$WIDTH" ] || [ -z "$HEIGHT" ]; then
        echo "   ⚠️  לא הצלחתי לקרוא את הגדלים, מדלג..."
        continue
    fi
    
    echo "   📏 גודל מקורי: ${WIDTH}x${HEIGHT}"
    
    # Create iPad screenshots for each size
    for size in "${IPAD_SIZES[@]}"; do
        IFS='x' read -r TARGET_WIDTH TARGET_HEIGHT <<< "$size"
        
        # Determine orientation
        if [ "$TARGET_HEIGHT" -gt "$TARGET_WIDTH" ]; then
            ORIENTATION="Portrait"
        else
            ORIENTATION="Landscape"
        fi
        
        # Create output filename
        output_file="$IPAD_DIR/${name_without_ext}_iPad_${TARGET_WIDTH}x${TARGET_HEIGHT}_${ORIENTATION}.${ext}"
        
        echo "   🖼️  יוצר: ${TARGET_WIDTH}x${TARGET_HEIGHT} (${ORIENTATION})"
        
        # Resize and crop to fit iPad dimensions
        # First, resize to fit the target dimensions while maintaining aspect ratio
        sips -z "$TARGET_HEIGHT" "$TARGET_WIDTH" "$iphone_file" --out "$output_file" 2>&1 > /dev/null
        
        # If the image doesn't match exactly, we need to crop or pad
        # For now, we'll use sips to resize which will maintain aspect ratio
        # You might need to adjust this based on your specific needs
        
        echo "      ✅ נוצר: $(basename "$output_file")"
    done
    
    echo ""
done

echo "✅ סיום!"
echo ""
echo "📁 צילומי המסך לאייפד נמצאים ב: $IPAD_DIR"
echo ""
echo "📋 קבצים שנוצרו:"
ls -lh "$IPAD_DIR"/*.png "$IPAD_DIR"/*.jpg 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
echo ""
echo "💡 עכשיו תוכל להעלות את הצילומים ל-App Store Connect"
