# הגדרת Twilio לשליחת סיכומים ב-WhatsApp

## שלב 1: בדיקת חשבון Twilio

אם יש לך כבר חשבון Twilio, דלג לשלב 2.

אם אין לך חשבון:
1. לך ל-https://www.twilio.com/try-twilio
2. הירשם (חינם - מקבל $15.50 קרדיט)
3. אמת את מספר הטלפון שלך

## שלב 2: קבלת פרטי ההתחברות

1. היכנס ל-Twilio Console: https://console.twilio.com
2. בדף הבית (Dashboard) תראה:
   - **Account SID** - זה המזהה של החשבון שלך
   - **Auth Token** - זה הסיסמה (לחץ על "View" כדי לראות)

## שלב 3: הפעלת WhatsApp Sandbox (לבדיקות)

**חשוב:** Twilio מספקת WhatsApp Sandbox לבדיקות חינם!

1. ב-Twilio Console, לך ל-Messaging → Try it out → Send a WhatsApp message
2. תראה הוראות להצטרפות ל-Sandbox
3. שלח את הקוד שמופיע ל-WhatsApp של Twilio (בדרך כלל: join [קוד])
4. אחרי ההצטרפות, תראה את המספר של Twilio WhatsApp (בפורמט: `whatsapp:+14155238886`)

## שלב 4: קבלת מספר WhatsApp קבוע (אופציונלי - לפרודקשן)

אם אתה רוצה מספר קבוע (לא Sandbox):
1. לך ל-Messaging → Settings → WhatsApp Senders
2. לחץ "Add WhatsApp Sender"
3. בחר "Use a Twilio number" או "Use your own number"
4. עקוב אחר ההוראות לאימות

## שלב 5: הוספת משתני סביבה

הוסף את המשתנים הבאים לקובץ `.env` בפרויקט:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+972XXXXXXXXX
```

**הסבר:**
- `TWILIO_ACCOUNT_SID` - העתק מ-Dashboard
- `TWILIO_AUTH_TOKEN` - העתק מ-Dashboard (לחץ "View")
- `TWILIO_WHATSAPP_FROM` - המספר של Twilio WhatsApp (מה-Sandbox או מספר קבוע)
  - פורמט: `whatsapp:+14155238886` (עם `whatsapp:` בהתחלה)
- `TWILIO_WHATSAPP_TO` - המספר שלך (אליו יישלחו ההודעות)
  - פורמט: `whatsapp:+972XXXXXXXXX` (עם `whatsapp:` וקידומת המדינה)

**דוגמה:**
```bash
TWILIO_ACCOUNT_SID=your_account_sid_from_twilio_dashboard
TWILIO_AUTH_TOKEN=your_auth_token_from_twilio_dashboard
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+972505123456
```

## שלב 6: התקנת הספרייה

הספרייה כבר נוספה ל-`requirements.txt`. התקן אותה:

```bash
cd second-brain-gemini
source venv/bin/activate
pip install twilio==9.3.0
```

## שלב 7: בדיקה

1. הפעל את השרת:
   ```bash
   PORT=8001 python -m app.main
   ```

2. הרץ ניתוח חדש דרך הממשק
3. אחרי שהניתוח מסתיים, אתה אמור לקבל הודעת WhatsApp!

## פתרון בעיות

### הודעה לא מגיעה

1. **בדוק שהמשתנים נכונים:**
   ```bash
   # בדוק שהמשתנים נטענו
   python -c "from app.core.config import settings; print('SID:', settings.twilio_account_sid[:10] if settings.twilio_account_sid else 'NOT SET')"
   ```

2. **בדוק את הלוגים:**
   - חפש: `✅ Twilio client initialized successfully`
   - חפש: `📱 Sending WhatsApp message...`
   - חפש: `✅ WhatsApp message sent successfully!`

3. **בדוק ב-Twilio Console:**
   - לך ל-Monitor → Logs → Messages
   - תראה את כל ההודעות שנשלחו
   - אם יש שגיאה, תראה אותה שם

### שגיאת "Unsubscribed recipient"

**הבעיה:** המספר לא מאומת ב-WhatsApp Sandbox

**פתרון:**
1. לך ל-Messaging → Try it out → Send a WhatsApp message
2. שלח את הקוד שמופיע ל-WhatsApp של Twilio
3. אחרי ההצטרפות, נסה שוב

### שגיאת "Invalid 'To' Phone Number"

**הבעיה:** המספר לא בפורמט הנכון

**פתרון:** ודא שהמספר בפורמט: `whatsapp:+972505123456`
- חייב להתחיל ב-`whatsapp:`
- חייב להיות עם `+` וקידומת המדינה
- ללא רווחים או תווים נוספים

### שגיאת "From number not configured"

**הבעיה:** `TWILIO_WHATSAPP_FROM` לא מוגדר

**פתרון:** ודא שהוספת את המשתנה ב-`.env` בפורמט: `whatsapp:+14155238886`

## עלויות

- **WhatsApp Sandbox:** חינם לבדיקות (מוגבל למספרים מאומתים)
- **WhatsApp Production:** 
  - הודעות נכנסות: $0.005 לכל הודעה
  - הודעות יוצאות: $0.005 לכל הודעה
  - עם $15.50 קרדיט חינם יש לך מספיק לבדיקות רבות

## הערות חשובות

- **Sandbox מוגבל:** ב-Sandbox אתה יכול לשלוח רק למספרים שהצטרפו ל-Sandbox
- **Production:** לפרודקשן, תצטרך לאמת את המספר שלך ב-Twilio
- **תוכן ההודעה:** ההודעה כוללת סיכום קצר, משימות פעולה, ותובנות מפתח
- **PDF:** ההודעה כוללת הפניה להורדת PDF מלא מהמערכת

## דוגמה להודעה שתישלח

```
🧠 *סיכום יומי - Second Brain*
📅 תאריך: 2024-01-30

*סיכום כללי:*
יום של החלטות אסטרטגיות משמעותיות...

*✅ משימות פעולה:*
1. הודעה לצוות על השינוי [high]
2. תכנון מפגש אסטרטגי [medium]

*💡 תובנות מפתח:*
• חשוב לשמור על תקשורת פתוחה
• הצוות זקוק להנחיה ברורה

📄 לפרטים מלאים, הורד את ה-PDF מהמערכת
```
