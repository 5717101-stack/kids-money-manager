#!/bin/bash
# סקריפט מהיר להגדרת Git לאחר התקנת Xcode Command Line Tools

export PATH="$HOME/.local/node/bin:$PATH"

cd ~/Projects/kids-money-manager

echo "=== הגדרת Git ==="
echo ""

# בדוק Git
if ! git --version &> /dev/null; then
    echo "❌ Git לא עובד. ודא ש-Xcode Command Line Tools מותקן:"
    echo "   xcode-select --install"
    exit 1
fi

echo "✓ Git עובד: $(git --version)"
echo ""

# הגדר config אם לא מוגדר
if [ -z "$(git config --global user.name 2>/dev/null)" ]; then
    echo "⚠️ Git config לא מוגדר"
    echo "הרץ:"
    echo "  git config --global user.name 'השם שלך'"
    echo "  git config --global user.email 'your.email@example.com'"
    echo ""
fi

# חבר ל-repository
if [ ! -d ".git" ]; then
    echo "מחבר ל-Git repository..."
    git init
    git remote add origin https://github.com/5717101-stack/kids-money-manager.git
    git fetch origin
    git branch -M main
    echo "✓ מחובר ל-repository"
else
    echo "✓ כבר מחובר ל-Git"
    git remote -v
fi

echo ""
echo "✅ מוכן! כעת תוכל לעשות:"
echo "  git add ."
echo "  git commit -m 'תיאור'"
echo "  git push"
