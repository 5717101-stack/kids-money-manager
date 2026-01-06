# עדכון גרסה - הוראות

## בעיה
הגרסה לא מתעדכנת בכל הקבצים או ב-iOS app.

## פתרון

### 1. עדכון גרסה בכל הקבצים
```bash
# עדכן את הגרסה ב-package.json
# ואז הרץ:
npm run build
npx cap sync
```

### 2. קבצים שצריכים עדכון
- `package.json` - גרסה מלאה (2.9.1)
- `server/package.json` - גרסה מלאה (2.9.1)
- `server/server.js` - גרסה מלאה (2.9.1)
- `src/App.jsx` - גרסה קצרה (2.9)
- `src/components/WelcomeScreen.jsx` - גרסה קצרה (2.9)
- `src/components/PhoneLogin.jsx` - גרסה קצרה (2.9)
- `src/components/OTPVerification.jsx` - גרסה קצרה (2.9)

### 3. עדכון iOS App
אחרי עדכון הגרסה, צריך:
```bash
npm run build
npx cap sync
```

ואז ב-Xcode:
1. פתח את הפרויקט ב-Xcode
2. Clean Build Folder (Cmd+Shift+K)
3. Build (Cmd+B)
4. Run על המכשיר

### 4. עדכון אוטומטי
השתמש ב-`auto_release.sh`:
```bash
bash auto_release.sh
```

זה יעדכן את כל הקבצים אוטומטית.

## הערות

- הגרסה ב-React היא קצרה (2.9) כי זה מה שמציג למשתמש
- הגרסה ב-package.json היא מלאה (2.9.1) כי זה מה שמשתמש npm
- אחרי כל עדכון גרסה, צריך לעשות `npm run build` ו-`npx cap sync`

