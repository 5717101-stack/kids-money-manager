import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

const OTPVerification = ({ phoneNumber, isExistingFamily, onVerified, onBack }) => {
  const { t } = useTranslation();
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
    <div className="otp-verification">
      <div className="otp-container">
        <div className="otp-header">
          <button className="back-button" onClick={onBack}>
            {t('auth.otpVerification.back', { defaultValue: '← חזור' })}
          </button>
          <h1>🔐 {t('auth.otpVerification.title', { defaultValue: 'אימות קוד' })}</h1>
          <p className="otp-subtitle">
            {t('auth.otpVerification.subtitle', { phone: phoneNumber, defaultValue: 'נשלח קוד ל-{phone}' })}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="otp-form" onPaste={handlePaste}>
          <div className="otp-inputs" dir="ltr">
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
                className="otp-input"
                autoFocus={index === 0}
                autoComplete={index === 0 ? "one-time-code" : "off"}
                autoCapitalize="off"
                autoCorrect="off"
                spellCheck="false"
              />
            ))}
          </div>

          {error && <div className="error-message">{error}</div>}

          <button 
            type="submit" 
            className="otp-button otp-button-green"
            disabled={isLoading || otp.join('').length !== 6}
          >
            {isLoading 
              ? t('auth.otpVerification.verifying', { defaultValue: 'מאמת...' })
              : t('auth.otpVerification.verify', { defaultValue: 'אימות' })}
          </button>

          <div className="resend-section">
            {canResend ? (
              <button 
                type="button" 
                className="resend-button"
                onClick={handleResend}
              >
                {t('auth.otpVerification.resend', { defaultValue: 'שלח קוד מחדש' })}
              </button>
            ) : (
              <p className="resend-timer">
                {t('auth.otpVerification.resendIn', { seconds: resendTimer, defaultValue: 'ניתן לשלוח קוד מחדש בעוד {seconds} שניות' })}
              </p>
            )}
          </div>
        </form>
      </div>
      <footer className="app-footer">
        <span className="version">{t('common.version', { defaultValue: 'גרסה' })} 3.4.31</span>
      </footer>
    </div>
  );
};

export default OTPVerification;

