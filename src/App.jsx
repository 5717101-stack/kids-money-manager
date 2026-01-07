import React, { useState, useEffect } from 'react';
import WelcomeScreen from './components/WelcomeScreen';
import PhoneLogin from './components/PhoneLogin';
import OTPVerification from './components/OTPVerification';
import ParentDashboard from './components/ParentDashboard';
import ChildView from './components/ChildView';

const App = () => {
  const [screen, setScreen] = useState('welcome'); // 'welcome', 'phone', 'otp', 'dashboard'
  const [familyId, setFamilyId] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [countryCode, setCountryCode] = useState('+972');
  const [view, setView] = useState('parent'); // 'parent', 'child1', 'child2', etc.
  const [children, setChildren] = useState([]);

  useEffect(() => {
    // Check if already logged in
    const savedFamilyId = sessionStorage.getItem('familyId');
    const savedPhoneNumber = sessionStorage.getItem('phoneNumber');
    const savedCountryCode = sessionStorage.getItem('countryCode');
    
    if (savedFamilyId) {
      setFamilyId(savedFamilyId);
      setPhoneNumber(savedPhoneNumber || '');
      setCountryCode(savedCountryCode || '+972');
      setScreen('dashboard');
      loadChildren(savedFamilyId);
    }
  }, []);

  const loadChildren = async (fId) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:3001/api'}/families/${fId}/children`);
      const data = await response.json();
      if (data.children) {
        const childrenList = Object.values(data.children);
        setChildren(childrenList);
        if (childrenList.length > 0 && !view.startsWith('child')) {
          setView('parent');
        }
      }
    } catch (error) {
      console.error('Error loading children:', error);
    }
  };

  const handleWelcomeCreate = () => {
    setScreen('phone');
  };

  const handleWelcomeJoin = () => {
    setScreen('phone');
  };

  const handleOTPSent = (phone, country, isExistingFamily) => {
    setPhoneNumber(phone);
    setCountryCode(country);
    setScreen('otp');
  };

  const handleOTPVerified = (fId, phone, isNewFamily) => {
    setFamilyId(fId);
    setPhoneNumber(phone);
    sessionStorage.setItem('familyId', fId);
    sessionStorage.setItem('phoneNumber', phone);
    sessionStorage.setItem('countryCode', countryCode);
    sessionStorage.setItem('parentLoggedIn', 'true');
    
    if (isNewFamily) {
      setScreen('dashboard');
      loadChildren(fId);
    } else {
      setScreen('dashboard');
      loadChildren(fId);
    }
  };

  const handleBack = () => {
    setScreen('phone');
  };

  const handleLogout = () => {
    sessionStorage.removeItem('familyId');
    sessionStorage.removeItem('phoneNumber');
    sessionStorage.removeItem('countryCode');
    sessionStorage.removeItem('parentLoggedIn');
    setFamilyId(null);
    setPhoneNumber('');
    setChildren([]);
    setView('parent');
    setScreen('welcome');
  };

  return (
    <div className="app">
      {screen === 'welcome' && (
        <WelcomeScreen 
          onSelectCreate={handleWelcomeCreate}
          onSelectJoin={handleWelcomeJoin}
        />
      )}

      {screen === 'phone' && (
        <PhoneLogin 
          onOTPSent={handleOTPSent}
          countryCode={countryCode}
        />
      )}

      {screen === 'otp' && (
        <OTPVerification 
          phoneNumber={phoneNumber}
          countryCode={countryCode}
          isExistingFamily={false}
          onVerified={handleOTPVerified}
          onBack={handleBack}
        />
      )}

      {screen === 'dashboard' && familyId && (
        <>
          <nav className="main-nav">
            <button
              className={`parent-button ${view === 'parent' ? 'active' : ''}`}
              onClick={() => setView('parent')}
            >
              👨‍👩‍👧‍👦 ממשק הורה
            </button>
            {children.map((child, index) => (
              <button
                key={child._id}
                className={view === child._id ? 'active' : ''}
                onClick={() => setView(child._id)}
              >
                {child.profileImage ? (
                  <img src={child.profileImage} alt={child.name} className="nav-profile-icon" />
                ) : (
                  <span>👦</span>
                )}
                {child.name}
              </button>
            ))}
            <button
              className="logout-button"
              onClick={handleLogout}
              title="התנתק"
            >
              🚪 התנתק
            </button>
          </nav>

          <main className="main-content">
            {view === 'parent' && (
              <ParentDashboard familyId={familyId} onChildrenUpdated={loadChildren} />
            )}
            {children.map(child => (
              view === child._id && (
                <ChildView key={child._id} childId={child._id} familyId={familyId} />
              )
            ))}
          </main>
          
          <footer className="app-footer">
            <button 
              className="test-logs-button"
              onClick={async () => {
                try {
                  const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-production.up.railway.app/api';
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
            <span className="version">גרסה 2.9.17</span>
          </footer>
        </>
      )}
    </div>
  );
};

export default App;
