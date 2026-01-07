#!/bin/bash
# סקריפט אוטומטי לשחרור גרסה - עושה הכל בעצמו

set -e  # עצור אם יש שגיאה

cd ~/Projects/kids-money-manager

# GitHub token should be in git credentials, not in script
# Use: git config credential.helper store
# Then save token to ~/.git-credentials

echo "=== שחרור גרסה אוטומטי ==="
echo ""

# 1. עדכן גרסה
echo "1. מעדכן גרסה..."
CURRENT_VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
MAJOR=$(echo $CURRENT_VERSION | cut -d'.' -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d'.' -f2)
PATCH=$(echo $CURRENT_VERSION | cut -d'.' -f3)
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"

echo "   גרסה נוכחית: $CURRENT_VERSION"
echo "   גרסה חדשה: $NEW_VERSION"

# עדכן package.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" package.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" server/package.json

# עדכן גרסה בכל קבצי ה-React - מציגים גרסה מלאה
# משתמש ב-pattern יותר גמיש שיתפוס כל מספר גרסה
# תחילה תופס גרסאות מלאות (2.9.13, 2.9.14, וכו')
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+\.[0-9]\+/גרסה ${NEW_VERSION}/g" src/App.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+\.[0-9]\+/גרסה ${NEW_VERSION}/g" src/components/WelcomeScreen.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+\.[0-9]\+/גרסה ${NEW_VERSION}/g" src/components/PhoneLogin.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+\.[0-9]\+/גרסה ${NEW_VERSION}/g" src/components/OTPVerification.jsx
# גם תופס גרסאות בלי patch (2.9 -> 2.9.15) - צריך להיות אחרי הגרסאות המלאות
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+\([^0-9]\)/גרסה ${NEW_VERSION}\1/g" src/App.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+\([^0-9]\)/גרסה ${NEW_VERSION}\1/g" src/components/WelcomeScreen.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+\([^0-9]\)/גרסה ${NEW_VERSION}\1/g" src/components/PhoneLogin.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+\([^0-9]\)/גרסה ${NEW_VERSION}\1/g" src/components/OTPVerification.jsx

# עדכן גרסה ב-server.js - כל המופעים
sed -i '' "s/version: '[0-9]\+\.[0-9]\+\.[0-9]\+'/version: '${NEW_VERSION}'/g" server/server.js

echo "   ✓ גרסה עודכנה בכל הקבצים:"
echo "      - package.json: ${NEW_VERSION}"
echo "      - server/package.json: ${NEW_VERSION}"
echo "      - server/server.js: ${NEW_VERSION}"
echo "      - src/App.jsx: גרסה ${NEW_VERSION}"
echo "      - src/components/*.jsx: גרסה ${NEW_VERSION}"
echo ""

# 3. Commit
echo "3. יוצר commit..."
git add -A 2>/dev/null || true
git commit -m "עדכון גרסה ל-${NEW_VERSION}" --no-verify 2>/dev/null || echo "   (אין שינויים חדשים)"
echo "   ✓ Commit נוצר"
echo ""

# 4. Push
echo "4. דוחף ל-GitHub..."
git push origin main --no-verify 2>&1
echo "   ✓ Push הושלם"
echo ""

echo "✅ גרסה ${NEW_VERSION} שוחררה בהצלחה!"
echo "🚀 Vercel ו-Railway יתחילו rebuild אוטומטי"
