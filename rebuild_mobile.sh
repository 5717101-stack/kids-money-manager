#!/bin/bash

# Script to rebuild mobile app with latest version

echo "🔨 Rebuilding mobile app with latest version..."
echo ""

# Clean build
echo "1. Cleaning build cache..."
rm -rf dist
rm -rf node_modules/.vite
echo "   ✅ Cache cleared"
echo ""

# Build
echo "2. Building web assets..."
npm run build
if [ $? -ne 0 ]; then
    echo "   ❌ Build failed!"
    exit 1
fi
echo "   ✅ Build complete"
echo ""

# Check version in built files
echo "3. Checking version in built files..."
if [ -f "dist/index.html" ]; then
    echo "   ✅ dist/index.html exists"
    # Try to find version in JS bundle
    if [ -f "dist/assets/index-*.js" ]; then
        VERSION_FILE=$(ls dist/assets/index-*.js | head -1)
        if grep -q "3.11.11" "$VERSION_FILE" 2>/dev/null; then
            echo "   ✅ Version 3.11.11 found in bundle"
        else
            echo "   ⚠️  Version 3.11.11 not found in bundle (might be minified)"
        fi
    fi
else
    echo "   ❌ dist/index.html not found!"
    exit 1
fi
echo ""

# Sync with Capacitor
echo "4. Syncing with Capacitor..."
npx cap sync
if [ $? -ne 0 ]; then
    echo "   ❌ Capacitor sync failed!"
    exit 1
fi
echo "   ✅ Capacitor sync complete"
echo ""

echo "✅ Mobile app rebuild complete!"
echo ""
echo "📱 Next steps:"
echo "   iOS: npx cap open ios"
echo "   Android: npx cap open android"
echo ""
echo "   Then build and install on device"
