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

    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      const trimmedPassword = password.trim();
      
      console.log('[CHILD-PASSWORD] Verifying password:', {
        familyId,
        passwordLength: trimmedPassword.length,
        passwordPreview: trimmedPassword.substring(0, 2) + '***',
        apiUrl
      });
      
      const requestBody = {
        familyId,
        password: trimmedPassword
      };
      
      const response = await fetch(`${apiUrl}/auth/verify-child-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });
      
      console.log('[CHILD-PASSWORD] Response status:', response.status);

      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        // If response is not JSON, try to get text
        const text = await response.text();
        throw new Error(text || 'שגיאה בעת אימות הסיסמה');
      }

      if (!response.ok) {
        // Better error handling for different error types
        const errorMessage = data?.error || data?.message || 'סיסמה שגויה';
        console.error('Password verification error:', {
          status: response.status,
          error: errorMessage,
          data: data
        });
        throw new Error(errorMessage);
      }

      if (data.child) {
        onChildVerified(data.child, familyId);
      } else {
        throw new Error('ילד לא נמצא');
      }
    } catch (error) {
      console.error('Error verifying child password:', error);
      // Translate common error messages to Hebrew
      let errorMessage = error.message || 'סיסמה שגויה';
      
      if (errorMessage.includes('pattern') || errorMessage.includes('expected pattern')) {
        errorMessage = 'סיסמה לא תקינה. אנא בדוק שהסיסמה נכונה והעתקת אותה במלואה.';
      } else if (errorMessage.includes('not found') || errorMessage.includes('לא נמצא')) {
        errorMessage = 'ילד לא נמצא במשפחה זו.';
      } else if (errorMessage.includes('incorrect') || errorMessage.includes('שגויה')) {
        errorMessage = 'סיסמה שגויה. אנא נסה שוב.';
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
        <span className="version">גרסה 3.0.0</span>
      </footer>
    </div>
  );
};

export default ChildPasswordLogin;

