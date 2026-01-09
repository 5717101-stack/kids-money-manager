import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { APP_VERSION } from '../constants';

const OTPVerification = ({ phoneNumber, isExistingFamily, onVerified, onBack }) => {
  const { t, i18n } = useTranslation();
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [canResend, setCanResend] = useState(false);
  const [resendTimer, setResendTimer] = useState(60);
  const inputRefs = useRef([]);

  useEffect(() => {
    const timer = setInterval(() => {
      setResendTimer(prev => {
        if (prev <= 1) {
          setCanResend(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);


  const handleOTPChange = (index, value) => {
    if (!/^\d*$/.test(value)) return;
    
    // Handle AutoFill - if value is longer than 1 digit, it's likely AutoFill
    if (value.length > 1) {
      const digits = value.replace(/\D/g, '').slice(0, 6);
      const newOtp = ['', '', '', '', '', ''];
      for (let i = 0; i < digits.length && i < 6; i++) {
        newOtp[i] = digits[i];
      }
      setOtp(newOtp);
      setError('');
      // Focus last filled input
      if (digits.length === 6) {
        inputRefs.current[5]?.focus();
      } else if (digits.length > 0) {
        inputRefs.current[digits.length - 1]?.focus();
      }
      return;
    }
    
    const newOtp = [...otp];
    newOtp[index] = value.slice(-1);
    setOtp(newOtp);
    setError('');

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    const newOtp = [...otp];
    for (let i = 0; i < 6; i++) {
      newOtp[i] = pastedData[i] || '';
    }
    setOtp(newOtp);
    if (pastedData.length === 6) {
      inputRefs.current[5]?.focus();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const otpCode = otp.join('');
    
    if (otpCode.length !== 6) {
      setError(t('auth.otpVerification.enterFullCode', { defaultValue: 'אנא הכנס קוד מלא' }));
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // For iOS, always use Render URL directly
      let apiUrl;
      if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
        // In native app, use Render URL directly
        apiUrl = 'https://kids-money-manager-server.onrender.com/api';
        console.log('[OTP] Using Render API URL for native app:', apiUrl);
      } else {
        // In web, use environment variable or fallback
        apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
        console.log('[OTP] Using API URL:', apiUrl);
      }
      
      const url = `${apiUrl}/auth/verify-otp`;
      
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds timeout
      
      let response;
      try {
        response = await fetch(url, {
          method: 'POST',
          mode: 'cors',
          credentials: 'omit',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify({
            phoneNumber,
            otpCode
          }),
          signal: controller.signal
        });
        clearTimeout(timeoutId);
      } catch (fetchError) {
        clearTimeout(timeoutId);
        console.error('[OTP] Fetch error details:', {
          name: fetchError.name,
          message: fetchError.message,
          stack: fetchError.stack,
          url: url,
          isNative: typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()
        });
        
        // Handle specific iOS/WebView errors
        if (fetchError.name === 'TypeError' && (fetchError.message === 'Load failed' || fetchError.message.includes('Failed to fetch'))) {
          const errorMsg = typeof window !== 'undefined' && window.Capacitor?.isNativePlatform() 
            ? t('auth.otpVerification.networkErrorIOS', { defaultValue: 'שגיאת רשת ב-iOS: לא ניתן להתחבר לשרת. ודא שהשרת רץ ונגיש.' })
            : t('auth.otpVerification.networkError', { defaultValue: 'שגיאת רשת: לא ניתן להתחבר לשרת. בדוק את חיבור האינטרנט או נסה שוב מאוחר יותר.' });
          throw new Error(errorMsg);
        }
        if (fetchError.name === 'AbortError') {
          throw new Error('הבקשה בוטלה: השרת לא הגיב בזמן. נסה שוב.');
        }
        throw fetchError;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || t('auth.otpVerification.invalidCode', { defaultValue: 'קוד אימות שגוי' }));
      }

      onVerified(data.familyId, data.phoneNumber, data.isNewFamily, data.isChild, data.childId, data.isAdditionalParent);
    } catch (error) {
      console.error('Error verifying OTP:', error);
      setError(error.message || t('auth.otpVerification.verifyError', { defaultValue: 'שגיאה באימות קוד' }));
      setOtp(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setCanResend(false);
    setResendTimer(60);
    setError('');
    setOtp(['', '', '', '', '', '']);

    try {
      // For iOS, always use Render URL directly
      let apiUrl;
      if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
        // In native app, use Render URL directly
        apiUrl = 'https://kids-money-manager-server.onrender.com/api';
        console.log('[OTP-RESEND] Using Render API URL for native app:', apiUrl);
      } else {
        // In web, use environment variable or fallback
        apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
        console.log('[OTP-RESEND] Using API URL:', apiUrl);
      }
      
      const url = `${apiUrl}/auth/send-otp`;
      console.log('📤 Resending OTP request to:', url);
      
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds timeout
      
      let response;
      try {
        response = await fetch(url, {
          method: 'POST',
          mode: 'cors',
          credentials: 'omit',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify({
            phoneNumber
          }),
          signal: controller.signal
        });
        clearTimeout(timeoutId);
      } catch (fetchError) {
        clearTimeout(timeoutId);
        console.error('[OTP-RESEND] Fetch error details:', {
          name: fetchError.name,
          message: fetchError.message,
          stack: fetchError.stack,
          url: url
        });
        
        // Handle specific iOS/WebView errors
        if (fetchError.name === 'TypeError' && (fetchError.message === 'Load failed' || fetchError.message.includes('Failed to fetch'))) {
          throw new Error(t('auth.otpVerification.networkError', { defaultValue: 'שגיאת רשת: לא ניתן להתחבר לשרת. בדוק את חיבור האינטרנט או נסה שוב מאוחר יותר.' }));
        }
        if (fetchError.name === 'AbortError') {
          throw new Error('הבקשה בוטלה: השרת לא הגיב בזמן. נסה שוב.');
        }
        throw fetchError;
      }
      
      console.log('📥 Response status:', response.status);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || t('auth.otpVerification.resendError', { defaultValue: 'שגיאה בשליחת קוד מחדש' }));
      }
    } catch (error) {
      setError(error.message || t('auth.otpVerification.resendError', { defaultValue: 'שגיאה בשליחת קוד מחדש' }));
    }
  };

  return (
    <div className="app-layout" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      <div className="app-header">
        <button 
          className="menu-btn"
          onClick={onBack}
          style={{ fontSize: '20px' }}
        >
          ←
        </button>
        <h1 className="header-title">
          {t('auth.otpVerification.title', { defaultValue: 'אימות קוד' })}
        </h1>
        <div style={{ width: '44px' }}></div>
      </div>

      <div className="content-area" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '20px' }}>
        <div className="fintech-card" style={{ maxWidth: '500px', width: '100%', margin: '0 auto' }}>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px', textAlign: 'center' }}>
            {t('auth.otpVerification.sentTo', { defaultValue: 'נשלח ל' })} {phoneNumber}
          </p>

          <form onSubmit={handleSubmit} onPaste={handlePaste} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }} dir="ltr">
              {otp.map((digit, index) => (
                <input
                  key={index}
                  ref={el => inputRefs.current[index] = el}
                  type="text"
                  inputMode="numeric"
                  maxLength={index === 0 ? 6 : 1}
                  value={digit}
                  onChange={(e) => handleOTPChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  autoFocus={index === 0}
                  autoComplete={index === 0 ? "one-time-code" : "off"}
                  autoCapitalize="off"
                  autoCorrect="off"
                  spellCheck="false"
                  style={{
                    width: '50px',
                    height: '60px',
                    borderRadius: '12px',
                    border: '2px solid rgba(0,0,0,0.1)',
                    fontSize: '24px',
                    fontWeight: 700,
                    textAlign: 'center',
                    outline: 'none',
                    transition: '0.2s'
                  }}
                  onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.1)'}
                />
              ))}
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
              disabled={isLoading || otp.join('').length !== 6}
              style={{
                width: '100%',
                height: '50px',
                borderRadius: '12px',
                background: isLoading || otp.join('').length !== 6 ? '#ccc' : 'var(--primary-gradient)',
                color: 'white',
                border: 'none',
                fontSize: '16px',
                fontWeight: 600,
                cursor: isLoading || otp.join('').length !== 6 ? 'not-allowed' : 'pointer',
                transition: '0.2s'
              }}
              onMouseEnter={(e) => {
                if (!isLoading && otp.join('').length === 6) {
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
                ? t('auth.otpVerification.verifying', { defaultValue: 'מאמת...' })
                : t('auth.otpVerification.verify', { defaultValue: 'אימות' })}
            </button>

            <div style={{ textAlign: 'center' }}>
              {canResend ? (
                <button 
                  type="button" 
                  onClick={handleResend}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--primary)',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: '8px 16px'
                  }}
                >
                  {t('auth.otpVerification.resend', { defaultValue: 'שלח קוד מחדש' })}
                </button>
              ) : (
                <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                  {t('auth.otpVerification.resendIn', { 
                    seconds: resendTimer,
                    defaultValue: i18n.language === 'he' 
                      ? 'ניתן לשלוח קוד מחדש בעוד {{seconds}} שניות' 
                      : 'You can resend code in {{seconds}} seconds'
                  })}
                </p>
              )}
            </div>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '12px', color: 'var(--text-muted)' }}>
          {t('common.version', { defaultValue: 'גרסה' })} {APP_VERSION}
        </div>
      </div>
    </div>
  );
};

export default OTPVerification;

