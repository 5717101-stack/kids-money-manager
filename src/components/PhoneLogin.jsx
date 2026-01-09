import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { APP_VERSION } from '../constants';

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

      // SMS is sent automatically, just proceed to OTP verification screen
      console.log('[FRONTEND] SMS sent, proceeding to OTP verification...');
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
      setError(error.message || t('auth.phoneLogin.sendError', { defaultValue: 'שגיאה בשליחת קוד אימות' }));
    } finally {
      console.log('[FRONTEND] Setting loading state to false...');
      setIsLoading(false);
      console.log('[FRONTEND] ========================================\n');
    }
  };

  return (
    <div className="app-layout" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      <div className="app-header">
        <div style={{ width: '44px' }}></div>
        <h1 className="header-title">
          {t('auth.phoneLogin.title', { defaultValue: 'הכנס מספר טלפון' })}
        </h1>
        <div style={{ width: '44px' }}></div>
      </div>

      <div className="content-area" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '20px' }}>
        <div className="fintech-card" style={{ maxWidth: '500px', width: '100%', margin: '0 auto' }}>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px', textAlign: 'center' }}>
            {t('auth.phoneLogin.subtitle', { defaultValue: 'נשלח לך קוד אימות ב-SMS' })}
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', gap: '10px', width: '100%', flexDirection: i18n.language === 'he' ? 'row-reverse' : 'row' }}>
              <div style={{ position: 'relative', flexShrink: 0 }}>
                <button
                  type="button"
                  onClick={() => setShowCountryList(!showCountryList)}
                  style={{
                    height: '50px',
                    width: '50px',
                    padding: '0',
                    borderRadius: '12px',
                    border: '1px solid rgba(0,0,0,0.1)',
                    background: 'white',
                    fontSize: '24px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  {selectedCountry.flag}
                </button>
                {showCountryList && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    [i18n.language === 'he' ? 'right' : 'left']: 0,
                    marginTop: '8px',
                    background: 'white',
                    borderRadius: '12px',
                    border: '1px solid rgba(0,0,0,0.1)',
                    boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                    maxHeight: '300px',
                    overflowY: 'auto',
                    zIndex: 1000,
                    minWidth: '250px',
                    width: 'auto'
                  }}>
                    {COUNTRY_CODES.map((country) => (
                      <button
                        key={country.code}
                        type="button"
                        onClick={() => {
                          setSelectedCountry(country);
                          setShowCountryList(false);
                        }}
                        style={{
                          width: '100%',
                          padding: '12px 16px',
                          border: 'none',
                          background: 'transparent',
                          textAlign: 'start',
                          cursor: 'pointer',
                          fontSize: '14px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#F3F4F6'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <span style={{ fontSize: '20px' }}>{country.flag}</span>
                        <span style={{ fontWeight: 600 }}>{country.code}</span>
                        <span style={{ flex: 1 }}>{country.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => {
                  setPhoneNumber(e.target.value);
                  setError('');
                }}
                placeholder={t('auth.phoneLogin.phonePlaceholder', { defaultValue: 'מספר טלפון' })}
                required
                autoFocus
                inputMode="numeric"
                style={{
                  flex: 1,
                  minWidth: 0,
                  height: '50px',
                  padding: '0 16px',
                  borderRadius: '12px',
                  border: '1px solid rgba(0,0,0,0.1)',
                  fontSize: '16px',
                  outline: 'none',
                  transition: '0.2s',
                  boxSizing: 'border-box'
                }}
                onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.1)'}
              />
            </div>

            {error && (
              <div style={{
                padding: '12px 16px',
                borderRadius: '12px',
                background: '#FEE2E2',
                color: '#DC2626',
                fontSize: '14px',
                textAlign: 'center'
              }}>
                {error}
              </div>
            )}

            <button 
              type="submit" 
              disabled={isLoading || !phoneNumber}
              style={{
                width: '100%',
                height: '50px',
                borderRadius: '12px',
                background: isLoading || !phoneNumber ? '#ccc' : 'var(--primary-gradient)',
                color: 'white',
                border: 'none',
                fontSize: '16px',
                fontWeight: 600,
                cursor: isLoading || !phoneNumber ? 'not-allowed' : 'pointer',
                transition: '0.2s'
              }}
              onMouseEnter={(e) => {
                if (!isLoading && phoneNumber) {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 10px 20px rgba(99, 102, 241, 0.3)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              {isLoading 
                ? t('auth.phoneLogin.sending', { defaultValue: 'שולח...' })
                : t('auth.phoneLogin.sendCode', { defaultValue: 'שלח קוד אימות' })}
            </button>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '12px', color: 'var(--text-muted)' }}>
          {t('common.version', { defaultValue: 'גרסה' })} {APP_VERSION}
        </div>
      </div>
    </div>
  );
};

export default PhoneLogin;
