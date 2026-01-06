# פתרון בעיית Container שנעצר ב-Railway

## הבעיה
הקונטיינר נעצר עם SIGTERM למרות שהשרת רץ בהצלחה.

## למה זה קורה?

SIGTERM ב-Railway יכול לקרות מסיבות שונות:
1. **Redeploy** - Railway עושה redeploy אוטומטי
2. **Scaling** - Railway משנה את ה-scaling
3. **Health Check Failed** - Railway לא מזהה שהשרת בריא
4. **Resource Limits** - השרת חורג מ-resource limits

## מה עשיתי

### 1. השרת מתחיל מיד
- לא מחכה ל-DB
- Health check עונה מיד
- Railway מזהה שהשרת בריא מהר יותר

### 2. שיפור לוגים
- עכשיו תראה כמה זמן השרת רץ לפני SIGTERM
- זה יעזור להבין אם זה redeploy או בעיה אחרת

## מה לבדוק עכשיו

### 1. בדוק את הלוגים
אחרי SIGTERM, תראה:
```
⚠️  SIGTERM received from Railway - this is normal for deployments
   Server was running for X seconds
```

**אם השרת רץ יותר מ-60 שניות לפני SIGTERM:**
- זה כנראה redeploy או scaling - זה נורמלי
- השרת יתחיל מחדש אוטומטית

**אם השרת רץ פחות מ-30 שניות לפני SIGTERM:**
- זה אומר ש-Railway לא מזהה שהשרת בריא
- צריך לבדוק את ה-Settings ב-Railway

### 2. בדוק את ה-Settings ב-Railway
1. היכנס ל-Railway Dashboard
2. בחר את השירות `kids-money-manager-server`
3. לך ל-Settings → Health Check
4. ודא ש:
   - **Health Check Path**: `/health`
   - **Health Check Timeout**: 30 שניות
   - **Health Check Interval**: 10-30 שניות

### 3. בדוק את ה-Deployments
1. ב-Railway Dashboard → Deployments
2. בדוק אם יש redeploy אוטומטי
3. אם יש, זה מסביר למה השרת נעצר

## אם השרת עדיין נעצר

### אפשרות 1: Railway Settings
- בדוק את ה-Health Check Settings
- ודא שהנתיב נכון (`/health`)
- נסה להגדיל את ה-timeout

### אפשרות 2: Manual Redeploy
- ב-Railway Dashboard → Deployments
- לחץ על "Redeploy"
- זה יכול לפתור בעיות של configuration

### אפשרות 3: Resource Limits
- בדוק אם השרת חורג מ-resource limits
- ב-Railway Dashboard → Metrics
- אם יש בעיה, צריך לשדרג את ה-plan

## הערות

- SIGTERM לא תמיד אומר שיש בעיה - זה יכול להיות redeploy נורמלי
- השרת יתחיל מחדש אוטומטית אחרי SIGTERM
- אם השרת רץ יותר מ-60 שניות לפני SIGTERM, זה כנראה נורמלי
- אם השרת רץ פחות מ-30 שניות, צריך לבדוק את ה-Settings

## מה לעשות עכשיו

1. **חכה ל-deploy החדש** (1-2 דקות)
2. **בדוק את הלוגים** - תראה כמה זמן השרת רץ לפני SIGTERM
3. **אם השרת רץ יותר מ-60 שניות** - זה נורמלי, השרת יתחיל מחדש
4. **אם השרת רץ פחות מ-30 שניות** - בדוק את ה-Settings ב-Railway

