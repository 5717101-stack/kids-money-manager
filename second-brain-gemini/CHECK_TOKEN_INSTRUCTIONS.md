# איך לבדוק את הטוקן שלך

## דרך 1: דרך Render Dashboard (הכי קל)

1. לך ל-[Render Dashboard](https://dashboard.render.com)
2. בחר את השירות שלך: `second-brain-6q8c`
3. לך ל-**Environment** tab
4. מצא את `WHATSAPP_CLOUD_API_TOKEN` והעתק אותו
5. הרץ את הפקודה הבאה:

```bash
python3 check_token.py YOUR_TOKEN_HERE
```

## דרך 2: דרך ה-Endpoint (אחרי Deployment)

אחרי שהקוד החדש יעלה (בעוד כמה דקות), תוכל לבדוק דרך:

```bash
curl https://second-brain-6q8c.onrender.com/whatsapp-provider-status | python3 -m json.tool
```

תראה ב-`meta_config.token_info` את כל המידע על הטוקן.

## דרך 3: ישירות דרך Meta API

אם יש לך את הטוקן, תוכל לבדוק ישירות:

```bash
curl -X GET "https://graph.facebook.com/v18.0/debug_token?input_token=YOUR_TOKEN&access_token=YOUR_TOKEN"
```

## מה לחפש:

- **`expires_at`** - תאריך התפוגה
- אם `expires_at` הוא בעוד פחות מ-24 שעות → זה **Short-Lived Token** (שעה)
- אם `expires_at` הוא בעוד יותר מ-30 יום → זה **Long-Lived Token** (60 יום)

## אם הטוקן הוא Short-Lived:

תצטרך להמיר אותו ל-Long-Lived (ראה `META_TOKEN_REFRESH.md`).
