# הוראות Signing & Capabilities ב-Xcode

## מה לעשות:

### 1. סמן "Automatically manage signing"
   - תראה checkbox עם הטקסט הזה
   - סמן אותו (✓)

### 2. בחר Team
   - תראה dropdown עם "Team"
   - לחץ עליו ובחר את ה-Team שלך
   - אם אין לך Team, תראה "Add an Account..."
   - לחץ על זה והיכנס עם Apple ID שלך

### 3. Bundle Identifier
   - ודא שזה: `com.bachar.kidsmoneymanager`
   - אם זה שונה, שנה אותו

### 4. אם יש שגיאות
   - "No signing certificate found" - זה תקין, Xcode ייצור אחד אוטומטית
   - "No provisioning profile" - זה תקין, Xcode ייצור אחד אוטומטית

## לאחר שסיימת:

1. בחר Simulator (iPhone 14 Pro, וכו')
2. לחץ ▶️ Run (Cmd+R)
3. האפליקציה תתבנה ותפתח ב-Simulator

## הערות:

- אם אין לך Apple Developer Account ($99/שנה), תוכל להריץ רק על Simulator
- להריץ על מכשיר אמיתי או להפיץ ל-TestFlight, צריך Apple Developer Account
