# Meta WhatsApp Token Refresh Guide

## הבעיה
טוקנים של Meta WhatsApp Cloud API פגי תוקף אחרי 60 יום (או פחות אם זה Short-Lived Token). זה גורם לשגיאות "Session has expired" או "Error validating access token".

## הפתרון
הוספנו מנגנון רענון אוטומטי לטוקן. כשהטוקן פג תוקף, המערכת מנסה לרענן אותו אוטומטית.

## הגדרה

### אפשרות 1: רענון אוטומטי (מומלץ)
הוסף את המשתנים הבאים ב-Render:
```bash
WHATSAPP_APP_ID=your_meta_app_id
WHATSAPP_APP_SECRET=your_meta_app_secret
```

כך המערכת תרענן את הטוקן אוטומטית כשהוא פג תוקף.

### אפשרות 2: עדכון ידני
אם לא הוספת App ID ו-Secret, תצטרך לעדכן את `WHATSAPP_CLOUD_API_TOKEN` ידנית כשהוא פג תוקף.

## איך להשיג App ID ו-App Secret

1. לך ל-[Meta for Developers](https://developers.facebook.com/)
2. בחר את ה-App שלך
3. לך ל-Settings > Basic
4. העתק את **App ID** ו-**App Secret**

## איך ליצור Long-Lived Token (60 יום)

### דרך 1: Graph API Explorer
1. לך ל-[Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. בחר את ה-App שלך
3. בחר את ה-Permissions: `whatsapp_business_messaging`, `whatsapp_business_management`
4. לחץ על "Generate Access Token"
5. העתק את הטוקן והשתמש בו כ-`WHATSAPP_CLOUD_API_TOKEN`

### דרך 2: Exchange Short-Lived Token
אם יש לך Short-Lived Token, תוכל להמיר אותו ל-Long-Lived:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

הטוקן החדש יהיה בתוקף 60 יום.

## בדיקה
אחרי הוספת App ID ו-Secret, כשהטוקן פג תוקף:
1. המערכת תזהה את השגיאה
2. תנסה לרענן את הטוקן אוטומטית
3. תשלח את ההודעה מחדש עם הטוקן החדש

אם הרענון נכשל, תקבל הודעת שגיאה ברורה עם הוראות.

## הערות חשובות
- Long-Lived Tokens בתוקף 60 יום
- עם App ID ו-Secret, הרענון אוטומטי
- בלי App ID ו-Secret, תצטרך לעדכן ידנית כל 60 יום
- מומלץ להשתמש ב-Long-Lived Token + App ID/Secret לרענון אוטומטי
