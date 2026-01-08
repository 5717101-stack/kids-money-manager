# מבנה מסד הנתונים - Kids Money Manager

## סקירה כללית

המערכת משתמשת ב-**MongoDB** עם מבנה **Embedded Documents** (מסמכים משובצים). בניגוד למסדי נתונים יחסיים (SQL), כאן כל הנתונים מאוחסנים בקולקציה אחת עיקרית: `families`.

---

## הקולקציות (Collections)

### 1. `families` - הקולקציה הראשית

זוהי הקולקציה היחידה שמכילה את כל הנתונים. כל מסמך (document) מייצג משפחה אחת.

#### מבנה מסמך משפחה:

```javascript
{
  _id: "family_1234567890_abc123",        // מזהה ייחודי של המשפחה
  phoneNumber: "+972501234567",            // מספר טלפון של ההורה (ייחודי)
  countryCode: "+972",                     // קידומת מדינה
  createdAt: "2024-01-15T10:30:00.000Z", // תאריך יצירה
  
  // ========== ילדים (Children) ==========
  children: [
    {
      _id: "child_1234567890_xyz789",      // מזהה ייחודי של הילד
      name: "נועה",                        // שם הילד
      phoneNumber: "+972501234568",        // מספר טלפון של הילד (ייחודי)
      balance: 150.50,                     // יתרה אצל ההורים (₪)
      cashBoxBalance: 30.00,              // יתרה בקופה (₪)
      profileImage: "https://...",         // תמונת פרופיל
      
      // הגדרות דמי כיס
      weeklyAllowance: 50,                // סכום דמי כיס
      allowanceType: "weekly",             // סוג: "weekly" או "monthly"
      allowanceDay: 1,                    // יום בשבוע (1=ראשון) או תאריך בחודש
      allowanceTime: "08:00",              // שעה להעברה אוטומטית
      
      // עסקאות (Transactions) - משובצות בתוך הילד
      transactions: [
        {
          _id: "trans_1234567890_def456",
          type: "deposit",                 // "deposit" או "expense"
          amount: 50.00,                   // סכום
          description: "דמי כיס שבועיים", // תיאור
          category: "cat_1",               // מזהה קטגוריה
          date: "2024-01-15T08:00:00.000Z" // תאריך
        },
        // ... עוד עסקאות
      ],
      
      // מטרות חיסכון (Savings Goals)
      savingsGoal: {
        title: "סט לגו חדש",              // שם המטרה
        targetAmount: 200.00,              // סכום יעד
        currentAmount: 150.50,             // סכום נוכחי
        createdAt: "2024-01-10T10:00:00.000Z"
      },
      
      createdAt: "2024-01-10T10:00:00.000Z"
    },
    // ... עוד ילדים
  ],
  
  // ========== קטגוריות (Categories) ==========
  categories: [
    {
      _id: "cat_1",
      name: "משחקים",
      activeFor: ["child_1234567890_xyz789"] // רשימת מזההי ילדים שהקטגוריה פעילה עבורם
    },
    {
      _id: "cat_2",
      name: "ממתקים",
      activeFor: []
    },
    // ... עוד קטגוריות
  ]
}
```

---

## הקשרים בין הנתונים

### 1. **משפחה ↔ ילדים**
- **קשר**: **1-to-Many** (משפחה אחת יכולה להכיל מספר ילדים)
- **אופן אחסון**: הילדים מאוחסנים כ-**מערך** (`children[]`) בתוך מסמך המשפחה
- **חיפוש**: `db.collection('families').findOne({ 'children._id': childId })`
- **עדכון**: `db.collection('families').updateOne({ _id: familyId, 'children._id': childId }, { $set: { 'children.$.field': value } })`

### 2. **ילד ↔ עסקאות**
- **קשר**: **1-to-Many** (ילד אחד יכול להכיל מספר עסקאות)
- **אופן אחסון**: העסקאות מאוחסנות כ-**מערך** (`transactions[]`) בתוך אובייקט הילד
- **חיפוש**: `family.children.find(c => c._id === childId).transactions`
- **עדכון**: עדכון הילד כולל את כל העסקאות שלו

