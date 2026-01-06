#!/bin/bash
# סקריפט לשחרור גרסה - מעדכן גרסה אוטומטית + כל השינויים

set -e

cd ~/Projects/kids-money-manager

GITHUB_TOKEN="YOUR_TOKEN_HERE"

echo "=== שחרור גרסה אוטומטי ==="
echo ""

# 1. עדכן גרסה
CURRENT_VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
MAJOR=$(echo $CURRENT_VERSION | cut -d'.' -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d'.' -f2)
NEW_MINOR=$((MINOR + 1))
NEW_VERSION="${MAJOR}.${NEW_MINOR}.0"

echo "גרסה נוכחית: $CURRENT_VERSION → גרסה חדשה: $NEW_VERSION"
echo ""

# עדכן בכל הקבצים
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" package.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" server/package.json
sed -i '' "s/גרסה ${CURRENT_VERSION%.*}/גרסה ${NEW_VERSION%.*}/" src/App.jsx

echo "✓ גרסה עודכנה בכל הקבצים"
echo ""

# 2. Commit כל השינויים
echo "יוצר commit..."
git add -A
git commit -m "עדכון גרסה ל-${NEW_VERSION}" --no-verify
echo "✓ Commit נוצר"
echo ""

# 3. Push
echo "דוחף ל-GitHub..."
git remote set-url origin https://${GITHUB_TOKEN}@github.com/5717101-stack/kids-money-manager.git
git push origin main --no-verify
git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git
echo "✓ Push הושלם"
echo ""

echo "✅ גרסה ${NEW_VERSION} שוחררה בהצלחה!"
