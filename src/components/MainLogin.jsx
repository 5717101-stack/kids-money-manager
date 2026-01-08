import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PhoneLogin from './PhoneLogin';
import OTPVerification from './OTPVerification';

const MainLogin = ({ onLoginSuccess, onShowWelcome }) => {
  const { t } = useTranslation();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showOTP, setShowOTP] = useState(false);
  const [isExistingFamily, setIsExistingFamily] = useState(false);

  const handleOTPSent = (phone, existingFamily) => {
    setPhoneNumber(phone);
    setIsExistingFamily(existingFamily);
    setShowOTP(true);
  };

  const handleOTPVerified = (fId, phoneNum, isNewFamily) => {
    // Pass to parent component - always treat as parent login
    onLoginSuccess(fId, phoneNum, true); // true = isNewFamily, always show parent dashboard
  };

  const handleBackFromOTP = () => {
    setShowOTP(false);
    setPhoneNumber('');
  };

  if (showOTP) {
    return (
      <OTPVerification
        phoneNumber={phoneNumber}
        isExistingFamily={isExistingFamily}
        onVerified={handleOTPVerified}
        onBack={handleBackFromOTP}
      />
    );
  }

  return (
    <div className="main-login">
      <PhoneLogin onOTPSent={handleOTPSent} />
      <div style={{ 
        textAlign: 'center', 
        marginTop: '20px',
        padding: '20px'
      }}>
        <button
          onClick={onShowWelcome}
          style={{
            background: 'transparent',
            border: '1px solid #3b82f6',
            color: '#3b82f6',
            padding: '12px 24px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: '500',
            transition: 'all 0.2s ease'
          }}
          onMouseOver={(e) => {
            e.target.style.background = '#3b82f6';
            e.target.style.color = 'white';
          }}
          onMouseOut={(e) => {
            e.target.style.background = 'transparent';
            e.target.style.color = '#3b82f6';
          }}
        >
          {t('login.newUser', { defaultValue: 'משתמש חדש' })}
        </button>
      </div>
    </div>
  );
};

export default MainLogin;

