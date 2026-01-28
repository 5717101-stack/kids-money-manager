# מדריך מפורט למילוי App Store Connect

## 🔴 שגיאה 1: Age Rating (דירוג גיל)

### איפה למצוא:
1. ב-App Store Connect, לך ל: **App Information** → **Age Rating**
2. או ישירות: בחר את האפליקציה → **App Information** → גלול למטה ל-**Age Rating**

### מה לכתוב:
**לאפליקציית ניהול כסף לילדים, מומלץ:**
- **Age Rating:** 4+ (או 9+ אם יש תכונות מתקדמות)
- **Content Descriptions:** 
  - **Unrestricted Web Access:** None (אין גישה לא מוגבלת לאינטרנט)
  - **User Generated Content:** None (אין תוכן שנוצר על ידי משתמשים)
  - **Gambling and Contests:** None (אין הימורים)
  - **Contests:** None (אין תחרויות)
  - **Simulated Gambling:** None (אין הימורים מדומים)
  - **Frequent/Intense Realistic Violence:** None
  - **Frequent/Intense Cartoon or Fantasy Violence:** None
  - **Frequent/Intense Sexual Content or Nudity:** None
  - **Frequent/Intense Mature/Suggestive Themes:** None
  - **Frequent/Intense Horror/Fear Themes:** None
  - **Frequent/Intense Profanity or Crude Humor:** None
  - **Frequent/Intense Alcohol, Tobacco, or Drug Use or References:** None
  - **Medical/Treatment Information:** None
  - **Unrestricted Web Access:** None
  - **Gambling and Contests:** None

**לכל סעיף, בחר "None" או "Infrequent/Mild"** (תלוי אם יש תכונות מסוימות)

---

## 🔴 שגיאה 2: Build (בחירת Build)

### איפה למצוא:
1. ב-App Store Connect, לך ל: **iOS App Version 1.1** → **Build**
2. לחץ על **"Select a build before you submit your app"** או **"+"** ליד Build

### מה לעשות:
**אם אין Build:**
1. **צריך לבנות את האפליקציה ב-Xcode:**
   - פתח את הפרויקט ב-Xcode
   - בחר **Product** → **Archive**
   - אחרי שהארכיון נוצר, לחץ **Distribute App**
   - בחר **App Store Connect**
   - בחר **Upload**
   - עקוב אחר ההוראות
   - **זה יכול לקחת 10-30 דקות** עד שהבילד יופיע ב-App Store Connect

**אם יש Build:**
- פשוט בחר אותו מהרשימה

**הערה:** Build חייב להיות ב-Release mode ולא Debug

---

## 🔴 שגיאה 3: App Privacy (מדיניות פרטיות)

### איפה למצוא:
1. ב-App Store Connect, לך ל: **App Privacy** (בתפריט השמאלי)
2. או: **App Information** → **App Privacy**

### מה לכתוב:

**1. Data Types (סוגי נתונים):**
   - **Phone Number:** 
     - Used for App Functionality
     - Linked to User
     - Used for Third-Party Advertising: No
     - Tracking: No
   
   - **Financial Information:**
     - Used for App Functionality
     - Linked to User
     - Used for Third-Party Advertising: No
     - Tracking: No
   
   - **User Content (תמונות):**
     - Used for App Functionality
     - Linked to User
     - Used for Third-Party Advertising: No
     - Tracking: No

**2. Data Use:**
   - **App Functionality:** Yes
   - **Analytics:** No (אלא אם כן אתה משתמש ב-analytics)
   - **Product Personalization:** No
   - **Advertising:** No
   - **Developer's Advertising or Marketing:** No
   - **Other Purposes:** No

**3. Data Linked to User:**
   - Yes (כי הנתונים קשורים למשתמש ספציפי)

**4. Tracking:**
   - No (אלא אם כן אתה עושה tracking)

**5. Privacy Policy URL:**
   ```
   https://5717101-stack.github.io/family-bank-support-/privacy.html
   ```

---

## 🔴 שגיאה 4: Pricing (מחיר)

### איפה למצוא:
1. ב-App Store Connect, לך ל: **Pricing and Availability**
2. או: **App Information** → **Pricing and Availability**

### מה לכתוב:

**1. Price:**
   - **Free** (אם האפליקציה חינמית)
   - או בחר מחיר (אם האפליקציה בתשלום)

**2. Availability:**
   - בחר את המדינות שבהן האפליקציה תהיה זמינה
   - מומלץ: **All Countries** (כל המדינות)

**3. Sales and Promotions:**
   - השאר ברירת מחדל (אלא אם כן יש לך מבצעים)

---

## ✅ סיכום - סדר פעולות:

1. **Age Rating** → בחר "None" לכל הסעיפים
2. **Build** → בנה ב-Xcode ו-Upload ל-App Store Connect
3. **App Privacy** → מלא את הפרטים + הוסף את Privacy Policy URL
4. **Pricing** → בחר "Free" או מחיר

---

## 🔗 קישורים שימושיים:

- **Privacy Policy:** https://5717101-stack.github.io/family-bank-support-/privacy.html
- **Support:** https://5717101-stack.github.io/family-bank-support-/

---

## 💡 טיפים:

- **Build:** אם אין לך Build, זה השלב הכי ארוך (10-30 דקות)
- **App Privacy:** אם אתה לא בטוח, בחר "No" לכל דבר חוץ מ-App Functionality
- **Age Rating:** לאפליקציית ניהול כסף לילדים, 4+ עם "None" לכל הסעיפים זה בטוח
