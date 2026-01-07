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
      const response = await fetch(`${apiUrl}/auth/verify-child-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          familyId,
          password: password.trim()
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'סיסמה שגויה');
      }

      if (data.child) {
        onChildVerified(data.child, familyId);
      } else {
        throw new Error('ילד לא נמצא');
      }
    } catch (error) {
      console.error('Error verifying child password:', error);
      setError(error.message || 'סיסמה שגויה');
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
              inputMode="numeric"
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
        <span className="version">גרסה 2.9.39</span>
      </footer>
    </div>
  );
};

export default ChildPasswordLogin;

