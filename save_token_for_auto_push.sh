#!/bin/bash
# סקריפט לשמירת Token ל-Push אוטומטי

echo "=== שמירת Token ל-Push אוטומטי ==="
echo ""
read -p "הכנס את ה-GitHub Token שלך: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ לא הוזן Token"
    exit 1
fi

echo ""
echo "שומר Token ב-credential store..."

# הגדר credential store
git config credential.helper store

# דחוף עם Token דרך URL (זה יישמר)
git remote set-url origin https://${GITHUB_TOKEN}@github.com/5717101-stack/kids-money-manager.git
git push origin main

# החזר את ה-URL הרגיל
git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git

echo ""
echo "✅ Token נשמר!"
echo ""
echo "עכשיו אני אוכל לדחוף אוטומטית בעתיד!"
echo ""
echo "בדיקה:"
git push origin main --dry-run 2>&1 | head -3
