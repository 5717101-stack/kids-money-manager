#!/bin/bash
# סקריפט להוספת משתני Twilio ל-Railway

echo "=== הוספת משתני Twilio ל-Railway ==="
echo ""
echo "אנא הכנס את הפרמטרים הבאים:"
echo ""

read -p "TWILIO_ACCOUNT_SID: " TWILIO_ACCOUNT_SID
read -p "TWILIO_AUTH_TOKEN: " TWILIO_AUTH_TOKEN
read -p "TWILIO_PHONE_NUMBER (בפורמט +972XXXXXXXXX): " TWILIO_PHONE_NUMBER

echo ""
echo "בודק אם Railway CLI מותקן..."

if command -v railway &> /dev/null; then
    echo "✅ Railway CLI נמצא"
    echo ""
    echo "מתחבר ל-Railway..."
    cd server
    
    echo ""
    echo "מוסיף משתנים..."
    railway variables set TWILIO_ACCOUNT_SID="$TWILIO_ACCOUNT_SID" 2>&1
    railway variables set TWILIO_AUTH_TOKEN="$TWILIO_AUTH_TOKEN" 2>&1
    railway variables set TWILIO_PHONE_NUMBER="$TWILIO_PHONE_NUMBER" 2>&1
    
    echo ""
    echo "✅ משתנים נוספו!"
    echo ""
    echo "Railway יבצע restart אוטומטי של ה-service"
else
    echo ""
    echo "⚠️ Railway CLI לא מותקן"
    echo ""
    echo "מתקין Railway CLI..."
    export PATH="$HOME/.local/node22/bin:$PATH"
    npm install -g @railway/cli 2>&1 | tail -5
    
    if command -v railway &> /dev/null; then
        echo ""
        echo "✅ Railway CLI הותקן!"
        echo ""
        echo "עכשיו תתחבר:"
        echo "1. הרץ: railway login"
        echo "2. אחרי ההתחברות, הרץ שוב את הסקריפט הזה"
    else
        echo ""
        echo "❌ לא הצלחתי להתקין Railway CLI"
        echo ""
        echo "אפשרויות:"
        echo "1. התקן ידנית: npm install -g @railway/cli"
        echo "2. או הוסף ידנית ב-Railway Dashboard"
        echo ""
        echo "המשתנים להוספה:"
        echo "TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID"
        echo "TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN"
        echo "TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER"
    fi
fi
