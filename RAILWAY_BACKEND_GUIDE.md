# איך לגשת ל-Backend ב-Railway

## שלב 1: התחברות ל-Railway

1. לך ל-https://railway.app
2. התחבר עם החשבון שלך (GitHub/Email)

## שלב 2: מציאת הפרויקט

1. ב-Dashboard תראה את כל הפרויקטים שלך
2. חפש את הפרויקט: **kids-money-manager** (או שם אחר אם שינית)
3. לחץ עליו

## שלב 3: מציאת ה-Backend Service

1. בתוך הפרויקט תראה את כל ה-Services:
   - **Frontend** (Vercel בדרך כלל, או service אחר)
   - **Backend** (זה מה שאתה מחפש!)

2. חפש service עם שם כמו:
   - `kids-money-manager-server`
   - `server`
   - או service שמריץ את `server.js`

3. **לחץ על ה-Backend Service**

## שלב 4: גישה ל-Variables (משתני סביבה)

1. אחרי שלחצת על ה-Backend Service, תראה תפריט:
   - **Deployments** - היסטוריית deployments
   - **Variables** ← **זה מה שאתה צריך!**
   - **Settings** - הגדרות
   - **Metrics** - סטטיסטיקות
   - **Logs** - לוגים

2. **לחץ על "Variables"**

## שלב 5: הוספת משתני Twilio

1. תראה רשימה של משתנים קיימים (כמו `MONGODB_URI`, `PORT`)
2. לחץ על **"+ New Variable"** או **"Add Variable"**
3. הוסף את 3 המשתנים:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_PHONE_NUMBER`

4. אחרי שתשמור, Railway יבצע **restart אוטומטי** של ה-service

## איך לזהות את ה-Backend Service?

- **שם**: בדרך כלל מכיל "server" או "backend"
- **נתיב**: אם יש GitHub repo, זה יהיה בתיקייה `server/`
- **Port**: בדרך כלל רץ על port 3001
- **Logs**: אם תפתח Logs, תראה הודעות כמו "Server running on..."

## אם לא מוצא את ה-Service:

1. בדוק אם יש לך יותר מפרויקט אחד ב-Railway
2. בדוק אם ה-service נקרא בשם אחר
3. אם אין service בכלל, אולי צריך ליצור אחד חדש:
   - לחץ "New Project"
   - בחר "Deploy from GitHub repo"
   - בחר את ה-repo שלך
   - בחר את התיקייה `server/`

## בדיקה שהכל עובד:

1. לך ל-Tab **"Logs"** ב-backend service
2. תראה הודעות כמו:
   - "Connected to MongoDB"
   - "Server running on..."
   - "Twilio SMS service initialized" (אם הגדרת נכון)

