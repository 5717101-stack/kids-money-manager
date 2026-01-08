import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

const COUNTRY_CODES_HE = [
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

const COUNTRY_CODES_EN = [
  { code: '+972', name: 'Israel', flag: '🇮🇱' },
  { code: '+1', name: 'USA/Canada', flag: '🇺🇸' },
  { code: '+44', name: 'United Kingdom', flag: '🇬🇧' },
  { code: '+33', name: 'France', flag: '🇫🇷' },
  { code: '+49', name: 'Germany', flag: '🇩🇪' },
  { code: '+39', name: 'Italy', flag: '🇮🇹' },
  { code: '+34', name: 'Spain', flag: '🇪🇸' },
  { code: '+7', name: 'Russia', flag: '🇷🇺' },
  { code: '+86', name: 'China', flag: '🇨🇳' },
  { code: '+81', name: 'Japan', flag: '🇯🇵' },
  { code: '+91', name: 'India', flag: '🇮🇳' },
  { code: '+61', name: 'Australia', flag: '🇦🇺' },
  { code: '+27', name: 'South Africa', flag: '🇿🇦' },
  { code: '+971', name: 'UAE', flag: '🇦🇪' },
  { code: '+966', name: 'Saudi Arabia', flag: '🇸🇦' }
];

const PhoneLogin = ({ onOTPSent }) => {
  const { t, i18n } = useTranslation();
  const COUNTRY_CODES = i18n.language === 'he' ? COUNTRY_CODES_HE : COUNTRY_CODES_EN;
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
      setError(t('auth.phoneLogin.invalidPhone', { defaultValue: 'מספר טלפון לא תקין' }));
      return;
    }

    const fullPhoneNumber = `${selectedCountry.code}${phoneNumber.replace(/\D/g, '')}`;
    console.log('[FRONTEND] ✅ Phone validation passed');
    console.log('[FRONTEND] Full Phone Number:', fullPhoneNumber);
    console.log('[FRONTEND] Setting loading state to true...');
    setIsLoading(true);

    try {
      // For iOS, always use Render URL directly
      let apiUrl;
      if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
        // In native app, use Render URL directly
        apiUrl = 'https://kids-money-manager-server.onrender.com/api';
        console.log('[FRONTEND] Using Render API URL for native app:', apiUrl);
      } else {
        // In web, use environment variable or fallback
        apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
        console.log('[FRONTEND] Using API URL:', apiUrl);
      }
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
      
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds timeout
      
      let response;
      try {
        // Add mode: 'cors' and credentials for iOS
        response = await fetch(url, {
          method: 'POST',
          mode: 'cors',
          credentials: 'omit',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify(requestBody),
          signal: controller.signal
        });
        clearTimeout(timeoutId);
      } catch (fetchError) {
        clearTimeout(timeoutId);
        console.error('[FRONTEND] Fetch error details:', {
          name: fetchError.name,
          message: fetchError.message,
          stack: fetchError.stack,
          url: url,
          isNative: typeof window !== 'undefined' && window.Capacitor?.isNativePlatform(),
          userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'N/A',
          platform: typeof window !== 'undefined' && window.Capacitor?.getPlatform ? window.Capacitor.getPlatform() : 'N/A'
        });
        
        // Log the actual URL being used
        console.error('[FRONTEND] API URL being used:', apiUrl);
        console.error('[FRONTEND] Full URL:', url);
        console.error('[FRONTEND] Is Native Platform:', typeof window !== 'undefined' && window.Capacitor?.isNativePlatform());
        
        // Handle specific iOS/WebView errors
        if (fetchError.name === 'TypeError' && (fetchError.message === 'Load failed' || fetchError.message.includes('Failed to fetch'))) {
          const errorMsg = typeof window !== 'undefined' && window.Capacitor?.isNativePlatform() 
            ? t('auth.phoneLogin.networkErrorIOS', { defaultValue: 'שגיאת רשת ב-iOS: לא ניתן להתחבר לשרת. ודא שהשרת רץ ונגיש.' })
            : t('auth.phoneLogin.networkError', { defaultValue: 'שגיאת רשת: לא ניתן להתחבר לשרת. בדוק את חיבור האינטרנט או נסה שוב מאוחר יותר.' });
          throw new Error(errorMsg);
        }
        if (fetchError.name === 'AbortError') {
          throw new Error(t('auth.phoneLogin.timeoutError', { defaultValue: 'הבקשה בוטלה: השרת לא הגיב בזמן. נסה שוב.' }));
        }
        throw fetchError;
      }
      
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
        throw new Error(data.error || t('auth.phoneLogin.sendError', { defaultValue: 'שגיאה בשליחת קוד אימות' }));
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
        
        const otpSentTitle = t('auth.phoneLogin.otpSent', { defaultValue: 'קוד אימות נשלח' });
        const otpSentTo = t('auth.phoneLogin.otpSentTo', { phone: fullPhoneNumber, defaultValue: `קוד האימות נשלח לטלפון ${fullPhoneNumber}` });
        const copyText = t('auth.phoneLogin.copy', { defaultValue: 'העתק' });
        const closeText = t('auth.phoneLogin.close', { defaultValue: 'סגור' });
        
        modalContent.innerHTML = `
          <h2 style="margin: 0 0 20px 0; color: #333; font-size: 24px;">✅ ${otpSentTitle}</h2>
          <p style="margin: 0 0 20px 0; color: #666; font-size: 16px;">${otpSentTo}</p>
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
            ">📋 ${copyText}</button>
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
          ">${closeText}</button>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        const copyBtn = modalContent.querySelector('#copy-otp-btn');
        const copiedText = t('auth.phoneLogin.copied', { defaultValue: 'הועתק!' });
        copyBtn.addEventListener('click', () => {
          navigator.clipboard.writeText(data.otpCode);
          const originalText = copyBtn.textContent;
          copyBtn.textContent = '✅ ' + copiedText;
          setTimeout(() => {
            copyBtn.textContent = originalText;
          }, 2000);
        });
        
        const closeModal = () => {
          if (modal.parentNode) {
            document.body.removeChild(modal);
          }
          // Call onOTPSent after modal is closed
          console.log('[FRONTEND] Modal closed, calling onOTPSent callback...');
          onOTPSent(fullPhoneNumber, data.isExistingFamily);
          console.log('[FRONTEND] ✅ onOTPSent called successfully');
        };
        
        const closeBtn = modalContent.querySelector('#close-otp-modal');
        closeBtn.addEventListener('click', closeModal);
        
        modal.addEventListener('click', (e) => {
          if (e.target === modal) {
            closeModal();
          }
        });
      } else {
        // Fallback to alert if no OTP code
        const successMessage = data.message || t('auth.phoneLogin.otpSentSuccess', { phone: fullPhoneNumber, defaultValue: `✅ קוד אימות נשלח בהצלחה לטלפון ${fullPhoneNumber}` });
        alert(successMessage);
        // Call onOTPSent after alert is closed
        console.log('[FRONTEND] Alert closed, calling onOTPSent callback...');
        onOTPSent(fullPhoneNumber, data.isExistingFamily);
        console.log('[FRONTEND] ✅ onOTPSent called successfully');
      }
    } catch (error) {
      console.error('[FRONTEND] ========================================');
      console.error('[FRONTEND] ❌❌❌ EXCEPTION CAUGHT ❌❌❌');
      console.error('[FRONTEND] ========================================');
      console.error('[FRONTEND] Error Name:', error.name);
      console.error('[FRONTEND] Error Message:', error.message);
      console.error('[FRONTEND] Error Stack:', error.stack);
      console.error('[FRONTEND] ========================================\n');
      setError(error.message || t('auth.phoneLogin.sendError', { defaultValue: 'שגיאה בשליחת קוד אימות' }));
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
          <h1>📱 {t('auth.phoneLogin.title', { defaultValue: 'הכנס מספר טלפון' })}</h1>
          <p className="phone-login-subtitle">{t('auth.phoneLogin.subtitle', { defaultValue: 'נשלח לך קוד אימות ב-SMS' })}</p>
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
              placeholder={t('auth.phoneLogin.phonePlaceholder', { defaultValue: 'מספר טלפון' })}
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
            {isLoading 
              ? t('auth.phoneLogin.sending', { defaultValue: 'שולח...' })
              : t('auth.phoneLogin.sendCode', { defaultValue: 'שלח קוד אימות' })}
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
        <span className="version">{t('common.version', { defaultValue: 'גרסה' })} 3.2.4</span>
      </footer>
    </div>
  );
};

export default PhoneLogin;
