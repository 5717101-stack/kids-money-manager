# הוראות להעלאת הפרויקט ל-Git

## שלב 1: הוסף את הקבצים

כל הקבצים החשובים כבר מוכנים. כדי להעלות אותם:

```bash
cd daily-sync-backend
git add .env.example .gitattributes .gitignore QUICK_START.md README.md SETUP_COMPLETE.md SYNC_INSTRUCTIONS.md app/ main.py requirements.txt
```

## שלב 2: Commit

```bash
git commit -m "Initial commit: Daily Sync AI Life Coach backend"
```

## שלב 3: Push

```bash
git push
```

## מה יועלה ל-Git?

✅ **יועלה:**
- כל קוד המקור (`app/`, `main.py`)
- `requirements.txt` - תלויות
- `.env.example` - תבנית להגדרות
- כל הקבצי תיעוד (`.md`)
- `.gitignore` ו-`.gitattributes`

❌ **לא יועלה** (בגלל .gitignore):
- `venv/` - סביבה וירטואלית
- `data/` - מסדי נתונים
- `.env` - API keys (רגיש!)

## אחרי ההעלאה

במחשב בבית, תוכל:
1. `git clone <repository-url>`
2. לעקוב אחרי ההוראות ב-`SYNC_INSTRUCTIONS.md`
