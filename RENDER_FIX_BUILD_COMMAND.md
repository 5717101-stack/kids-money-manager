# תיקון Build Command ב-Render

## ❌ הבעיה:

בתמונה רואים:
- **Build Command:** `server/ $ npm install; npm run build`
- **Start Command:** `server/ $ npm start`

## 🔧 הבעיות:

1. **`npm run build` לא קיים** ב-`server/package.json` - זה יגרום לשגיאה!
2. **אם Root Directory = `server`**, אז הפקודות כבר רצות מתוך התיקייה הזו, אז לא צריך `server/ $`

## ✅ התיקון:

### Build Command:
```
npm install
```

**לא:**
- ❌ `server/ $ npm install; npm run build`
- ❌ `npm install; npm run build`

### Start Command:
```
npm start
```

**לא:**
- ❌ `server/ $ npm start`
- ❌ `cd server && npm start` (אם Root Directory = `server`)

## 📝 איך לתקן:

1. **לך ל-Render Dashboard → Service → Settings**
2. **מצא "Build Command"**
3. **שנה ל:** `npm install`
4. **מצא "Start Command"**
5. **שנה ל:** `npm start`
6. **לחץ "Save Changes"**
7. **Redeploy:**
   - Deployments → "..." → "Redeploy"

## ✅ אחרי התיקון:

אמור לראות ב-Logs:
```
[BUILD] Running: npm install
[BUILD] ✅ Dependencies installed
[START] Running: npm start
[START] ✅ Server started on port...
```

---

**חשוב:** אם Root Directory = `server`, אז כל הפקודות רצות מתוך התיקייה הזו אוטומטית!

