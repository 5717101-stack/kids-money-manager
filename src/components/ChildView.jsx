import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getChild, getChildTransactions, updateCashBoxBalance, getSavingsGoal, updateSavingsGoal, deleteSavingsGoal, updateProfileImage, getExpensesByCategory } from '../utils/api';
import ExpensePieChart from './ExpensePieChart';

const ChildView = ({ childId, familyId }) => {
  const { t, i18n } = useTranslation();
  const [childData, setChildData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [savingsGoal, setSavingsGoal] = useState(null);
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [goalName, setGoalName] = useState('');
  const [goalAmount, setGoalAmount] = useState('');
  const [editingGoal, setEditingGoal] = useState(false);
  const [showImagePicker, setShowImagePicker] = useState(false);
  const fileInputRef = React.useRef(null);
  const [expensesPeriod, setExpensesPeriod] = useState('month'); // 'week' or 'month'
  const [expensesByCategory, setExpensesByCategory] = useState([]);
  const [loadingExpenses, setLoadingExpenses] = useState(false);

  useEffect(() => {
    loadChildData();
    loadSavingsGoal();
    // Refresh every 5 seconds to show updated balance (but not expenses chart)
    const interval = setInterval(() => {
      loadChildData();
      loadSavingsGoal();
      // Don't reload expenses chart automatically - only when period changes
    }, 5000);
    return () => clearInterval(interval);
  }, [childId, familyId]);

  // Load expenses when period changes or on initial load
  useEffect(() => {
    if (familyId && childId) {
      loadExpensesByCategory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expensesPeriod, familyId, childId]);

  const loadChildData = async () => {
    if (!familyId || !childId) return;
    try {
      const child = await getChild(familyId, childId);
      if (child) {
        setChildData(child);
        // Show last 10 transactions
        const trans = await getChildTransactions(familyId, childId, 10);
        setTransactions(trans);
      }
    } catch (error) {
      console.error('Error loading child data:', error);
    }
  };

  const loadSavingsGoal = async () => {
    if (!familyId || !childId) return;
    try {
      const goal = await getSavingsGoal(familyId, childId);
      setSavingsGoal(goal);
      if (goal) {
        setGoalName(goal.name || '');
        setGoalAmount(goal.targetAmount?.toString() || '');
      }
    } catch (error) {
      console.error('Error loading savings goal:', error);
    }
  };

  const loadExpensesByCategory = async () => {
    if (!familyId || !childId) return;
    try {
      setLoadingExpenses(true);
      const days = expensesPeriod === 'week' ? 7 : 30;
      const expenses = await getExpensesByCategory(familyId, childId, days);
      setExpensesByCategory(expenses || []);
    } catch (error) {
      console.error('Error loading expenses by category:', error);
      setExpensesByCategory([]);
    } finally {
      setLoadingExpenses(false);
    }
  };

  const handleCashBoxUpdate = async (newValue) => {
    if (!familyId || !childId) return;
    try {
      await updateCashBoxBalance(familyId, childId, newValue);
      await loadChildData();
    } catch (error) {
      alert(t('child.dashboard.error', { defaultValue: 'שגיאה בעדכון יתרת הקופה' }) + ': ' + error.message);
      throw error;
    }
  };

  const handleSaveGoal = async () => {
    if (!goalName.trim() || !goalAmount || parseFloat(goalAmount) <= 0) {
      alert(t('child.savingsGoal.invalidGoal', { defaultValue: 'אנא הכנס שם מטרה וסכום תקין' }));
      return;
    }

    try {
      await updateSavingsGoal(familyId, childId, goalName.trim(), parseFloat(goalAmount));
      await loadSavingsGoal();
      setShowGoalModal(false);
      setEditingGoal(false);
    } catch (error) {
      alert(t('child.savingsGoal.error', { defaultValue: 'שגיאה בשמירת מטרה' }) + ': ' + error.message);
    }
  };

  const handleDeleteGoal = async () => {
    if (!window.confirm(t('child.savingsGoal.confirmDelete', { defaultValue: 'האם אתה בטוח שברצונך למחוק את מטרת החיסכון?' }))) {
      return;
    }

    try {
      await deleteSavingsGoal(familyId, childId);
      setSavingsGoal(null);
      setGoalName('');
      setGoalAmount('');
    } catch (error) {
      alert(t('child.savingsGoal.error', { defaultValue: 'שגיאה במחיקת מטרה' }) + ': ' + error.message);
    }
  };

  const handleImageUpload = async (file) => {
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert(t('child.profile.invalidFile', { defaultValue: 'אנא בחר קובץ תמונה בלבד' }));
      return;
    }

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      alert(t('child.profile.fileTooLarge', { defaultValue: 'גודל הקובץ גדול מדי. אנא בחר תמונה קטנה מ-10MB' }));
      return;
    }

    // Compress image
    const compressImage = (file, maxWidth = 1920, maxHeight = 1920, quality = 0.8) => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const img = new Image();
          img.onload = () => {
            const canvas = document.createElement('canvas');
            let width = img.width;
            let height = img.height;
            
            if (width > height) {
              if (width > maxWidth) {
                height = (height * maxWidth) / width;
                width = maxWidth;
              }
            } else {
              if (height > maxHeight) {
                width = (width * maxHeight) / height;
                height = maxHeight;
              }
            }
            
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            
            canvas.toBlob((blob) => {
              if (blob) {
                const reader2 = new FileReader();
                reader2.onloadend = () => resolve(reader2.result);
                reader2.onerror = reject;
                reader2.readAsDataURL(blob);
              } else {
                reject(new Error('Failed to compress image'));
              }
            }, 'image/jpeg', quality);
          };
          img.onerror = reject;
          img.src = e.target.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    };

    try {
      let base64Image = await compressImage(file);
      if (base64Image.length > 5 * 1024 * 1024) {
        base64Image = await compressImage(file, 1280, 1280, 0.6);
      }
      
      await updateProfileImage(familyId, childId, base64Image);
      await loadChildData();
      setShowImagePicker(false);
    } catch (error) {
      alert(t('child.profile.error', { defaultValue: 'שגיאה בעדכון תמונת הפרופיל' }) + ': ' + error.message);
    }
  };

  const handleRemoveImage = async () => {
    try {
      await updateProfileImage(familyId, childId, null);
      await loadChildData();
    } catch (error) {
      alert(t('child.profile.error', { defaultValue: 'שגיאה בהסרת תמונה' }) + ': ' + error.message);
    }
  };

  if (!childData) {
    return (
      <div className="child-view-loading" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div className="loading">{t('common.loading', { defaultValue: 'טוען...' })}</div>
      </div>
    );
  }

  const totalBalance = (childData.balance || 0) + (childData.cashBoxBalance || 0);
  const goalProgress = savingsGoal && savingsGoal.targetAmount > 0
    ? Math.min((totalBalance / savingsGoal.targetAmount) * 100, 100)
    : 0;

  return (
    <div className="child-view" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      {/* Top Profile Section */}
      <div className="child-profile-section">
        <div className="profile-image-container">
          {childData.profileImage ? (
            <img 
              src={childData.profileImage} 
              alt={childData.name}
              className="child-profile-image-large"
            />
          ) : (
            <div className="child-profile-placeholder-large">
              {childData.name.charAt(0).toUpperCase()}
            </div>
          )}
          <button 
            className="camera-icon-button"
            onClick={() => setShowImagePicker(true)}
            title={t('child.profile.changePicture', { defaultValue: 'שנה תמונה' })}
          >
            📷
          </button>
        </div>
        <h1 className="child-greeting">
          {t('child.dashboard.hello', { defaultValue: 'שלום' })}, {childData.name}! 👋
        </h1>
      </div>

      {/* Big Number - Current Balance */}
      <div className="big-balance-display">
        <div className="big-balance-label">{t('child.dashboard.totalBalance', { defaultValue: 'יתרה כוללת' })}</div>
        <div className="big-balance-value">₪{totalBalance.toFixed(2)}</div>
        <div className="balance-breakdown">
          <span className="balance-item">
            {t('child.dashboard.balance', { defaultValue: 'יתרה' })}: ₪{(childData.balance || 0).toFixed(2)}
          </span>
          <span className="balance-item">
            {t('child.dashboard.cashBox', { defaultValue: 'קופה' })}: ₪{(childData.cashBoxBalance || 0).toFixed(2)}
          </span>
        </div>
      </div>

      {/* Savings Goal Tracker */}
      <div className="savings-goal-section">
        <div className="savings-goal-header">
          <h2>{t('child.savingsGoal.title', { defaultValue: 'מטרת חיסכון' })}</h2>
          {savingsGoal ? (
            <div className="goal-actions">
              <button 
                className="edit-goal-button"
                onClick={() => {
                  setEditingGoal(true);
                  setShowGoalModal(true);
                }}
              >
                {t('child.savingsGoal.editGoal', { defaultValue: 'ערוך מטרה' })}
              </button>
              <button 
                className="delete-goal-button"
                onClick={handleDeleteGoal}
              >
                {t('common.delete', { defaultValue: 'מחק' })}
              </button>
            </div>
          ) : (
            <button 
              className="set-goal-button"
              onClick={() => {
                setEditingGoal(false);
                setShowGoalModal(true);
              }}
            >
              {t('child.savingsGoal.setGoal', { defaultValue: 'הגדר מטרת חיסכון' })}
            </button>
          )}
        </div>

        {savingsGoal ? (
          <div className="savings-goal-display">
            <div className="goal-title">{savingsGoal.name}</div>
            <div className="goal-progress-bar-large">
              <div 
                className="goal-progress-fill-large"
                style={{ width: `${goalProgress}%` }}
              />
            </div>
            <div className="goal-progress-text">
              {goalProgress.toFixed(0)}% {t('child.savingsGoal.achieved', { defaultValue: 'הושג' })} - 
              ₪{totalBalance.toFixed(2)} {t('child.savingsGoal.of', { defaultValue: 'מתוך' })} ₪{savingsGoal.targetAmount.toFixed(2)}
            </div>
          </div>
        ) : (
          <div className="no-goal-message">
            {t('child.savingsGoal.noGoal', { defaultValue: 'אין מטרת חיסכון' })}
          </div>
        )}
      </div>

      {/* Expenses Distribution Chart */}
      <div className="expenses-chart-section">
        <div className="expenses-chart-header">
          <h2>{t('child.expenses.title', { defaultValue: 'התפלגות הוצאות' })}</h2>
          <div className="period-toggle">
            <button
              className={`period-button ${expensesPeriod === 'week' ? 'active' : ''}`}
              onClick={() => setExpensesPeriod('week')}
            >
              {t('child.expenses.week', { defaultValue: 'שבוע אחרון' })}
            </button>
            <button
              className={`period-button ${expensesPeriod === 'month' ? 'active' : ''}`}
              onClick={() => setExpensesPeriod('month')}
            >
              {t('child.expenses.month', { defaultValue: 'חודש אחרון' })}
            </button>
          </div>
        </div>
        {loadingExpenses ? (
          <div className="chart-loading">
            {t('common.loading', { defaultValue: 'טוען...' })}
          </div>
        ) : (
          <ExpensePieChart
            expensesByCategory={expensesByCategory}
            title={expensesPeriod === 'week' 
              ? t('child.expenses.week', { defaultValue: 'הוצאות - שבוע אחרון' })
              : t('child.expenses.month', { defaultValue: 'הוצאות - חודש אחרון' })
            }
            days={expensesPeriod === 'week' ? 7 : 30}
          />
        )}
      </div>

      {/* My History */}
      <div className="child-history-section">
        <h2>{t('child.history.title', { defaultValue: 'ההיסטוריה שלי' })}</h2>
        {transactions.length === 0 ? (
          <div className="no-transactions-message">
            {t('child.history.noTransactions', { defaultValue: 'אין עסקאות' })}
          </div>
        ) : (
          <div className="transactions-list-simple">
            {transactions.map((transaction, index) => (
              <div key={index} className={`transaction-item-simple ${transaction.type === 'deposit' ? 'positive' : 'negative'}`}>
                <div className="transaction-main-simple">
                  <span className="transaction-description-simple">
                    {transaction.description || transaction.category || t('child.history.transaction', { defaultValue: 'עסקה' })}
                  </span>
                  <span className="transaction-amount-simple">
                    {transaction.type === 'deposit' ? '+' : '-'}₪{Math.abs(transaction.amount || 0).toFixed(2)}
                  </span>
                </div>
                {transaction.date && (
                  <div className="transaction-date-simple">
                    {new Date(transaction.date).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US')}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Goal Modal */}
      {showGoalModal && (
        <div className="modal-overlay" onClick={() => setShowGoalModal(false)}>
          <div className="modal-content goal-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                {editingGoal 
                  ? t('child.savingsGoal.editGoal', { defaultValue: 'ערוך מטרת חיסכון' })
                  : t('child.savingsGoal.setGoal', { defaultValue: 'הגדר מטרת חיסכון' })
                }
              </h2>
              <button className="modal-close" onClick={() => setShowGoalModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>{t('child.savingsGoal.goalName', { defaultValue: 'שם המטרה' })}:</label>
                <input
                  type="text"
                  value={goalName}
                  onChange={(e) => setGoalName(e.target.value)}
                  placeholder={t('child.savingsGoal.goalNamePlaceholder', { defaultValue: 'לדוגמה: סט לגו חדש' })}
                />
              </div>
              <div className="form-group">
                <label>{t('child.savingsGoal.targetAmount', { defaultValue: 'סכום יעד' })} (₪):</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={goalAmount}
                  onChange={(e) => setGoalAmount(e.target.value)}
                  placeholder="0.00"
                />
              </div>
            </div>
            <div className="modal-actions">
              <button className="cancel-button" onClick={() => setShowGoalModal(false)}>
                {t('common.cancel', { defaultValue: 'ביטול' })}
              </button>
              <button className="submit-button" onClick={handleSaveGoal}>
                {t('common.save', { defaultValue: 'שמור' })}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Image Picker Modal */}
      {showImagePicker && (
        <div className="modal-overlay" onClick={() => setShowImagePicker(false)}>
          <div className="modal-content image-picker-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('child.profile.changePicture', { defaultValue: 'שנה תמונת פרופיל' })}</h2>
              <button className="modal-close" onClick={() => setShowImagePicker(false)}>✕</button>
            </div>
            <div className="modal-body">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handleImageUpload(file);
                  }
                }}
              />
              <div className="image-picker-actions">
                <button 
                  className="upload-button"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {t('child.profile.upload', { defaultValue: 'העלה תמונה' })}
                </button>
                {childData.profileImage && (
                  <button 
                    className="remove-button"
                    onClick={handleRemoveImage}
                  >
                    {t('child.profile.remove', { defaultValue: 'הסר תמונה' })}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChildView;
