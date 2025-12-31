import React, { useState } from 'react';

const PARENT_PASSWORD = '2016';

const ParentLogin = ({ onLogin }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (password === PARENT_PASSWORD) {
      // Save login state in sessionStorage
      sessionStorage.setItem('parentLoggedIn', 'true');
      onLogin();
    } else {
      setError('סיסמה שגויה. אנא נסה שוב.');
      setPassword('');
    }
  };

  return (
    <div className="parent-login">
      <div className="login-container">
        <h1>🔒 גישה לממשק הורה</h1>
        <p className="login-subtitle">אנא הכנס סיסמה כדי לגשת לממשק ההורה</p>
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="password">סיסמה:</label>
            <input
              type="password"
              id="password"
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

          <button type="submit" className="login-button">
            התחבר
          </button>
        </form>
      </div>
    </div>
  );
};

export default ParentLogin;

