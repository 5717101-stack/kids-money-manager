# פתרון: Render מוסיף `server/ $` אוטומטית

## הבעיה:

Render **אוטומטית מוסיף** `server/ $` כשה-Root Directory = `server`, אז:
- **Build Command:** `server/ $ npm install; npm run build` ← Render הוסיף `server/ $` אוטומטית
- **Start Command:** `server/ $ npm start` ← Render הוסיף `server/ $` אוטומטית

## הפתרון:

### אפשרות 1: להסיר רק את `npm run build` (מומלץ)

**Build Command:**
```
npm install
```

**לא:**
- ❌ `npm install; npm run build` (זה יגרום לשגיאה)

**Start Command:**
```
npm start
```

Render יוסיף `server/ $` אוטומטית, אז זה יהיה:
- `server/ $ npm install` ✅
- `server/ $ npm start` ✅

---

### אפשרות 2: להסיר את Root Directory ולהשתמש ב-`cd server &&`

אם Render לא נותן למחוק את `server/ $`:

1. **הסר את Root Directory** (השאר ריק)
2. **Build Command:**
   ```
   cd server && npm install
   ```
3. **Start Command:**
   ```
   cd server && npm start
   ```

---

## איך לתקן:

### שלב 1: תקן את Build Command

1. **לך ל-Settings → Build Command**
2. **מחק את `npm run build`** (השאר רק `npm install`)
3. **אמור להיות:** `npm install` (ו-Render יוסיף `server/ $` אוטומטית)

### שלב 2: ודא ש-Start Command נכון

1. **לך ל-Settings → Start Command**
2. **ודא שזה:** `npm start` (ו-Render יוסיף `server/ $` אוטומטית)

### שלב 3: Save & Redeploy

1. **לחץ "Save Changes"**
2. **Redeploy:**
   - Deployments → "..." → "Redeploy"

---

## מה אמור להיות:

### Build Command:
```
npm install
```

Render יהפוך את זה ל:
```
server/ $ npm install
```

### Start Command:
```
npm start
```

Render יהפוך את זה ל:
```
server/ $ npm start
```

---

## אם עדיין לא עובד:

אם Render עדיין מוסיף `npm run build` או משהו אחר:

1. **נסה להסיר את Root Directory** (השאר ריק)
2. **Build Command:** `cd server && npm install`
3. **Start Command:** `cd server && npm start`

זה יעבוד בוודאות!

