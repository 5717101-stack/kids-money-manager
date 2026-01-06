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
echo "מוסיף משתנים ל-Railway..."

# נסה להוסיף דרך Railway CLI
if command -v railway &> /dev/null; then
    cd server
    railway variables set TWILIO_ACCOUNT_SID="$TWILIO_ACCOUNT_SID"
    railway variables set TWILIO_AUTH_TOKEN="$TWILIO_AUTH_TOKEN"
    railway variables set TWILIO_PHONE_NUMBER="$TWILIO_PHONE_NUMBER"
    echo "✅ משתנים נוספו בהצלחה!"
else
    echo ""
    echo "⚠️ Railway CLI לא מותקן"
    echo ""
    echo "אפשרויות:"
    echo "1. התקן Railway CLI: npm i -g @railway/cli"
    echo "2. או הוסף ידנית ב-Railway Dashboard"
    echo ""
    echo "המשתנים להוספה:"
    echo "TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID"
    echo "TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN"
    echo "TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER"
fi
