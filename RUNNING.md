# הפרויקט רץ! 🎉

## ✅ מה שהותקן:

1. ✅ **Node.js v20.11.0** - הותקן ב-`~/.local/node/`
2. ✅ **Dependencies של Frontend** - הותקנו
3. ✅ **Dependencies של Backend** - הותקנו
4. ✅ **הפרויקט רץ!**

## 🌐 גישה לאפליקציה:

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:3001

## 🔑 סיסמת הורה:

`2016`

## 🛑 עצירת הפרויקט:

הפרויקט רץ ברקע. כדי לעצור אותו:

```bash
# מצא את ה-process ID
ps aux | grep "node.*server.js\|vite" | grep -v grep

# או עצור את כל ה-processes
pkill -f "kids-money-manager"
```

## 🚀 הפעלה מחדש:

```bash
export PATH="$HOME/.local/node/bin:$PATH"
cd ~/Projects/kids-money-manager
npm run dev:all
```

## 📝 הערות:

- הפרויקט רץ עם אחסון זמני בזיכרון (ללא MongoDB)
- הנתונים יאבדו בסגירת השרת
- כדי לשמור נתונים, התקן MongoDB והגדר `server/.env`

## 🔧 פתרון בעיות:

**אם הפרויקט לא נפתח:**
- בדוק שהפורטים 5173 ו-3001 פנויים
- בדוק את הלוגים: `cat /tmp/project.log`

**אם יש שגיאות:**
- ודא ש-Node.js ב-PATH: `export PATH="$HOME/.local/node/bin:$PATH"`
- נסה להריץ מחדש: `npm run dev:all`
