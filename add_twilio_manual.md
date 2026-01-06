# הוספת משתני Twilio ידנית

אם Railway CLI לא עובד, אפשר להוסיף ידנית:

## דרך 1: Railway Dashboard

1. לך ל: https://railway.app
2. בחר את הפרויקט שלך
3. לחץ על ה-Service (אם יש כמה, נסה את כולם)
4. לך ל-Tab "Variables"
5. הוסף את המשתנים הבאים:

### משתנה 1:
- **Key**: `TWILIO_ACCOUNT_SID`
- **Value**: [העתק את Account SID]

### משתנה 2:
- **Key**: `TWILIO_AUTH_TOKEN`
- **Value**: [העתק את Auth Token]

### משתנה 3:
- **Key**: `TWILIO_PHONE_NUMBER`
- **Value**: [המספר בפורמט +972XXXXXXXXX]

## דרך 2: Railway CLI

אם יש לך Railway CLI מותקן:

```bash
cd server
railway variables set TWILIO_ACCOUNT_SID="הערך שלך"
railway variables set TWILIO_AUTH_TOKEN="הערך שלך"
railway variables set TWILIO_PHONE_NUMBER="+972XXXXXXXXX"
```

## דרך 3: דרך GitHub Actions / CI/CD

אפשר גם להוסיף דרך GitHub Secrets ואז להשתמש ב-Railway GitHub Integration.
