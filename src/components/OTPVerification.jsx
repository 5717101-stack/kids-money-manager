import React, { useState, useRef, useEffect } from 'react';

const OTPVerification = ({ phoneNumber, isExistingFamily, onVerified, onBack }) => {
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
      setError('אנא הכנס קוד מלא');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:3001/api'}/auth/verify-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phoneNumber,
          otpCode
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'קוד אימות שגוי');
      }

      onVerified(data.familyId, data.phoneNumber, data.isNewFamily);
    } catch (error) {
      console.error('Error verifying OTP:', error);
      setError(error.message || 'קוד אימות שגוי');
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
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      const url = `${apiUrl}/auth/send-otp`;
      console.log('📤 Resending OTP request to:', url);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phoneNumber
        })
      });
      
      console.log('📥 Response status:', response.status);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'שגיאה בשליחת קוד');
      }
    } catch (error) {
      setError(error.message || 'שגיאה בשליחת קוד מחדש');
    }
  };

  return (
    <div className="otp-verification">
      <div className="otp-container">
        <div className="otp-header">
          <button className="back-button" onClick={onBack}>
            ← חזור
          </button>
          <h1>🔐 אימות קוד</h1>
          <p className="otp-subtitle">
            נשלח קוד ל-{phoneNumber}
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
                maxLength="1"
                value={digit}
                onChange={(e) => handleOTPChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                className="otp-input"
                autoFocus={index === 0}
              />
            ))}
          </div>

          {error && <div className="error-message">{error}</div>}

          <button 
            type="submit" 
            className="otp-button otp-button-green"
            disabled={isLoading || otp.join('').length !== 6}
          >
            {isLoading ? 'מאמת...' : 'אימות'}
          </button>

          <div className="resend-section">
            {canResend ? (
              <button 
                type="button" 
                className="resend-button"
                onClick={handleResend}
              >
                שלח קוד מחדש
              </button>
            ) : (
              <p className="resend-timer">
                ניתן לשלוח קוד מחדש בעוד {resendTimer} שניות
              </p>
            )}
          </div>
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
        <span className="version">גרסה 3.0.9</span>
      </footer>
    </div>
  );
};

export default OTPVerification;

