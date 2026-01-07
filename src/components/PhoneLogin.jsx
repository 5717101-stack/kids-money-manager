import React, { useState, useEffect } from 'react';

const COUNTRY_CODES = [
  { code: '+972', name: 'ישראל', flag: '🇮🇱' },
  { code: '+1', name: 'ארה"ב/קנדה', flag: '🇺🇸' },
  { code: '+44', name: 'בריטניה', flag: '🇬🇧' },
  { code: '+33', name: 'צרפת', flag: '🇫🇷' },
  { code: '+49', name: 'גרמניה', flag: '🇩🇪' },
  { code: '+39', name: 'איטליה', flag: '🇮🇹' },
  { code: '+34', name: 'ספרד', flag: '🇪🇸' },
  { code: '+7', name: 'רוסיה', flag: '🇷🇺' },
  { code: '+86', name: 'סין', flag: '🇨🇳' },
  { code: '+81', name: 'יפן', flag: '🇯🇵' },
  { code: '+91', name: 'הודו', flag: '🇮🇳' },
  { code: '+61', name: 'אוסטרליה', flag: '🇦🇺' },
  { code: '+27', name: 'דרום אפריקה', flag: '🇿🇦' },
  { code: '+971', name: 'איחוד האמירויות', flag: '🇦🇪' },
  { code: '+966', name: 'ערב הסעודית', flag: '🇸🇦' }
];

const PhoneLogin = ({ onOTPSent }) => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!email || !validateEmail(email)) {
      setError('כתובת מייל לא תקינה');
      return;
    }

    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://web-production-4e378.up.railway.app/api';
      const url = `${apiUrl}/auth/send-otp`;
      console.log('📤 Sending OTP request to:', url);
      console.log('📤 Request body:', { email });
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim().toLowerCase()
        })
      });
      
      console.log('📥 Response status:', response.status);
      console.log('📥 Response ok:', response.ok);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'שגיאה בשליחת קוד');
      }

      onOTPSent(email.trim().toLowerCase(), data.isExistingFamily);
    } catch (error) {
      console.error('Error sending OTP:', error);
      setError(error.message || 'שגיאה בשליחת קוד אימות');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="phone-login">
      <div className="phone-login-container">
        <div className="phone-login-header">
          <h1>📧 הכנס כתובת מייל</h1>
          <p className="phone-login-subtitle">נשלח לך קוד אימות במייל</p>
        </div>

        <form onSubmit={handleSubmit} className="phone-login-form">
          <div className="phone-input-group">
            <input
              type="email"
              className="phone-input"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setError('');
              }}
              placeholder="כתובת מייל"
              required
              autoFocus
              inputMode="email"
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button 
            type="submit" 
            className="phone-login-button"
            disabled={isLoading || !email}
          >
            {isLoading ? 'שולח...' : 'שלח קוד אימות'}
          </button>
        </form>
      </div>
      <footer className="app-footer">
        <button 
          className="test-logs-button"
          onClick={async () => {
            try {
              const apiUrl = import.meta.env.VITE_API_URL || 'https://web-production-4e378.up.railway.app/api';
              await fetch(`${apiUrl}/test-logs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
              });
            } catch (error) {
              console.error('Error sending test log:', error);
            }
          }}
          title="בדיקת לוגים"
        >
          🔍 בדיקת לוגים
        </button>
        <span className="version">גרסה 2.9.21</span>
      </footer>
    </div>
  );
};

export default PhoneLogin;

