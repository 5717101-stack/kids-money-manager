# בדיקת משתני Twilio ב-Railway

## הבעיה:
הלוגים לא מראים "Twilio SMS service initialized"

## פתרונות:

### 1. בדוק שהמשתנים הוגדרו נכון ב-Railway:
- לך ל-Railway Dashboard → הפרויקט → Service → Variables
- ודא שיש לך בדיוק:
  - `TWILIO_ACCOUNT_SID` (לא `TWILIO_ACCOUNT_SID ` עם רווח)
  - `TWILIO_AUTH_TOKEN` (לא `TWILIO_AUTH_TOKEN ` עם רווח)
  - `TWILIO_PHONE_NUMBER` (לא `TWILIO_PHONE_NUMBER ` עם רווח)

### 2. ודא שהערכים נכונים:
- TWILIO_ACCOUNT_SID = [TWILIO_ACCOUNT_SID]
- TWILIO_AUTH_TOKEN = [TWILIO_AUTH_TOKEN]
- TWILIO_PHONE_NUMBER = [TWILIO_PHONE_NUMBER]

### 3. בדוק אם יש שגיאות:
- לך ל-Logs ב-Railway
- חפש שגיאות או אזהרות

### 4. נסה Redeploy:
- ב-Railway Dashboard → Service → Settings
- לחץ "Redeploy" או "Deploy Latest"

### 5. בדוק את ה-Logs אחרי Redeploy:
- תראה אחד מהשניים:
  - ✅ "Twilio SMS service initialized" (אם הכל תקין)
  - ⚠️ "Twilio not configured - SMS will be logged to console only" (אם המשתנים לא הוגדרו)

## אם עדיין לא עובד:

1. מחק את המשתנים ב-Railway
2. הוסף אותם מחדש
3. ודא שאין רווחים לפני/אחרי השם או הערך
4. Redeploy
