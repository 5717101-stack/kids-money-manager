# פתרון בעיית Container שנעצר ב-Railway

## הבעיה
הקונטיינר נעצר עם SIGTERM למרות שהשרת רץ בהצלחה.

## מה עשיתי

### 1. שיפור Health Check
- שיניתי את ה-healthcheckPath ל-`/health` (יותר מהיר)
- ה-health check עכשיו עונה מיד ללא פעולות async
- הוספתי response מהיר יותר

### 2. הוספתי Heartbeat
- Heartbeat כל 30 שניות
- Heartbeat תכוף יותר ב-50 השניות הראשונות (כל 5 שניות)
- Ping עצמי ל-health check כדי לשמור אותו "חם"

### 3. שינוי railway.json
- healthcheckPath: `/health` (במקום `/api/health`)
- healthcheckTimeout: 100 שניות

## מה לבדוק עכשיו

### 1. בדוק את הלוגים ב-Railway
אחרי ה-deploy, תראה:
- `💓 Initial heartbeat 1/10` - ב-50 השניות הראשונות
- `💓 Heartbeat: Server is alive` - כל 30 שניות
- השרת לא אמור להיעצר

### 2. אם השרת עדיין נעצר
זה אומר שהבעיה היא ב-Railway configuration:
1. היכנס ל-Railway Dashboard
2. בחר את השירות
3. לך ל-Settings → Health Check
4. ודא ש:
   - Health Check Path: `/health`
   - Health Check Timeout: 100 שניות
   - Health Check Interval: 30 שניות

### 3. בדוק אם SMS עובד
אם השרת לא נעצר, נסה לשלוח SMS:
1. נסה דרך האפליקציה
2. בדוק את הלוגים - תראה:
   - `📨 === Sending OTP ===`
   - `📤 Attempting to send SMS...`
   - `✅ SMS sent successfully` או `❌ Error sending SMS`

## אם עדיין לא עובד

### אפשרות 1: Railway לא מזהה את השרת
- נסה לעשות Manual Redeploy
- בדוק את ה-Settings ב-Railway

### אפשרות 2: הבעיה היא ב-Twilio
- בדוק את הלוגים - אם אתה רואה `📨 === Sending OTP ===` אבל לא `✅ SMS sent`, הבעיה היא ב-Twilio
- קרא את `SMS_TROUBLESHOOTING.md`

### אפשרות 3: הבעיה היא ב-Frontend
- פתח Developer Tools (F12) → Console
- חפש שגיאות
- בדוק את ה-Network tab

## הערות

- השרת עכשיו יש לו heartbeat תכוף יותר ב-50 השניות הראשונות
- Health check עונה מהר יותר
- אם השרת עדיין נעצר, הבעיה היא ב-Railway configuration
