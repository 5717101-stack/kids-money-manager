# 🔑 איך להשיג API Keys

## אפשרות 1: OpenAI (מומלץ להתחלה)

### שלב 1: הרשמה/התחברות
1. לך ל: https://platform.openai.com/
2. התחבר או הירשם (אם אין לך חשבון)
3. תצטרך כרטיס אשראי (יש $5 credit חינם להתחלה)

### שלב 2: יצירת API Key
1. לחץ על פרופיל שלך (פינה ימנית עליונה)
2. בחר "API keys" או "View API keys"
3. לחץ "Create new secret key"
4. תן שם (למשל: "Daily Sync")
5. העתק את ה-key מיד! (לא תוכל לראות אותו שוב)

### שלב 3: הוספה לפרויקט
```bash
cd daily-sync-backend
# ערוך את .env
nano .env
# או
open .env
```

הוסף את השורה:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

### מחירים (נכון ל-2024):
- GPT-4o: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- GPT-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- יש $5 credit חינם להתחלה

---

## אפשרות 2: Anthropic (Claude)

### שלב 1: הרשמה
1. לך ל: https://console.anthropic.com/
2. הירשם או התחבר
3. תצטרך כרטיס אשראי

### שלב 2: יצירת API Key
1. לך ל: https://console.anthropic.com/settings/keys
2. לחץ "Create Key"
3. תן שם (למשל: "Daily Sync")
4. העתק את ה-key

### שלב 3: הוספה לפרויקט
```bash
cd daily-sync-backend
# ערוך את .env
nano .env
```

הוסף את השורה:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

### מחירים (נכון ל-2024):
- Claude 3.5 Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- יש $5 credit חינם להתחלה

---

## איזה לבחור?

### OpenAI (GPT-4o) - מומלץ להתחלה:
✅ יותר זול  
✅ יותר מהיר  
✅ יותר תיעוד ודוגמאות  
✅ $5 credit חינם  

### Anthropic (Claude 3.5 Sonnet):
✅ איכות כתיבה טובה יותר  
✅ הבנה עמוקה יותר של הקשר  
✅ טוב יותר לניתוחים ארוכים  

**המלצה**: התחל עם OpenAI GPT-4o, זה יותר זול וקל להתחלה.

---

## הוספת API Key לפרויקט

### שיטה 1: עורך טקסט
```bash
cd daily-sync-backend
cp .env.example .env
# ערוך את .env והוסף:
OPENAI_API_KEY=sk-your-key-here
```

### שיטה 2: שורת פקודה
```bash
cd daily-sync-backend
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### שיטה 3: עורך גרפי
```bash
cd daily-sync-backend
open .env  # ב-Mac
# או
code .env  # ב-VS Code
```

---

## בדיקה שהכל עובד

לאחר שהוספת את ה-API key:

```bash
cd daily-sync-backend
source venv/bin/activate
python test_script.py
```

אם הכל תקין, תראה ניתוח AI אמיתי במקום הודעות placeholder.

---

## אבטחה - חשוב!

⚠️ **לעולם אל תעלה את .env ל-Git!**

הקובץ `.env` כבר ב-`.gitignore`, אבל תמיד בדוק:
- ✅ `.env` לא ב-Git
- ✅ רק `.env.example` ב-Git (ללא keys אמיתיים)
- ✅ אם בטעות העלית key, שנה אותו מיד ב-OpenAI/Anthropic

---

## בעיות נפוצות

### "Invalid API key"
- בדוק שהעתקת את כל ה-key (ללא רווחים)
- בדוק שיש `OPENAI_API_KEY=` או `ANTHROPIC_API_KEY=` לפני ה-key
- ודא שהקובץ `.env` בתיקיית `daily-sync-backend/`

### "Insufficient credits"
- הוסף כרטיס אשראי ב-OpenAI/Anthropic console
- בדוק את ה-usage ב-dashboard

### "Rate limit exceeded"
- חכה כמה דקות
- או שדרג את התוכנית שלך

---

## קישורים שימושיים

- OpenAI Platform: https://platform.openai.com/
- OpenAI API Keys: https://platform.openai.com/api-keys
- Anthropic Console: https://console.anthropic.com/
- Anthropic API Keys: https://console.anthropic.com/settings/keys
- OpenAI Pricing: https://openai.com/api/pricing/
- Anthropic Pricing: https://www.anthropic.com/pricing

---

## טיפים לחיסכון

1. **השתמש ב-GPT-4o-mini** לבדיקות (זול יותר):
   ```env
   DEFAULT_MODEL=gpt-4o-mini
   ```

2. **הגבל את אורך הקלט** - פחות tokens = פחות כסף

3. **עקוב אחרי ה-usage** ב-dashboard

4. **השתמש ב-cache** - ChromaDB שומר embeddings

---

## מוכן להתחיל?

1. לך ל-https://platform.openai.com/
2. צור API key
3. הוסף ל-`.env`
4. הרץ `python test_script.py`

🎉 **בהצלחה!**
