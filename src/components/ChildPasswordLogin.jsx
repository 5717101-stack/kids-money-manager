import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getData, getChildPassword } from '../utils/api';

const ChildPasswordLogin = ({ familyId, onChildVerified, onBack }) => {
  const { t } = useTranslation();
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!password || password.length < 4) {
      setError(t('auth.childPassword.enterValidPassword', { defaultValue: 'אנא הכנס סיסמה תקינה' }));
      return;
    }

    if (!familyId) {
      setError(t('auth.childPassword.familyIdNotFound', { defaultValue: 'שגיאה: לא נמצא מספר משפחה. אנא נסה להתחבר מחדש.' }));
      return;
    }

    setIsLoading(true);

    try {
      const trimmedPassword = password.trim();
      
      console.log('[CHILD-PASSWORD] Verifying password:', {
        familyId,
        familyIdType: typeof familyId,
        familyIdLength: familyId?.length,
        passwordLength: trimmedPassword.length,
        passwordPreview: trimmedPassword.substring(0, 2) + '***'
      });
      
      // Get all children in the family
      const familyData = await getData(familyId);
      const children = Object.values(familyData.children || {});
      
      console.log('[CHILD-PASSWORD] Found children:', children.length);
      
      // Find child with matching password
      let foundChild = null;
      for (const child of children) {
        try {
          const childPassword = await getChildPassword(familyId, child._id);
          console.log(`[CHILD-PASSWORD] Checking child ${child._id} (${child.name})`);
          
          if (childPassword === trimmedPassword) {
            foundChild = { ...child, _id: child._id };
            console.log('[CHILD-PASSWORD] ✅ Password match found!', foundChild);
            break;
          }
        } catch (err) {
          console.warn(`[CHILD-PASSWORD] Error checking password for child ${child._id}:`, err);
        }
      }
      
      if (!foundChild) {
        throw new Error(t('auth.childPassword.wrongPassword', { defaultValue: 'סיסמה שגויה' }));
      }
      
      const data = { child: foundChild };

      if (data.child) {
        onChildVerified(data.child, familyId);
      } else {
        throw new Error(t('auth.childPassword.childNotFound', { defaultValue: 'ילד לא נמצא' }));
      }
    } catch (error) {
      console.error('[CHILD-PASSWORD] Error verifying child password:', error);
      console.error('[CHILD-PASSWORD] Error name:', error.name);
      console.error('[CHILD-PASSWORD] Error message:', error.message);
      console.error('[CHILD-PASSWORD] Error stack:', error.stack);
      
      // Translate common error messages to Hebrew
      let errorMessage = error.message || t('auth.childPassword.wrongPassword', { defaultValue: 'סיסמה שגויה' });
      
      // Handle network errors
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        errorMessage = t('auth.childPassword.networkError', { defaultValue: 'שגיאת רשת. אנא בדוק את החיבור לאינטרנט ונסה שוב.' });
      }
      // Handle JSON parse errors (HTML response)
      else if (error.message.includes('Unexpected token') || error.message.includes('JSON') || error.message.includes('DOCTYPE')) {
        errorMessage = t('auth.childPassword.serverError', { defaultValue: 'השרת החזיר שגיאה. אנא נסה שוב מאוחר יותר או פנה לתמיכה.' });
      }
      // Handle pattern validation errors
      else if (errorMessage.includes('pattern') || errorMessage.includes('expected pattern') || errorMessage.includes('validation')) {
        errorMessage = t('auth.childPassword.invalidPasswordFormat', { defaultValue: 'סיסמה לא תקינה. אנא בדוק שהסיסמה נכונה והעתקת אותה במלואה (ללא רווחים מיותרים).' });
      }
      // Handle not found errors
      else if (errorMessage.includes('not found') || errorMessage.includes('לא נמצא') || errorMessage.includes('NotFound')) {
        errorMessage = t('auth.childPassword.childNotFoundInFamily', { defaultValue: 'ילד לא נמצא במשפחה זו.' });
      }
      // Handle incorrect password
      else if (errorMessage.includes('incorrect') || errorMessage.includes('שגויה') || errorMessage.includes('Invalid')) {
        errorMessage = t('auth.childPassword.wrongPasswordTryAgain', { defaultValue: 'סיסמה שגויה. אנא נסה שוב.' });
      }
      // Handle ObjectId validation errors
      else if (errorMessage.includes('ObjectId') || errorMessage.includes('Cast to ObjectId')) {
        errorMessage = t('auth.childPassword.invalidFamilyId', { defaultValue: 'שגיאה: מספר משפחה לא תקין. אנא נסה להתחבר מחדש.' });
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="child-password-login">
      <div className="child-password-container">
        <div className="child-password-header">
          <button className="back-button" onClick={onBack}>
            {t('auth.childPassword.back', { defaultValue: '← חזור' })}
          </button>
          <h1>🔐 {t('auth.childPassword.title', { defaultValue: 'הכנס סיסמה' })}</h1>
          <p className="child-password-subtitle">
            {t('auth.childPassword.subtitle', { defaultValue: 'הכנס את הסיסמה שלך כדי להתחבר לחשבון' })}
          </p>
          <p style={{ 
            fontSize: '14px', 
            color: '#64748b', 
            marginTop: '8px',
            padding: '12px',
            backgroundColor: '#f1f5f9',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            💡 <strong>{t('auth.childPassword.whereToFind', { defaultValue: 'איפה למצוא את הסיסמה?' })}</strong><br/>
            {t('auth.childPassword.parentCanSee', { defaultValue: 'ההורה שלך יכול לראות את הסיסמה שלך בהגדרות' })}<br/>
            ({t('auth.childPassword.parentInstructions', { defaultValue: '⚙️ הגדרות → בחר אותך → 🔑 שחזר סיסמה' })})
          </p>
        </div>

        <form onSubmit={handleSubmit} className="child-password-form">
          <div className="form-group">
            <label htmlFor="password">{t('auth.childPassword.passwordLabel', { defaultValue: 'סיסמה' })}:</label>
            <input
              type="password"
              id="password"
              className="password-input"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError('');
              }}
              placeholder={t('auth.childPassword.passwordPlaceholder', { defaultValue: 'הכנס סיסמה' })}
              required
              autoFocus
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button 
            type="submit" 
            className="child-password-button"
            disabled={isLoading || !password}
          >
            {isLoading 
              ? t('auth.childPassword.verifying', { defaultValue: 'מאמת...' })
              : t('auth.childPassword.login', { defaultValue: 'התחבר' })}
          </button>
        </form>
      </div>
      <footer className="app-footer">
        <span className="version">{t('common.version', { defaultValue: 'גרסה' })} 3.4.51</span>
      </footer>
    </div>
  );
};

export default ChildPasswordLogin;

