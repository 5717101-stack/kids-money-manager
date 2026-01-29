# 🔧 תיקון שגיאת Build ב-Render

## הבעיה

הבנייה נכשלה עם השגיאות:
- `Keyerror: __version__`
- `Getting requirements to build wheel did not run successfully`
- Render מנסה להשתמש ב-Node.js במקום Python

## פתרון

### שלב 1: בדוק את ההגדרות ב-Render

1. לך ל-Render Dashboard → Service → Settings

2. ודא שההגדרות הבאות נכונות:

   **Environment:**
   ```
   Python 3
   ```
   ⚠️ **חשוב:** לא Node.js!

   **Root Directory:**
   ```
   daily-sync-backend
   ```
   ⚠️ **חשוב מאוד!** זה אומר ל-Render שהקוד נמצא בתיקייה הזו.

   **Build Command:**
   ```
   pip install -r requirements.txt
   ```

   **Start Command:**
   ```
   python main.py
   ```

### שלב 2: עדכן את requirements.txt

עדכנתי את `requirements.txt` עם version constraints טובים יותר.

אם עדיין יש בעיה, נסה:

1. **לעשות Redeploy:**
   - Render Dashboard → Service → Manual Deploy → Deploy latest commit

2. **או Clear Build Cache:**
   - Render Dashboard → Service → Settings → Clear Build Cache
   - אחר כך Manual Deploy

### שלב 3: בדוק את ה-Logs

אם עדיין יש שגיאה, בדוק את ה-Logs:
- Render Dashboard → Service → Logs
- חפש שגיאות הקשורות ל:
  - `pip install`
  - `requirements.txt`
  - `__version__`

### שלב 4: פתרון חלופי - Runtime.txt

אם עדיין יש בעיות, צור קובץ `runtime.txt`:

```bash
cd daily-sync-backend
echo "python-3.11.0" > runtime.txt
```

זה יגיד ל-Render להשתמש ב-Python 3.11.

## בדיקה

אחרי התיקון, בדוק:
1. Health endpoint: `https://YOUR_SERVICE.onrender.com/health`
2. API docs: `https://YOUR_SERVICE.onrender.com/docs`

## אם עדיין לא עובד

1. **בדוק את ה-Logs** - Render Dashboard → Logs
2. **ודא ש-Environment = Python 3** (לא Node.js!)
3. **ודא ש-Root Directory = daily-sync-backend**
4. **נסה Clear Build Cache + Redeploy**

---

**💡 טיפ:** אם Render עדיין מנסה להשתמש ב-Node.js, זה אומר ש-Root Directory לא מוגדר נכון או ש-Environment לא מוגדר כ-Python 3.
