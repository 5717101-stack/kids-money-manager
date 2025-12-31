# מדריך מהיר - פרסום ב-5 דקות

## שלבים מהירים

### 1. MongoDB Atlas (2 דקות)
1. הירשם ב-[MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. צור Cluster (M0 Free)
3. Database Access → Add User (שמור username/password)
4. Network Access → Allow from Anywhere (0.0.0.0/0)
5. Connect → Connect your app → העתק Connection String
6. החלף `<username>` ו-`<password>` והוסף `/kids-money-manager` בסוף

### 2. GitHub (1 דקה)
```bash
cd "/Users/itzikbachar/Test Cursor"
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/kids-money-manager.git
git push -u origin main
```

### 3. Railway - Backend (2 דקות)
1. [Railway.app](https://railway.app) → Login with GitHub
2. New Project → Deploy from GitHub → בחר repository
3. Settings → Root Directory: `server`
4. Variables → הוסף:
   - `MONGODB_URI` = (הדבק Connection String)
   - `PORT` = `3001`
5. Settings → Domains → Generate Domain
6. **שמור את הכתובת!** (לדוגמה: `https://my-app.up.railway.app`)

### 4. Vercel - Frontend (1 דקה)
1. [Vercel.com](https://vercel.com) → Login with GitHub
2. Add New → Project → בחר repository
3. Environment Variables → הוסף:
   - `VITE_API_URL` = `https://my-app.up.railway.app/api`
4. Deploy

**סיימת! האפליקציה זמינה באינטרנט! 🎉**

---

למדריך מפורט עם תמונות, ראה `DEPLOYMENT.md`

