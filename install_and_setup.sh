#!/bin/bash

echo "=== התקנת והגדרת Git ==="
echo ""

# בדוק אם Xcode tools מותקן
if xcode-select -p &> /dev/null; then
    echo "✓ Xcode Command Line Tools מותקן"
else
    echo "⚠️ Xcode Command Line Tools לא מותקן"
    echo "מתחיל התקנה..."
    xcode-select --install
    echo ""
    echo "⏳ חכה שההתקנה תסתיים (10-15 דקות)"
    echo "לאחר מכן הרץ שוב: ./install_and_setup.sh"
    exit 0
fi

# בדוק Git
if git --version &> /dev/null; then
    echo "✓ Git עובד: $(git --version)"
else
    echo "❌ Git לא עובד"
    exit 1
fi

echo ""

# הגדר Git config אם לא מוגדר
if [ -z "$(git config --global user.name 2>/dev/null)" ]; then
    echo "הגדרת Git config..."
    read -p "הכנס שם משתמש ל-Git: " git_name
    git config --global user.name "$git_name"
fi

if [ -z "$(git config --global user.email 2>/dev/null)" ]; then
    read -p "הכנס אימייל ל-Git: " git_email
    git config --global user.email "$git_email"
fi

echo ""
echo "✓ Git config:"
echo "  Name: $(git config --global user.name)"
echo "  Email: $(git config --global user.email)"
echo ""

# חבר ל-repository
cd ~/Projects/kids-money-manager

if [ ! -d ".git" ]; then
    echo "מחבר ל-Git repository..."
    git init
    git remote add origin https://github.com/5717101-stack/kids-money-manager.git 2>/dev/null || git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git
    git fetch origin 2>&1 | head -5
    git branch -M main 2>/dev/null
    echo "✓ מחובר ל-repository"
else
    echo "✓ כבר מחובר ל-Git"
    git remote -v
fi

echo ""
echo "=== סיום ==="
echo ""
echo "✅ Git מוכן לשימוש!"
echo ""
echo "כעת תוכל לעשות:"
echo "  git add ."
echo "  git commit -m 'תיאור השינויים'"
echo "  git push"
