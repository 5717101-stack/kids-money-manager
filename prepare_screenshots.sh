#!/bin/bash

# Script to prepare App Store screenshots from source images
# Usage: ./prepare_screenshots.sh [source_image_path]

set -e

SOURCE_IMAGE="${1:-}"
DESKTOP_DIR="$HOME/Desktop/App_Store_Screenshots"
IPHONE_DIR="$DESKTOP_DIR/iPhone"
IPAD_DIR="$DESKTOP_DIR/iPad"

# Create directories
mkdir -p "$IPHONE_DIR" "$IPAD_DIR"

# iPhone screenshot sizes (most common)
IPHONE_SIZES=(
    "1290x2796"  # iPhone 14 Pro Max (6.7")
    "1284x2778"  # iPhone 13 Pro Max (6.7")
    "1242x2688"  # iPhone 11 Pro Max (6.5")
    "1242x2208"  # iPhone 8 Plus (5.5")
)

# iPad screenshot sizes
IPAD_SIZES=(
    "2048x2732"  # iPad Pro 12.9" Portrait
    "2732x2048"  # iPad Pro 12.9" Landscape
    "1668x2388"  # iPad Pro 11" Portrait
    "2388x1668"  # iPad Pro 11" Landscape
    "1536x2048"  # iPad 9.7" Portrait
    "2048x1536"  # iPad 9.7" Landscape
)

process_image() {
    local input_file="$1"
    local base_name=$(basename "$input_file")
    local name_without_ext="${base_name%.*}"
    local ext="${base_name##*.}"
    
    echo "📐 מעבד: $base_name"
    
    # Get original dimensions
    WIDTH=$(sips -g pixelWidth "$input_file" 2>/dev/null | grep pixelWidth | awk '{print $2}')
    HEIGHT=$(sips -g pixelHeight "$input_file" 2>/dev/null | grep pixelHeight | awk '{print $2}')
    
    if [ -z "$WIDTH" ] || [ -z "$HEIGHT" ]; then
        echo "   ⚠️  לא הצלחתי לקרוא את הגדלים, מדלג..."
        return 1
    fi
    
    echo "   📏 גודל מקורי: ${WIDTH}x${HEIGHT}"
    
    # Create iPhone screenshots
    echo "   📱 יוצר צילומי מסך לאייפון..."
    for size in "${IPHONE_SIZES[@]}"; do
        IFS='x' read -r TARGET_WIDTH TARGET_HEIGHT <<< "$size"
        output_file="$IPHONE_DIR/${name_without_ext}_iPhone_${TARGET_WIDTH}x${TARGET_HEIGHT}.${ext}"
        
        # Resize maintaining aspect ratio, then crop to exact size
        sips -z "$TARGET_HEIGHT" "$TARGET_WIDTH" "$input_file" --out "$output_file" 2>&1 > /dev/null
        
        # Crop to exact dimensions if needed
        CURRENT_W=$(sips -g pixelWidth "$output_file" 2>/dev/null | grep pixelWidth | awk '{print $2}')
        CURRENT_H=$(sips -g pixelHeight "$output_file" 2>/dev/null | grep pixelHeight | awk '{print $2}')
        
        if [ "$CURRENT_W" != "$TARGET_WIDTH" ] || [ "$CURRENT_H" != "$TARGET_HEIGHT" ]; then
            # Crop to center
            sips -c "$TARGET_HEIGHT" "$TARGET_WIDTH" "$output_file" --out "$output_file" 2>&1 > /dev/null
        fi
        
        echo "      ✅ iPhone ${TARGET_WIDTH}x${TARGET_HEIGHT}"
    done
    
    # Create iPad screenshots
    echo "   📱 יוצר צילומי מסך לאייפד..."
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
        sips -z "$TARGET_HEIGHT" "$TARGET_WIDTH" "$input_file" --out "$output_file" 2>&1 > /dev/null
        
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
}

# If source image provided, process it
if [ -n "$SOURCE_IMAGE" ] && [ -f "$SOURCE_IMAGE" ]; then
    process_image "$SOURCE_IMAGE"
else
    # Look for images in common locations
    echo "🔍 מחפש תמונות..."
    
    # Check Desktop
    for img in ~/Desktop/*.png ~/Desktop/*.jpg ~/Desktop/*.jpeg ~/Desktop/*.PNG ~/Desktop/*.JPG ~/Desktop/*.JPEG; do
        if [ -f "$img" ] 2>/dev/null; then
            process_image "$img"
        fi
    done
    
    # Check Downloads
    for img in ~/Downloads/*.png ~/Downloads/*.jpg ~/Downloads/*.jpeg ~/Downloads/*.PNG ~/Downloads/*.JPG ~/Downloads/*.JPEG; do
        if [ -f "$img" ] 2>/dev/null && [ -z "$SOURCE_IMAGE" ]; then
            # Only process recent files (last 24 hours)
            if [ -n "$(find "$img" -mtime -1 2>/dev/null)" ]; then
                process_image "$img"
            fi
        fi
    done
fi

echo "✅ סיום!"
echo ""
echo "📁 הצילומים נמצאים ב:"
echo "   iPhone: $IPHONE_DIR"
echo "   iPad: $IPAD_DIR"
echo ""
echo "📋 קבצים שנוצרו:"
echo ""
echo "📱 iPhone:"
ls -lh "$IPHONE_DIR"/*.{png,jpg,jpeg} 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}' || echo "   אין קבצים"
echo ""
echo "📱 iPad:"
ls -lh "$IPAD_DIR"/*.{png,jpg,jpeg} 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}' || echo "   אין קבצים"
