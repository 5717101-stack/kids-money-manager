import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getData, getCategories, getChildTransactions, addTransaction } from '../utils/api';
import Sidebar from './Sidebar';
import QuickActionModal from './QuickActionModal';
import Settings from './Settings';

const ParentDashboard = ({ familyId, onChildrenUpdated, onLogout, onViewChild }) => {
  const { t, i18n } = useTranslation();
  const [allData, setAllData] = useState({ children: {} });
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSidebar, setShowSidebar] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard', 'categories', 'profileImages', 'allowances', 'children', 'parents'
  const [showQuickAction, setShowQuickAction] = useState(false);
  const [quickActionType, setQuickActionType] = useState('deposit'); // 'deposit' or 'expense'
  const [showChildSelector, setShowChildSelector] = useState(false);
  const [pendingActionType, setPendingActionType] = useState(null); // 'deposit' or 'expense'
  const [selectedChild, setSelectedChild] = useState(null); // Store selected child object
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [totalFamilyBalance, setTotalFamilyBalance] = useState(0);
  const [familyPhoneNumber, setFamilyPhoneNumber] = useState('');

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [familyId]);

  const loadData = async () => {
    if (!familyId) return;
    try {
      const [dataResult, categoriesResult] = await Promise.allSettled([
        getData(familyId),
        getCategories(familyId)
      ]);

      if (dataResult.status === 'fulfilled' && dataResult.value) {
        setAllData(dataResult.value);
        
        // Get family phone number from sessionStorage
        const savedPhone = sessionStorage.getItem('phoneNumber') || '';
        setFamilyPhoneNumber(savedPhone);
        
        // Calculate total family balance
        const children = Object.values(dataResult.value.children || {});
        const total = children.reduce((sum, child) => {
          return sum + (child.balance || 0) + (child.cashBoxBalance || 0);
        }, 0);
        setTotalFamilyBalance(total);

        // Load recent transactions from all children
        const allTransactions = [];
        for (const child of children) {
          try {
            const trans = await getChildTransactions(familyId, child._id, 5);
            trans.forEach(t => {
              allTransactions.push({
                ...t,
                childName: child.name,
                childId: child._id
              });
            });
          } catch (err) {
            console.error(`Error loading transactions for ${child.name}:`, err);
          }
        }
        // Sort by date (newest first) and take last 5
        allTransactions.sort((a, b) => new Date(b.date || b.createdAt) - new Date(a.date || a.createdAt));
        setRecentTransactions(allTransactions.slice(0, 5));
      }

      if (categoriesResult.status === 'fulfilled') {
        setCategories(categoriesResult.value || []);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAction = (type) => {
    setQuickActionType(type);
    setShowQuickAction(true);
  };

  const handleQuickActionComplete = async () => {
    await loadData();
    if (onChildrenUpdated) {
      await onChildrenUpdated();
    }
  };

  const childrenList = Object.values(allData.children || {}).filter(child => child && child._id);

  // Load selected child from sessionStorage when childrenList is available
  useEffect(() => {
    if (typeof window !== 'undefined' && childrenList.length > 0) {
      const savedChildId = sessionStorage.getItem('selectedChildId');
      if (savedChildId) {
        const child = childrenList.find(c => c._id === savedChildId);
        if (child) {
          setSelectedChild(child);
        } else {
          // Child not found, clear selection
          sessionStorage.removeItem('selectedChildId');
          setSelectedChild(null);
        }
      }
    } else if (childrenList.length === 0) {
      // No children, clear selection
      setSelectedChild(null);
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('selectedChildId');
      }
    }
  }, [childrenList]);

  const handleBottomNavAction = (type) => {
    console.log('[ParentDashboard] handleBottomNavAction called with type:', type);
    console.log('[ParentDashboard] childrenList.length:', childrenList.length);
    console.log('[ParentDashboard] selectedChild:', selectedChild);
    
    // If children list is empty, show message
    if (childrenList.length === 0) {
      alert(t('parent.dashboard.noChildren', { defaultValue: 'אין ילדים במשפחה. הוסף ילד בהגדרות.' }));
      return;
    }
    
    // If no child is selected, show selector
    if (!selectedChild) {
      console.log('[ParentDashboard] No child selected, showing selector');
      setPendingActionType(type);
      setShowChildSelector(true);
      return;
    }
    
    // If only one child exists, use it directly
    if (childrenList.length === 1) {
      console.log('[ParentDashboard] Only one child, using directly');
      setQuickActionType(type);
      setShowQuickAction(true);
      return;
    }
    
    // Child is selected, proceed with action
    console.log('[ParentDashboard] Child selected, showing quick action');
    setQuickActionType(type);
    setShowQuickAction(true);
  };

  const handleChildSelected = (child) => {
    setSelectedChild(child);
    setShowChildSelector(false);
    
    // Store selected child ID in sessionStorage
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('selectedChildId', child._id);
    }
    
    // If there was a pending action, execute it
    if (pendingActionType) {
      setQuickActionType(pendingActionType);
      setShowQuickAction(true);
      setPendingActionType(null);
    }
  };

  const handleCenterButtonClick = () => {
    console.log('[ParentDashboard] handleCenterButtonClick called');
    console.log('[ParentDashboard] childrenList.length:', childrenList.length);
    
    // If children list is empty, show message
    if (childrenList.length === 0) {
      alert(t('parent.dashboard.noChildren', { defaultValue: 'אין ילדים במשפחה. הוסף ילד בהגדרות.' }));
      return;
    }
    
    // If only one child, select it automatically
    if (childrenList.length === 1) {
      console.log('[ParentDashboard] Only one child, selecting automatically');
      handleChildSelected(childrenList[0]);
      return;
    }
    
    // Show child selector
    console.log('[ParentDashboard] Showing child selector');
    setPendingActionType(null);
    setShowChildSelector(true);
  };

  if (loading) {
    return (
      <div className="parent-dashboard-new">
        <div className="loading">טוען נתונים...</div>
      </div>
    );
  }

  // Get page title based on current view
  const getPageTitle = () => {
    switch (currentView) {
      case 'dashboard':
        return t('parent.dashboard.title', { defaultValue: 'ממשק הורים' });
      case 'categories':
        return t('parent.settings.categories.title', { defaultValue: 'קטגוריות' });
      case 'profileImages':
        return t('parent.settings.profileImages.title', { defaultValue: 'תמונות פרופיל' });
      case 'allowances':
        return t('parent.settings.allowance.title', { defaultValue: 'דמי כיס' });
      case 'children':
        return t('parent.settings.manageChildren', { defaultValue: 'ניהול ילדים' });
      case 'parents':
        return t('parent.settings.parents.title', { defaultValue: 'ניהול הורים' });
      default:
        return t('parent.dashboard.title', { defaultValue: 'ממשק הורים' });
    }
  };

  return (
    <div className="app-layout parent-dashboard-new" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="app-header">
        <button 
          className="menu-btn" 
          onClick={() => setShowSidebar(true)}
          title={t('common.settings', { defaultValue: 'הגדרות' })}
          aria-label={t('common.settings', { defaultValue: 'הגדרות' })}
        >
          ☰
        </button>
        <h1 className="header-title">
          {getPageTitle()}
        </h1>
        <div style={{ width: '44px' }}></div> {/* Spacer for centering */}
      </div>

      {/* Content based on current view */}
      {currentView === 'dashboard' && (
        <div className="content-area">

      {/* Total Family Balance Card */}
      <div className="fintech-card">
        <div className="label-text">{t('parent.dashboard.totalBalance', { defaultValue: 'יתרה כוללת' })}</div>
        <div className="big-balance">₪{totalFamilyBalance.toFixed(2)}</div>
      </div>

      {/* Recent Activity */}
      <div className="fintech-card">
        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px', marginTop: 0 }}>{t('parent.dashboard.recentActivity', { defaultValue: 'פעילות אחרונה' })}</h2>
        {recentTransactions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
            {t('parent.dashboard.noActivity', { defaultValue: 'אין פעילות אחרונה' })}
          </div>
        ) : (
          <div>
            {recentTransactions.map((transaction, index) => (
              <div key={index} style={{ padding: '12px 0', borderBottom: index < recentTransactions.length - 1 ? '1px solid var(--border)' : 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '14px', fontWeight: 500 }}>{transaction.childName}:</span>
                  <span style={{ fontSize: '16px', fontWeight: 600, color: transaction.type === 'deposit' ? '#10B981' : '#EF4444' }}>
                    {transaction.type === 'deposit' ? '+' : '-'}₪{Math.abs(transaction.amount || 0).toFixed(2)}
                  </span>
                </div>
                {transaction.description && (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{transaction.description}</div>
                )}
                {transaction.category && (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{transaction.category}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
        </div>
      )}

      {/* Sidebar */}
      <Sidebar
        isOpen={showSidebar}
        onClose={async () => {
          setShowSidebar(false);
          await loadData();
          if (onChildrenUpdated) {
            await onChildrenUpdated();
          }
        }}
        onMenuItemClick={(tab) => {
          setShowSidebar(false);
          setCurrentView(tab);
        }}
        familyId={familyId}
        onLogout={onLogout}
        onChildrenUpdated={onChildrenUpdated}
        childrenList={childrenList}
        onChildDashboardClick={(child) => {
          if (onViewChild) {
            onViewChild(child);
          }
        }}
      />

      {/* Settings Content (not modal) */}
      {currentView !== 'dashboard' && (
        <div className="content-area">
          <Settings 
            familyId={familyId}
            onClose={async () => {
              setCurrentView('dashboard');
              await loadData();
              if (onChildrenUpdated) {
                await onChildrenUpdated();
              }
            }}
            onLogout={onLogout}
            activeTab={currentView}
            hideTabs={true}
            inSidebar={false}
            asPage={true}
          />
        </div>
      )}

      {/* Bottom Navigation Bar - Always visible for parent */}
      <div className="bottom-nav">
          <button 
            className="nav-item"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleBottomNavAction('expense');
            }}
            type="button"
          >
            <span style={{ fontSize: '20px' }}>-</span>
            <span>{t('parent.dashboard.recordExpense', { defaultValue: 'דיווח הוצאה' })}</span>
          </button>
          
          <button 
            className="fab-btn"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleCenterButtonClick();
            }}
            type="button"
          >
            {selectedChild ? (
              <span style={{ fontSize: '14px', fontWeight: 700 }}>{selectedChild.name}</span>
            ) : (
              <span style={{ fontSize: '14px', fontWeight: 700 }}>{t('parent.dashboard.selectChild', { defaultValue: 'בחירת ילד' })}</span>
            )}
          </button>
          
          <button 
            className="nav-item"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleBottomNavAction('deposit');
            }}
            type="button"
          >
            <span style={{ fontSize: '20px' }}>+</span>
            <span>{t('parent.dashboard.addMoney', { defaultValue: 'הוספת כסף' })}</span>
          </button>
        </div>

      {/* Child Selector Modal */}
      {showChildSelector && (
        <div className="child-selector-modal-overlay" onClick={() => setShowChildSelector(false)}>
          <div className="child-selector-modal" onClick={(e) => e.stopPropagation()}>
            <div className="child-selector-header">
              <h2>{t('parent.dashboard.selectChild', { defaultValue: 'בחר ילד' })}</h2>
              <button 
                className="close-button" 
                onClick={() => setShowChildSelector(false)}
              >
                ✕
              </button>
            </div>
            <div className="child-selector-list">
              {childrenList.map((child) => (
                <button
                  key={child._id}
                  className="child-selector-item"
                  onClick={() => handleChildSelected(child)}
                >
                  {child.profileImage ? (
                    <img src={child.profileImage} alt={child.name} className="child-selector-avatar" />
                  ) : (
                    <div className="child-selector-avatar-placeholder">
                      {child.name.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <span className="child-selector-name">{child.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {showQuickAction && (
        <QuickActionModal
          familyId={familyId}
          children={childrenList}
          categories={categories}
          type={quickActionType}
          onClose={() => {
            setShowQuickAction(false);
            sessionStorage.removeItem('selectedChildId');
          }}
          onComplete={handleQuickActionComplete}
        />
      )}
    </div>
  );
};

export default ParentDashboard;
