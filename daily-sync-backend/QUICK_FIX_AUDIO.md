# ⚡ פתרון מהיר - שגיאת אודיו

## הבעיה:
```
Error processing audio: [Errno 2] No such file or directory: 'ffmpeg'
```

## פתרון מהיר:

### אופציה 1: התקן ffmpeg (מומלץ)

**ב-Mac:**
```bash
# אם יש לך Homebrew:
brew install ffmpeg

# אם אין Homebrew, התקן אותו קודם:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install ffmpeg
```

**בדוק:**
```bash
ffmpeg -version
```

### אופציה 2: השתמש רק בטקסט (זמני)

עד שתתקין ffmpeg, תוכל:
1. להמיר את האודיו לטקסט ידנית
2. להזין את הטקסט ישירות בשדה הטקסט בדף
3. להריץ את הניתוח

## אחרי ההתקנה:

1. **הפעל מחדש את השרת**:
   ```bash
   # עצור את השרת (Ctrl+C)
   python main.py
   ```

2. **נסה שוב** - העלה קובץ אודיו והרץ ניתוח

## למה זה קורה?

Whisper (הכלי ל-transcription) דורש ffmpeg כדי להמיר פורמטי אודיו שונים לפורמט שהוא יכול לעבד.

---

**💡 טיפ:** אם אתה לא יכול להתקין ffmpeg עכשיו, פשוט העתק את התוכן של האודיו כטקסט והזן אותו בשדה הטקסט.
