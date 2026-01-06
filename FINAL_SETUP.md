# הגדרת Git - סיכום סופי

## ⚠️ המצב הנוכחי:

Git לא יכול לעבוד כי **Xcode Command Line Tools לא מותקן**.

## ✅ מה שכבר מוכן:

1. ✅ הפרויקט רץ מקומית
2. ✅ מחובר ל-Railway backend עם הנתונים
3. ✅ שינויים בנתונים מתעדכנים אוטומטית
4. ✅ סקריפטים להגדרת Git מוכנים

## 📋 מה צריך לעשות כדי לסנכרן קוד:

### שלב 1: התקן Xcode Command Line Tools

**פתח Terminal והרץ:**
```bash
xcode-select --install
```

זה יפתח חלון התקנה. לחץ **"Install"** וחכה שההתקנה תסתיים (10-15 דקות).

### שלב 2: הגדר Git

לאחר שההתקנה תסתיים, הרץ:
```bash
cd ~/Projects/kids-money-manager
./QUICK_GIT_SETUP.sh
```

או הגדר ידנית:
```bash
# הגדר Git config
git config --global user.name "השם שלך"
git config --global user.email "your.email@example.com"

# חבר ל-repository
cd ~/Projects/kids-money-manager
git init
git remote add origin https://github.com/5717101-stack/kids-money-manager.git
git fetch origin
git branch -M main
```

### שלב 3: סנכרן שינויים

לאחר שינויים בקוד:
```bash
cd ~/Projects/kids-money-manager
git add .
git commit -m "תיאור השינויים"
git push
```

במחשב השני:
```bash
git pull
```

## 💡 בינתיים:

✅ **שינויים בנתונים** - מתעדכנים אוטומטית (כולם משתמשים באותו MongoDB)

⚠️ **שינויים בקוד** - צריך להתקין Git תחילה (ראה שלב 1)

## 📁 קבצים שנוצרו:

- `QUICK_GIT_SETUP.sh` - סקריפט מהיר להגדרה
- `setup_git.sh` - סקריפט מפורט
- `GIT_SETUP_NOW.md` - הוראות מפורטות
- `HOW_TO_SYNC.md` - הסבר על סנכרון
