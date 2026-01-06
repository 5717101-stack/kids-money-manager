# איך לסנכרן שינויים בין המחשבים

## תשובה קצרה:

### ✅ שינויים בנתונים (Database)
**כן, מתעדכנים אוטומטית!**
- כל השינויים בנתונים (הוספת כסף, הוצאות) נשמרים ב-MongoDB Atlas
- כל המחשבים והפרודקשן משתמשים באותו database
- השינויים יופיעו מיד בכל המקומות

### ⚠️ שינויים בקוד (Frontend/Backend)
**לא, לא מתעדכנים אוטומטית**
- צריך לעשות `git commit` ו-`git push` כדי לעדכן את ה-repository
- Vercel ו-Railway יתחילו rebuild אוטומטי לאחר push
- במחשב השני - צריך לעשות `git pull`

## מה צריך לעשות כדי לסנכרן קוד:

### שלב 1: הגדר Git (אם עדיין לא)

הפרויקט הורד כ-zip, אז צריך לחבר אותו ל-Git repository:

```bash
cd ~/Projects/kids-money-manager

# הגדר Git (אם עדיין לא)
export PATH="$HOME/.local/node/bin:$PATH"
git config --global user.name "השם שלך"
git config --global user.email "your.email@example.com"

# חבר ל-repository הקיים
git init
git remote add origin https://github.com/5717101-stack/kids-money-manager.git
git fetch
git checkout -b main
git branch --set-upstream-to=origin/main main
```

### שלב 2: לאחר שינויים בקוד

```bash
cd ~/Projects/kids-money-manager

# בדוק מה השתנה
git status

# הוסף את השינויים
git add .

# צור commit
git commit -m "תיאור השינויים"

# העלה ל-GitHub
git push
```

### שלב 3: במחשב השני

```bash
cd /path/to/project

# משוך את השינויים
git pull
```

### שלב 4: בפרודקשן
- Vercel ו-Railway יתחילו rebuild אוטומטי לאחר push
- זה יכול לקחת 1-2 דקות

## סיכום:

| סוג שינוי | מתעדכן אוטומטית? | מה צריך לעשות |
|-----------|-------------------|----------------|
| נתונים (Database) | ✅ כן | כלום - זה קורה אוטומטית |
| קוד (Frontend/Backend) | ❌ לא | `git commit` + `git push` |

## הערה חשובה:

כרגע הפרויקט לא מחובר ל-Git repository (הורד כ-zip). כדי לסנכרן קוד, צריך לחבר אותו ל-Git תחילה (ראה שלב 1 למעלה).
