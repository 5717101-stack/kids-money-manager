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
    const clickTime = new Date().toISOString();
    
    console.log('========================================');
    console.log('[FRONTEND] 🎯 SEND OTP BUTTON CLICKED 🎯');
    console.log('[FRONTEND] ========================================');
    console.log('[FRONTEND] Timestamp:', clickTime);
    console.log('[FRONTEND] Email entered:', email);
    console.log('[FRONTEND] ========================================\n');
    
    setError('');
    
    if (!email || !validateEmail(email)) {
      console.error('[FRONTEND] ❌ Email validation failed');
      console.error('[FRONTEND] Email:', email);
      console.error('[FRONTEND] Valid format:', validateEmail(email));
      setError('כתובת מייל לא תקינה');
      return;
    }

    console.log('[FRONTEND] ✅ Email validation passed');
    console.log('[FRONTEND] Setting loading state to true...');
    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      const url = `${apiUrl}/auth/send-otp`;
      const normalizedEmail = email.trim().toLowerCase();
      const requestBody = { email: normalizedEmail };
      
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] 📤 Preparing to send OTP request...');
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] API URL:', apiUrl);
      console.log('[FRONTEND] Full URL:', url);
      console.log('[FRONTEND] Method: POST');
      console.log('[FRONTEND] Headers:', { 'Content-Type': 'application/json' });
      console.log('[FRONTEND] Request Body (JSON):', JSON.stringify(requestBody, null, 2));
      console.log('[FRONTEND] Normalized Email:', normalizedEmail);
      console.log('[FRONTEND] ========================================\n');
      
      const requestStartTime = Date.now();
      console.log('[FRONTEND] 🚀 Calling fetch()...');
      console.log('[FRONTEND] Request start time:', new Date().toISOString());
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });
      
      const requestDuration = Date.now() - requestStartTime;
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] 📥 Response received!');
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] Response Time:', requestDuration + 'ms');
      console.log('[FRONTEND] Response Status:', response.status);
      console.log('[FRONTEND] Response Status Text:', response.statusText);
      console.log('[FRONTEND] Response OK:', response.ok);
      console.log('[FRONTEND] Response Headers:', Object.fromEntries(response.headers.entries()));
      console.log('[FRONTEND] ========================================\n');

      console.log('[FRONTEND] 📋 Parsing response JSON...');
      const data = await response.json();
      console.log('[FRONTEND] Response Data (JSON):', JSON.stringify(data, null, 2));

      if (!response.ok) {
        console.error('[FRONTEND] ========================================');
        console.error('[FRONTEND] ❌❌❌ REQUEST FAILED ❌❌❌');
        console.error('[FRONTEND] ========================================');
        console.error('[FRONTEND] Status:', response.status);
        console.error('[FRONTEND] Error:', data.error || 'Unknown error');
        console.error('[FRONTEND] Full Error Data:', JSON.stringify(data, null, 2));
        console.error('[FRONTEND] ========================================\n');
        throw new Error(data.error || 'שגיאה בשליחת קוד');
      }

      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] ✅✅✅ REQUEST SUCCESSFUL ✅✅✅');
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] Success:', data.success);
      console.log('[FRONTEND] Message:', data.message);
      console.log('[FRONTEND] Is Existing Family:', data.isExistingFamily);
      console.log('[FRONTEND] Email Sent:', data.emailSent);
      console.log('[FRONTEND] Email ID:', data.emailId || 'N/A');
      console.log('[FRONTEND] ========================================\n');

      // Show success message from server
      const successMessage = data.message || `✅ קוד אימות נשלח בהצלחה למייל ${normalizedEmail}`;
      alert(successMessage);
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] 📢 SUCCESS MESSAGE SHOWN TO USER');
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] Message:', successMessage);
      console.log('[FRONTEND] ========================================\n');

      console.log('[FRONTEND] Calling onOTPSent callback...');
      onOTPSent(normalizedEmail, data.isExistingFamily);
      console.log('[FRONTEND] ✅ onOTPSent called successfully');
    } catch (error) {
      console.error('[FRONTEND] ========================================');
      console.error('[FRONTEND] ❌❌❌ EXCEPTION CAUGHT ❌❌❌');
      console.error('[FRONTEND] ========================================');
      console.error('[FRONTEND] Error Name:', error.name);
      console.error('[FRONTEND] Error Message:', error.message);
      console.error('[FRONTEND] Error Stack:', error.stack);
      console.error('[FRONTEND] Full Error:', error);
      console.error('[FRONTEND] ========================================\n');
      setError(error.message || 'שגיאה בשליחת קוד אימות');
    } finally {
      console.log('[FRONTEND] Setting loading state to false...');
      setIsLoading(false);
      console.log('[FRONTEND] ========================================\n');
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
              const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
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
        <span className="version">גרסה 2.9.28</span>
      </footer>
    </div>
  );
};

export default PhoneLogin;

