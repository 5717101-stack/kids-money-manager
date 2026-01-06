#!/bin/bash
# סקריפט מהיר לדחיפה עם Token

echo "=== דחיפה ל-GitHub עם Token ==="
echo ""
echo "אם יש לך Personal Access Token, הכנס אותו:"
read -p "GitHub Token: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ לא הוזן Token"
    echo ""
    echo "צור Token ב: https://github.com/settings/tokens"
    exit 1
fi

echo ""
echo "דוחף ל-GitHub..."
git remote set-url origin https://${GITHUB_TOKEN}@github.com/5717101-stack/kids-money-manager.git
git push origin main

echo ""
echo "✅ הושלם!"
echo ""
echo "החזרתי את ה-URL המקורי..."
git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git
