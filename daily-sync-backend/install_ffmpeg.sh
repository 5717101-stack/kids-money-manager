#!/bin/bash
# Script to install ffmpeg

echo "🔧 Installing ffmpeg..."

# Check if ffmpeg already exists
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ ffmpeg is already installed!"
    ffmpeg -version | head -1
    exit 0
fi

# Try to use Homebrew if available
if command -v brew >/dev/null 2>&1; then
    echo "📦 Using Homebrew to install ffmpeg..."
    brew install ffmpeg
    if command -v ffmpeg >/dev/null 2>&1; then
        echo "✅ ffmpeg installed successfully!"
        ffmpeg -version | head -1
        exit 0
    fi
fi

# Download ffmpeg directly
echo "📥 Downloading ffmpeg..."
mkdir -p /tmp/ffmpeg_install
cd /tmp/ffmpeg_install

curl -L -o ffmpeg.zip "https://evermeet.cx/ffmpeg/getrelease/zip" 2>/dev/null

if [ -f ffmpeg.zip ]; then
    unzip -q ffmpeg.zip
    if [ -f ffmpeg ]; then
        chmod +x ffmpeg
        
        # Try to copy to /usr/local/bin (requires sudo)
        echo "📋 Copying ffmpeg to /usr/local/bin (requires password)..."
        sudo cp ffmpeg /usr/local/bin/ 2>/dev/null
        sudo chmod +x /usr/local/bin/ffmpeg 2>/dev/null
        
        if command -v ffmpeg >/dev/null 2>&1; then
            echo "✅ ffmpeg installed successfully!"
            ffmpeg -version | head -1
            exit 0
        else
            echo "⚠️  ffmpeg downloaded but not in PATH"
            echo "   Location: /tmp/ffmpeg_install/ffmpeg"
            echo "   Add to PATH: export PATH=\"/tmp/ffmpeg_install:\$PATH\""
        fi
    fi
fi

echo "❌ Failed to install ffmpeg automatically"
echo "   Please install manually:"
echo "   1. brew install ffmpeg (if Homebrew is installed)"
echo "   2. Or download from: https://evermeet.cx/ffmpeg/"
exit 1
