# 🔧 התקנת ffmpeg - הוראות מהירות

## הבעיה:
הקובץ `/usr/local/bin/ffmpeg` פגום (טקסט "Not Found" במקום בינארי).

## פתרון מהיר:

### שלב 1: מחק את הקובץ הפגום

פתח טרמינל והרץ:
```bash
sudo rm /usr/local/bin/ffmpeg
```

### שלב 2: הורד והתקן ffmpeg

**אופציה A: עם Homebrew (מומלץ)**
```bash
# אם יש לך Homebrew:
brew install ffmpeg

# אם אין לך Homebrew, התקן אותו קודם:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# אחרי ההתקנה:
brew install ffmpeg
```

**אופציה B: הורדה ישירה (ללא Homebrew)**

1. פתח דפדפן ולך ל:
   ```
   https://evermeet.cx/ffmpeg/
   ```

2. הורד את הקובץ `ffmpeg` (הקובץ הירוק, לא ה-zip)

3. בטרמינל:
   ```bash
   # העתק את הקובץ שהורדת
   sudo cp ~/Downloads/ffmpeg /usr/local/bin/
   sudo chmod +x /usr/local/bin/ffmpeg
   ```

### שלב 3: בדוק שההתקנה הצליחה

```bash
ffmpeg -version
```

אם אתה רואה גרסה (למשל "ffmpeg version 6.x"), הכל תקין! ✅

### שלב 4: הפעל מחדש את השרת

השרת כבר רץ, אבל הוא יזהה את ffmpeg אוטומטית בפעם הבאה שתעלה קובץ MP3.

## אחרי ההתקנה:

1. נסה להעלות קובץ MP3 ב: http://localhost:8000
2. זה אמור לעבוד! 🎉

---

**💡 המלצה:** השתמש ב-Homebrew (אופציה A) - זה הכי אמין וקל לעדכון.
