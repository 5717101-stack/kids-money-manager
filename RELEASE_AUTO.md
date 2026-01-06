# שחרור גרסה אוטומטי

## שימוש:

```bash
cd ~/Projects/kids-money-manager
./auto_release.sh
```

הסקריפט:
1. ✅ מעדכן את הגרסה אוטומטית (+0.1.0)
2. ✅ עושה commit
3. ✅ דוחף ל-GitHub
4. ✅ הכל אוטומטי - אין צורך באישורים!

## שינוי צבע כפתור:

אם צריך לשנות צבע כפתור "ממשק הורה", ערוך את `src/styles/App.css`:

```css
.main-nav button.parent-button.active {
  background: var(--secondary);  /* סגול */
  /* או */
  background: var(--primary);    /* כחול */
  /* או */
  background: var(--success);    /* ירוק */
}
```

ואז הרץ: `./auto_release.sh`
