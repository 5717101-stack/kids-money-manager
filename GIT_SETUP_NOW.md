# הגדרת Git - הוראות מיידיות

## המצב:
Git דורש Xcode Command Line Tools שצריך להתקין ידנית.

## מה לעשות:

### שלב 1: התקן Xcode Command Line Tools

פתח Terminal והרץ:
```bash
xcode-select --install
```

זה יפתח חלון התקנה. לחץ "Install" וחכה שההתקנה תסתיים (יכול לקחת 10-15 דקות).

### שלב 2: לאחר ההתקנה

הרץ את הסקריפט:
```bash
cd ~/Projects/kids-money-manager
./setup_git.sh
```

או הגדר ידנית:
```bash
cd ~/Projects/kids-money-manager

# הגדר Git config
git config --global user.name "השם שלך"
git config --global user.email "your.email@example.com"

# חבר ל-repository
git init
git remote add origin https://github.com/5717101-stack/kids-money-manager.git
git fetch origin
git branch -M main
git branch --set-upstream-to=origin/main main
```

### שלב 3: לאחר שינויים בקוד

```bash
cd ~/Projects/kids-money-manager
git add .
git commit -m "תיאור השינויים"
git push
```

## הערה:
כרגע Git לא יכול לעבוד כי Xcode Command Line Tools לא מותקן. אחרי ההתקנה, הכל יעבוד.
