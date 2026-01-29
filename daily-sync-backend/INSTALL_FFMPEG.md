# 🔧 התקנת ffmpeg

## הבעיה:
Whisper דורש `ffmpeg` לעיבוד קבצי אודיו. אם הוא לא מותקן, תקבל שגיאה:
```
Error processing audio: [Errno 2] No such file or directory: 'ffmpeg'
```

## פתרון:

### macOS (עם Homebrew):

1. **התקן Homebrew** (אם אין):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **התקן ffmpeg**:
   ```bash
   brew install ffmpeg
   ```

3. **בדוק שההתקנה הצליחה**:
   ```bash
   ffmpeg -version
   ```

### macOS (ללא Homebrew):

1. **הורד מ-MacPorts**:
   ```bash
   sudo port install ffmpeg
   ```

2. **או הורד ישירות**:
   - לך ל: https://evermeet.cx/ffmpeg/
   - הורד את הקובץ המתאים
   - העתק ל-`/usr/local/bin/`

### Linux (Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### Linux (Fedora/RHEL):

```bash
sudo dnf install ffmpeg
```

### Windows:

1. הורד מ: https://ffmpeg.org/download.html
2. חלץ את הקובץ
3. הוסף ל-PATH

## בדיקה:

לאחר ההתקנה, בדוק:
```bash
ffmpeg -version
```

אם אתה רואה גרסה, הכל תקין! ✅

## הערה:

אם אתה לא יכול להתקין ffmpeg, הקוד ינסה להשתמש ב-pydub כחלופה, אבל זה לא תמיד עובד עם כל הפורמטים.

---

**לאחר ההתקנה, הפעל מחדש את השרת והנסה שוב!**
