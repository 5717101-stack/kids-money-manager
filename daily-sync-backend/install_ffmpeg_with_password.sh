#!/bin/bash
# Script to install ffmpeg with password

PASSWORD="2882"

echo "🔧 Installing ffmpeg..."

# Check if already installed
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ ffmpeg is already installed!"
    ffmpeg -version | head -1
    exit 0
fi

# Try Homebrew first
if command -v brew >/dev/null 2>&1; then
    echo "📦 Installing ffmpeg via Homebrew..."
    echo "$PASSWORD" | sudo -S brew install ffmpeg 2>&1
    if command -v ffmpeg >/dev/null 2>&1; then
        echo "✅ ffmpeg installed successfully!"
        ffmpeg -version | head -1
        exit 0
    fi
fi

# Try to install Homebrew if not exists
if ! command -v brew >/dev/null 2>&1; then
    echo "📦 Installing Homebrew first..."
    echo "$PASSWORD" | sudo -S /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>&1
    
    # Add Homebrew to PATH
    if [ -f /opt/homebrew/bin/brew ]; then
        export PATH="/opt/homebrew/bin:$PATH"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f /usr/local/bin/brew ]; then
        export PATH="/usr/local/bin:$PATH"
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    # Now install ffmpeg
    if command -v brew >/dev/null 2>&1; then
        echo "📦 Installing ffmpeg..."
        brew install ffmpeg
        if command -v ffmpeg >/dev/null 2>&1; then
            echo "✅ ffmpeg installed successfully!"
            ffmpeg -version | head -1
            exit 0
        fi
    fi
fi

echo "❌ Could not install ffmpeg automatically"
echo "   Please try manually:"
echo "   1. Open Terminal"
echo "   2. Run: brew install ffmpeg"
echo "   3. Or download from: https://evermeet.cx/ffmpeg/"
exit 1
