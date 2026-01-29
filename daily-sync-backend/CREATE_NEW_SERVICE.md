# 🔧 יצירת Service חדש ב-Render

## הבעיה

ה-service הקיים נקרא "kids-money-manager" ומזהה Node.js במקום Python.

## פתרון: יצירת Service חדש

### שלב 1: צור Service חדש

1. לך ל-[Render Dashboard](https://dashboard.render.com/)
2. לחץ על **"New"** (למעלה מימין)
3. בחר **"Web Service"**
4. בחר את ה-repository: `5717101-stack/kids-money-manager`

### שלב 2: הגדר את ה-Service

**שם:**
```
daily-sync-backend
```

**Branch:**
```
main
```

**Root Directory:**
```
daily-sync-backend
```
⚠️ **זה החשוב ביותר!** זה אומר ל-Render שהקוד נמצא בתיקייה הזו.

**Environment:**
```
Python 3
```
⚠️ **לא Node.js!**

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python main.py
```

**Health Check Path:**
```
/health
```

### שלב 3: הוסף Environment Variables

לך ל-Settings → Environment Variables והוסף:

```
MONGODB_URI=mongodb+srv://BacharIsraeli:Rwv57m88!@bacharisraeli.xgmevpl.mongodb.net/daily_sync?appName=BacharIsraeli&retryWrites=true&w=majority
```

```
OPENAI_API_KEY=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
```

```
USE_WHISPER_API=true
```

```
CORS_ORIGINS=*
```

### שלב 4: Deploy

לחץ על **"Create Web Service"** או **"Manual Deploy"**

## הכתובת החדשה

אחרי ה-deploy, הכתובת תהיה:
```
https://daily-sync-backend.onrender.com
```

(או משהו דומה, תלוי בשם ה-service)

## בדיקה

אחרי ה-deploy, בדוק:
- `/health` - צריך להחזיר `{"status":"healthy"}`
- `/docs` - צריך להציג את ה-API documentation
- `/` - צריך להציג את דף ההעלאה

## הערות

- ה-service הישן "kids-money-manager" יכול להישאר (או למחוק אותו)
- ה-service החדש "daily-sync-backend" יהיה נפרד לחלוטין
- כל service ב-Render מקבל כתובת URL משלו

---

**💡 טיפ:** אם אתה רוצה לשנות את השם של ה-service הקיים במקום ליצור חדש, זה אפשרי ב-Settings → Name, אבל עדיף ליצור service חדש כדי לא לבלבל.
