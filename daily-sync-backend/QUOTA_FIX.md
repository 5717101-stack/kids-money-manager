# ⚠️ פתרון בעיית Quota

## הבעיה:
```
Error code: 429 - insufficient_quota
You exceeded your current quota
```

## מה זה אומר?
ה-API key תקין, אבל אין credits/כרטיס אשראי בחשבון OpenAI.

## פתרון:

### שלב 1: הוסף כרטיס אשראי
1. לך ל: https://platform.openai.com/account/billing
2. לחץ "Add payment method"
3. הוסף כרטיס אשראי
4. הגדר spending limit (למשל $10 לחודש)

### שלב 2: בדוק credits
1. לך ל: https://platform.openai.com/usage
2. בדוק כמה credits נותרו
3. אם יש $5 credit חינם - ייתכן שהוא אזל

### שלב 3: הרץ שוב
```bash
cd daily-sync-backend
source venv/bin/activate
python test_script.py
```

## חלופות:

### אפשרות 1: Anthropic (Claude)
אם יש לך Anthropic API key:
```bash
# ערוך .env
ANTHROPIC_API_KEY=sk-ant-your-key
DEFAULT_LLM_PROVIDER=anthropic
```

### אפשרות 2: GPT-4o-mini (זול יותר)
אם יש לך קצת credits, נסה עם מודל זול יותר:
```bash
# ערוך .env
DEFAULT_MODEL=gpt-4o-mini
```

## הערות:
- ה-API key תקין ✅
- החיבור עובד ✅
- רק צריך credits/כרטיס אשראי

## קישורים:
- Billing: https://platform.openai.com/account/billing
- Usage: https://platform.openai.com/usage
- Pricing: https://openai.com/api/pricing/
