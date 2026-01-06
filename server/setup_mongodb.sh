#!/bin/bash

echo "=== הגדרת MongoDB לפרויקט ==="
echo ""

# בדיקה אם קובץ .env כבר קיים
if [ -f ".env" ]; then
    echo "⚠ קובץ .env כבר קיים!"
    read -p "האם אתה רוצה להחליף אותו? (y/n): " replace
    if [ "$replace" != "y" ]; then
        echo "בוטל."
        exit 0
    fi
fi

echo "אנא הזן את ה-MongoDB Connection String:"
echo "דוגמה: mongodb+srv://username:password@cluster.mongodb.net/kids-money-manager"
echo ""
read -p "MONGODB_URI: " mongodb_uri

if [ -z "$mongodb_uri" ]; then
    echo "❌ לא הוזן connection string. בוטל."
    exit 1
fi

# יצירת קובץ .env
cat > .env << ENVEOF
MONGODB_URI=$mongodb_uri
PORT=3001
ENVEOF

echo ""
echo "✅ קובץ .env נוצר בהצלחה!"
echo ""
echo "כעת הפעל מחדש את השרת:"
echo "  pkill -f 'node.*server.js'"
echo "  cd ~/Projects/kids-money-manager"
echo "  npm run dev:all"
