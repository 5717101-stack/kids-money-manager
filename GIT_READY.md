# ✅ Git מוכן לשימוש!

## מה שבוצע:

1. ✅ Xcode Command Line Tools הותקן
2. ✅ Git עובד
3. ✅ הפרויקט מחובר ל-Git repository
4. ✅ Git config הוגדר

## איך לסנכרן שינויים:

### לאחר שינויים בקוד:

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

### במחשב השני:

```bash
cd /path/to/project

# משוך את השינויים
git pull
```

### בפרודקשן:
- Vercel (Frontend) ו-Railway (Backend) יתחילו rebuild אוטומטי לאחר push
- זה יכול לקחת 1-2 דקות

## סיכום:

| סוג שינוי | מתעדכן אוטומטית? | מה צריך לעשות |
|-----------|-------------------|----------------|
| נתונים (Database) | ✅ כן | כלום - זה קורה אוטומטית |
| קוד (Frontend/Backend) | ✅ כן (אחרי push) | `git commit` + `git push` |

## הערות:

- כל השינויים בקוד יישמרו ב-GitHub
- כל השינויים בנתונים יישמרו ב-MongoDB Atlas
- הפרויקט מסתנכרן בין כל המחשבים והפרודקשן
