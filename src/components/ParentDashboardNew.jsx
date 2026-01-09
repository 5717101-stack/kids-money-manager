import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getData, getCategories, getChildTransactions, addTransaction } from '../utils/api';
import Sidebar from './Sidebar';
import QuickActionModal from './QuickActionModal';
import Settings from './Settings';

const ParentDashboard = ({ familyId, onChildrenUpdated, onLogout }) => {
  const { t, i18n } = useTranslation();
  const [allData, setAllData] = useState({ children: {} });
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSidebar, setShowSidebar] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard', 'categories', 'profileImages', 'allowances', 'children', 'parents'
  const [showQuickAction, setShowQuickAction] = useState(false);
  const [quickActionType, setQuickActionType] = useState('deposit'); // 'deposit' or 'expense'
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
        <div className="header-left">
        </div>
        <h1 className="family-name">
          {getPageTitle()}
        </h1>
        <button 
          className="hamburger-menu-button" 
          onClick={() => setShowSidebar(true)}
          title={t('common.settings', { defaultValue: 'הגדרות' })}
          aria-label={t('common.settings', { defaultValue: 'הגדרות' })}
        >
          <span className="hamburger-icon">
            <span></span>
            <span></span>
            <span></span>
          </span>
        </button>
      </div>

      {/* Content based on current view */}
      {currentView === 'dashboard' && (
        <>

      {/* Total Family Balance Card */}
      <div className="total-balance-card">
        <div className="total-balance-label">{t('parent.dashboard.totalBalance', { defaultValue: 'יתרה כוללת' })}</div>
        <div className="total-balance-value">₪{totalFamilyBalance.toFixed(2)}</div>
      </div>

      {/* Children Overview */}
      <div className="children-overview">
        <h2 className="section-title">{t('parent.dashboard.children', { defaultValue: 'ילדים' })}</h2>
        <div className="children-cards-container">
          {childrenList.length === 0 ? (
            <div className="no-children-message">
              {t('parent.dashboard.noChildren', { defaultValue: 'אין ילדים במשפחה. הוסף ילד בהגדרות.' })}
            </div>
          ) : (
            childrenList.map((child, index) => {
              const balance = (child.balance || 0) + (child.cashBoxBalance || 0);
              const goal = child.savingsGoal || null;
              const goalProgress = goal && goal.targetAmount > 0 
                ? Math.min((balance / goal.targetAmount) * 100, 100) 
                : 0;
              
              return (
                <div key={child._id} className="child-card">
                  <div className="child-card-header">
                    <div className="child-profile-section">
                      {child.profileImage ? (
                        <img 
                          src={child.profileImage} 
                          alt={child.name}
                          className="child-profile-image"
                        />
                      ) : (
                        <div className="child-profile-placeholder">
                          {child.name.charAt(0).toUpperCase()}
                        </div>
                      )}
                      <div className="child-info">
                        <h3 className="child-name">{child.name}</h3>
                        <div className="child-balance">₪{balance.toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                  
                  {goal && goal.targetAmount > 0 && (
                    <div className="goal-progress-mini">
                      <div className="goal-progress-label">
                        {goal.name || t('child.savingsGoals', { defaultValue: 'מטרת חיסכון' })}
                      </div>
                      <div className="goal-progress-bar">
                        <div 
                          className="goal-progress-fill"
                          style={{ width: `${goalProgress}%` }}
                        />
                      </div>
                      <div className="goal-progress-text">
                        {goalProgress.toFixed(0)}% ({balance.toFixed(2)} / {goal.targetAmount.toFixed(2)})
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <button 
          className="quick-action-button deposit-button"
          onClick={() => handleQuickAction('deposit')}
        >
          <span className="quick-action-icon">+</span>
          <span className="quick-action-label">{t('parent.dashboard.addMoney', { defaultValue: 'הוסף כסף' })}</span>
        </button>
        <button 
          className="quick-action-button expense-button"
          onClick={() => handleQuickAction('expense')}
        >
          <span className="quick-action-icon">-</span>
          <span className="quick-action-label">{t('parent.dashboard.recordExpense', { defaultValue: 'דווח הוצאה' })}</span>
        </button>
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
        </>
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
      />

      {/* Settings Content (not modal) */}
      {currentView !== 'dashboard' && (
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
      )}

      {showQuickAction && (
        <QuickActionModal
          familyId={familyId}
          children={childrenList}
          categories={categories}
          type={quickActionType}
          onClose={() => setShowQuickAction(false)}
          onComplete={handleQuickActionComplete}
        />
      )}
    </div>
  );
};

export default ParentDashboard;
