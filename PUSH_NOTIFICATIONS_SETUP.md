# 📱 Push Notifications Setup Guide

## סקירה כללית

האפליקציה תומכת כעת ב-Push Notifications עבור iOS ו-Android. המשתמשים יקבלו הודעות על:
- **דמי כיס** - כשדמי כיס משולמים אוטומטית
- **ריבית** - כשהריבית היומית מחושבת
- **עסקאות** - כשמתבצעות עסקאות (אופציונלי)

## מה כבר הוטמע

✅ **Frontend:**
- Capacitor Push Notifications plugin מותקן
- Service לניהול push notifications (`src/services/pushNotifications.js`)
- Registration אוטומטי אחרי login
- Unregistration ב-logout

✅ **Backend:**
- Endpoints לשמירת device tokens (צריך להוסיף)
- לוגיקה לשליחת הודעות (צריך להוסיף)

## מה צריך להשלים

### 1. Firebase Cloud Messaging (FCM) ל-Android

#### שלב 1: צור Firebase Project
1. לך ל: https://console.firebase.google.com/
2. לחץ **Add project**
3. בחר שם לפרויקט
4. המשך עם ההגדרות

#### שלב 2: הוסף Android App
1. לחץ על אייקון **Android** (או **Add app**)
2. **Package name:** `com.bachar.kidsmoneymanager`
3. **App nickname:** Family Bank (אופציונלי)
4. לחץ **Register app**

#### שלב 3: הורד `google-services.json`
1. הורד את הקובץ `google-services.json`
2. העתק ל: `android/app/google-services.json`

#### שלב 4: קבל Server Key
1. **Project Settings** → **Cloud Messaging**
2. העתק את **Server Key** (או **Legacy Server Key**)
3. שמור אותו - נצטרך אותו לשרת

### 2. Apple Push Notification Service (APNs) ל-iOS

#### שלב 1: Apple Developer Account
1. צריך **Apple Developer Account** (99$ לשנה)
2. או **Apple Developer Program** membership

#### שלב 2: צור Push Notification Certificate
1. לך ל: https://developer.apple.com/account/resources/certificates/list
2. לחץ **+** ליצירת certificate חדש
3. בחר **Apple Push Notification service SSL (Sandbox & Production)**
4. בחר את **App ID** שלך
5. הורד את ה-certificate
6. פתח ב-Keychain Access
7. ייצא כ-`.p12` עם סיסמה

#### שלב 3: קבל Key ID ו-Team ID
1. **Certificates, Identifiers & Profiles** → **Keys**
2. צור **Key** חדש עם **Apple Push Notifications service (APNs)**
3. שמור את **Key ID** ו-**Team ID**

### 3. הגדרת Backend

#### שלב 1: התקן חבילות
```bash
cd server
npm install firebase-admin node-apn
```

#### שלב 2: הוסף משתני סביבה
הוסף ל-`.env` או ל-Railway/Render:
```
# Firebase (Android)
FIREBASE_SERVER_KEY=your_firebase_server_key_here

# Apple Push Notifications (iOS)
APNS_KEY_ID=your_apns_key_id
APNS_TEAM_ID=your_apns_team_id
APNS_BUNDLE_ID=com.bachar.kidsmoneymanager
APNS_KEY_PATH=./apns-key.p8
# או
APNS_P12_PATH=./apns-cert.p12
APNS_P12_PASSWORD=your_password
```

#### שלב 3: הוסף endpoints לשרת
צריך להוסיף:
- `POST /api/families/:familyId/push-token` - שמירת token
- `DELETE /api/families/:familyId/push-token` - מחיקת token
- פונקציות לשליחת הודעות

#### שלב 4: הוסף לוגיקה לשליחת הודעות
צריך להוסיף קריאות לשליחת הודעות ב:
- `processAllowancesForFamily` - כשדמי כיס משולמים
- `processInterestForFamily` - כשהריבית מחושבת
- `app.post('/api/families/:familyId/transactions')` - כשמתבצעת עסקה (אופציונלי)

## מבנה Database

צריך להוסיף שדה `pushTokens` לכל משפחה:
```javascript
{
  _id: "family_id",
  name: "Family Name",
  pushTokens: [
    {
      token: "device_token_here",
      platform: "ios" | "android",
      createdAt: "2025-01-11T..."
    }
  ],
  // ... שאר השדות
}
```

## הודעות

### דמי כיס
**כותרת:** "דמי כיס התקבלו! 💰"
**תוכן:** "התקבלו {amount} ש״ח דמי כיס שבועיים/חודשיים"

### ריבית
**כותרת:** "הרווחת ריבית! 📈"
**תוכן:** "הרווחת {amount} ש״ח מריבית יומית. המשך לחסוך!"

### עסקאות (אופציונלי)
**כותרת:** "עסקה חדשה"
**תוכן:** "{type}: {amount} ש״ח - {description}"

## בדיקה

### Android
1. התקן את האפליקציה על מכשיר
2. התחבר
3. בדוק ב-logs שהטוקן נרשם
4. בדוק שההודעות מגיעות

### iOS
1. צריך מכשיר פיזי (לא סימולטור)
2. התקן את האפליקציה
3. תן הרשאות ל-push notifications
4. בדוק שההודעות מגיעות

## פתרון בעיות

### Android - הודעות לא מגיעות
- בדוק ש-`google-services.json` קיים
- בדוק ש-Firebase Server Key נכון
- בדוק ב-logs של Firebase Console

### iOS - הודעות לא מגיעות
- בדוק שה-certificate תקף
- בדוק ש-Bundle ID נכון
- בדוק ש-APNs Key/Password נכונים
- צריך מכשיר פיזי (לא סימולטור)

## הערות

- **Android:** עובד גם ב-emulator (אבל צריך Google Play Services)
- **iOS:** צריך מכשיר פיזי - לא עובד ב-simulator
- **Web:** לא תומך ב-push notifications (רק native)

## שלבים הבאים

1. ✅ Frontend - הושלם
2. ⏳ Firebase setup ל-Android
3. ⏳ APNs setup ל-iOS
4. ⏳ Backend endpoints
5. ⏳ לוגיקה לשליחת הודעות
6. ⏳ בדיקה
