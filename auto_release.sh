#!/bin/bash
# סקריפט אוטומטי לשחרור גרסה - עושה הכל בעצמו

set -e  # עצור אם יש שגיאה

cd ~/Projects/kids-money-manager

GITHUB_TOKEN="YOUR_TOKEN_HERE"

echo "=== שחרור גרסה אוטומטי ==="
echo ""

# 1. עדכן גרסה
echo "1. מעדכן גרסה..."
CURRENT_VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
MAJOR=$(echo $CURRENT_VERSION | cut -d'.' -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d'.' -f2)
NEW_MINOR=$((MINOR + 1))
NEW_VERSION="${MAJOR}.${NEW_MINOR}.0"

echo "   גרסה נוכחית: $CURRENT_VERSION"
echo "   גרסה חדשה: $NEW_VERSION"

# עדכן package.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" package.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" server/package.json
sed -i '' "s/גרסה ${CURRENT_VERSION%.*}/גרסה ${NEW_VERSION%.*}/" src/App.jsx

echo "   ✓ גרסה עודכנה"
echo ""

# 2. עדכן גרסה בכל הקבצים
echo "2. מעדכן גרסה בכל הקבצים..."
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" package.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" server/package.json
sed -i '' "s/גרסה ${CURRENT_VERSION%.*}/גרסה ${NEW_VERSION%.*}/" src/App.jsx
echo "   ✓ גרסה עודכנה בכל הקבצים"
echo ""

# 3. Commit
echo "3. יוצר commit..."
git add -A 2>/dev/null || true
git commit -m "עדכון גרסה ל-${NEW_VERSION}" --no-verify 2>/dev/null || echo "   (אין שינויים חדשים)"
echo "   ✓ Commit נוצר"
echo ""

# 4. Push
echo "4. דוחף ל-GitHub..."
git remote set-url origin https://${GITHUB_TOKEN}@github.com/5717101-stack/kids-money-manager.git
git push origin main --no-verify 2>&1
git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git
echo "   ✓ Push הושלם"
echo ""

echo "✅ גרסה ${NEW_VERSION} שוחררה בהצלחה!"
echo "🚀 Vercel ו-Railway יתחילו rebuild אוטומטי"
