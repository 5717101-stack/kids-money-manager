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

      // Show success message with OTP in a modal instead of alert
      if (data.otpCode) {
        // Create a modal for OTP display with copy functionality
        const modal = document.createElement('div');
        modal.className = 'otp-modal-overlay';
        modal.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10000;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
          background: white;
          padding: 30px;
          border-radius: 16px;
          max-width: 400px;
          width: 90%;
          text-align: center;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        `;
        
        modalContent.innerHTML = `
          <h2 style="margin: 0 0 20px 0; color: #333; font-size: 24px;">✅ קוד אימות נשלח</h2>
          <p style="margin: 0 0 20px 0; color: #666; font-size: 16px;">קוד האימות נשלח לטלפון ${fullPhoneNumber}</p>
          <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin: 20px 0;">
            <div id="otp-display" style="
              font-size: 32px;
              font-weight: bold;
              letter-spacing: 8px;
              color: #3b82f6;
              padding: 15px 20px;
              background: #f0f9ff;
              border-radius: 8px;
              border: 2px solid #3b82f6;
              font-family: monospace;
            ">${data.otpCode}</div>
            <button id="copy-otp-btn" style="
              padding: 12px 20px;
              background: #3b82f6;
              color: white;
              border: none;
              border-radius: 8px;
              cursor: pointer;
              font-size: 16px;
              font-weight: 600;
            ">📋 העתק</button>
          </div>
          <button id="close-otp-modal" style="
            padding: 12px 30px;
            background: #10b981;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin-top: 10px;
          ">סגור</button>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        const copyBtn = modalContent.querySelector('#copy-otp-btn');
        copyBtn.addEventListener('click', () => {
          navigator.clipboard.writeText(data.otpCode);
          const originalText = copyBtn.textContent;
          copyBtn.textContent = '✅ הועתק!';
          setTimeout(() => {
            copyBtn.textContent = originalText;
          }, 2000);
        });
        
        const closeBtn = modalContent.querySelector('#close-otp-modal');
        closeBtn.addEventListener('click', () => {
          document.body.removeChild(modal);
        });
        
        modal.addEventListener('click', (e) => {
          if (e.target === modal) {
            document.body.removeChild(modal);
          }
        });
      } else {
        // Fallback to alert if no OTP code
        const successMessage = data.message || `✅ קוד אימות נשלח בהצלחה לטלפון ${fullPhoneNumber}`;
        alert(successMessage);
      }

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
        <span className="version">גרסה 3.0.1</span>
      </footer>
    </div>
  );
};

export default PhoneLogin;
