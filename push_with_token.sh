#!/bin/bash
# סקריפט לדחיפה עם Token דרך URL

echo "=== דחיפה ל-GitHub עם Token ==="
echo ""
read -p "הכנס את ה-GitHub Token שלך: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ לא הוזן Token"
    echo ""
    echo "צור Token ב: https://github.com/settings/tokens"
    exit 1
fi

echo ""
echo "דוחף ל-GitHub..."

# שמור את ה-URL המקורי
ORIGINAL_URL=$(git remote get-url origin)

# שנה ל-URL עם Token
git remote set-url origin https://${GITHUB_TOKEN}@github.com/5717101-stack/kids-money-manager.git

# דחוף
git push origin main

# החזר את ה-URL המקורי
git remote set-url origin "$ORIGINAL_URL"

echo ""
if [ $? -eq 0 ]; then
    echo "✅ Push הושלם בהצלחה!"
    echo ""
    echo "💡 טיפ: כדי שזה יעבוד אוטומטית בעתיד,"
    echo "   השתמש ב-SSH: ./setup_ssh.sh"
else
    echo "❌ Push נכשל"
    exit 1
fi
