#!/bin/bash

# Script to build signed AAB for Google Play
# This script uses Android Studio's bundletool or manual signing

set -e

echo "🔨 בונה AAB חתום..."

cd "$(dirname "$0")"

# Build unsigned AAB first
echo "📦 בונה AAB לא חתום..."
cd android
./gradlew clean bundleProdRelease -x signProdReleaseBundle 2>&1 | tail -10

# Find the unsigned AAB
UNSIGNED_AAB="app/build/outputs/bundle/prodRelease/app-prod-release.aab"

if [ ! -f "$UNSIGNED_AAB" ]; then
    echo "❌ לא נמצא AAB לא חתום"
    exit 1
fi

echo "✅ נמצא AAB לא חתום: $UNSIGNED_AAB"

# Sign the AAB using jarsigner
echo "🔐 חותם את ה-AAB..."
KEYSTORE="../release.keystore"
KEYSTORE_PASS="android"
KEY_ALIAS="release"

# Extract, sign, and repackage
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Extract AAB
unzip -q "$OLDPWD/$UNSIGNED_AAB" -d .

# Sign all JAR files in the bundle
find . -name "*.jar" -exec jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 -keystore "$OLDPWD/$KEYSTORE" -storepass "$KEYSTORE_PASS" {} "$KEY_ALIAS" \;

# Create signed AAB
SIGNED_AAB="$OLDPWD/../app-prod-release-signed.aab"
zip -q -r "$SIGNED_AAB" .

# Clean up
cd "$OLDPWD"
rm -rf "$TEMP_DIR"

echo "✅ AAB חתום נוצר: $SIGNED_AAB"

# Copy to desktop
DESKTOP_DIR="$HOME/Desktop/Google_Play_Release"
mkdir -p "$DESKTOP_DIR"
cp "$SIGNED_AAB" "$DESKTOP_DIR/FamilyBank-5.0.9-signed.aab"

echo "✅ AAB חתום הועתק ל: $DESKTOP_DIR/FamilyBank-5.0.9-signed.aab"
ls -lh "$DESKTOP_DIR/FamilyBank-5.0.9-signed.aab"
