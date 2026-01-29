# 🏠 עבודה מהבית - הוראות

## ✅ מה כבר נדחף ל-GitHub:

- ✅ כל הקוד של `daily-sync-backend/`
- ✅ כל המדריכים והקבצים
- ✅ כל ההגדרות (render.yaml, requirements.txt, runtime.txt)
- ✅ גרסה 6.0.0 של הפרויקט הראשי

## 🔧 מה לעשות בבית:

### שלב 1: משוך את השינויים

```bash
cd "/Users/itzhakbachar/Family Bank/kids-money-manager"
git pull
```

### שלב 2: עבור לתיקיית daily-sync-backend

```bash
cd daily-sync-backend
```

### שלב 3: צור/הפעל סביבה וירטואלית

**אם יש לך venv:**
```bash
source venv/bin/activate
```

**אם אין לך venv:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### שלב 4: הרץ את השרת מקומית (אופציונלי)

```bash
python main.py
```

השרת ירוץ על: `http://localhost:8000`

## 🚀 להמשך הטמעה ב-Render:

### מדריכים זמינים:

1. **`DEPLOY_NOW.md`** - הוראות הטמעה מהירות
2. **`CHECK_ENVIRONMENT.md`** - איך לבדוק את Environment ב-Render
3. **`FIX_RENDER_ROOT_DIR.md`** - תיקון בעיות Root Directory
4. **`CREATE_NEW_SERVICE.md`** - יצירת service חדש ב-Render

### מה צריך לעשות ב-Render:

1. לך ל-[Render Dashboard](https://dashboard.render.com/)
2. בדוק את ה-service `daily-sync-backend`
3. ודא ש-Environment = Python 3 (לא Node.js!)
4. Clear Build Cache
5. Manual Deploy

## 📋 קבצים חשובים:

- `requirements.txt` - כל התלויות
- `render.yaml` - הגדרות Render
- `runtime.txt` - גרסת Python
- `.env` - משתני סביבה (לא ב-GitHub - צריך ליצור מחדש)

## 🔑 משתני סביבה שצריך:

אם אתה צריך ליצור `.env` מחדש:

```bash
cp .env.example .env
# ערוך את .env והוסף:
# MONGODB_URI=...
# OPENAI_API_KEY=...
# USE_WHISPER_API=true
```

## 💡 טיפים:

- כל השינויים ב-GitHub - תוכל לעבוד מכל מחשב
- ה-venv לא ב-GitHub - צריך ליצור מחדש בכל מחשב
- ה-.env לא ב-GitHub - צריך ליצור מחדש (אבל הערכים ב-DEPLOY_NOW.md)

---

**✅ הכל מוכן לעבודה מהבית!**
