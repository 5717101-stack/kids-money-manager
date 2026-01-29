#!/bin/bash
# Script to fix and install ffmpeg

echo "🔧 Fixing ffmpeg installation..."

# Step 1: Remove broken ffmpeg
echo "📋 Step 1: Removing broken ffmpeg..."
sudo rm -f /usr/local/bin/ffmpeg
sudo rm -f /usr/local/bin/ffprobe

# Step 2: Try to download ffmpeg
echo "📥 Step 2: Downloading ffmpeg..."

# Try multiple download methods
DOWNLOAD_SUCCESS=false

# Method 1: Direct binary download (if available)
if curl -L -o /tmp/ffmpeg_binary "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip" 2>/dev/null; then
    if [ -f /tmp/ffmpeg_binary ]; then
        # Check if it's actually a binary
        if file /tmp/ffmpeg_binary | grep -q "Mach-O"; then
            echo "✅ Downloaded ffmpeg binary"
            sudo cp /tmp/ffmpeg_binary /usr/local/bin/ffmpeg
            sudo chmod +x /usr/local/bin/ffmpeg
            DOWNLOAD_SUCCESS=true
        elif file /tmp/ffmpeg_binary | grep -q "Zip"; then
            # It's a zip file, extract it
            unzip -q -o /tmp/ffmpeg_binary -d /tmp/ 2>/dev/null
            if [ -f /tmp/ffmpeg ]; then
                sudo cp /tmp/ffmpeg /usr/local/bin/ffmpeg
                sudo chmod +x /usr/local/bin/ffmpeg
                DOWNLOAD_SUCCESS=true
            fi
        fi
    fi
fi

# Method 2: Try alternative URL
if [ "$DOWNLOAD_SUCCESS" = false ]; then
    echo "📥 Trying alternative download method..."
    if curl -L -o /tmp/ffmpeg.zip "https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip" 2>/dev/null; then
        if [ -f /tmp/ffmpeg.zip ]; then
            unzip -q -o /tmp/ffmpeg.zip -d /tmp/ 2>/dev/null
            if [ -f /tmp/ffmpeg ]; then
                sudo cp /tmp/ffmpeg /usr/local/bin/ffmpeg
                sudo chmod +x /usr/local/bin/ffmpeg
                DOWNLOAD_SUCCESS=true
            fi
        fi
    fi
fi

# Step 3: Verify installation
if [ "$DOWNLOAD_SUCCESS" = true ]; then
    echo "✅ Step 3: Verifying installation..."
    if /usr/local/bin/ffmpeg -version >/dev/null 2>&1; then
        echo "✅ ffmpeg installed successfully!"
        /usr/local/bin/ffmpeg -version | head -1
        exit 0
    else
        echo "❌ ffmpeg file exists but doesn't work"
    fi
else
    echo "❌ Could not download ffmpeg automatically"
fi

# Step 4: Instructions for manual installation
echo ""
echo "📋 Manual installation required:"
echo ""
echo "Option 1: Install Homebrew first, then ffmpeg"
echo "  1. /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
echo "  2. eval \"\$(/opt/homebrew/bin/brew shellenv)\""
echo "  3. brew install ffmpeg"
echo ""
echo "Option 2: Download manually"
echo "  1. Go to: https://evermeet.cx/ffmpeg/"
echo "  2. Download the 'ffmpeg' file (green button)"
echo "  3. Run: sudo cp ~/Downloads/ffmpeg /usr/local/bin/"
echo "  4. Run: sudo chmod +x /usr/local/bin/ffmpeg"
echo ""
exit 1
