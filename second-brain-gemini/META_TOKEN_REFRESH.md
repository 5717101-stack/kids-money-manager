# Meta WhatsApp Token Refresh Guide

## הבעיה
טוקנים של Meta WhatsApp Cloud API יכולים להיות שני סוגים:
- **Short-Lived Token** - תוקף 1 שעה בלבד! ⚠️
- **Long-Lived Token** - תוקף 60 יום ✅

אם אתה מקבל שגיאה אחרי כמה שעות, כנראה שיש לך **Short-Lived Token** שצריך להמיר ל-Long-Lived.

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

## איך לבדוק איזה סוג טוקן יש לך

המערכת בודקת אוטומטית את סוג הטוקן בהפעלה. תוכל גם לבדוק דרך ה-endpoint:
```
GET /whatsapp-provider-status
```

אם אתה רואה "Short-Lived" או "expires in X hours" - יש לך טוקן של שעה שצריך להמיר!

## איך ליצור Long-Lived Token (60 יום)

### דרך 1: Exchange Short-Lived Token (הכי קל!)
אם יש לך Short-Lived Token (שפג תוקף אחרי שעה), תוכל להמיר אותו ל-Long-Lived:

**חשוב:** צריך App ID ו-App Secret!

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

הטוקן החדש יהיה בתוקף 60 יום.

### דרך 2: Graph API Explorer
1. לך ל-[Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. בחר את ה-App שלך
3. בחר את ה-Permissions: `whatsapp_business_messaging`, `whatsapp_business_management`
4. לחץ על "Generate Access Token"
5. **חשוב:** הטוקן שיוצר כאן הוא Short-Lived! צריך להמיר אותו (ראה דרך 1)
6. העתק את הטוקן והשתמש בו כ-`WHATSAPP_CLOUD_API_TOKEN`

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
