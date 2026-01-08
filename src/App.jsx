import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import MainLogin from './components/MainLogin';
import WelcomeScreen from './components/WelcomeScreen';
import PhoneLogin from './components/PhoneLogin';
import OTPVerification from './components/OTPVerification';
import ParentDashboard from './components/ParentDashboardNew';
import ChildView from './components/ChildView';
import ChildPasswordLogin from './components/ChildPasswordLogin';
import JoinParentScreen from './components/JoinParentScreen';
import JoinChildScreen from './components/JoinChildScreen';
import LanguageToggle from './components/LanguageToggle';

const App = () => {
  const { i18n } = useTranslation();
  const [screen, setScreen] = useState('main-login'); // 'main-login', 'welcome', 'phone', 'otp', 'child-password', 'parent-invite', 'child-invite', 'dashboard', 'child-view'
  const [familyId, setFamilyId] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [view, setView] = useState('parent'); // 'parent', 'child1', 'child2', etc.
  const [children, setChildren] = useState([]);
  const [currentChild, setCurrentChild] = useState(null); // For child-only view
  const [isChildView, setIsChildView] = useState(false); // Track if we're in child-only mode
  const [isCreatingFamily, setIsCreatingFamily] = useState(false); // Track if user is creating a new family

  // Update document direction based on language
  useEffect(() => {
    const dir = i18n.language === 'he' ? 'rtl' : 'ltr';
    document.documentElement.dir = dir;
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);

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
    } else {
      // If not logged in, show main login screen
      setScreen('main-login');
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
    setIsCreatingFamily(true); // Mark that user wants to create a family
    setScreen('phone');
  };

  const handleWelcomeJoinAsParent = () => {
    setIsCreatingFamily(false); // Not creating, joining as parent
    setScreen('parent-invite');
  };

  const handleWelcomeJoinAsChild = () => {
    setIsCreatingFamily(false); // Not creating, joining as child
    setScreen('child-invite');
  };

  const handleOTPSent = (phoneNum, isExistingFamily) => {
    setPhoneNumber(phoneNum);
    setScreen('otp');
    // If user is creating family but number exists, we'll handle it in OTP verification
  };

  const loadChildData = async (fId, childId) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://kids-money-manager-server.onrender.com/api';
      const response = await fetch(`${apiUrl}/families/${fId}/children/${childId}`);
      const data = await response.json();
      if (data) {
        const childData = { ...data, _id: childId };
        setCurrentChild(childData);
        console.log('[APP] Child data loaded:', childData);
        return childData;
      }
    } catch (error) {
      console.error('Error loading child data:', error);
      return null;
    }
  };

  const handleOTPVerified = (fId, phoneNum, isNewFamily) => {
    setFamilyId(fId);
    setPhoneNumber(phoneNum);
    sessionStorage.setItem('familyId', fId);
    sessionStorage.setItem('phoneNumber', phoneNum);
    
    // Priority order:
    // 1. If user was creating a family (even if number already exists), treat them as parent
    // 2. If coming from main login, always show parent dashboard
    // 3. If it's a new family, show parent dashboard
    // 4. Otherwise (existing family from "Join"), show child password login
    if (isCreatingFamily || screen === 'main-login' || isNewFamily) {
      // User came from "Create Family" OR "Main Login" OR it's a new family - show parent dashboard
      sessionStorage.setItem('parentLoggedIn', 'true');
      sessionStorage.removeItem('isChildView');
      sessionStorage.removeItem('childId');
      setIsChildView(false);
      setScreen('dashboard');
      loadChildren(fId);
    } else {
      // Existing family and user came from "Join" - show child password login
      sessionStorage.removeItem('parentLoggedIn');
      setScreen('child-password');
    }
    
    // Reset the flag
    setIsCreatingFamily(false);
  };

  const handleChildPasswordVerified = (child, fId) => {
    console.log('[APP] handleChildPasswordVerified called:', { child, fId });
    
    // Ensure familyId is set
    if (fId) {
      setFamilyId(fId);
      sessionStorage.setItem('familyId', fId);
    }
    
    // Ensure child has all required properties
    const childData = {
      ...child,
      _id: child._id || child.id,
      name: child.name || 'ילד'
    };
    
    setCurrentChild(childData);
    setIsChildView(true);
    sessionStorage.setItem('childId', childData._id);
    sessionStorage.setItem('isChildView', 'true');
    sessionStorage.removeItem('parentLoggedIn');
    
    console.log('[APP] Setting screen to child-view with:', { 
      familyId: fId || familyId, 
      currentChild: childData 
    });
    
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
    setScreen('main-login');
  };

  return (
    <div className="app">
      <div style={{ position: 'fixed', top: '16px', right: '16px', zIndex: 1000 }}>
        <LanguageToggle />
      </div>
      {screen === 'main-login' && (
        <MainLogin 
          onLoginSuccess={handleOTPVerified}
          onShowWelcome={() => setScreen('welcome')}
        />
      )}
      {screen === 'welcome' && (
        <WelcomeScreen 
          onSelectCreate={handleWelcomeCreate}
          onSelectJoinAsParent={handleWelcomeJoinAsParent}
          onSelectJoinAsChild={handleWelcomeJoinAsChild}
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
          isExistingFamily={!isCreatingFamily}
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

      {screen === 'parent-invite' && (
        <JoinParentScreen
          onVerified={(fId) => {
            setFamilyId(fId);
            setScreen('dashboard');
            loadChildren(fId);
          }}
          onBack={() => setScreen('welcome')}
        />
      )}

      {screen === 'child-invite' && (
        <JoinChildScreen
          onVerified={(fId, childId, child) => {
            setFamilyId(fId);
            setCurrentChild(child);
            setIsChildView(true);
            setScreen('child-view');
          }}
          onBack={() => setScreen('welcome')}
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
            <span className="version">{t('common.version', { defaultValue: 'גרסה' })} 3.2.6</span>
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
            <span className="version">גרסה 3.0.16</span>
          </footer>
        </>
      )}
    </div>
  );
};

export default App;
