import React, { useState, useEffect } from 'react';
import WelcomeScreen from './components/WelcomeScreen';
import PhoneLogin from './components/PhoneLogin';
import OTPVerification from './components/OTPVerification';
import ParentDashboard from './components/ParentDashboard';
import ChildView from './components/ChildView';
import ChildPasswordLogin from './components/ChildPasswordLogin';

const App = () => {
  const [screen, setScreen] = useState('welcome'); // 'welcome', 'phone', 'otp', 'child-password', 'dashboard', 'child-view'
  const [familyId, setFamilyId] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [view, setView] = useState('parent'); // 'parent', 'child1', 'child2', etc.
  const [children, setChildren] = useState([]);
  const [currentChild, setCurrentChild] = useState(null); // For child-only view
  const [isChildView, setIsChildView] = useState(false); // Track if we're in child-only mode

  useEffect(() => {
    // Check if already logged in
    const savedFamilyId = sessionStorage.getItem('familyId');
    const savedPhoneNumber = sessionStorage.getItem('phoneNumber');
    const savedChildId = sessionStorage.getItem('childId');
    const savedIsChildView = sessionStorage.getItem('isChildView') === 'true';
    
    if (savedFamilyId) {
      setFamilyId(savedFamilyId);
      setPhoneNumber(savedPhoneNumber || '');
      
      if (savedIsChildView && savedChildId) {
        // Load child data and show child view
        setIsChildView(true);
        setCurrentChild({ _id: savedChildId });
        setScreen('child-view');
        loadChildData(savedFamilyId, savedChildId);
      } else {
        setScreen('dashboard');
        loadChildren(savedFamilyId);
      }
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

  const handleOTPSent = (phoneNum, isExistingFamily) => {
    setPhoneNumber(phoneNum);
    setScreen('otp');
  };

  const loadChildData = async (fId, childId) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      const response = await fetch(`${apiUrl}/families/${fId}/children/${childId}`);
      const data = await response.json();
      if (data) {
        setCurrentChild({ ...data, _id: childId });
      }
    } catch (error) {
      console.error('Error loading child data:', error);
    }
  };

  const handleOTPVerified = (fId, phoneNum, isNewFamily) => {
    setFamilyId(fId);
    setPhoneNumber(phoneNum);
    sessionStorage.setItem('familyId', fId);
    sessionStorage.setItem('phoneNumber', phoneNum);
    
    if (isNewFamily) {
      // New family - show parent dashboard
      sessionStorage.setItem('parentLoggedIn', 'true');
      sessionStorage.removeItem('isChildView');
      sessionStorage.removeItem('childId');
      setIsChildView(false);
      setScreen('dashboard');
      loadChildren(fId);
    } else {
      // Existing family - show child password login
      sessionStorage.removeItem('parentLoggedIn');
      setScreen('child-password');
    }
  };

  const handleChildPasswordVerified = (child, fId) => {
    setCurrentChild(child);
    setIsChildView(true);
    sessionStorage.setItem('childId', child._id);
    sessionStorage.setItem('isChildView', 'true');
    sessionStorage.removeItem('parentLoggedIn');
    setScreen('child-view');
  };

  const handleBack = () => {
    setScreen('phone');
  };

  const handleLogout = () => {
    sessionStorage.removeItem('familyId');
    sessionStorage.removeItem('phoneNumber');
    sessionStorage.removeItem('parentLoggedIn');
    sessionStorage.removeItem('childId');
    sessionStorage.removeItem('isChildView');
    setFamilyId(null);
    setPhoneNumber('');
    setChildren([]);
    setCurrentChild(null);
    setIsChildView(false);
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
        />
      )}

      {screen === 'otp' && (
        <OTPVerification 
          phoneNumber={phoneNumber}
          isExistingFamily={false}
          onVerified={handleOTPVerified}
          onBack={handleBack}
        />
      )}

      {screen === 'child-password' && familyId && (
        <ChildPasswordLogin
          familyId={familyId}
          onChildVerified={handleChildPasswordVerified}
          onBack={handleBack}
        />
      )}

      {screen === 'child-view' && familyId && currentChild && (
        <>
          <nav className="main-nav child-only-nav">
            <div className="child-nav-info">
              {currentChild.profileImage ? (
                <img src={currentChild.profileImage} alt={currentChild.name} className="nav-profile-icon" />
              ) : (
                <span>👦</span>
              )}
              <span className="child-name">{currentChild.name}</span>
            </div>
            <button
              className="logout-button"
              onClick={handleLogout}
              title="התנתק"
            >
              🚪 התנתק
            </button>
          </nav>

          <main className="main-content">
            <ChildView childId={currentChild._id} familyId={familyId} />
          </main>
          
          <footer className="app-footer">
            <span className="version">גרסה 2.9.37</span>
          </footer>
        </>
      )}

      {screen === 'dashboard' && familyId && !isChildView && (
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
            <span className="version">גרסה 2.9.36</span>
          </footer>
        </>
      )}
    </div>
  );
};

export default App;
