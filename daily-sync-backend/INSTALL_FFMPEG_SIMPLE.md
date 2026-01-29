# 🔧 התקנת ffmpeg - הוראות פשוטות

## שלב 1: פתח טרמינל חדש

פתח את Terminal (⌘+Space, הקלד "Terminal", Enter)

## שלב 2: מחק את הקובץ הפגום

העתק והדבק בטרמינל:
```bash
sudo rm /usr/local/bin/ffmpeg
```
(תתבקש להזין סיסמה)

## שלב 3: התקן Homebrew (אם אין)

העתק והדבק:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

זה יקח כמה דקות. תצטרך:
- להזין סיסמת מנהל
- ללחוץ Enter כמה פעמים

## שלב 4: הוסף Homebrew ל-PATH

לאחר שההתקנה מסתיימת, הרץ:
```bash
eval "$(/opt/homebrew/bin/brew shellenv)"
```

או אם זה לא עובד:
```bash
eval "$(/usr/local/bin/brew shellenv)"
```

## שלב 5: התקן ffmpeg

```bash
brew install ffmpeg
```

זה יקח כמה דקות.

## שלב 6: בדוק שההתקנה הצליחה

```bash
ffmpeg -version
```

אם אתה רואה גרסה, הכל תקין! ✅

## שלב 7: הפעל מחדש את השרת (אם צריך)

השרת כבר רץ, אבל הוא יזהה את ffmpeg אוטומטית בפעם הבאה שתעלה קובץ MP3.

---

## 🎉 אחרי ההתקנה:

1. נסה להעלות קובץ MP3 ב: http://localhost:8000
2. זה אמור לעבוד!

---

**💡 טיפ:** אם אתה לא רוצה להתקין Homebrew, תוכל להוריד ffmpeg ישירות מ-https://evermeet.cx/ffmpeg/ ולהעתיק ל-`/usr/local/bin/`
