# דיבוג בעיית SMS

## הבעיה
הקונטיינר נעצר מיד אחרי ההתחלה, אבל השרת עדיין רץ (health check עובד).

## מה עשיתי

### 1. שיפור Health Check
- הוספתי response מהיר יותר
- הוספתי heartbeat כל 30 שניות
- הגדלתי את ה-healthcheckTimeout ל-300 שניות

### 2. בדיקת SMS

**אם אתה רואה בלוגים:**
```
📨 === Sending OTP ===
📤 Attempting to send SMS...
```
זה אומר שהקוד רץ אבל יש שגיאה ב-Twilio.

**אם אתה לא רואה את זה:**
זה אומר שהבקשה לא מגיעה לשרת.

## מה לבדוק עכשיו

### 1. בדוק את הלוגים ב-Railway
אחרי ניסיון לשלוח SMS, חפש:
- `📨 === Sending OTP ===` - אם אתה רואה את זה, הקוד רץ
- `📤 Attempting to send SMS...` - אם אתה רואה את זה, Twilio מנסה לשלוח
- `✅ SMS sent successfully` - אם אתה רואה את זה, SMS נשלח
- `❌ Error sending SMS` - אם אתה רואה את זה, יש שגיאה

### 2. בדוק את ה-Console בדפדפן
פתח את ה-Developer Tools (F12) → Console
חפש שגיאות כמו:
- `Failed to fetch`
- `Network error`
- `CORS error`

### 3. בדוק את ה-Network Tab
פתח את ה-Developer Tools (F12) → Network
נסה לשלוח SMS שוב
חפש את הבקשה ל-`/api/auth/send-otp`
בדוק:
- האם הבקשה נשלחת? (Status: 200 או שגיאה)
- מה ה-Response? (האם יש שגיאה?)

### 4. בדוק את Twilio Console
1. היכנס ל: https://console.twilio.com
2. לך ל-Monitor → Logs → Errors
3. חפש שגיאות שנשלחו

## אם עדיין לא עובד

### בדוק את ה-URL
ודא שהאפליקציה שולחת ל-URL הנכון:
- Production: `https://kids-money-manager-production.up.railway.app/api`
- Development: `http://localhost:3001/api`

### בדוק את ה-Environment Variables
ב-Vercel, ודא שיש:
- `VITE_API_URL=https://kids-money-manager-production.up.railway.app/api`

### נסה לשלוח SMS ידנית
```bash
curl -X POST https://kids-money-manager-production.up.railway.app/api/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber":"505717101","countryCode":"+972"}'
```

אם זה עובד, הבעיה היא ב-frontend.
אם זה לא עובד, הבעיה היא ב-backend או ב-Twilio.

## הערות

- השרת עכשיו יש לו heartbeat כל 30 שניות
- Health check עונה מהר יותר
- הלוגים מפורטים מאוד - תראה בדיוק מה קורה

