#!/bin/bash
# סקריפט להוספת משתני Twilio דרך Railway CLI

cd ~/Projects/kids-money-manager/server
export PATH="$HOME/.local/node22/bin:$PATH"

echo "=== הוספת משתני Twilio ל-Railway ==="
echo ""

# בדוק אם מחובר
echo "בודק התחברות ל-Railway..."
if railway whoami &>/dev/null; then
    echo "✅ מחובר ל-Railway"
else
    echo "❌ לא מחובר. צריך להתחבר:"
    echo ""
    echo "הרץ בעצמך:"
    echo "  cd ~/Projects/kids-money-manager/server"
    echo "  railway login"
    echo ""
    echo "אחרי ההתחברות, הרץ שוב:"
    echo "  ./add_twilio_cli.sh"
    exit 1
fi

echo ""
echo "מוסיף משתנים..."

# הוסף את המשתנים
railway variables --set "TWILIO_ACCOUNT_SID=[TWILIO_ACCOUNT_SID]" 2>&1
railway variables --set "TWILIO_AUTH_TOKEN=[TWILIO_AUTH_TOKEN]" 2>&1
railway variables --set "TWILIO_PHONE_NUMBER=[TWILIO_PHONE_NUMBER]" 2>&1

echo ""
echo "בודק שהמשתנים נוספו..."
railway variables 2>&1 | grep -i twilio

echo ""
echo "✅ הושלם!"
echo ""
echo "Railway יבצע restart אוטומטי של ה-service"
echo "בדוק את ה-Logs כדי לראות: 'Twilio SMS service initialized'"
