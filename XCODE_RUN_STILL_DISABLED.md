# פתרון: iPhone 16 Pro נבחר אבל Run עדיין דהוי

## סיבות אפשריות:

### 1. Signing לא מוגדר כראוי
**פתרון:**
- בחר את ה-Target "App"
- Signing & Capabilities
- ודא ש-"Automatically manage signing" מסומן (✓)
- ודא שיש Team נבחר (לא "None")
- אם יש שגיאות signing, תקן אותן

### 2. Build נכשל (אבל לא רואים שגיאות)
**פתרון:**
- Product → Clean Build Folder (Shift+Cmd+K)
- Product → Build (Cmd+B)
- בתחתית Xcode, בדוק את ה-Logs
- Report Navigator (האיקון עם רשימה) → בדוק Build Log

### 3. Scheme לא נכון
**פתרון:**
- בחלק העליון של Xcode
- ודא שהבחירה היא: "App" → "App" → iPhone 16 Pro
- לא "Any iOS Device"

### 4. צריך להוסיף Apple ID
**פתרון:**
- Xcode → Settings (Preferences) → Accounts
- לחץ "+" → Add Apple ID
- היכנס עם Apple ID שלך
- חזור ל-Signing & Capabilities
- בחר את ה-Team

### 5. פרויקט לא מסונכרן
**פתרון:**
- סגור את Xcode
- הרץ:
  ```bash
  cd ~/Projects/kids-money-manager
  export PATH="$HOME/.local/node22/bin:$PATH"
  npm run build
  npx cap sync ios
  ```
- פתח מחדש: `npx cap open ios`
