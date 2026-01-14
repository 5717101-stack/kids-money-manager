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
import { getData, getChild } from './utils/api';

const App = () => {
  const { t, i18n } = useTranslation();
  const [screen, setScreen] = useState('main-login'); // 'main-login', 'welcome', 'phone', 'otp', 'child-password', 'parent-invite', 'child-invite', 'dashboard', 'child-view'
  const [familyId, setFamilyId] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [view, setView] = useState('parent'); // 'parent', 'child1', 'child2', etc.
  const [children, setChildren] = useState([]);
  const [currentChild, setCurrentChild] = useState(null); // For child-only view
  const [isChildView, setIsChildView] = useState(false); // Track if we're in child-only mode
  const [isCreatingFamily, setIsCreatingFamily] = useState(false); // Track if user is creating a new family
  const [isNewFamily, setIsNewFamily] = useState(false); // Track if this is a new family (for onboarding)

  // Update document direction based on language
  useEffect(() => {
    const dir = i18n.language === 'he' ? 'rtl' : 'ltr';
    document.documentElement.dir = dir;
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);

  useEffect(() => {
    // Check if already logged in
    // Use localStorage instead of sessionStorage to persist login across app restarts
    const savedFamilyId = localStorage.getItem('familyId');
    const savedPhoneNumber = localStorage.getItem('phoneNumber');
    const savedChildId = localStorage.getItem('childId');
    const savedIsChildView = localStorage.getItem('isChildView') === 'true';
    
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
      const data = await getData(fId);
      if (data && data.children) {
        const childrenList = Object.values(data.children);
        setChildren(childrenList);
        if (childrenList.length > 0 && !view.startsWith('child')) {
          setView('parent');
        }
      }
    } catch (error) {
      console.error('Error loading children:', error?.message || error?.toString() || error);
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
      const data = await getChild(fId, childId);
      if (data) {
        const childData = { ...data, _id: childId };
        setCurrentChild(childData);
        console.log('[APP] Child data loaded:', childData);
        return childData;
      }
      return null;
    } catch (error) {
      console.error('Error loading child data:', error?.message || error?.toString() || error);
      return null;
    }
  };

  const handleOTPVerified = (fId, phoneNum, isNewFamilyParam, isChild, childId, isAdditionalParent) => {
    setFamilyId(fId);
    setPhoneNumber(phoneNum);
    // Use localStorage to persist login across app restarts
    localStorage.setItem('familyId', fId);
    localStorage.setItem('phoneNumber', phoneNum);
    
    // Set isNewFamily state for onboarding flow
    setIsNewFamily(isNewFamilyParam || false);
    
    // If this is a child login (phone number belongs to a child)
    if (isChild && childId) {
      localStorage.setItem('childId', childId);
      localStorage.setItem('isChildView', 'true');
      localStorage.removeItem('parentLoggedIn');
      setIsChildView(true);
      setCurrentChild({ _id: childId });
      setScreen('child-view');
      loadChildData(fId, childId);
      setIsCreatingFamily(false);
      setIsNewFamily(false);
      return;
    }
    
    // Priority order for parent login:
    // 1. If user is an additional parent, show parent dashboard
    // 2. If user was creating a family (even if number already exists), treat them as parent
    // 3. If coming from main login, always show parent dashboard
    // 4. If it's a new family, show parent dashboard
    // 5. Otherwise (existing family from "Join"), show child password login
    if (isAdditionalParent || isCreatingFamily || screen === 'main-login' || isNewFamilyParam) {
      // User is additional parent OR came from "Create Family" OR "Main Login" OR it's a new family - show parent dashboard
      localStorage.setItem('parentLoggedIn', 'true');
      localStorage.removeItem('isChildView');
      localStorage.removeItem('childId');
      setIsChildView(false);
      setScreen('dashboard');
      loadChildren(fId);
    } else {
      // Existing family and user came from "Join" - show child password login
      localStorage.removeItem('parentLoggedIn');
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
      localStorage.setItem('familyId', fId);
    }
    
    // Ensure child has all required properties
    const childData = {
      ...child,
      _id: child._id || child.id,
      name: child.name || 'ילד'
    };
    
    setCurrentChild(childData);
    setIsChildView(true);
    localStorage.setItem('childId', childData._id);
    localStorage.setItem('isChildView', 'true');
    localStorage.removeItem('parentLoggedIn');
    
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
    // Clear all login data from localStorage
    localStorage.removeItem('familyId');
    localStorage.removeItem('phoneNumber');
    localStorage.removeItem('parentLoggedIn');
    localStorage.removeItem('childId');
    localStorage.removeItem('isChildView');
    setFamilyId(null);
    setPhoneNumber('');
    setChildren([]);
    setCurrentChild(null);
    setIsChildView(false);
    setView('parent');
    setScreen('main-login');
  };

  return (
    <div className="app" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
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
        <div className="app-layout">
          <ChildView 
            childId={currentChild._id} 
            familyId={familyId}
            onBackToParent={() => {
              setIsChildView(false);
              setCurrentChild(null);
              setScreen('dashboard');
              localStorage.removeItem('childId');
              localStorage.removeItem('isChildView');
              localStorage.setItem('parentLoggedIn', 'true');
            }}
            onLogout={handleLogout}
          />
        </div>
      )}

      {screen === 'dashboard' && familyId && !isChildView && (
        <div className="app-layout">
          <ParentDashboard 
            familyId={familyId} 
            isNewFamily={isNewFamily}
            onChildrenUpdated={loadChildren} 
            onLogout={handleLogout}
            onViewChild={(child) => {
              setCurrentChild(child);
              setIsChildView(true);
              setScreen('child-view');
              localStorage.setItem('childId', child._id);
              localStorage.setItem('isChildView', 'true');
            }}
            onNewFamilyComplete={() => {
              setIsNewFamily(false);
            }}
          />
        </div>
      )}
    </div>
  );
};

export default App;
