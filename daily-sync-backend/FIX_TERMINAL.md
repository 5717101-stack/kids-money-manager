# 🔧 פתרון שגיאות בטרמינל

## הבעיות שראיתי:

1. ❌ `cd: no such file or directory: daily-sync-backend` - לא בתיקייה הנכונה
2. ❌ `zsh: command not found: brew` - Homebrew לא מותקן

## פתרון שלב אחר שלב:

### שלב 1: נווט לתיקייה הנכונה

```bash
cd "/Users/itzhakbachar/Family Bank/kids-money-manager/daily-sync-backend"
```

או אם אתה בתיקייה הראשית:
```bash
cd "Family Bank/kids-money-manager/daily-sync-backend"
```

### שלב 2: התקן Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

זה יקח כמה דקות וידרוש סיסמת מנהל.

### שלב 3: הוסף Homebrew ל-PATH

לאחר ההתקנה, הרץ:

```bash
# אם אתה ב-Mac עם Apple Silicon (M1/M2):
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc

# או אם אתה ב-Mac עם Intel:
echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

### שלב 4: התקן ffmpeg

```bash
brew install ffmpeg
```

### שלב 5: בדוק

```bash
ffmpeg -version
```

אם אתה רואה גרסה, הכל תקין! ✅

## פקודות מהירות (העתק והדבק):

```bash
# 1. נווט לתיקייה
cd "/Users/itzhakbachar/Family Bank/kids-money-manager/daily-sync-backend"

# 2. התקן Homebrew (אם אין)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. הוסף ל-PATH
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc

# 4. התקן ffmpeg
brew install ffmpeg

# 5. בדוק
ffmpeg -version
```

## אם יש בעיות:

- אם Homebrew כבר מותקן אבל לא ב-PATH, נסה:
  ```bash
  export PATH="/opt/homebrew/bin:$PATH"
  brew install ffmpeg
  ```

- אם אתה לא בטוח איפה הפרויקט:
  ```bash
  find ~ -name "daily-sync-backend" -type d 2>/dev/null
  ```

---

**💡 טיפ:** אחרי ההתקנה, הפעל מחדש את השרת!
