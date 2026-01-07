# מדריך מעבר ל-Render - שלב אחר שלב

## ✅ מה צריך לעשות:

### שלב 1: יצירת חשבון ב-Render

1. לך ל-[render.com](https://render.com)
2. לחץ "Get Started for Free"
3. היכנס עם **GitHub** (הכי קל)
4. אישר גישה ל-repository שלך

---

### שלב 2: יצירת Web Service

1. **Dashboard → "New" → "Web Service"**
2. **בחר את ה-repository שלך:**
   - `5717101-stack/kids-money-manager` (או השם שלך)
3. **הגדרות בסיסיות:**
   - **Name:** `kids-money-manager-server`
   - **Environment:** `Node`
   - **Region:** `Frankfurt` (או הכי קרוב אליך)
   - **Branch:** `main`
   - **Root Directory:** `server` ⚠️ **חשוב!**
   - **Build Command:** `npm install`
   - **Start Command:** `npm start`
   - **Plan:** `Free` (או `Starter` $7/חודש ל-Always On)

4. **לחץ "Create Web Service"**

---

### שלב 3: הגדרת Environment Variables

1. **לך ל-Settings → Environment**
2. **הוסף את ה-Variables הבאים:**

   ```
   MONGODB_URI=your-mongodb-connection-string
   RESEND_API_KEY=your-resend-api-key
   RESEND_FROM_EMAIL=your-email@domain.com
   NODE_ENV=production
   ```

   ⚠️ **חשוב:** העתק את הערכים מ-Railway (או מה-Variables הקיימים שלך)

3. **לחץ "Save Changes"**

---

### שלב 4: הגדרת Health Check

1. **לך ל-Settings → Health Check**
2. **הגדר:**
   - **Health Check Path:** `/health`
   - **Health Check Timeout:** `600` שניות
3. **לחץ "Save Changes"**

---

### שלב 5: המתן ל-Deploy

1. Render יתחיל לבנות את ה-Service אוטומטית
2. **זה יכול לקחת 5-10 דקות**
3. **בדוק את ה-Logs:**
   - לחץ על ה-Service → "Logs"
   - אמור לראות: `[SERVER] Version 2.9.25 - Started on port...`

---

### שלב 6: קבלת ה-URL

1. **אחרי שה-Deploy מסתיים:**
   - לך ל-Settings → "Service Details"
   - מצא את **"Service URL"**
   - זה יראה כמו: `https://kids-money-manager-server.onrender.com`

2. **בדוק שה-Health Check עובד:**
   - פתח בדפדפן: `https://YOUR-SERVICE-NAME.onrender.com/health`
   - אמור לראות: `{"status":"ok",...}`

---

### שלב 7: עדכון ה-API URLs בקוד

1. **עדכן את `src/utils/api.js`:**
   - החלף `YOUR-SERVICE-NAME` ב-URL האמיתי מ-Render
   - או השאר את `VITE_API_URL` (מומלץ)

2. **עדכן את `src/components/WelcomeScreen.jsx`:**
   - החלף `YOUR-SERVICE-NAME` ב-URL האמיתי

3. **עדכן את `src/components/PhoneLogin.jsx`:**
   - החלף `YOUR-SERVICE-NAME` ב-URL האמיתי

4. **עדכן את `src/components/OTPVerification.jsx`:**
   - החלף `YOUR-SERVICE-NAME` ב-URL האמיתי

5. **עדכן את `src/App.jsx`:**
   - החלף `YOUR-SERVICE-NAME` ב-URL האמיתי

---

### שלב 8: הגדרת VITE_API_URL ב-Vercel

1. **לך ל-Vercel Dashboard → Project → Settings → Environment Variables**
2. **הוסף:**
   - **Name:** `VITE_API_URL`
   - **Value:** `https://YOUR-SERVICE-NAME.onrender.com/api`
   - **Environment:** `Production`, `Preview`, `Development`
3. **לחץ "Save"**
4. **Redeploy את ה-Frontend:**
   - Deployments → "..." → "Redeploy"

---

### שלב 9: בדיקה

1. **פתח את האפליקציה**
2. **נסה לשלוח OTP:**
   - אמור לעבוד!
3. **בדוק את ה-Logs ב-Render:**
   - אמור לראות את כל ה-Logs

---

## ⚠️ הערות חשובות:

### Free Tier:
- **Render Free Tier יכול להירדם אחרי 15 דקות ללא פעילות**
- **הפעלה ראשונה יכולה לקחת 30-60 שניות** (cold start)
- **אם זה מפריע → שדרג ל-Starter ($7/חודש) ל-Always On**

### Always On:
- **אם אתה רוצה שהשירות יישאר פעיל כל הזמן:**
  - Settings → Plan → שדרג ל-"Starter" ($7/חודש)
  - זה יבטיח שהשירות לא יירדם

### Auto-Deploy:
- **Render יבנה ויפרס אוטומטית מ-GitHub**
- **כל push ל-main יגרום ל-deploy חדש**

### Logs:
- **Render יש Logs מעולים**
- **לך ל-Service → "Logs" כדי לראות הכל**

---

## 🔧 אם משהו לא עובד:

### Build נכשל:
1. **בדוק את ה-Logs:**
   - Service → Logs
   - חפש שגיאות
2. **ודא ש-Root Directory = `server`**
3. **ודא ש-Build Command = `npm install`**
4. **ודא ש-Start Command = `npm start`**

### Health Check נכשל:
1. **בדוק שה-Health Check Path = `/health`**
2. **פתח בדפדפן:** `https://YOUR-SERVICE-NAME.onrender.com/health`
3. **אמור לראות:** `{"status":"ok",...}`

### Environment Variables לא עובדים:
1. **ודא שה-Variables מוגדרים ב-Settings → Environment**
2. **ודא שהשמות נכונים (case-sensitive)**
3. **Redeploy אחרי שינוי Variables**

---

## 📝 סיכום:

1. ✅ יצירת חשבון ב-Render
2. ✅ יצירת Web Service
3. ✅ הגדרת Environment Variables
4. ✅ קבלת ה-URL
5. ✅ עדכון ה-API URLs בקוד
6. ✅ הגדרת VITE_API_URL ב-Vercel
7. ✅ בדיקה

**אחרי שתסיים את כל השלבים, תגיד לי ואעדכן את הקוד עם ה-URL האמיתי!**

