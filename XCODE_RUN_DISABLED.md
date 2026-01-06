# פתרון: Product → Run דהוי ולא ניתן ללחיצה

## סיבות נפוצות:

### 1. Simulator לא נבחר
**פתרון:**
- בחלק העליון של Xcode, ליד כפתור Run
- לחץ על ה-dropdown (שם המכשיר)
- בחר Simulator (iPhone 16 Pro, iPhone 15, וכו')
- לא "Any iOS Device"

### 2. Signing לא מוגדר
**פתרון:**
- בחר את ה-Target "App"
- Signing & Capabilities
- סמן "Automatically manage signing"
- בחר Team (או "Add an Account...")

### 3. Build נכשל
**פתרון:**
- Product → Build (Cmd+B)
- בדוק אם יש שגיאות
- אם יש שגיאות, תקן אותן

### 4. Scheme לא נכון
**פתרון:**
- בחלק העליון של Xcode
- ודא שהבחירה היא: "App" → "App" → Simulator
- לא "Any iOS Device"

### 5. פרויקט לא נטען כראוי
**פתרון:**
- סגור את Xcode
- פתח מחדש: `npx cap open ios`

## צעדים מהירים:

1. **בחר Simulator** - ליד כפתור Run
2. **בדוק Signing** - Signing & Capabilities
3. **Build** - Product → Build (Cmd+B)
4. **Run** - Product → Run (Cmd+R)
