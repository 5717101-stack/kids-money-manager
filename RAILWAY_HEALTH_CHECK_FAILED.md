# תיקון: Health Check נכשל

## הבעיה
Health check נכשל כי השרת לא עונה בזמן.

## מה לבדוק

### 1. בדוק את הלוגים של השרת
ב-Railway Dashboard:
1. בחר את השירות
2. לחץ על **Deployments**
3. לחץ על ה-Deployment האחרון
4. בדוק את ה-Logs

### 2. מה לחפש בלוגים
- האם השרת מתחיל בכלל?
- האם רואים `[SERVER] Started on port`?
- האם רואים `[SERVER] Health check endpoint is ready`?
- כמה זמן לוקח להתחיל?

### 3. אם השרת לא מתחיל
אם השרת לא מתחיל בכלל, הבעיה יכולה להיות:
- **Dependencies לא מותקנים** - בדוק את ה-Build Logs
- **שגיאה בקוד** - בדוק את ה-Logs
- **Port לא נכון** - בדוק שהשרת מאזין ל-`process.env.PORT`

### 4. אם השרת מתחיל אבל health check נכשל
אם השרת מתחיל אבל health check נכשל:
- **Health check endpoint לא עובד** - בדוק שהנתיב נכון (`/health`)
- **השרת לא עונה מספיק מהר** - הגדל את `healthcheckTimeout`
- **השרת לא מאזין ל-PORT הנכון** - בדוק שהשרת מאזין ל-`0.0.0.0:PORT`

## פתרונות

### פתרון 1: הגדלת Timeout
ב-Railway Dashboard:
1. Settings → Health Check
2. הגדל את **Health Check Timeout** ל-600 שניות (10 דקות)

### פתרון 2: בדיקת Port
ודא שהשרת מאזין ל-`process.env.PORT` ולא ל-port קבוע.

### פתרון 3: בדיקת Health Check Endpoint
נסה לגשת ל-health check endpoint ידנית:
```
curl https://your-service.railway.app/health
```

אם זה עובד, הבעיה היא ב-Railway Settings.
אם זה לא עובד, הבעיה היא בקוד.

## אם עדיין לא עובד
שלח את הלוגים המלאים של השרת כדי שנראה מה קורה.

