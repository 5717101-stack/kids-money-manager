import React, { useState } from 'react';

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
  const [selectedCountry, setSelectedCountry] = useState(COUNTRY_CODES[0]);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCountryList, setShowCountryList] = useState(false);

  const validatePhoneNumber = (phone) => {
    // Remove all non-digits
    const digitsOnly = phone.replace(/\D/g, '');
    // Check if it's a valid phone number (at least 7 digits, max 15)
    return digitsOnly.length >= 7 && digitsOnly.length <= 15;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const clickTime = new Date().toISOString();
    
    console.log('========================================');
    console.log('[FRONTEND] 🎯 SEND OTP BUTTON CLICKED 🎯');
    console.log('[FRONTEND] ========================================');
    console.log('[FRONTEND] Timestamp:', clickTime);
    console.log('[FRONTEND] Country Code:', selectedCountry.code);
    console.log('[FRONTEND] Phone Number:', phoneNumber);
    console.log('[FRONTEND] ========================================\n');
    
    setError('');
    
    if (!phoneNumber || !validatePhoneNumber(phoneNumber)) {
      console.error('[FRONTEND] ❌ Phone validation failed');
      console.error('[FRONTEND] Phone:', phoneNumber);
      setError('מספר טלפון לא תקין');
      return;
    }

    const fullPhoneNumber = `${selectedCountry.code}${phoneNumber.replace(/\D/g, '')}`;
    console.log('[FRONTEND] ✅ Phone validation passed');
    console.log('[FRONTEND] Full Phone Number:', fullPhoneNumber);
    console.log('[FRONTEND] Setting loading state to true...');
    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      const url = `${apiUrl}/auth/send-otp`;
      const requestBody = { phoneNumber: fullPhoneNumber };
      
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] 📤 Preparing to send OTP request...');
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] API URL:', apiUrl);
      console.log('[FRONTEND] Full URL:', url);
      console.log('[FRONTEND] Method: POST');
      console.log('[FRONTEND] Headers:', { 'Content-Type': 'application/json' });
      console.log('[FRONTEND] Request Body (JSON):', JSON.stringify(requestBody, null, 2));
      console.log('[FRONTEND] Full Phone Number:', fullPhoneNumber);
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
        console.error('[FRONTEND] ========================================\n');
        throw new Error(data.error || 'שגיאה בשליחת קוד');
      }

      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] ✅✅✅ REQUEST SUCCESSFUL ✅✅✅');
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] Success:', data.success);
      console.log('[FRONTEND] Message:', data.message);
      console.log('[FRONTEND] Is Existing Family:', data.isExistingFamily);
      console.log('[FRONTEND] SMS Sent:', data.smsSent);
      console.log('[FRONTEND] OTP Code:', data.otpCode || 'NOT PROVIDED');
      console.log('[FRONTEND] ========================================\n');

      // Show success message with OTP
      let successMessage;
      if (data.otpCode) {
        successMessage = `✅ קוד אימות נשלח בהצלחה לטלפון ${fullPhoneNumber}\n\nקוד האימות: ${data.otpCode}`;
      } else if (data.message) {
        successMessage = data.message;
      } else {
        successMessage = `✅ קוד אימות נשלח בהצלחה לטלפון ${fullPhoneNumber}`;
      }
      
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] 📢 SUCCESS MESSAGE DATA');
      console.log('[FRONTEND] ========================================');
      console.log('[FRONTEND] data.message:', data.message);
      console.log('[FRONTEND] data.otpCode:', data.otpCode);
      console.log('[FRONTEND] Final message:', successMessage);
      console.log('[FRONTEND] ========================================\n');
      
      alert(successMessage);

      console.log('[FRONTEND] Calling onOTPSent callback...');
      onOTPSent(fullPhoneNumber, data.isExistingFamily);
      console.log('[FRONTEND] ✅ onOTPSent called successfully');
    } catch (error) {
      console.error('[FRONTEND] ========================================');
      console.error('[FRONTEND] ❌❌❌ EXCEPTION CAUGHT ❌❌❌');
      console.error('[FRONTEND] ========================================');
      console.error('[FRONTEND] Error Name:', error.name);
      console.error('[FRONTEND] Error Message:', error.message);
      console.error('[FRONTEND] Error Stack:', error.stack);
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
          <h1>📱 הכנס מספר טלפון</h1>
          <p className="phone-login-subtitle">נשלח לך קוד אימות ב-SMS</p>
        </div>

        <form onSubmit={handleSubmit} className="phone-login-form">
          <div className="phone-input-group">
            <div className="country-code-selector">
              <button
                type="button"
                className="country-code-button"
                onClick={() => setShowCountryList(!showCountryList)}
              >
                {selectedCountry.flag} {selectedCountry.code}
              </button>
              {showCountryList && (
                <div className="country-list">
                  {COUNTRY_CODES.map((country) => (
                    <button
                      key={country.code}
                      type="button"
                      className="country-item"
                      onClick={() => {
                        setSelectedCountry(country);
                        setShowCountryList(false);
                      }}
                    >
                      {country.flag} {country.code} {country.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <input
              type="tel"
              className="phone-input"
              value={phoneNumber}
              onChange={(e) => {
                setPhoneNumber(e.target.value);
                setError('');
              }}
              placeholder="מספר טלפון"
              required
              autoFocus
              inputMode="numeric"
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
        <span className="version">גרסה 2.9.32</span>
      </footer>
    </div>
  );
};

export default PhoneLogin;
