# הוראות התחברות ל-Railway CLI

## הבעיה:
ההתחברות לא נשמרה או לא עובדת.

## פתרון:

### שלב 1: התחבר מחדש
```bash
cd ~/Projects/kids-money-manager/server
railway login
```

זה יפתח דפדפן - התחבר שם.

### שלב 2: קשר את הפרויקט (אם צריך)
```bash
railway link
```
בחר את הפרויקט שלך מהרשימה.

### שלב 3: הוסף את המשתנים
```bash
railway variables --set "TWILIO_ACCOUNT_SID=[TWILIO_ACCOUNT_SID]"
railway variables --set "TWILIO_AUTH_TOKEN=[TWILIO_AUTH_TOKEN]"
railway variables --set "TWILIO_PHONE_NUMBER=[TWILIO_PHONE_NUMBER]"
```

### שלב 4: בדוק שהמשתנים נוספו
```bash
railway variables | grep -i twilio
```

## או דרך Dashboard (הכי פשוט):

1. לך ל: https://railway.app
2. בחר את הפרויקט → Service → Variables
3. הוסף את 3 המשתנים:
   - TWILIO_ACCOUNT_SID = [TWILIO_ACCOUNT_SID]
   - TWILIO_AUTH_TOKEN = [TWILIO_AUTH_TOKEN]
   - TWILIO_PHONE_NUMBER = [TWILIO_PHONE_NUMBER]
