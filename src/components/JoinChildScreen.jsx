import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PhoneLogin from './PhoneLogin';
import OTPVerification from './OTPVerification';
import ChildPasswordLogin from './ChildPasswordLogin';

const JoinChildScreen = ({ onVerified, onBack }) => {
  const { t } = useTranslation();
  const [step, setStep] = useState('phone'); // 'phone', 'otp', 'password'
  const [phoneNumber, setPhoneNumber] = useState('');
  const [familyId, setFamilyId] = useState(null);

  // Use the existing flow: Phone -> OTP -> Child Password
  // This works with the existing backend
  if (step === 'phone') {
    return (
      <div>
        <div style={{ padding: '20px', textAlign: 'center', maxWidth: '500px', margin: '0 auto' }}>
          <h1>{t('welcome.joinAsChild')}</h1>
          <p style={{ marginBottom: '10px', color: '#64748b' }}>
            {t('welcome.joinAsChildDesc')}
          </p>
          <p style={{ fontSize: '14px', color: '#64748b', marginBottom: '20px', padding: '12px', backgroundColor: '#f1f5f9', borderRadius: '8px' }}>
            💡 הכנס את מספר הטלפון של המשפחה, ולאחר מכן את סיסמת הילד
          </p>
        </div>
        <PhoneLogin 
          onOTPSent={(phoneNum, isExistingFamily) => {
            setPhoneNumber(phoneNum);
            setStep('otp');
          }}
        />
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <button
            onClick={onBack}
            style={{
              padding: '12px 24px',
              backgroundColor: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              cursor: 'pointer',
              color: 'var(--text-primary)'
            }}
          >
            {t('common.back')}
          </button>
        </div>
      </div>
    );
  }

  if (step === 'otp') {
    return (
      <OTPVerification
        phoneNumber={phoneNumber}
        isExistingFamily={true}
        onVerified={(fId, phoneNum, isNewFamily) => {
          setFamilyId(fId);
          setStep('password');
        }}
        onBack={() => setStep('phone')}
      />
    );
  }

  // After OTP verification, show child password login
  if (step === 'password' && familyId) {
    return (
      <ChildPasswordLogin
        familyId={familyId}
        onChildVerified={(child, fId) => {
          localStorage.setItem('familyId', fId);
          localStorage.setItem('childId', child._id);
          localStorage.setItem('isChildView', 'true');
          onVerified(fId, child._id, child);
        }}
        onBack={() => setStep('otp')}
      />
    );
  }

  return null;
};

export default JoinChildScreen;
