import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PhoneLogin from './PhoneLogin';
import OTPVerification from './OTPVerification';
import UsersTable from './UsersTable';

const MainLogin = ({ onLoginSuccess, onShowWelcome }) => {
  const { t } = useTranslation();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showOTP, setShowOTP] = useState(false);
  const [isExistingFamily, setIsExistingFamily] = useState(false);
  const [showUsersTable, setShowUsersTable] = useState(false);

  const handleOTPSent = (phone, existingFamily) => {
    setPhoneNumber(phone);
    setIsExistingFamily(existingFamily);
    setShowOTP(true);
  };

  const handleOTPVerified = (fId, phoneNum, isNewFamily, isChild, childId) => {
    // Pass to parent component with child info if applicable
    onLoginSuccess(fId, phoneNum, isNewFamily, isChild, childId);
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

  if (showUsersTable) {
    return <UsersTable onClose={() => setShowUsersTable(false)} />;
  }

  return (
    <div className="main-login">
      <PhoneLogin onOTPSent={handleOTPSent} />
    </div>
  );
};

export default MainLogin;

