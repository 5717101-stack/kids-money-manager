#!/bin/bash

echo "=== בדיקת והגדרת Git ==="
echo ""

# בדוק אם Xcode tools מותקן
if ! xcode-select -p &> /dev/null; then
    echo "⏳ Xcode Command Line Tools עדיין לא מותקן"
    echo "ההתקנה יכולה לקחת 10-15 דקות"
    echo ""
    echo "אם ההתקנה הסתיימה, הרץ שוב:"
    echo "  ./auto_setup_git.sh"
    exit 0
fi

echo "✓ Xcode Command Line Tools מותקן"
echo ""

# בדוק Git
if ! git --version &> /dev/null; then
    echo "❌ Git לא עובד"
    exit 1
fi

echo "✓ Git עובד: $(git --version)"
echo ""

# הגדר Git config אם לא מוגדר
if [ -z "$(git config --global user.name 2>/dev/null)" ]; then
    echo "⚠️ Git config לא מוגדר"
    echo "הרץ:"
    echo "  git config --global user.name 'השם שלך'"
    echo "  git config --global user.email 'your.email@example.com'"
    echo ""
fi

# חבר ל-repository
cd ~/Projects/kids-money-manager

if [ ! -d ".git" ]; then
    echo "מחבר ל-Git repository..."
    git init
    git remote add origin https://github.com/5717101-stack/kids-money-manager.git 2>/dev/null || git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git
    git fetch origin 2>&1 | head -3
    git branch -M main 2>/dev/null
    echo "✓ מחובר ל-repository"
else
    echo "✓ כבר מחובר ל-Git"
    git remote -v 2>/dev/null | head -2
fi

echo ""
echo "✅ Git מוכן!"
echo ""
echo "כעת תוכל לעשות:"
echo "  git add ."
echo "  git commit -m 'תיאור השינויים'"
echo "  git push"
