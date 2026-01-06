#!/bin/bash
# שמירת Token ישירות ב-.git-credentials

echo "=== שמירת Token ישירות ==="
echo ""
read -p "הכנס את ה-GitHub Token שלך: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ לא הוזן Token"
    exit 1
fi

echo ""
echo "שומר Token..."

# צור את הקובץ .git-credentials
echo "https://5717101-stack:${GITHUB_TOKEN}@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials

# הגדר credential helper
git config --global credential.helper store

echo "✅ Token נשמר ב-~/.git-credentials"
echo ""
echo "בודק..."
git push origin main --dry-run 2>&1 | head -3

echo ""
echo "✅ הושלם! עכשיו אני אוכל לדחוף אוטומטית!"
