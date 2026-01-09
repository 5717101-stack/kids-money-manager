import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getChild, getChildTransactions, updateCashBoxBalance, getSavingsGoal, updateSavingsGoal, deleteSavingsGoal, updateProfileImage, getExpensesByCategory, addTransaction, getCategories } from '../utils/api';
import { smartCompressImage } from '../utils/imageCompression';
import ExpensePieChart from './ExpensePieChart';

const ChildView = ({ childId, familyId, onBackToParent, onLogout }) => {
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
  const [showCalculator, setShowCalculator] = useState(false);
  const [showTransactionModal, setShowTransactionModal] = useState(false);
  const [transactionType, setTransactionType] = useState('deposit'); // 'deposit' or 'expense'
  const [transactionAmount, setTransactionAmount] = useState('');
  const [transactionDescription, setTransactionDescription] = useState('');
  const [transactionCategory, setTransactionCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const [submittingTransaction, setSubmittingTransaction] = useState(false);
  const [calculatorValue, setCalculatorValue] = useState('0');
  const [calculatorHistory, setCalculatorHistory] = useState('');
  const [calculatorResult, setCalculatorResult] = useState(null);

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
      loadCategories();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expensesPeriod, familyId, childId]);

  const loadCategories = async () => {
    if (!familyId) return;
    try {
      const cats = await getCategories(familyId);
      setCategories(cats || []);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

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

    try {
      // Compress image before uploading using smart compression
      console.log('Compressing image, original size:', file.size, 'bytes');
      const base64Image = await smartCompressImage(file);
      console.log('Compressed image size:', base64Image.length, 'bytes');
      
      // Check if compressed image is still too large (max 1MB base64)
      if (base64Image.length > 1024 * 1024) {
        throw new Error(t('child.profile.error', { defaultValue: 'התמונה גדולה מדי גם לאחר דחיסה. אנא בחר תמונה קטנה יותר.' }));
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

  const handleBottomNavAction = (type) => {
    console.log('[ChildView] handleBottomNavAction called with type:', type);
    setTransactionType(type);
    setTransactionAmount('');
    setTransactionDescription('');
    setTransactionCategory('');
    setShowTransactionModal(true);
    console.log('[ChildView] showTransactionModal set to true');
  };

  const handleCalculatorClick = () => {
    console.log('[ChildView] handleCalculatorClick called');
    setShowCalculator(true);
    setCalculatorValue('0');
    setCalculatorHistory('');
    setCalculatorResult(null);
  };

  const handleCalculatorInput = (value) => {
    if (calculatorResult !== null) {
      // If there's a result, start fresh
      setCalculatorValue(value);
      setCalculatorHistory('');
      setCalculatorResult(null);
      return;
    }

    if (value === 'C') {
      setCalculatorValue('0');
      setCalculatorHistory('');
      return;
    }

    if (value === '=') {
      try {
        // Evaluate the expression safely
        // Replace × with * for evaluation
        const expression = calculatorHistory.replace(/×/g, '*');
        // Use Function constructor with strict mode for safe evaluation
        const result = new Function('"use strict"; return (' + expression + ')')();
        const roundedResult = Math.round(result * 100) / 100; // Round to 2 decimal places
        setCalculatorResult(roundedResult);
        setCalculatorValue(roundedResult.toString());
      } catch (error) {
        setCalculatorValue('Error');
        setCalculatorResult(null);
      }
      return;
    }

    if (value === '←') {
      if (calculatorHistory.length > 0) {
        const newHistory = calculatorHistory.slice(0, -1);
        setCalculatorHistory(newHistory);
        setCalculatorValue(newHistory || '0');
      }
      return;
    }

    // Handle operators
    if (['+', '-', '*', '/', '×'].includes(value)) {
      // Replace × with * for internal storage
      const operator = value === '×' ? '*' : value;
      setCalculatorHistory(calculatorHistory + operator);
      setCalculatorValue(value);
      return;
    }

    // Handle numbers and decimal
    if (calculatorHistory === '' || ['+', '-', '*', '/'].includes(calculatorHistory.slice(-1))) {
      setCalculatorHistory(calculatorHistory + value);
      setCalculatorValue(value);
    } else {
      const newHistory = calculatorHistory + value;
      setCalculatorHistory(newHistory);
      setCalculatorValue(newHistory.match(/[\d.]+$/)?.[0] || value);
    }
  };

  const useCalculatorResult = () => {
    if (calculatorResult !== null) {
      setTransactionAmount(calculatorResult.toString());
      setShowCalculator(false);
    }
  };

  const handleSubmitTransaction = async () => {
    if (!transactionAmount || parseFloat(transactionAmount) <= 0) {
      alert(t('parent.dashboard.invalidAmount', { defaultValue: 'אנא הכנס סכום תקין' }));
      return;
    }

    if (transactionType === 'expense' && categories.length > 0 && !transactionCategory) {
      alert(t('parent.dashboard.selectCategory', { defaultValue: 'אנא בחר קטגוריה' }));
      return;
    }

    try {
      setSubmittingTransaction(true);
      const category = transactionType === 'expense' ? transactionCategory : null;
      await addTransaction(familyId, childId, transactionType, transactionAmount, transactionDescription, category);
      
      // Reset form
      setTransactionAmount('');
      setTransactionDescription('');
      setTransactionCategory('');
      setShowTransactionModal(false);
      
      // Reload data to show updated balance
      await loadChildData();
      await loadExpensesByCategory();
    } catch (error) {
      alert(t('parent.dashboard.error', { defaultValue: 'שגיאה' }) + ': ' + error.message);
    } finally {
      setSubmittingTransaction(false);
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

  // Check if user is a parent (logged in as parent)
  const isParent = typeof window !== 'undefined' && sessionStorage.getItem('parentLoggedIn') === 'true';

  return (
    <div className="app-layout" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="app-header">
        {isParent && onBackToParent && (
          <button 
            className="menu-btn"
            onClick={onBackToParent}
            title={t('child.dashboard.backToParent', { defaultValue: 'חזור לממשק הורים' })}
            aria-label={t('child.dashboard.backToParent', { defaultValue: 'חזור לממשק הורים' })}
          >
            ←
          </button>
        )}
        {!isParent && (
          <div style={{ width: '44px' }}></div>
        )}
        <h1 className="header-title">
          {childData.name}
        </h1>
        {!isParent && onLogout && (
          <button 
            className="menu-btn"
            onClick={onLogout}
            title={t('common.logout', { defaultValue: 'התנתק' })}
          >
            🚪
          </button>
        )}
        {isParent && (
          <div style={{ width: '44px' }}></div>
        )}
      </div>
      
      <div className="content-area" style={{ flex: 1, overflowY: 'auto', paddingBottom: '120px' }}>
      {/* My Balance Card */}
      <div className="fintech-card">
        <div className="label-text">{t('child.dashboard.myBalance', { defaultValue: 'היתרה שלי:' })}</div>
        <div className="big-balance">₪{totalBalance.toFixed(2)}</div>
      </div>

      {/* Savings Goal Tracker */}
      <div className="fintech-card">
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
          <div className="savings-goal-display-circular">
            <div className="circular-progress-container">
              <svg className="circular-progress" viewBox="0 0 200 200">
                <circle
                  className="circular-progress-bg"
                  cx="100"
                  cy="100"
                  r="90"
                  fill="none"
                  stroke="#E5E7EB"
                  strokeWidth="16"
                />
                <circle
                  className="circular-progress-fill"
                  cx="100"
                  cy="100"
                  r="90"
                  fill="none"
                  stroke="#10B981"
                  strokeWidth="16"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 90}`}
                  strokeDashoffset={`${2 * Math.PI * 90 * (1 - goalProgress / 100)}`}
                  transform="rotate(-90 100 100)"
                />
              </svg>
              <div className="circular-progress-content">
                <div className="circular-progress-percentage">{goalProgress.toFixed(0)}%</div>
              </div>
            </div>
            <div className="goal-info">
              <div className="goal-name">{savingsGoal.name}</div>
              <div className="goal-remaining">
                {t('child.savingsGoal.missing', { defaultValue: 'חסר' })}: ₪{Math.max(0, savingsGoal.targetAmount - totalBalance).toFixed(2)}
              </div>
            </div>
          </div>
        ) : (
          <div className="no-goal-message">
            {t('child.savingsGoal.noGoal', { defaultValue: 'אין מטרת חיסכון' })}
          </div>
        )}
      </div>

      {/* Expenses Distribution Chart */}
      <div className="fintech-card">
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
      <div className="fintech-card">
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
                  inputMode="decimal"
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

      {/* Calculator Overlay */}
      {showCalculator && (
        <div className="calculator-overlay" onClick={() => setShowCalculator(false)}>
          <div className="calculator-modal" onClick={(e) => e.stopPropagation()}>
            <div className="calculator-header">
              <h2>{t('child.calculator.title', { defaultValue: 'מחשבון' })}</h2>
              <button 
                className="calculator-close" 
                onClick={() => setShowCalculator(false)}
              >
                ✕
              </button>
            </div>
            <div className="calculator-display">
              <div className="calculator-history">{calculatorHistory || ' '}</div>
              <div className="calculator-value">{calculatorValue}</div>
            </div>
            <div className="calculator-buttons">
              <button className="calc-btn calc-btn-clear" onClick={() => handleCalculatorInput('C')}>C</button>
              <button className="calc-btn calc-btn-operator" onClick={() => handleCalculatorInput('←')}>←</button>
              <button className="calc-btn calc-btn-operator" onClick={() => handleCalculatorInput('/')}>/</button>
              <button className="calc-btn calc-btn-operator" onClick={() => handleCalculatorInput('×')}>×</button>
              
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('7')}>7</button>
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('8')}>8</button>
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('9')}>9</button>
              <button className="calc-btn calc-btn-operator" onClick={() => handleCalculatorInput('-')}>-</button>
              
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('4')}>4</button>
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('5')}>5</button>
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('6')}>6</button>
              <button className="calc-btn calc-btn-operator" onClick={() => handleCalculatorInput('+')}>+</button>
              
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('1')}>1</button>
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('2')}>2</button>
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('3')}>3</button>
              <button className="calc-btn calc-btn-equals" rowSpan="2" onClick={() => handleCalculatorInput('=')}>=</button>
              
              <button className="calc-btn calc-btn-number calc-btn-zero" onClick={() => handleCalculatorInput('0')}>0</button>
              <button className="calc-btn calc-btn-number" onClick={() => handleCalculatorInput('.')}>.</button>
            </div>
            {calculatorResult !== null && (
              <button className="calculator-use-result" onClick={useCalculatorResult}>
                {t('child.calculator.useResult', { defaultValue: 'השתמש בתוצאה' })}: {calculatorResult}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Transaction Modal */}
      {showTransactionModal && (
        <div className="modal-overlay" onClick={() => setShowTransactionModal(false)}>
          <div className="modal-content quick-action-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                {transactionType === 'deposit' 
                  ? t('parent.dashboard.addMoney', { defaultValue: 'הוספת כסף' })
                  : t('parent.dashboard.recordExpense', { defaultValue: 'דיווח הוצאה' })
                }
              </h2>
              <button className="modal-close" onClick={() => setShowTransactionModal(false)}>✕</button>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); handleSubmitTransaction(); }} className="quick-action-form">
              <div className="form-group">
                <label>{t('parent.dashboard.amount', { defaultValue: 'סכום' })} (₪):</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="number"
                    inputMode="decimal"
                    step="0.01"
                    min="0.01"
                    value={transactionAmount}
                    onChange={(e) => setTransactionAmount(e.target.value)}
                    placeholder="0.00"
                    required
                    style={{ flex: 1 }}
                  />
                  <button 
                    type="button"
                    className="calculator-button-small"
                    onClick={() => {
                      setShowCalculator(true);
                      setCalculatorValue(transactionAmount || '0');
                      setCalculatorHistory(transactionAmount || '0');
                      setCalculatorResult(null);
                    }}
                    title={t('child.calculator.title', { defaultValue: 'מחשבון' })}
                  >
                    🧮
                  </button>
                </div>
              </div>

              {transactionType === 'expense' && categories.length > 0 && (
                <div className="form-group">
                  <label>{t('parent.dashboard.category', { defaultValue: 'קטגוריה' })}:</label>
                  <select
                    value={transactionCategory}
                    onChange={(e) => setTransactionCategory(e.target.value)}
                    required
                  >
                    <option value="">{t('parent.dashboard.selectCategory', { defaultValue: 'בחר קטגוריה' })}</option>
                    {categories.map(cat => (
                      <option key={cat._id} value={cat.name}>{cat.name}</option>
                    ))}
                  </select>
                </div>
              )}

              <div className="form-group">
                <label>{t('parent.dashboard.description', { defaultValue: 'תיאור' })} (אופציונלי):</label>
                <input
                  type="text"
                  value={transactionDescription}
                  onChange={(e) => setTransactionDescription(e.target.value)}
                  placeholder={t('parent.dashboard.descriptionPlaceholder', { defaultValue: 'תיאור הפעולה' })}
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="cancel-button" onClick={() => setShowTransactionModal(false)}>
                  {t('common.cancel', { defaultValue: 'ביטול' })}
                </button>
                <button type="submit" className="submit-button" disabled={submittingTransaction}>
                  {submittingTransaction 
                    ? t('common.saving', { defaultValue: 'שומר...' })
                    : t('common.confirm', { defaultValue: 'אישור' })
                  }
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      </div>

      {/* Bottom Navigation Bar - Outside content-area */}
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
            handleCalculatorClick();
          }}
          type="button"
        >
          🧮
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
    </div>
  );
};

export default ChildView;
