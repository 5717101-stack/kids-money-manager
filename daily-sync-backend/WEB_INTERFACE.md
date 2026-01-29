# 🌐 ממשק Web - Daily Sync

## איך להשתמש:

### 1. הפעל את השרת:
```bash
cd daily-sync-backend
source venv/bin/activate
python main.py
```

### 2. פתח בדפדפן:
```
http://localhost:8000
```

או ישירות:
```
http://localhost:8000/static/index.html
```

## תכונות:

✅ **העלאת קבצי אודיו** - גרור ושחרר או לחץ לבחירה  
✅ **הזנת טקסט חופשי** - הערות, מחשבות, יומן  
✅ **כפתור "הרץ ניתוח AI"** - מפעיל את כל 3 הסוכנים  
✅ **תוצאות מפורטות** - עם טאבים לנוחות  

## הטאבים:

1. **סיכום** - Executive summary יומי
2. **Leadership** - ניתוח Leadership Coach (Simon Sinek)
3. **Strategy** - ניתוח Strategy Consultant
4. **Parenting** - ניתוח Parenting Coach (Adler Institute)
5. **פעולות** - Action items מפורטים

## הערות:

- האודיו יעבור transcription אוטומטי (Whisper)
- הטקסט נשמר במסד נתונים
- הניתוח יכול לקחת כמה דקות (תלוי באורך התוכן)
- כל התוצאות נשמרות במסד הנתונים

## פתרון בעיות:

### "שגיאה: Connection refused"
- ודא שהשרת רץ (`python main.py`)
- בדוק שהפורט 8000 פנוי

### "שגיאה: API key not set"
- הוסף API key ל-`.env`
- ראה `HOW_TO_GET_API_KEYS.md`

### האודיו לא מתעבד
- ודא שהקובץ בפורמט נתמך (mp3, wav, m4a, וכו')
- בדוק את הלוגים של השרת

---

**🎉 תהנה מהשימוש!**
