#!/bin/bash
# Fix Homebrew installation and install ffmpeg

echo "🔧 Fixing Homebrew and installing ffmpeg..."

# Find where Homebrew is installed
if [ -f /opt/homebrew/bin/brew ]; then
    BREW_PATH="/opt/homebrew/bin/brew"
    echo "✅ Found Homebrew at: $BREW_PATH"
elif [ -f /usr/local/bin/brew ]; then
    BREW_PATH="/usr/local/bin/brew"
    echo "✅ Found Homebrew at: $BREW_PATH"
else
    echo "❌ Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Try again after installation
    if [ -f /opt/homebrew/bin/brew ]; then
        BREW_PATH="/opt/homebrew/bin/brew"
    elif [ -f /usr/local/bin/brew ]; then
        BREW_PATH="/usr/local/bin/brew"
    else
        echo "❌ Homebrew installation failed or incomplete"
        echo "   Please run manually: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
fi

# Add to PATH
BREW_DIR=$(dirname "$BREW_PATH")
echo "eval \"\$($BREW_DIR/brew shellenv)\"" >> ~/.zshrc

# Load it in current session
eval "$($BREW_PATH shellenv)"

# Check if brew works now
if command -v brew >/dev/null 2>&1; then
    echo "✅ Homebrew is now available!"
    brew --version | head -1
    
    echo ""
    echo "📦 Installing ffmpeg..."
    brew install ffmpeg
    
    if command -v ffmpeg >/dev/null 2>&1; then
        echo ""
        echo "✅ ffmpeg installed successfully!"
        ffmpeg -version | head -1
    else
        echo "⚠️ ffmpeg installation may need more time"
    fi
else
    echo "❌ Homebrew still not working"
    echo "   Try manually: export PATH=\"$BREW_DIR:\$PATH\""
    echo "   Then: brew install ffmpeg"
fi
