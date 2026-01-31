# ⏰ הגדרת Cron Job לעיבוד הקלטות פגישות

מדריך להגדרת background process שיבדוק Google Drive ויעבד הקלטות פגישות באופן אוטומטי.

## 📋 מה הסקריפט עושה

1. **בודק Google Drive** - מחפש קבצי אודיו חדשים בתיקיית Inbox
2. **מוריד קבצים** - מוריד זמנית לעיבוד
3. **מעבד עם Gemini** - מעלה ל-Gemini 1.5 Pro ומקבל סיכום בעברית
4. **שולח SMS** - שולח את הסיכום בהודעת SMS דרך Twilio
5. **מעביר לארכיון** - מעביר את הקובץ מתיקיית Inbox לתיקיית Archive

## 🔧 דרישות

### 1. Google Drive Service Account

צריך ליצור Service Account ב-Google Cloud:

1. לך ל-[Google Cloud Console](https://console.cloud.google.com)
2. בחר/צור project
3. לך ל-**APIs & Services** → **Credentials**
4. לחץ **Create Credentials** → **Service Account**
5. תן שם (לדוגמה: `drive-meeting-processor`)
6. לחץ **Create and Continue**
7. תן role: **Editor** (או **Drive API** → **Service Account User`)
8. לחץ **Done**

### 2. קבלת Credentials

1. לחץ על ה-Service Account שיצרת
2. לך ל-**Keys** tab
3. לחץ **Add Key** → **Create new key**
4. בחר **JSON**
5. הורד את הקובץ JSON

### 3. הגדרת Google Drive Folders

1. צור תיקייה ב-Google Drive בשם "Meeting Inbox"
2. צור תיקייה ב-Google Drive בשם "Meeting Archive"
3. שתף את שתי התיקיות עם ה-Service Account email (מה-JSON)
4. תן הרשאות: **Editor** (או **Viewer** + **Organizer**)
5. העתק את ה-Folder IDs מה-URL:
   - URL נראה כך: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - העתק את `FOLDER_ID_HERE`

### 4. הוספת Environment Variables ב-Render

לך ל-Render Dashboard → Service → **Environment** tab והוסף:

#### Google Drive Service Account (מה-JSON שהורדת):
```
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_PRIVATE_KEY_ID=your-private-key-id
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GOOGLE_CLIENT_EMAIL=your-service-account@project.iam.gserviceaccount.com
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
```

**⚠️ חשוב:** ב-`GOOGLE_PRIVATE_KEY`, ודא שיש `\n` אמיתיים (לא `\\n`). Render יטען את זה נכון.

#### Google Drive Folder IDs:
```
DRIVE_INBOX_ID=your-inbox-folder-id
DRIVE_ARCHIVE_ID=your-archive-folder-id
```

#### Phone Number:
```
MY_PHONE_NUMBER=+972505717101
```

#### Google Gemini (אם עוד לא הוספת):
```
GOOGLE_API_KEY=your-google-api-key
```

#### Twilio (אם עוד לא הוספת):
```
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_SMS_FROM=+17692878554
```

## 🚀 הגדרת Cron Job ב-Render

### אופציה 1: Render Cron Jobs (מומלץ)

1. ב-Render Dashboard, לחץ **"New +"** → **"Cron Job"**
2. הגדר:
   ```
   Name: process-meetings
   Schedule: 0 */6 * * *  (כל 6 שעות)
   Command: cd second-brain-gemini && python process_meetings.py
   Environment: Python 3
   ```
3. בחר את ה-repository שלך
4. הגדר **Root Directory**: `second-brain-gemini`
5. הוסף את כל ה-Environment Variables (כמו ב-Web Service)
6. לחץ **"Create Cron Job"**

### אופציה 2: Scheduled Job (Alternative)

אם אין Cron Jobs ב-Render שלך:

1. צור **Background Worker** חדש
2. הגדר **Start Command**: `python process_meetings.py`
3. השתמש ב-external scheduler (כמו [cron-job.org](https://cron-job.org)) שיקרא ל-webhook
4. או השתמש ב-GitHub Actions עם scheduled workflow

### אופציה 3: GitHub Actions Scheduled Workflow

צור `.github/workflows/process-meetings.yml`:

```yaml
name: Process Meeting Recordings

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:  # Allow manual trigger

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd second-brain-gemini
          pip install -r requirements.txt
      
      - name: Process meetings
        env:
          GOOGLE_PROJECT_ID: ${{ secrets.GOOGLE_PROJECT_ID }}
          GOOGLE_PRIVATE_KEY: ${{ secrets.GOOGLE_PRIVATE_KEY }}
          GOOGLE_CLIENT_EMAIL: ${{ secrets.GOOGLE_CLIENT_EMAIL }}
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_X509_CERT_URL: ${{ secrets.GOOGLE_CLIENT_X509_CERT_URL }}
          DRIVE_INBOX_ID: ${{ secrets.DRIVE_INBOX_ID }}
          DRIVE_ARCHIVE_ID: ${{ secrets.DRIVE_ARCHIVE_ID }}
          MY_PHONE_NUMBER: ${{ secrets.MY_PHONE_NUMBER }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          TWILIO_ACCOUNT_SID: ${{ secrets.TWILIO_ACCOUNT_SID }}
          TWILIO_AUTH_TOKEN: ${{ secrets.TWILIO_AUTH_TOKEN }}
          TWILIO_SMS_FROM: ${{ secrets.TWILIO_SMS_FROM }}
        run: |
          cd second-brain-gemini
          python process_meetings.py
```

## 🧪 בדיקה מקומית

לפני הפריסה, תוכל לבדוק מקומית:

```bash
cd second-brain-gemini

# הגדר environment variables
export GOOGLE_PROJECT_ID="..."
export GOOGLE_PRIVATE_KEY="..."
# ... וכו'

# הרץ את הסקריפט
python process_meetings.py
```

## 📊 לוגים

הסקריפט יוצר קובץ `process_meetings.log` עם כל הלוגים.

ב-Render, תוכל לראות את הלוגים ב:
- **Cron Job** → **Logs** tab
- או ב-**Events** tab

## ⚙️ הגדרת Schedule

### דוגמאות ל-Schedule:

- **כל שעה**: `0 * * * *`
- **כל 6 שעות**: `0 */6 * * *`
- **כל יום ב-9:00**: `0 9 * * *`
- **כל יום ב-9:00 ו-21:00**: `0 9,21 * * *`
- **כל יום ראשון ב-10:00**: `0 10 * * 0`

### פורמט Cron:
```
* * * * *
│ │ │ │ │
│ │ │ │ └── Day of week (0-7, 0 or 7 = Sunday)
│ │ │ └──── Month (1-12)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)
```

## 🔍 פתרון בעיות

### "Missing Google Drive credentials"
**פתרון:** ודא שהוספת את כל משתני ה-Service Account ב-Environment Variables

### "Permission denied" ב-Google Drive
**פתרון:** ודא ששיתפת את התיקיות עם ה-Service Account email

### "File processing timeout"
**פתרון:** קבצים גדולים לוקחים יותר זמן. אפשר להגדיל את `max_wait` ב-`process_meetings.py`

### "SMS not sent"
**פתרון:** בדוק ש-`TWILIO_SMS_FROM` ו-`TWILIO_SMS_TO` מוגדרים נכון

## 📝 הערות

- הסקריפט מטפל בשגיאות - אם קובץ אחד נכשל, הוא ממשיך לקובץ הבא
- קבצים זמניים נמחקים אוטומטית
- קבצים מעובדים מועברים לארכיון
- הסיכום מוגבל ל-1500 תווים (גבול SMS)

## 🔗 קישורים שימושיים

- [Render Cron Jobs Docs](https://render.com/docs/cron-jobs)
- [Google Drive API Docs](https://developers.google.com/drive/api)
- [Cron Expression Generator](https://crontab.guru/)

---

**💡 טיפ:** התחל עם schedule של כל שעה לבדיקה, ואז שנה ל-6 שעות או יותר לפי הצורך.