### 3. **משפחה ↔ קטגוריות**
- **קשר**: **1-to-Many** (משפחה אחת יכולה להכיל מספר קטגוריות)
- **אופן אחסון**: הקטגוריות מאוחסנות כ-**מערך** (`categories[]`) בתוך מסמך המשפחה
- **חיפוש**: `family.categories.find(c => c._id === categoryId)`
- **עדכון**: `db.collection('families').updateOne({ _id: familyId }, { $set: { categories: newCategories } })`

### 4. **קטגוריה ↔ ילדים**
- **קשר**: **Many-to-Many** (קטגוריה יכולה להיות פעילה עבור מספר ילדים)
- **אופן אחסון**: כל קטגוריה מכילה מערך `activeFor[]` עם מזההי הילדים
- **דוגמה**: `{ _id: "cat_1", name: "משחקים", activeFor: ["child_1", "child_2"] }`

---

## אינדקסים (Indexes)

המערכת יוצרת אינדקסים כדי לשפר ביצועים:

1. **`phoneNumber`** - ייחודי (unique) - מונע מספרי טלפון כפולים למשפחות
2. **`children._id`** - מאפשר חיפוש מהיר של ילדים לפי מזהה
3. **`otpCodes.phoneNumber`** - לחיפוש מהיר של קודי OTP
4. **`otpCodes.expiresAt`** - עם TTL (Time To Live) למחיקה אוטומטית

---

## יתרונות המבנה הנוכחי

### ✅ יתרונות:
1. **פשוט לניהול** - כל הנתונים של משפחה במקום אחד
2. **קריאה מהירה** - אין צורך ב-JOIN בין טבלאות
3. **עקביות** - עדכון אחד מעדכן את כל הנתונים הקשורים
4. **גמישות** - קל להוסיף שדות חדשים

### ⚠️ חסרונות:
1. **גודל מסמך** - אם יש הרבה ילדים/עסקאות, המסמך יכול להיות גדול
2. **שכפול** - קטגוריות משוכפלות בכל משפחה (אבל זה מתאים כי כל משפחה יכולה להתאים אותן)
3. **עדכונים מורכבים** - עדכון עסקה אחת דורש עדכון של כל מערך העסקאות

---

## דוגמאות לשאילתות נפוצות

### מציאת משפחה לפי מספר טלפון:
```javascript
const family = await db.collection('families').findOne({ 
  phoneNumber: "+972501234567" 
});
```

### מציאת ילד לפי מספר טלפון:
```javascript
const family = await db.collection('families').findOne({
  'children.phoneNumber': "+972501234568"
});
const child = family.children.find(c => c.phoneNumber === "+972501234568");
```

### הוספת עסקה לילד:
```javascript
await db.collection('families').updateOne(
  { _id: familyId, 'children._id': childId },
  { 
    $push: { 
      'children.$.transactions': newTransaction 
    },
    $set: { 
      'children.$.balance': newBalance 
    }
  }
);
```

### עדכון יתרה של ילד:
```javascript
await db.collection('families').updateOne(
  { _id: familyId, 'children._id': childId },
  { $set: { 'children.$.balance': 200.00 } }
);
```

---

## סיכום

המערכת משתמשת ב-**מבנה Embedded Documents** שבו:
- **קולקציה אחת עיקרית**: `families`
- **כל הנתונים משובצים**: ילדים, עסקאות, קטגוריות - הכל בתוך מסמך המשפחה
- **חיפוש לפי שדות משובצים**: `'children.phoneNumber'`, `'children._id'`
- **עדכונים עם positional operator**: `$` לעדכון אובייקט ספציפי במערך

זה מבנה **NoSQL** טיפוסי שמתאים למערכת שבה כל משפחה היא יחידה עצמאית עם כל הנתונים שלה.

