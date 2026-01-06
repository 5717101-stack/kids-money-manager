# הוספת משתני Twilio ל-Railway

## הפרמטרים שלך:

✅ **TWILIO_ACCOUNT_SID**: [TWILIO_ACCOUNT_SID]
✅ **TWILIO_AUTH_TOKEN**: [TWILIO_AUTH_TOKEN]
✅ **TWILIO_PHONE_NUMBER**: [TWILIO_PHONE_NUMBER]

## איך להוסיף ב-Railway Dashboard:

1. לך ל: https://railway.app
2. התחבר לחשבון שלך
3. בחר את הפרויקט שלך
4. לחץ על **כל Service** שאתה רואה (אם יש כמה)
5. לך ל-Tab **"Variables"**
6. לחץ **"+ New Variable"** או **"Add Variable"**
7. הוסף את 3 המשתנים הבאים:

### משתנה 1:
- **Key**: `TWILIO_ACCOUNT_SID`
- **Value**: `[TWILIO_ACCOUNT_SID]`

### משתנה 2:
- **Key**: `TWILIO_AUTH_TOKEN`
- **Value**: `[TWILIO_AUTH_TOKEN]`

### משתנה 3:
- **Key**: `TWILIO_PHONE_NUMBER`
- **Value**: `[TWILIO_PHONE_NUMBER]`

8. אחרי שתשמור כל משתנה, Railway יבצע **restart אוטומטי**

## איך לזהות את ה-Backend Service:

אם יש לך כמה Services:
- לך לכל Service
- פתח את ה-Tab **"Logs"**
- אם תראה הודעות כמו:
  - "Server running on..."
  - "Connected to MongoDB"
  - "Twilio SMS service initialized"
  
  **זה ה-Backend Service!**

## בדיקה שהכל עובד:

1. אחרי שהוספת את המשתנים, לך ל-Logs
2. תראה הודעה: **"Twilio SMS service initialized"**
3. נסה להריץ את האפליקציה ולהכניס מספר טלפון
4. אתה אמור לקבל SMS עם קוד OTP!

## אם לא מוצא את ה-Service:

- נסה להוסיף את המשתנים בכל ה-Services שיש לך
- זה לא יזיק - רק ה-Backend ישתמש בהם
