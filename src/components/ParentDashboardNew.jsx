import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getData, getCategories, getChildTransactions, addTransaction, getFamilyInfo, updateParentProfileImage, getPaymentRequests, approvePaymentRequest, rejectPaymentRequest } from '../utils/api';
import { smartCompressImage } from '../utils/imageCompression';
import Sidebar from './Sidebar';
import QuickActionModal from './QuickActionModal';
import Settings from './Settings';
import DeleteFamilyProfile from './DeleteFamilyProfile';
import ExpensesPieChart from './ExpensesPieChart';
import Guide from './Guide';

const ParentDashboard = ({ familyId, onChildrenUpdated, onLogout, onViewChild }) => {
  const { t, i18n } = useTranslation();
  const [allData, setAllData] = useState({ children: {} });
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSidebar, setShowSidebar] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard', 'categories', 'tasks', 'profileImages', 'allowances', 'children', 'parents', 'deleteFamily', 'guide'
  const [showQuickAction, setShowQuickAction] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [quickActionType, setQuickActionType] = useState('deposit'); // 'deposit' or 'expense'
  const [showChildSelector, setShowChildSelector] = useState(false);
  const [pendingActionType, setPendingActionType] = useState(null); // 'deposit' or 'expense'
  const [selectedChild, setSelectedChild] = useState(null); // Store selected child object
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [filteredCategory, setFilteredCategory] = useState(null); // Category to filter transactions
  const [totalFamilyBalance, setTotalFamilyBalance] = useState(0);
  const [familyPhoneNumber, setFamilyPhoneNumber] = useState('');
  const [parentName, setParentName] = useState('');
  const [parentProfileImage, setParentProfileImage] = useState(null);
  const [showImagePicker, setShowImagePicker] = useState(false);
  const fileInputRef = React.useRef(null);
  const [showBalanceDetail, setShowBalanceDetail] = useState(false);
  const [activityLimit, setActivityLimit] = useState(() => {
    // Load from localStorage or default to 5
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('parentActivityLimit');
      if (saved === 'all') return null;
      return saved ? parseInt(saved, 10) : 5;
    }
    return 5;
  });
  const [chartReloadKey, setChartReloadKey] = useState(0);
  const [paymentRequests, setPaymentRequests] = useState([]);
  const [showPaymentRequests, setShowPaymentRequests] = useState(false);
  const [selectedPaymentRequest, setSelectedPaymentRequest] = useState(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000); // Refresh every 15 seconds (reduced for better performance)
    return () => clearInterval(interval);
  }, [familyId, activityLimit]);

  // Check if guide should be shown on first visit
  useEffect(() => {
    if (currentView === 'dashboard' && !localStorage.getItem('guideSeen_parent')) {
      setShowGuide(true);
    }
  }, [currentView]);

  const loadData = async () => {
    if (!familyId) return;
    try {
      const [dataResult, categoriesResult, familyInfoResult, paymentRequestsResult] = await Promise.allSettled([
        getData(familyId),
        getCategories(familyId),
        getFamilyInfo(familyId),
        getPaymentRequests(familyId, 'pending').catch(() => [])
      ]);

      if (dataResult.status === 'fulfilled' && dataResult.value) {
        setAllData(dataResult.value);
        
        // Get family phone number from localStorage
        const savedPhone = localStorage.getItem('phoneNumber') || '';
        setFamilyPhoneNumber(savedPhone);
        
        // Load parent info
        if (familyInfoResult.status === 'fulfilled' && familyInfoResult.value) {
          setParentName(familyInfoResult.value.parentName || '');
          setParentProfileImage(familyInfoResult.value.parentProfileImage || null);
        }
        
        // Load pending payment requests
        if (paymentRequestsResult.status === 'fulfilled') {
          setPaymentRequests(paymentRequestsResult.value || []);
        }
        
        // Calculate total family balance (only balance with parents, not cashBoxBalance)
        const children = Object.values(dataResult.value.children || {});
        const total = children.reduce((sum, child) => {
          return sum + (child.balance || 0);
        }, 0);
        setTotalFamilyBalance(total);

        // Load recent transactions from all children
        const allTransactions = [];
        // If limit is null (all), load more transactions per child, otherwise use the limit
        const perChildLimit = activityLimit === null ? 50 : Math.ceil(activityLimit / Math.max(children.length, 1));
        
        for (const child of children) {
          try {
            const trans = await getChildTransactions(familyId, child._id, perChildLimit);
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
        // Sort by date (newest first)
        allTransactions.sort((a, b) => new Date(b.date || b.createdAt) - new Date(a.date || a.createdAt));
        // Apply limit if not null
        const finalTransactions = activityLimit === null ? allTransactions : allTransactions.slice(0, activityLimit);
        setRecentTransactions(finalTransactions);
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
    // Force chart reload when transaction is added
    setChartReloadKey(prev => prev + 1);
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
    // Show payment requests instead of child selector
    setShowPaymentRequests(true);
  };

  const handlePaymentRequestClick = (request) => {
    setSelectedPaymentRequest(request);
  };

  const handleApprovePayment = async (requestId) => {
    if (!familyId) return;
    try {
      await approvePaymentRequest(familyId, requestId);
      await loadData();
      setSelectedPaymentRequest(null);
      // Show success notification
      const notification = document.createElement('div');
      notification.textContent = t('parent.dashboard.paymentApproved', { defaultValue: 'תשלום אושר בהצלחה!' });
      const isRTL = i18n.language === 'he';
      const animationName = isRTL ? 'slideInRTL' : 'slideIn';
      const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
      const rightOrLeft = isRTL ? 'left' : 'right';
      notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        ${rightOrLeft}: 20px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        z-index: 10005;
        font-weight: 600;
        animation: ${animationName} 0.3s ease;
        max-width: calc(100% - 40px);
      `;
      document.body.appendChild(notification);
      setTimeout(() => {
        notification.style.animation = `${animationOutName} 0.3s ease`;
        setTimeout(() => notification.remove(), 300);
      }, 2000);
    } catch (error) {
      alert(t('parent.dashboard.paymentApproveError', { defaultValue: 'שגיאה באישור תשלום' }) + ': ' + error.message);
    }
  };

  const handleRejectPayment = async (requestId) => {
    if (!familyId) return;
    try {
      await rejectPaymentRequest(familyId, requestId);
      await loadData();
      setSelectedPaymentRequest(null);
    } catch (error) {
      alert(t('parent.dashboard.paymentRejectError', { defaultValue: 'שגיאה בדחיית תשלום' }) + ': ' + error.message);
    }
  };

  if (loading) {
    return (
      <div className="parent-dashboard-new">
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '60px 20px',
          gap: '20px',
          minHeight: '100vh'
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            border: '5px solid rgba(99, 102, 241, 0.2)',
            borderTopColor: '#6366F1',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite'
          }}></div>
          <div style={{ color: 'var(--text-muted)', fontSize: '16px', fontWeight: 500 }}>
            {t('common.loading', { defaultValue: 'Loading...' })}
          </div>
        </div>
      </div>
    );
  }

  // Get page title based on current view
  const getPageTitle = () => {
    switch (currentView) {
      case 'dashboard':
        return parentName || t('parent.dashboard.title', { defaultValue: 'ממשק הורים' });
      case 'categories':
        return t('parent.settings.categories.title', { defaultValue: 'קטגוריות' });
      case 'tasks':
        return t('parent.settings.tasks.title', { defaultValue: 'מטלות' });
      case 'profileImages':
        return t('parent.settings.profileImages.title', { defaultValue: 'תמונות פרופיל' });
      case 'children':
        return t('parent.settings.manageChildren', { defaultValue: 'ניהול ילדים' });
      case 'parents':
        return t('parent.settings.parents.title', { defaultValue: 'ניהול הורים' });
      case 'deleteFamily':
        return t('deleteFamily.title', { defaultValue: 'מחיקת פרופיל משפחתי' });
      default:
        return parentName || t('parent.dashboard.title', { defaultValue: 'ממשק הורים' });
    }
  };

  const handleImageUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      // Compress image before upload - smartCompressImage already returns base64 string
      const base64Image = await smartCompressImage(file);
      
      try {
        await updateParentProfileImage(familyId, base64Image);
        setParentProfileImage(base64Image);
        await loadData(); // Reload to get updated data
      } catch (error) {
        alert(t('parent.profile.error', { defaultValue: 'שגיאה בעדכון תמונת הפרופיל' }) + ': ' + error.message);
      }
    } catch (error) {
      alert(t('parent.profile.error', { defaultValue: 'שגיאה בעדכון תמונת הפרופיל' }) + ': ' + error.message);
    }
    
    // Reset file input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveImage = async () => {
    try {
      await updateParentProfileImage(familyId, null);
      setParentProfileImage(null);
      await loadData(); // Reload to get updated data
    } catch (error) {
      alert(t('parent.profile.error', { defaultValue: 'שגיאה בהסרת תמונה' }) + ': ' + error.message);
    }
  };

  return (
    <div className="app-layout parent-dashboard-new" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="app-header">
        <h1 className="header-title">
          {getPageTitle()}
        </h1>
      </div>
      
      {/* Menu button in top right corner */}
      <button 
        className="menu-btn menu-btn-top-right" 
        onClick={() => setShowSidebar(true)}
        title={t('common.settings', { defaultValue: 'הגדרות' })}
        aria-label={t('common.settings', { defaultValue: 'הגדרות' })}
      >
        ☰
      </button>

      {/* Content based on current view */}
      {currentView === 'dashboard' && (
        <div className="content-area" style={{ flex: 1, overflowY: 'auto', paddingBottom: 'calc(90px + env(safe-area-inset-bottom))', minHeight: 0 }}>
      {/* Profile Image Section */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px', paddingTop: '10px' }}>
        <div style={{ position: 'relative' }}>
          {parentProfileImage ? (
            <img 
              src={parentProfileImage} 
              alt={parentName}
              loading="lazy"
              decoding="async"
              onClick={() => setShowImagePicker(true)}
              style={{
                width: '120px',
                height: '120px',
                borderRadius: '50%',
                objectFit: 'cover',
                border: '4px solid white',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                cursor: 'pointer'
              }}
            />
          ) : (
            <div style={{
              width: '120px',
              height: '120px',
              borderRadius: '50%',
              background: 'var(--primary-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '48px',
              color: 'white',
              fontWeight: 700,
              border: '4px solid white',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
            }}>
              {parentName?.charAt(0)?.toUpperCase() || 'ה'}
            </div>
          )}
          <button
            onClick={() => {
              if (parentProfileImage) {
                // If image exists, open modal with options
                setShowImagePicker(true);
              } else {
                // If no image, open file picker directly
                fileInputRef.current?.click();
              }
            }}
            style={{
              position: 'absolute',
              bottom: 0,
              right: 0,
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'var(--primary)',
              border: '3px solid white',
              color: 'white',
              fontSize: '18px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
            }}
            title={parentProfileImage ? t('parent.profile.changePicture', { defaultValue: 'שנה תמונה' }) : t('parent.profile.upload', { defaultValue: 'העלה תמונה' })}
          >
            {parentProfileImage ? '✏️' : '+'}
          </button>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleImageUpload}
      />

      {/* Image picker modal - only shown when image exists */}
      {showImagePicker && parentProfileImage && (
        <div className="modal-overlay" onClick={() => setShowImagePicker(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('parent.profile.changePicture', { defaultValue: 'שנה תמונה' })}</h2>
              <button className="close-button" onClick={() => setShowImagePicker(false)}>✕</button>
            </div>
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <button
                onClick={() => {
                  fileInputRef.current?.click();
                  setShowImagePicker(false);
                }}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  background: 'var(--primary-gradient)',
                  color: 'white',
                  border: 'none',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {t('parent.profile.replace', { defaultValue: 'החלף תמונה' })}
              </button>
              <button
                onClick={() => {
                  handleRemoveImage();
                  setShowImagePicker(false);
                }}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  background: '#EF4444',
                  color: 'white',
                  border: 'none',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {t('parent.profile.remove', { defaultValue: 'מחק תמונה' })}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Total Family Balance Card */}
      <div className="fintech-card balance-card" onClick={() => setShowBalanceDetail(true)} style={{ cursor: 'pointer' }}>
        <div className="label-text">{t('parent.dashboard.totalBalance', { defaultValue: 'יתרה כוללת' })}</div>
        <div className="big-balance">₪{totalFamilyBalance.toFixed(2)}</div>
      </div>

      {/* Expenses Pie Chart */}
      <ExpensesPieChart 
        familyId={familyId}
        children={childrenList}
        categories={categories}
        onCategorySelect={setFilteredCategory}
        selectedCategory={filteredCategory}
        forceReload={chartReloadKey}
      />

      {/* Recent Activity */}
      <div className="fintech-card activity-card">
        <div className="activity-header">
          <h2>{t('parent.dashboard.recentActivity', { defaultValue: 'פעילות אחרונה' })}</h2>
          <div className="activity-limit-selector">
            <button
              className={`activity-limit-btn ${activityLimit === 5 ? 'active' : ''}`}
              onClick={() => {
                setActivityLimit(5);
                localStorage.setItem('parentActivityLimit', '5');
              }}
            >
              5
            </button>
            <button
              className={`activity-limit-btn ${activityLimit === 20 ? 'active' : ''}`}
              onClick={() => {
                setActivityLimit(20);
                localStorage.setItem('parentActivityLimit', '20');
              }}
            >
              20
            </button>
            <button
              className={`activity-limit-btn ${activityLimit === null ? 'active' : ''}`}
              onClick={() => {
                setActivityLimit(null);
                localStorage.setItem('parentActivityLimit', 'all');
              }}
            >
              {t('parent.dashboard.all', { defaultValue: 'הכל' })}
            </button>
          </div>
        </div>
        <div className="activity-content">
          {(() => {
            const filtered = filteredCategory 
              ? recentTransactions.filter(t => t.category === filteredCategory)
              : recentTransactions;
            
            if (filtered.length === 0) {
              return (
                <div className="no-activity-message">
                  {filteredCategory 
                    ? t('parent.dashboard.noActivityForCategory', { category: filteredCategory }).replace('{category}', filteredCategory)
                    : t('parent.dashboard.noActivity', { defaultValue: 'אין פעילות אחרונה' })
                  }
                </div>
              );
            }
            
            return (
              <div className="activity-list-container">
                {filtered.map((transaction, index) => (
                  <div key={index} className="activity-item">
                    <div className="activity-main">
                      <span className="activity-child-name">{transaction.childName}:</span>
                      <span className={`activity-amount ${transaction.type === 'deposit' ? 'positive' : 'negative'}`}>
                        {transaction.type === 'deposit' ? '+' : '-'}₪{Math.abs(transaction.amount || 0).toFixed(2)}
                      </span>
                    </div>
                    {transaction.description && (
                      <div className="activity-description">{transaction.description}</div>
                    )}
                    {transaction.category && (
                      <div className="activity-category">{transaction.category}</div>
                    )}
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      </div>

      {/* Balance Detail Modal */}
      {showBalanceDetail && (
        <div className="modal-overlay" onClick={() => setShowBalanceDetail(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('parent.dashboard.balanceDetail', { defaultValue: 'פירוט יתרה לפי ילדים' })}</h2>
              <button className="close-button" onClick={() => setShowBalanceDetail(false)}>✕</button>
            </div>
            <div style={{ padding: '20px' }}>
              {childrenList.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
                  {t('parent.dashboard.noChildren', { defaultValue: 'אין ילדים' })}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {childrenList.map((child) => (
                    <div key={child._id} style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      padding: '12px',
                      background: '#F9FAFB',
                      borderRadius: '12px'
                    }}>
                      <span style={{ fontSize: '16px', fontWeight: 600 }}>{child.name}</span>
                      <span style={{ fontSize: '18px', fontWeight: 700, color: 'var(--primary)' }}>
                        ₪{(child.balance || 0).toFixed(2)}
                      </span>
                    </div>
                  ))}
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '16px',
                    marginTop: '8px',
                    background: 'var(--primary-gradient)',
                    borderRadius: '12px',
                    color: 'white'
                  }}>
                    <span style={{ fontSize: '18px', fontWeight: 700 }}>{t('parent.dashboard.total', { defaultValue: 'סה"כ' })}</span>
                    <span style={{ fontSize: '24px', fontWeight: 700 }}>
                      ₪{totalFamilyBalance.toFixed(2)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
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
          if (tab === 'guide') {
            setShowGuide(true);
          } else {
            setCurrentView(tab);
          }
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
      {currentView !== 'dashboard' && currentView !== 'deleteFamily' && (
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
            onChildrenUpdated={onChildrenUpdated}
            onTabChange={(tab) => setCurrentView(tab)}
          />
        </div>
      )}

      {/* Delete Family Profile */}
      {currentView === 'deleteFamily' && (
        <DeleteFamilyProfile
          familyId={familyId}
          onDeleteComplete={() => {
            // Clear session storage and logout
            // Clear only login-related items from localStorage
            localStorage.removeItem('familyId');
            localStorage.removeItem('phoneNumber');
            localStorage.removeItem('parentLoggedIn');
            localStorage.removeItem('childId');
            localStorage.removeItem('isChildView');
            if (onLogout) {
              onLogout();
            }
          }}
          onCancel={() => {
            setCurrentView('dashboard');
          }}
        />
      )}

      {/* Bottom Navigation Bar - Hidden on settings screens */}
      {!(['categories', 'tasks', 'children', 'parents', 'deleteFamily'].includes(currentView) || showGuide) && (
        <div className="bottom-nav">
          {/* Left: Income (Deposit) */}
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
          
          <button 
            className="fab-btn"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleCenterButtonClick();
            }}
            type="button"
            style={{ position: 'relative' }}
          >
            {paymentRequests.length > 0 && (
              <span style={{
                position: 'absolute',
                top: '-4px',
                right: '-4px',
                background: '#EF4444',
                color: 'white',
                borderRadius: '50%',
                width: '20px',
                height: '20px',
                fontSize: '12px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '2px solid white'
              }}>
                {paymentRequests.length > 9 ? '9+' : paymentRequests.length}
              </span>
            )}
            <span style={{ fontSize: '20px' }}>💰</span>
          </button>
          
          {/* Right: Expense */}
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
        </div>
      )}

      {/* Payment Requests Modal */}
      {showPaymentRequests && (
        <div className="child-selector-modal-overlay" onClick={() => {
          setShowPaymentRequests(false);
          setSelectedPaymentRequest(null);
        }}>
          <div className="child-selector-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            {!selectedPaymentRequest ? (
              <>
                <div className="child-selector-header">
                  <h2>{t('parent.dashboard.paymentRequests', { defaultValue: 'בקשות תשלום' })}</h2>
                  <button 
                    className="close-button" 
                    onClick={() => {
                      setShowPaymentRequests(false);
                      setSelectedPaymentRequest(null);
                    }}
                  >
                    ✕
                  </button>
                </div>
                <div className="child-selector-list">
                  {paymentRequests.length === 0 ? (
                    <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      {t('parent.dashboard.noPaymentRequests', { defaultValue: 'אין בקשות תשלום ממתינות' })}
                    </div>
                  ) : (
                    paymentRequests.map((request) => (
                      <button
                        key={request._id}
                        className="child-selector-item"
                        onClick={() => handlePaymentRequestClick(request)}
                        style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '8px' }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                          <div>
                            <div style={{ fontSize: '16px', fontWeight: 600 }}>{request.taskName}</div>
                            <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                              {request.childName} - ₪{request.taskPrice.toFixed(2)}
                            </div>
                          </div>
                          <span style={{ fontSize: '20px' }}>→</span>
                        </div>
                        {request.note && (
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            {request.note.substring(0, 50)}{request.note.length > 50 ? '...' : ''}
                          </div>
                        )}
                      </button>
                    ))
                  )}
                </div>
              </>
            ) : (
              <div style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h2 style={{ margin: 0 }}>{selectedPaymentRequest.taskName}</h2>
                  <button 
                    className="close-button" 
                    onClick={() => setSelectedPaymentRequest(null)}
                  >
                    ✕
                  </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {t('parent.dashboard.child', { defaultValue: 'ילד' })}
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 600 }}>{selectedPaymentRequest.childName}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {t('parent.dashboard.amount', { defaultValue: 'סכום' })}
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--primary)' }}>
                      ₪{selectedPaymentRequest.taskPrice.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {t('parent.dashboard.requestedAt', { defaultValue: 'זמן ביצוע' })}
                    </div>
                    <div style={{ fontSize: '14px' }}>
                      {new Date(selectedPaymentRequest.requestedAt).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                  </div>
                  {selectedPaymentRequest.note && (
                    <div>
                      <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        {t('parent.dashboard.note', { defaultValue: 'הערה' })}
                      </div>
                      <div style={{ fontSize: '14px', padding: '12px', background: '#F9FAFB', borderRadius: '8px' }}>
                        {selectedPaymentRequest.note}
                      </div>
                    </div>
                  )}
                  {selectedPaymentRequest.image && (
                    <div>
                      <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        {t('parent.dashboard.image', { defaultValue: 'תמונה' })}
                      </div>
                      <img 
                        src={selectedPaymentRequest.image} 
                        alt="Task completion" 
                        style={{
                          maxWidth: '100%',
                          maxHeight: '300px',
                          borderRadius: '8px',
                          objectFit: 'contain'
                        }}
                      />
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                    <button
                      onClick={() => handleRejectPayment(selectedPaymentRequest._id)}
                      style={{
                        flex: 1,
                        padding: '12px',
                        borderRadius: '8px',
                        background: '#EF4444',
                        color: 'white',
                        border: 'none',
                        fontSize: '16px',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      {t('parent.dashboard.reject', { defaultValue: 'דחה' })}
                    </button>
                    <button
                      onClick={() => handleApprovePayment(selectedPaymentRequest._id)}
                      style={{
                        flex: 1,
                        padding: '12px',
                        borderRadius: '8px',
                        background: 'var(--primary-gradient)',
                        color: 'white',
                        border: 'none',
                        fontSize: '16px',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      {t('parent.dashboard.approve', { defaultValue: 'אשר תשלום' })}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
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
                    <img src={child.profileImage} alt={child.name} className="child-selector-avatar" loading="lazy" decoding="async" />
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

      {/* Guide Modal */}
      {showGuide && (
        <Guide 
          userType="parent" 
          onClose={() => {
            setShowGuide(false);
            setCurrentView('dashboard');
          }} 
        />
      )}
    </div>
  );
};

export default ParentDashboard;
