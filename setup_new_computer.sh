#!/bin/bash

echo "=== התקנת הפרויקט במחשב חדש ==="
echo ""

# טען את nvm אם קיים
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    source "$NVM_DIR/nvm.sh"
    echo "✓ nvm נטען"
else
    echo "⚠️ nvm לא נמצא, מתקין..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
fi

# התקן Node.js LTS אם לא מותקן
if ! command -v node &> /dev/null; then
    echo "📦 מתקין Node.js LTS..."
    nvm install --lts
    nvm use --lts
    nvm alias default node
else
    echo "✓ Node.js כבר מותקן: $(node --version)"
fi

# בדוק גרסאות
echo ""
echo "=== גרסאות ==="
node --version
npm --version
echo ""

# עבור לתיקיית הפרויקט
cd "/Users/itzhakbachar/Family Bank/kids-money-manager"

# התקן תלויות frontend
echo "📦 מתקין תלויות frontend..."
npm install

# התקן תלויות backend
echo "📦 מתקין תלויות backend..."
cd server
npm install
cd ..

echo ""
echo "=== ✅ התקנה הושלמה! ==="
echo ""
echo "כדי להריץ את הפרויקט:"
echo "  npm run dev:all"
echo ""
echo "או בשני חלונות נפרדים:"
echo "  חלון 1: cd server && npm run dev"
echo "  חלון 2: npm run dev"
echo ""
