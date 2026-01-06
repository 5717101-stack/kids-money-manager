# סנכרון שינויים בין המחשבים

## איך זה עובד:

### 1. שינויים בקוד (Frontend/Backend)
- השינויים בקוד **לא** מתעדכנים אוטומטית
- צריך לעשות `git commit` ו-`git push` כדי לעדכן את ה-repository
- Vercel (Frontend) ו-Railway (Backend) יתחילו rebuild אוטומטי לאחר push
- במחשב השני - צריך לעשות `git pull` כדי לקבל את השינויים

### 2. שינויים בנתונים (Database)
- השינויים בנתונים **מתעדכנים אוטומטית** כי כולם משתמשים באותו MongoDB Atlas
- כל שינוי בנתונים (הוספת כסף, הוצאות) יופיע מיד בכל המחשבים

## איך לעדכן שינויים בקוד:

### במחשב הזה (לאחר שינויים):

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

### במחשב השני (לאחר push):

```bash
cd /path/to/project

# משוך את השינויים
git pull
```

### בפרודקשן:
- Vercel ו-Railway יתחילו rebuild אוטומטי לאחר push
- זה יכול לקחת 1-2 דקות

## הערות חשובות:

⚠️ **שינויים בקוד לא מתעדכנים אוטומטית** - צריך לעשות commit ו-push

✅ **שינויים בנתונים מתעדכנים אוטומטית** - כי כולם משתמשים באותו MongoDB

## הגדרת Git (אם עדיין לא):

```bash
git config --global user.name "השם שלך"
git config --global user.email "your.email@example.com"
```
