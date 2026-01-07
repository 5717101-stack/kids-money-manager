import React, { useState } from 'react';

const ChildPasswordLogin = ({ familyId, onChildVerified, onBack }) => {
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!password || password.length < 4) {
      setError('אנא הכנס סיסמה תקינה');
      return;
    }

    if (!familyId) {
      setError('שגיאה: לא נמצא מספר משפחה. אנא נסה להתחבר מחדש.');
      return;
    }

    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      const trimmedPassword = password.trim();
      
      console.log('[CHILD-PASSWORD] Verifying password:', {
        familyId,
        familyIdType: typeof familyId,
        familyIdLength: familyId?.length,
        passwordLength: trimmedPassword.length,
        passwordPreview: trimmedPassword.substring(0, 2) + '***',
        apiUrl
      });
      
      // Ensure familyId is a string
      const familyIdStr = String(familyId).trim();
      
      const requestBody = {
        familyId: familyIdStr,
        password: trimmedPassword
      };
      
      console.log('[CHILD-PASSWORD] Request body:', {
        ...requestBody,
        password: '***'
      });
      
      const response = await fetch(`${apiUrl}/auth/verify-child-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });
      
      console.log('[CHILD-PASSWORD] Response status:', response.status);
      console.log('[CHILD-PASSWORD] Response headers:', Object.fromEntries(response.headers.entries()));

      let data;
      let responseText;
      try {
        responseText = await response.text();
        console.log('[CHILD-PASSWORD] Response text:', responseText);
        data = JSON.parse(responseText);
      } catch (jsonError) {
        // If response is not JSON, use the text as error
        console.error('[CHILD-PASSWORD] Failed to parse JSON:', jsonError);
        console.error('[CHILD-PASSWORD] Response text was:', responseText);
        throw new Error(responseText || 'שגיאה בעת אימות הסיסמה');
      }

      if (!response.ok) {
        // Better error handling for different error types
        const errorMessage = data?.error || data?.message || data?.details || responseText || 'סיסמה שגויה';
        console.error('[CHILD-PASSWORD] Password verification error:', {
          status: response.status,
          statusText: response.statusText,
          error: errorMessage,
          fullData: data,
          responseText: responseText
        });
        throw new Error(errorMessage);
      }

      if (data.child) {
        onChildVerified(data.child, familyId);
      } else {
        throw new Error('ילד לא נמצא');
      }
    } catch (error) {
      console.error('[CHILD-PASSWORD] Error verifying child password:', error);
      console.error('[CHILD-PASSWORD] Error name:', error.name);
      console.error('[CHILD-PASSWORD] Error message:', error.message);
      console.error('[CHILD-PASSWORD] Error stack:', error.stack);
      
      // Translate common error messages to Hebrew
      let errorMessage = error.message || 'סיסמה שגויה';
      
      // Handle network errors
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        errorMessage = 'שגיאת רשת. אנא בדוק את החיבור לאינטרנט ונסה שוב.';
      }
      // Handle pattern validation errors
      else if (errorMessage.includes('pattern') || errorMessage.includes('expected pattern') || errorMessage.includes('validation')) {
        errorMessage = 'סיסמה לא תקינה. אנא בדוק שהסיסמה נכונה והעתקת אותה במלואה (ללא רווחים מיותרים).';
      }
      // Handle not found errors
      else if (errorMessage.includes('not found') || errorMessage.includes('לא נמצא') || errorMessage.includes('NotFound')) {
        errorMessage = 'ילד לא נמצא במשפחה זו.';
      }
      // Handle incorrect password
      else if (errorMessage.includes('incorrect') || errorMessage.includes('שגויה') || errorMessage.includes('Invalid')) {
        errorMessage = 'סיסמה שגויה. אנא נסה שוב.';
      }
      // Handle ObjectId validation errors
      else if (errorMessage.includes('ObjectId') || errorMessage.includes('Cast to ObjectId')) {
        errorMessage = 'שגיאה: מספר משפחה לא תקין. אנא נסה להתחבר מחדש.';
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
            ← חזור
          </button>
          <h1>🔐 הכנס סיסמה</h1>
          <p className="child-password-subtitle">
            הכנס את הסיסמה שלך כדי להתחבר לחשבון
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
            💡 <strong>איפה למצוא את הסיסמה?</strong><br/>
            ההורה שלך יכול לראות את הסיסמה שלך בהגדרות<br/>
            (⚙️ הגדרות → בחר אותך → 🔑 שחזר סיסמה)
          </p>
        </div>

        <form onSubmit={handleSubmit} className="child-password-form">
          <div className="form-group">
            <label htmlFor="password">סיסמה:</label>
            <input
              type="password"
              id="password"
              className="password-input"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError('');
              }}
              placeholder="הכנס סיסמה"
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
            {isLoading ? 'מאמת...' : 'התחבר'}
          </button>
        </form>
      </div>
      <footer className="app-footer">
        <span className="version">גרסה 3.0.2</span>
      </footer>
    </div>
  );
};

export default ChildPasswordLogin;

