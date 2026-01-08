import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

const PARENT_PASSWORD = '2016';

const ParentLogin = ({ onLogin }) => {
  const { t } = useTranslation();
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
      setError(t('parentLogin.wrongPassword', { defaultValue: 'סיסמה שגויה. אנא נסה שוב.' }));
      setPassword('');
    }
  };

  return (
    <div className="parent-login">
      <div className="login-container">
        <h1>🔒 {t('parentLogin.title', { defaultValue: 'גישה לממשק הורה' })}</h1>
        <p className="login-subtitle">{t('parentLogin.subtitle', { defaultValue: 'אנא הכנס סיסמה כדי לגשת לממשק ההורה' })}</p>
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="password">{t('parentLogin.passwordLabel', { defaultValue: 'סיסמה' })}:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError('');
              }}
              placeholder={t('parentLogin.passwordPlaceholder', { defaultValue: 'הכנס סיסמה' })}
              required
              autoFocus
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="login-button">
            {t('parentLogin.login', { defaultValue: 'התחבר' })}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ParentLogin;

