# פתרון: Build Succeeded אבל האפליקציה לא נפתחת

## בעיות נפוצות:

### 1. Simulator לא נבחר
**פתרון:**
- בחלק העליון של Xcode, ליד כפתור Run
- לחץ על ה-dropdown (שם המכשיר)
- בחר Simulator (iPhone 14 Pro, iPhone 15, וכו')
- לחץ Run שוב

### 2. Simulator לא רץ
**פתרון:**
- Xcode → Window → Devices and Simulators
- בחר Simulator
- לחץ "Boot" או "Open"

### 3. האפליקציה לא מסונכרנת
**פתרון:**
```bash
cd ~/Projects/kids-money-manager
export PATH="$HOME/.local/node22/bin:$PATH"
npm run build
npx cap sync ios
```

ואז ב-Xcode:
- Product → Clean Build Folder (Shift+Cmd+K)
- Product → Build (Cmd+B)
- Product → Run (Cmd+R)

### 4. Scheme לא נכון
**פתרון:**
- בחלק העליון של Xcode, ליד כפתור Run
- ודא שהבחירה היא: "App" → "App" → Simulator
- לא "Any iOS Device"

### 5. בדוק את ה-Logs
**פתרון:**
- ב-Xcode, בתחתית החלון
- לחץ על "Report Navigator" (האיקון עם רשימה)
- בדוק אם יש שגיאות או אזהרות

## צעדים מהירים:

1. **בחר Simulator** - ליד כפתור Run
2. **Clean Build** - Shift+Cmd+K
3. **Build** - Cmd+B
4. **Run** - Cmd+R

אם זה לא עובד, בדוק את ה-Logs בתחתית Xcode.
