#!/bin/bash

export PATH="$HOME/.local/node/bin:$PATH"

cd ~/Projects/kids-money-manager

echo "=== הגדרת Git לפרויקט ==="
echo ""

# בדוק אם Git מותקן
if ! command -v git &> /dev/null; then
    echo "❌ Git לא מותקן"
    echo ""
    echo "נדרש להתקין Xcode Command Line Tools:"
    echo "  xcode-select --install"
    echo ""
    echo "או להתקין Git דרך Homebrew:"
    echo "  brew install git"
    exit 1
fi

echo "✓ Git מותקן: $(git --version)"
echo ""

# הגדר Git config אם לא מוגדר
if [ -z "$(git config --global user.name)" ]; then
    echo "הגדרת Git config..."
    read -p "הכנס שם משתמש ל-Git: " git_name
    git config --global user.name "$git_name"
fi

if [ -z "$(git config --global user.email)" ]; then
    read -p "הכנס אימייל ל-Git: " git_email
    git config --global user.email "$git_email"
fi

echo ""
echo "✓ Git config:"
echo "  Name: $(git config --global user.name)"
echo "  Email: $(git config --global user.email)"
echo ""

# בדוק אם יש .git directory
if [ ! -d ".git" ]; then
    echo "מחבר את הפרויקט ל-Git repository..."
    git init
    git remote add origin https://github.com/5717101-stack/kids-money-manager.git 2>/dev/null || git remote set-url origin https://github.com/5717101-stack/kids-money-manager.git
    git fetch origin
    git branch -M main
    git branch --set-upstream-to=origin/main main 2>/dev/null || echo "Branch setup will be done on first push"
    echo "✓ הפרויקט מחובר ל-Git repository"
else
    echo "✓ הפרויקט כבר מחובר ל-Git"
    git remote -v
fi

echo ""
echo "=== סיום ==="
echo ""
echo "כעת תוכל לעשות:"
echo "  git add ."
echo "  git commit -m 'תיאור השינויים'"
echo "  git push"
