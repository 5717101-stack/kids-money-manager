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

const PhoneLogin = ({ onOTPSent, countryCode: initialCountryCode }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [countryCode, setCountryCode] = useState(initialCountryCode || '+972');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Detect country code from device
  useEffect(() => {
    if (!initialCountryCode) {
      try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (timezone.includes('Asia/Jerusalem') || timezone.includes('Israel')) {
          setCountryCode('+972');
        }
      } catch (e) {
        // Fallback to default
      }
    }
  }, [initialCountryCode]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!phoneNumber || !phoneNumber.match(/^\d+$/)) {
      setError('מספר טלפון לא תקין');
      return;
    }

    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-production.up.railway.app/api';
      const url = `${apiUrl}/auth/send-otp`;
      console.log('📤 Sending OTP request to:', url);
      console.log('📤 Request body:', { phoneNumber: phoneNumber.replace(/\D/g, ''), countryCode });
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phoneNumber: phoneNumber.replace(/\D/g, ''),
          countryCode
        })
      });
      
      console.log('📥 Response status:', response.status);
      console.log('📥 Response ok:', response.ok);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'שגיאה בשליחת קוד');
      }

      onOTPSent(phoneNumber.replace(/\D/g, ''), countryCode, data.isExistingFamily);
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
          <h1>📱 הכנס מספר טלפון</h1>
          <p className="phone-login-subtitle">נשלח לך קוד אימות ב-SMS</p>
        </div>

        <form onSubmit={handleSubmit} className="phone-login-form">
          <div className="phone-input-group">
            <select
              className="country-code-select"
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
            >
              {COUNTRY_CODES.map(country => (
                <option key={country.code} value={country.code}>
                  {country.flag} {country.code}
                </option>
              ))}
            </select>
            
            <input
              type="tel"
              className="phone-input"
              value={phoneNumber}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '');
                setPhoneNumber(value);
                setError('');
              }}
              placeholder="מספר טלפון"
              required
              autoFocus
              maxLength="15"
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button 
            type="submit" 
            className="phone-login-button"
            disabled={isLoading || !phoneNumber}
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
              const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-production.up.railway.app/api';
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
        <span className="version">גרסה 2.9.19</span>
      </footer>
    </div>
  );
};

export default PhoneLogin;

