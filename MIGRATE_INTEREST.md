# Migration: עדכון תנועות ריבית היסטוריות

## הבעיה
לפני התיקון, תנועות ריבית זוהו לפי `description` (תיאור). זה אפשר למשתמשים ליצור תנועות מזויפות עם תיאור "ריבית".

## התיקון
עכשיו תנועות ריבית מזוהות לפי `id` שמתחיל ב-`"interest_"`. רק השרת יכול ליצור תנועות עם id כזה.

## מה צריך לעשות

### עדכון נתונים היסטוריים
יש תנועות ריבית קיימות בדאטה בייס שנוצרו לפני התיקון. צריך לעדכן אותן.

### הרצת Migration

**אופציה 1: מהתיקייה הראשית**
```bash
cd server
export MONGODB_URI="your-mongodb-connection-string"
node migrate_interest_transactions.js
```

**אופציה 2: עם סקריפט**
```bash
export MONGODB_URI="your-mongodb-connection-string"
./server/migrate_interest_transactions.sh
```

**אופציה 3: אם יש .env בשרת**
```bash
cd server
node migrate_interest_transactions.js
```

## מה הסקריפט עושה

1. **מחפש** כל תנועות ריבית קיימות:
   - `description` מכיל "ריבית" או "interest"
   - אבל `id` לא מתחיל ב-`"interest_"`

2. **מעדכן** את ה-`id` לפורמט הנכון:
   - `interest_${timestamp}_${childId}`
   - משתמש ב-`date` של התנועה ל-timestamp

3. **שומר** את כל התנועות המעודכנות בדאטה בייס

## דוגמת פלט

```
🔄 Starting interest transactions migration...
✅ Connected to MongoDB
📊 Found 5 families to process
  📝 Updating transaction: txn_123 -> interest_1768138878185_child_123 (ריבית יומית)
✅ Updated family 507f1f77bcf86cd799439011
✅ Migration complete!
📊 Summary:
   - Families processed: 5
   - Families updated: 2
   - Transactions updated: 15
```

## הערות חשובות

1. **גיבוי**: מומלץ לגבות את הדאטה בייס לפני הרצת migration
2. **פעם אחת**: הסקריפט בטוח להרצה מספר פעמים (idempotent)
3. **לא הרסני**: הסקריפט רק מעדכן id, לא מוחק או משנה סכומים

## בדיקה לאחר Migration

לאחר הרצת הסקריפט, בדוק:
1. פתח את האפליקציה
2. בדוק את `totalInterestEarned` - צריך להיות נכון
3. בדוק את תנועות הריבית - כולן צריכות להיות עם id שמתחיל ב-`"interest_"`
