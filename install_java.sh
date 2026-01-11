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
echo "📦 Installing Java (requires sudo password)..."
sudo installer -pkg /tmp/openjdk.pkg -target /

# Clean up
rm /tmp/openjdk.pkg

# Verify installation
sleep 2
if /usr/libexec/java_home -V &>/dev/null; then
    JAVA_HOME=$(/usr/libexec/java_home)
    echo "✅ Java installed successfully!"
    echo "📍 Java Home: $JAVA_HOME"
    export JAVA_HOME
    export PATH=$JAVA_HOME/bin:$PATH
    java -version
else
    echo "⚠️ Java installation may need a restart or manual verification"
fi
