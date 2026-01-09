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

  const handleBottomNavAction = (type) => {
    // If children list is empty, show message
    if (childrenList.length === 0) {
      alert(t('parent.dashboard.noChildren', { defaultValue: 'אין ילדים במשפחה. הוסף ילד בהגדרות.' }));
      return;
    }
    
    // If no child is selected, show selector
    if (!selectedChild) {
      setPendingActionType(type);
      setShowChildSelector(true);
      return;
    }
    
    // If only one child exists, use it directly
    if (childrenList.length === 1) {
      setQuickActionType(type);
      setShowQuickAction(true);
      return;
    }
    
    // Child is selected, proceed with action
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
    // If children list is empty, show message
    if (childrenList.length === 0) {
      alert(t('parent.dashboard.noChildren', { defaultValue: 'אין ילדים במשפחה. הוסף ילד בהגדרות.' }));
      return;
    }
    
    // If only one child, select it automatically
    if (childrenList.length === 1) {
      handleChildSelected(childrenList[0]);
      return;
    }
    
    // Show child selector
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
    <div className="parent-dashboard-new" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="dashboard-header-new">
        <button 
          className="hamburger-menu-button" 
          onClick={() => setShowSidebar(true)}
          title={t('common.settings', { defaultValue: 'הגדרות' })}
          aria-label={t('common.settings', { defaultValue: 'הגדרות' })}
          style={{ position: 'absolute', top: 'calc(12px + var(--safe-area-inset-top))', [i18n.language === 'he' ? 'right' : 'left']: '16px', zIndex: 10 }}
        >
          <span className="hamburger-icon">
            <span></span>
            <span></span>
            <span></span>
          </span>
        </button>
        <h1 className="family-name" style={{ textAlign: 'center', width: '100%' }}>
          {getPageTitle()}
        </h1>
      </div>

      {/* Content based on current view */}
      {currentView === 'dashboard' && (
        <div className="dashboard-content-wrapper">

      {/* Total Family Balance Card */}
      <div className="total-balance-card">
        <div className="total-balance-label">{t('parent.dashboard.totalBalance', { defaultValue: 'יתרה כוללת' })}</div>
        <div className="total-balance-value">₪{totalFamilyBalance.toFixed(2)}</div>
      </div>

      {/* Recent Activity */}
      <div className="recent-activity-section">
        <h2 className="section-title">{t('parent.dashboard.recentActivity', { defaultValue: 'פעילות אחרונה' })}</h2>
        {recentTransactions.length === 0 ? (
          <div className="no-activity-message">
            {t('parent.dashboard.noActivity', { defaultValue: 'אין פעילות אחרונה' })}
          </div>
        ) : (
          <div className="recent-transactions-list">
            {recentTransactions.map((transaction, index) => (
              <div key={index} className="recent-transaction-item">
                <div className="transaction-main">
                  <span className="transaction-child-name">{transaction.childName}:</span>
                  <span className={`transaction-amount ${transaction.type === 'deposit' ? 'positive' : 'negative'}`}>
                    {transaction.type === 'deposit' ? '+' : '-'}₪{Math.abs(transaction.amount || 0).toFixed(2)}
                  </span>
                </div>
                {transaction.description && (
                  <div className="transaction-description">{transaction.description}</div>
                )}
                {transaction.category && (
                  <div className="transaction-category">{transaction.category}</div>
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
        <div className="settings-page-wrapper">
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

      {/* Bottom Navigation Bar - Only show on dashboard view */}
      {currentView === 'dashboard' && (
      <div className="bottom-nav-bar">
        <button 
          className="bottom-nav-button expense-button"
          onClick={() => handleBottomNavAction('expense')}
        >
          <span className="bottom-nav-icon">-</span>
          <span className="bottom-nav-label">{t('parent.dashboard.recordExpense', { defaultValue: 'דיווח הוצאה' })}</span>
        </button>
        
        <button 
          className="bottom-nav-button center-button"
          onClick={handleCenterButtonClick}
        >
          {selectedChild ? (
            <span className="center-button-text">{selectedChild.name}</span>
          ) : (
            <span className="center-button-text">{t('parent.dashboard.selectChild', { defaultValue: 'בחירת ילד' })}</span>
          )}
        </button>
        
        <button 
          className="bottom-nav-button income-button"
          onClick={() => handleBottomNavAction('deposit')}
        >
          <span className="bottom-nav-icon">+</span>
          <span className="bottom-nav-label">{t('parent.dashboard.addMoney', { defaultValue: 'הוספת כסף' })}</span>
        </button>
      </div>
      )}

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
