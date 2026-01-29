# הוראות סנכרון בין מחשבים

## סנכרון ראשוני (במחשב הראשון)

1. **הוסף את כל הקבצים ל-Git**:
   ```bash
   cd daily-sync-backend
   git add .
   git commit -m "Initial commit: Daily Sync AI Life Coach backend"
   git push
   ```

## התקנה במחשב אחר (בבית)

1. **שכפל את הפרויקט**:
   ```bash
   git clone <repository-url>
   cd daily-sync-backend
   ```

2. **צור סביבה וירטואלית והתקן תלויות**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # ב-Windows: venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **העתק את קובץ ההגדרות**:
   ```bash
   cp .env.example .env
   ```

4. **ערוך את `.env` והוסף את ה-API keys שלך**:
   ```bash
   # פתח את .env בעורך טקסט והוסף:
   OPENAI_API_KEY=sk-your-key-here
   # או
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

5. **אתחל את מסד הנתונים**:
   ```bash
   python -c "from app.core.database import init_sqlite_db; import asyncio; asyncio.run(init_sqlite_db())"
   ```

6. **הרץ את השרת**:
   ```bash
   python main.py
   ```

## סנכרון יומיומי

### לפני שסוגרים את המחשב:
```bash
cd daily-sync-backend
git add .
git commit -m "Work progress: [תיאור קצר]"
git push
```

### כשמתחילים לעבוד במחשב אחר:
```bash
cd daily-sync-backend
git pull
source venv/bin/activate  # אם הסביבה לא פעילה
```

## קבצים שלא מסונכרנים (בגלל .gitignore)

הקבצים הבאים **לא** יועלו ל-Git (זה בסדר):
- `venv/` - סביבה וירטואלית (תתקין מחדש בכל מחשב)
- `data/` - מסדי נתונים (ייווצרו מחדש)
- `.env` - API keys (תיצור מחדש מ-.env.example)

## פתרון בעיות

### אם יש קונפליקטים ב-Git:
```bash
git pull
# אם יש קונפליקטים, פתור אותם ידנית ואז:
git add .
git commit -m "Resolved conflicts"
git push
```

### אם הסביבה הוירטואלית לא עובדת:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
