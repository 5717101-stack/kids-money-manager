#!/bin/bash

# Script to install Java JDK on macOS

echo "🔧 Installing Java JDK..."

ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    URL="https://api.adoptium.net/v3/installer/latest/17/ga/mac/aarch64/jdk/hotspot/normal/eclipse?project=jdk"
    echo "📥 Downloading Java for Apple Silicon (ARM64)..."
else
    URL="https://api.adoptium.net/v3/installer/latest/17/ga/mac/x64/jdk/hotspot/normal/eclipse?project=jdk"
    echo "📥 Downloading Java for Intel (x64)..."
fi

# Download Java
curl -L -o /tmp/openjdk.pkg "$URL"

if [ ! -f /tmp/openjdk.pkg ]; then
    echo "❌ Failed to download Java"
    echo "Please download manually from: https://adoptium.net/"
    exit 1
fi

echo "✅ Download complete"
echo "📦 Opening Java installer..."
open /tmp/openjdk.pkg

echo ""
echo "✅ Java installer opened!"
echo "📋 Please complete the installation:"
echo "   1. Click 'Continue' in the installer window"
echo "   2. Click 'Install'"
echo "   3. Enter your admin password"
echo "   4. Wait for installation to complete"
echo ""
echo "After installation, verify with:"
echo "   /usr/libexec/java_home -V"
echo ""
echo "Then run: ./setup_android_build.sh"
