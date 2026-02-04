# הגדרת Webhook ל-Meta WhatsApp

## הבעיה שלך:

1. **שליחה עובדת** ✅ - כשאתה שולח test whatsapp מהמסך, ההודעה מגיעה למספר הזמני (+15551543922)
   - זה אומר ש-Meta WhatsApp API עובד לשליחה

2. **קבלת הודעות לא עובדת** ❌ - כשאתה שולח הודעה למספר הזמני, אתה לא מקבל אישור
   - זה אומר שה-webhook לא מוגדר או לא עובד

3. **Twilio עובד** ✅ - כשאתה שולח מהמספר שלך (לא זמני), אתה מקבל אישור דרך Twilio
   - זה אומר ש-Twilio webhook עובד

## מה זה אומר?

**הבעיה:** ה-webhook של Meta WhatsApp לא מוגדר או לא עובד.

כשמישהו שולח הודעה למספר הזמני שלך (+15551543922), Meta צריך לשלוח webhook לשרת שלך, אבל זה לא קורה כי:
- ה-webhook לא מוגדר ב-Meta Business Suite
- או ה-webhook מוגדר אבל ה-URL לא נכון
- או ה-verify token לא נכון

## איך לתקן:

### שלב 1: הגדר Webhook ב-Meta Business Suite

1. לך ל-[Meta Business Suite](https://business.facebook.com/)
2. בחר את ה-Business Account שלך
3. לך ל-WhatsApp > API Setup
4. לחץ על "Edit" ליד "Webhook"
5. הוסף את ה-URL הבא:
   ```
   https://second-brain-6q8c.onrender.com/webhook
   ```
   או:
   ```
   https://second-brain-6q8c.onrender.com/whatsapp
   ```
   (שניהם עובדים, אבל `/webhook` הוא החדש)

6. הוסף את ה-Verify Token:
   - זה הערך של `WEBHOOK_VERIFY_TOKEN` ב-Render
   - או `WHATSAPP_VERIFY_TOKEN` (אם זה מה שהגדרת)

7. בחר את ה-Events:
   - ✅ `messages` - הודעות נכנסות
   - ✅ `message_status` - סטטוס הודעות

8. לחץ "Verify and Save"

### שלב 2: בדוק את ה-Environment Variables ב-Render

ודא שיש לך:
- `WEBHOOK_VERIFY_TOKEN` - אותו ערך שהוספת ב-Meta Business Suite
- או `WHATSAPP_VERIFY_TOKEN` - אם זה מה שהגדרת

### שלב 3: בדוק את הלוגים

אחרי שהגדרת את ה-webhook:
1. שלח הודעה למספר הזמני (+15551543922)
2. בדוק את הלוגים ב-Render
3. אתה אמור לראות:
   ```
   📱 WhatsApp Cloud API Webhook Received
   📨 Incoming Message:
      From: +972505717101
      Message: ...
   ```

### שלב 4: הוסף תשובה אוטומטית (אופציונלי)

אם תרצה לשלוח תשובה אוטומטית, תוכל להוסיף את זה ב-`/webhook` endpoint.

## איזה Endpoint להשתמש?

יש לך שני endpoints:
- `/webhook` - חדש, מיועד ל-Meta WhatsApp
- `/whatsapp` - קיים, מטפל גם ב-Meta וגם ב-Twilio

**מומלץ:** השתמש ב-`/webhook` ל-Meta WhatsApp, כי זה יותר נקי ומסודר.

## בדיקה מהירה:

1. שלח הודעה למספר הזמני (+15551543922)
2. בדוק את הלוגים ב-Render
3. אם אתה רואה "📱 WhatsApp Cloud API Webhook Received" - זה עובד! ✅
4. אם לא רואה כלום - ה-webhook לא מוגדר או לא עובד ❌

## פתרון בעיות:

### אם ה-webhook לא עובד:

1. **בדוק את ה-URL** - ודא שהוא נכון ונגיש
2. **בדוק את ה-Verify Token** - ודא שהוא תואם ב-Meta וב-Render
3. **בדוק את ה-Logs** - אולי יש שגיאות
4. **בדוק את ה-Events** - ודא ש-`messages` מופעל

### אם אתה רואה שגיאות:

- **403 Forbidden** - ה-verify token לא נכון
- **404 Not Found** - ה-URL לא נכון
- **500 Internal Server Error** - יש בעיה בקוד

## סיכום:

הבעיה היא שה-webhook לא מוגדר ב-Meta Business Suite. אחרי שתגדיר אותו, תוכל לקבל הודעות נכנסות ולשלוח תשובות אוטומטיות.
