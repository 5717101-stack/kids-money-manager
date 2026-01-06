# הוספת משתני Twilio - הוראות מהירות

## המשתנים להוספה:

1. **TWILIO_ACCOUNT_SID** = `[TWILIO_ACCOUNT_SID]`
2. **TWILIO_AUTH_TOKEN** = `[TWILIO_AUTH_TOKEN]`
3. **TWILIO_PHONE_NUMBER** = `[TWILIO_PHONE_NUMBER]`

## דרך מהירה:

1. לך ל: **https://railway.app**
2. בחר את הפרויקט שלך
3. לחץ על **כל Service** שאתה רואה
4. לך ל-Tab **"Variables"**
5. לחץ **"+ New Variable"**
6. העתק-הדבק את 3 המשתנים למעלה
7. שמור

## דרך CLI (אם אתה מחובר):

```bash
cd server
railway login  # אם לא מחובר
railway variables --set "TWILIO_ACCOUNT_SID=[TWILIO_ACCOUNT_SID]" --set "TWILIO_AUTH_TOKEN=[TWILIO_AUTH_TOKEN]" --set "TWILIO_PHONE_NUMBER=[TWILIO_PHONE_NUMBER]"
```

## בדיקה:

לך ל-Logs ותראה: "Twilio SMS service initialized" ✅
