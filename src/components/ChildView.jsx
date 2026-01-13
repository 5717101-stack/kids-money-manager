import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { getChild, getChildTransactions, updateCashBoxBalance, getSavingsGoal, updateSavingsGoal, deleteSavingsGoal, updateProfileImage, getExpensesByCategory, addTransaction, getCategories, getTasks, requestTaskPayment } from '../utils/api';
// Camera is imported dynamically when needed
import { smartCompressImage } from '../utils/imageCompression';
import { getCached, setCached } from '../utils/cache';
import ExpensePieChart from './ExpensePieChart';
import Guide from './Guide';

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
  const [filteredCategory, setFilteredCategory] = useState(null); // Category to filter transactions
  const [historyLimit, setHistoryLimit] = useState(() => {
    // Load from localStorage or default to 5
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('childHistoryLimit');
      if (saved === 'all') return null;
      return saved ? parseInt(saved, 10) : 5;
    }
    return 5;
  });
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
  const [calculatorFromTransaction, setCalculatorFromTransaction] = useState(false); // Track if calculator opened from transaction modal
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showGuide, setShowGuide] = useState(false);
  const [chartReloadKey, setChartReloadKey] = useState(0);
  const [tasks, setTasks] = useState([]);
  const [showTasksList, setShowTasksList] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [taskNote, setTaskNote] = useState('');
  const [taskImage, setTaskImage] = useState(null);
  const [submittingTaskRequest, setSubmittingTaskRequest] = useState(false);

  useEffect(() => {
    // Reset loading and error when childId or familyId changes
    setLoading(true);
    setError(null);
    setChildData(null);
    
    // Load data
    const loadData = async () => {
      if (!familyId || !childId) {
        setLoading(false);
        return;
      }
      
      try {
        // Load child data and transactions in parallel
        // Load more transactions if limit is null (all) or if limit is higher
        const transactionLimit = historyLimit === null ? 50 : Math.max(historyLimit, 10);
        const [child, trans, goal, tasksData] = await Promise.all([
          getChild(familyId, childId),
          getChildTransactions(familyId, childId, transactionLimit),
          getSavingsGoal(familyId, childId),
          getTasks(familyId).catch(() => [])
        ]);
        
        if (child) {
          // Load ALL transactions (no limit) to calculate totalInterestEarned accurately
          const allTrans = await getChildTransactions(familyId, childId, null);
          
          // Calculate totalInterestEarned from ALL transactions
          // IMPORTANT: Only count transactions with id starting with "interest_" to prevent manipulation
          // Real interest transactions are created by the server with id format: "interest_${Date.now()}_${child._id}"
          const interestTransactions = (allTrans || []).filter(t => 
            t && t.id && typeof t.id === 'string' && t.id.startsWith('interest_')
          );
          
          if (interestTransactions.length > 0) {
            const calculatedTotal = interestTransactions.reduce((sum, t) => sum + (t.amount || 0), 0);
            // Always use calculated value if we have interest transactions
            child.totalInterestEarned = calculatedTotal;
            console.log(`[CHILD-VIEW-INIT] Calculated totalInterestEarned: ${calculatedTotal.toFixed(2)} from ${interestTransactions.length} interest transactions`);
            console.log(`[CHILD-VIEW-INIT] Interest transactions:`, interestTransactions.map(t => ({ desc: t.description, amount: t.amount })));
          } else {
            console.log(`[CHILD-VIEW-INIT] No interest transactions found. Total transactions: ${allTrans.length}`);
          }
          
          setChildData(child);
          setTransactions(trans);
          setError(null);
        } else {
          setError(t('child.dashboard.childNotFound', { defaultValue: 'Child not found' }));
        }
        
        setSavingsGoal(goal);
        if (goal) {
          setGoalName(goal.name || '');
          setGoalAmount(goal.targetAmount?.toString() || '');
        }
        
        // Filter tasks active for this child
        const activeTasks = (tasksData || []).filter(task => 
          (task.activeFor || []).includes(childId)
        );
        setTasks(activeTasks);
      } catch (err) {
        console.error('Error loading child data:', err);
        setError(err.message || t('child.dashboard.loadError', { defaultValue: 'Error loading data' }));
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
    
    // Check if guide should be shown on first visit
    if (!localStorage.getItem('guideSeen_child')) {
      setShowGuide(true);
    }
    
    // Refresh every 15 seconds to show updated balance (reduced frequency for better performance)
    const interval = setInterval(() => {
      if (familyId && childId && !loading) {
        loadChildData();
        loadSavingsGoal();
        // Don't reload expenses chart automatically - only when period changes
      }
    }, 15000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [childId, familyId, historyLimit]);

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

  const loadChildData = useCallback(async () => {
    if (!familyId || !childId) return;
    try {
      const child = await getChild(familyId, childId);
      if (child) {
        // Load transactions based on limit for display
        const transactionLimit = historyLimit === null ? 50 : Math.max(historyLimit, 10);
        const trans = await getChildTransactions(familyId, childId, transactionLimit);
        setTransactions(trans);
        
        // Load ALL transactions (no limit) to calculate totalInterestEarned accurately
        const allTrans = await getChildTransactions(familyId, childId, null);
        
        // Calculate totalInterestEarned from ALL transactions
        // IMPORTANT: Only count transactions with id starting with "interest_" to prevent manipulation
        // Real interest transactions are created by the server with id format: "interest_${Date.now()}_${child._id}"
        const interestTransactions = (allTrans || []).filter(t => 
          t && t.id && typeof t.id === 'string' && t.id.startsWith('interest_')
        );
        
        if (interestTransactions.length > 0) {
          const calculatedTotal = interestTransactions.reduce((sum, t) => sum + (t.amount || 0), 0);
          // Always use calculated value if we have interest transactions
          child.totalInterestEarned = calculatedTotal;
          console.log(`[CHILD-VIEW] Calculated totalInterestEarned: ${calculatedTotal.toFixed(2)} from ${interestTransactions.length} interest transactions`);
          console.log(`[CHILD-VIEW] Interest transactions:`, interestTransactions.map(t => ({ desc: t.description, amount: t.amount })));
        } else {
          console.log(`[CHILD-VIEW] No interest transactions found. Total transactions: ${allTrans.length}`);
        }
        
        setChildData(child);
        setError(null);
      } else {
        setError(t('child.dashboard.childNotFound', { defaultValue: 'Child not found' }));
      }
    } catch (error) {
      console.error('Error loading child data:', error);
      setError(error.message || t('child.dashboard.loadError', { defaultValue: 'Error loading child data' }));
      throw error; // Re-throw to be caught by useEffect
    }
  }, [familyId, childId, historyLimit, t]);

  const loadSavingsGoal = useCallback(async () => {
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
  }, [familyId, childId]);

  const lastChartReloadKeyRef = useRef(chartReloadKey);
  
  const loadExpensesByCategory = async () => {
    if (!familyId || !childId) return;
    
    const days = expensesPeriod === 'week' ? 7 : 30;
    const cacheKey = `expenses_by_category_${familyId}_${childId}_${days}`;
    const cacheTTL = 10 * 60 * 1000; // 10 minutes cache
    
    // Check if we need to reload (chartReloadKey changed means new expense was added)
    const chartReloadChanged = lastChartReloadKeyRef.current !== chartReloadKey;
    
    // Check cache first (unless force reload)
    if (!chartReloadChanged) {
      const cached = getCached(cacheKey, cacheTTL);
      if (cached !== null) {
        setExpensesByCategory(cached);
        setLoadingExpenses(false);
        return;
      }
    }
    
    // Update ref
    lastChartReloadKeyRef.current = chartReloadKey;
    
    try {
      setLoadingExpenses(true);
      const expenses = await getExpensesByCategory(familyId, childId, days);
      setExpensesByCategory(expenses || []);
      
      // Cache the result
      setCached(cacheKey, expenses || [], cacheTTL);
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
      alert(t('child.dashboard.error', { defaultValue: 'Error updating cash box balance' }) + ': ' + error.message);
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
      alert(t('child.savingsGoal.error', { defaultValue: 'Error saving goal' }) + ': ' + error.message);
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
      alert(t('child.savingsGoal.errorDeleting', { defaultValue: 'Error deleting goal' }) + ': ' + error.message);
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
        throw new Error(t('child.profile.errorImageTooLarge', { defaultValue: 'Image is too large even after compression. Please select a smaller image.' }));
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
      alert(t('child.profile.errorRemoving', { defaultValue: 'Error removing image' }) + ': ' + error.message);
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
    // If there are active tasks, show tasks list instead of calculator
    if (tasks.length > 0) {
      setShowTasksList(true);
      return;
    }
    // Otherwise, show calculator as before
    setShowCalculator(true);
    setCalculatorValue('0');
    setCalculatorHistory('');
    setCalculatorResult(null);
    setCalculatorFromTransaction(false); // Main calculator, not from transaction modal
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
    // If current value is "0" and user enters a number, replace "0" instead of appending
    if (calculatorHistory === '' || ['+', '-', '*', '/', '×'].includes(calculatorHistory.slice(-1))) {
      // Starting a new number - if current value is "0", replace it
      if (calculatorValue === '0' && /[0-9]/.test(value)) {
        setCalculatorHistory(value);
        setCalculatorValue(value);
      } else {
        setCalculatorHistory(calculatorHistory + value);
        setCalculatorValue(value);
      }
    } else {
      // Continuing a number
      // Check if the displayed value is "0" - if so, replace it
      if (calculatorValue === '0' && /[0-9]/.test(value)) {
        // Find where the current number starts and replace it
        const lastNumberMatch = calculatorHistory.match(/[\d.]+$/);
        if (lastNumberMatch && lastNumberMatch[0] === '0') {
          const newHistory = calculatorHistory.slice(0, -1) + value;
          setCalculatorHistory(newHistory);
          setCalculatorValue(value);
        } else {
          const newHistory = calculatorHistory + value;
          setCalculatorHistory(newHistory);
          setCalculatorValue(newHistory.match(/[\d.]+$/)?.[0] || value);
        }
      } else {
        const newHistory = calculatorHistory + value;
        setCalculatorHistory(newHistory);
        setCalculatorValue(newHistory.match(/[\d.]+$/)?.[0] || value);
      }
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
      const amount = parseFloat(transactionAmount);
      const currentCashBox = childData?.cashBoxBalance || 0;
      
      // Update cashBoxBalance based on transaction type
      // Deposit adds to cash box, expense subtracts from cash box
      const newCashBoxBalance = transactionType === 'deposit' 
        ? currentCashBox + amount 
        : Math.max(0, currentCashBox - amount);
      
      // Update cash box balance
      await updateCashBoxBalance(familyId, childId, newCashBoxBalance);
      
      // Also add transaction to history (for display purposes)
      const category = transactionType === 'expense' ? transactionCategory : null;
      await addTransaction(familyId, childId, transactionType, transactionAmount, transactionDescription, category);
      
      // Reset form
      setTransactionAmount('');
      setTransactionDescription('');
      setTransactionCategory('');
      setShowTransactionModal(false);
      
      // Reload data to show updated balance
      await loadChildData();
      // Only reload expenses chart if it was an expense
      if (transactionType === 'expense') {
        setChartReloadKey(prev => prev + 1);
      }
    } catch (error) {
      alert(t('parent.dashboard.error', { defaultValue: 'שגיאה' }) + ': ' + error.message);
    } finally {
      setSubmittingTransaction(false);
    }
  };

  // Memoize calculations to avoid unnecessary recalculations
  // IMPORTANT: All hooks must be called before any early returns
  const totalBalance = useMemo(() => {
    return (childData?.balance || 0) + (childData?.cashBoxBalance || 0);
  }, [childData?.balance, childData?.cashBoxBalance]);
  
  const goalProgress = useMemo(() => {
    if (!savingsGoal || !savingsGoal.targetAmount || savingsGoal.targetAmount <= 0) return 0;
    return Math.min((totalBalance / savingsGoal.targetAmount) * 100, 100);
  }, [savingsGoal, totalBalance]);

  // Check if user is a parent (logged in as parent)
  const isParent = typeof window !== 'undefined' && localStorage.getItem('parentLoggedIn') === 'true';

  // Show loading state
  if (loading) {
    return (
      <div className="child-view-loading" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '60px 20px',
          gap: '20px'
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
            {t('common.loading', { defaultValue: 'טוען...' })}
          </div>
        </div>
      </div>
    );
  }
  
  // Show error state
  if (error && !childData) {
    return (
      <div className="app-layout" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div className="app-header">
          {isParent && onBackToParent && (
            <button 
              className="menu-btn"
              onClick={onBackToParent}
              title={t('child.dashboard.backToParent', { defaultValue: 'חזור לממשק הורים' })}
              style={{ 
                fontSize: '20px',
                position: 'absolute',
                [i18n.language === 'he' ? 'right' : 'left']: '20px',
                transform: i18n.language === 'he' ? 'scaleX(-1)' : 'none' // Flip arrow for RTL
              }}
            >
              ←
            </button>
          )}
          <h1 className="header-title">{t('child.dashboard.error', { defaultValue: 'Error' })}</h1>
          <div style={{ width: '44px' }}></div>
        </div>
        <div className="content-area" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '40px' }}>
          <div className="fintech-card" style={{ textAlign: 'center', maxWidth: '400px' }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>⚠️</div>
            <h2 style={{ marginBottom: '16px' }}>{error}</h2>
            <button
              onClick={() => {
                setLoading(true);
                setError(null);
                loadChildData();
                loadSavingsGoal();
              }}
              style={{
                padding: '12px 24px',
                borderRadius: '12px',
                background: 'var(--primary-gradient)',
                color: 'white',
                border: 'none',
                fontSize: '16px',
                fontWeight: 600,
                cursor: 'pointer',
                marginTop: '20px'
              }}
            >
              {t('common.retry', { defaultValue: 'נסה שוב' })}
            </button>
            {isParent && onBackToParent && (
              <button
                onClick={onBackToParent}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  background: 'transparent',
                  color: 'var(--text-main)',
                  border: '1px solid rgba(0,0,0,0.1)',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  marginTop: '12px'
                }}
              >
                {t('child.dashboard.backToParent', { defaultValue: 'חזור לממשק הורים' })}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }
  
  // If no child data after loading, show error
  if (!childData) {
    return (
      <div className="child-view-loading" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '60px 20px',
          gap: '20px'
        }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '16px', fontWeight: 500 }}>
            {t('child.dashboard.noData', { defaultValue: 'אין נתונים' })}
          </div>
        </div>
      </div>
    );
  }

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
            style={{ 
              fontSize: '20px',
              position: 'absolute',
              [i18n.language === 'he' ? 'right' : 'left']: '20px',
              transform: i18n.language === 'he' ? 'scaleX(-1)' : 'none' // Flip arrow for RTL
            }}
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
      
      <div className="content-area" style={{ flex: 1, overflowY: 'auto', paddingBottom: 'calc(90px + env(safe-area-inset-bottom))', minHeight: 0 }}>
      {/* Profile Image Section */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px', paddingTop: '10px' }}>
        <div style={{ position: 'relative' }}>
          {childData?.profileImage ? (
            <img 
              src={childData.profileImage} 
              alt={childData.name}
              loading="lazy"
              decoding="async"
              style={{
                width: '120px',
                height: '120px',
                borderRadius: '50%',
                objectFit: 'cover',
                border: '4px solid white',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
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
              {childData?.name?.charAt(0)?.toUpperCase() || '?'}
            </div>
          )}
          <button
            onClick={() => {
              if (childData?.profileImage) {
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
            title={childData?.profileImage ? t('child.profile.changePicture', { defaultValue: 'שנה תמונה' }) : t('child.profile.upload', { defaultValue: 'העלה תמונה' })}
          >
            {childData?.profileImage ? '✏️' : '+'}
          </button>
        </div>
      </div>

      {/* Total Balance Card - Redesigned */}
      <div className="fintech-card">
        <div className="label-text" style={{ marginBottom: '8px' }}>{t('child.dashboard.totalBalance', { defaultValue: 'יתרה כוללת' })}</div>
        <div className="big-balance" style={{ marginBottom: '16px' }}>₪{totalBalance.toFixed(2)}</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: 'var(--text-muted)', paddingTop: '12px', borderTop: '1px solid rgba(0,0,0,0.1)' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '12px', marginBottom: '4px' }}>{t('child.dashboard.balanceWithParents', { defaultValue: 'יתרה אצל ההורים' })}</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-main)' }}>₪{(childData?.balance || 0).toFixed(2)}</div>
            <div style={{
              marginTop: '12px',
              padding: '14px 16px',
              borderRadius: '12px',
              background: (childData?.totalInterestEarned && childData.totalInterestEarned > 0) 
                ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(16, 185, 129, 0.1) 100%)' 
                : 'linear-gradient(135deg, rgba(107, 114, 128, 0.15) 0%, rgba(107, 114, 128, 0.08) 100%)',
              color: (childData?.totalInterestEarned && childData.totalInterestEarned > 0) ? '#10B981' : 'var(--text-muted)',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              border: (childData?.totalInterestEarned && childData.totalInterestEarned > 0) 
                ? '2px solid rgba(16, 185, 129, 0.4)' 
                : '2px solid rgba(107, 114, 128, 0.25)',
              boxShadow: (childData?.totalInterestEarned && childData.totalInterestEarned > 0)
                ? '0 2px 8px rgba(16, 185, 129, 0.15)'
                : '0 2px 4px rgba(0, 0, 0, 0.05)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '22px' }}>💰</span>
                <span style={{ fontSize: '14px' }}>{t('child.dashboard.interestEarned', { defaultValue: 'ריבית נצברה:' })}</span>
              </div>
              <span style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '0.5px' }}>
                ₪{(childData?.totalInterestEarned || 0).toFixed(2)}
              </span>
            </div>
          </div>
          <div style={{ textAlign: 'right', flex: 1 }}>
            <div style={{ fontSize: '12px', marginBottom: '4px' }}>{t('child.dashboard.cashBoxBalance', { defaultValue: 'יתרה בקופה' })}</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-main)' }}>₪{(childData?.cashBoxBalance || 0).toFixed(2)}</div>
          </div>
        </div>
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
          <div className="savings-goal-display-compact">
            <div className="goal-main-info">
              <div className="goal-name-compact">{savingsGoal.name}</div>
              <div className="goal-target-prominent">
                <span className="goal-target-label">{t('child.savingsGoal.target', { defaultValue: 'יעד' })}:</span>
                <span className="goal-target-amount">₪{savingsGoal.targetAmount.toFixed(2)}</span>
              </div>
            </div>
            <div className="linear-progress-container-compact">
              <div 
                className="linear-progress-bar"
                style={{ width: `${goalProgress}%` }}
              />
            </div>
            <div className="goal-progress-info">
              <div className="goal-progress-text">
                <span className="goal-progress-percentage-compact">{goalProgress.toFixed(0)}%</span>
                <span className="goal-progress-details">
                  {t('child.savingsGoal.saved', { defaultValue: 'נחסך' })}: ₪{totalBalance.toFixed(2)} • {t('child.savingsGoal.missing', { defaultValue: 'חסר' })}: ₪{Math.max(0, savingsGoal.targetAmount - totalBalance).toFixed(2)}
                </span>
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
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '40px 20px',
            gap: '16px'
          }}>
            <div style={{
              width: '40px',
              height: '40px',
              border: '4px solid rgba(99, 102, 241, 0.2)',
              borderTopColor: '#6366F1',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }}></div>
            <div style={{ color: 'var(--text-muted)', fontSize: '14px', fontWeight: 500 }}>
              {t('common.loading', { defaultValue: 'טוען...' })}
            </div>
          </div>
        ) : expensesByCategory && expensesByCategory.length > 0 ? (
          <ExpensePieChart
            expensesByCategory={expensesByCategory}
            title={t('child.expenses.chartTitle', { 
              period: expensesPeriod === 'week' 
                ? t('child.expenses.week', { defaultValue: 'Last Week' })
                : t('child.expenses.month', { defaultValue: 'Last Month' }),
              defaultValue: 'Expenses - {period}'
            })}
            days={expensesPeriod === 'week' ? 7 : 30}
            onCategorySelect={setFilteredCategory}
            selectedCategory={filteredCategory}
          />
        ) : (
          <div className="no-expenses-message">
            {t('child.expenses.noExpenses', { defaultValue: 'אין הוצאות בתקופה זו' })}
          </div>
        )}
      </div>

      {/* My History - Scrollable */}
      <div className="fintech-card history-card">
        <div className="history-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <h2>{t('child.history.title', { defaultValue: 'ההיסטוריה שלי' })}</h2>
          <div className="activity-limit-selector">
            <button
              className={`activity-limit-btn ${historyLimit === 5 ? 'active' : ''}`}
              onClick={() => {
                setHistoryLimit(5);
                localStorage.setItem('childHistoryLimit', '5');
                loadChildData();
              }}
            >
              5
            </button>
            <button
              className={`activity-limit-btn ${historyLimit === 20 ? 'active' : ''}`}
              onClick={() => {
                setHistoryLimit(20);
                localStorage.setItem('childHistoryLimit', '20');
                loadChildData();
              }}
            >
              20
            </button>
            <button
              className={`activity-limit-btn ${historyLimit === null ? 'active' : ''}`}
              onClick={() => {
                setHistoryLimit(null);
                localStorage.setItem('childHistoryLimit', 'all');
                loadChildData();
              }}
            >
              {t('parent.dashboard.all', { defaultValue: 'הכל' })}
            </button>
          </div>
        </div>
        <div className="history-content">
          {(() => {
            const filtered = filteredCategory 
              ? transactions.filter(t => t.category === filteredCategory)
              : transactions;
            
            // Apply limit if not null
            const limited = historyLimit === null ? filtered : filtered.slice(0, historyLimit);
            
            if (limited.length === 0) {
              return (
                <div className="no-transactions-message">
                  {filteredCategory 
                    ? t('child.history.noTransactionsForCategory', { category: filteredCategory }).replace('{category}', filteredCategory)
                    : t('child.history.noTransactions', { defaultValue: 'אין עסקאות' })
                  }
                </div>
              );
            }
            
            return (
              <div className="transactions-list-container">
                {limited.map((transaction, index) => (
                  <div key={index} className={`transaction-item ${transaction.type === 'deposit' ? 'positive' : 'negative'}`}>
                    <div className="transaction-icon">
                      {transaction.type === 'deposit' ? '📈' : '📉'}
                    </div>
                    <div className="transaction-details">
                      <div className="transaction-main">
                        <span className="transaction-description">
                          {transaction.description || transaction.category || t('child.history.transaction', { defaultValue: 'עסקה' })}
                        </span>
                        <span className={`transaction-amount ${transaction.type === 'deposit' ? 'positive' : 'negative'}`}>
                          {transaction.type === 'deposit' ? '+' : '-'}₪{Math.abs(transaction.amount || 0).toFixed(2)}
                        </span>
                      </div>
                      {transaction.date && (
                        <div className="transaction-date">
                          {new Date(transaction.date).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US', { 
                            day: '2-digit', 
                            month: '2-digit', 
                            year: 'numeric' 
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
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
      {showImagePicker && childData?.profileImage && (
        <div className="modal-overlay" onClick={() => setShowImagePicker(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('child.profile.changePicture', { defaultValue: 'שנה תמונה' })}</h2>
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

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;

          try {
            // Compress image before upload
            const base64Image = await smartCompressImage(file);
            
            try {
              await updateProfileImage(familyId, childId, base64Image);
              await loadChildData();
            } catch (error) {
              alert(t('child.profile.error', { defaultValue: 'שגיאה בעדכון תמונת הפרופיל' }) + ': ' + error.message);
            }
          } catch (error) {
            alert(t('child.profile.error', { defaultValue: 'שגיאה בעדכון תמונת הפרופיל' }) + ': ' + error.message);
          }
          
          // Reset file input so same file can be selected again
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        }}
      />

      {/* Calculator Overlay */}
      {showCalculator && (
        <div className="calculator-overlay" onClick={() => setShowCalculator(false)}>
          <div className="calculator-modal" onClick={(e) => e.stopPropagation()} dir="ltr">
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
            {calculatorResult !== null && calculatorFromTransaction && (
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
                      const initialValue = transactionAmount || '0';
                      setCalculatorValue(initialValue);
                      setCalculatorHistory(initialValue);
                      setCalculatorResult(null);
                      setCalculatorFromTransaction(true); // Mark that calculator opened from transaction modal
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
                <label>{t('parent.dashboard.description', { defaultValue: 'תיאור' })} ({t('common.optional', { defaultValue: 'אופציונלי' })}):</label>
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
        {/* Left: Income (Deposit) - affects cash box */}
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
          <span>{t('child.dashboard.addIncome', { defaultValue: 'הכנסה' })}</span>
        </button>
        
        {/* Center: Calculator or Tasks */}
        <button 
          className="fab-btn"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleCalculatorClick();
          }}
          type="button"
        >
          {tasks.length > 0 ? '✅' : '🧮'}
        </button>
        
        {/* Right: Expense - affects cash box */}
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
          <span>{t('child.dashboard.recordExpense', { defaultValue: 'הוצאה' })}</span>
        </button>
      </div>

      {/* Tasks List Modal */}
      {showTasksList && !selectedTask && (
        <div className="calculator-overlay" onClick={() => setShowTasksList(false)}>
          <div className="calculator-modal" onClick={(e) => e.stopPropagation()} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
            <div className="calculator-header">
              <h2>{t('child.dashboard.tasks', { defaultValue: 'מטלות' })}</h2>
              <button 
                className="calculator-close" 
                onClick={() => setShowTasksList(false)}
              >
                ✕
              </button>
            </div>
            <div style={{ padding: '20px', maxHeight: '60vh', overflowY: 'auto' }}>
              {tasks.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  {t('child.dashboard.noTasks', { defaultValue: 'אין מטלות פעילות' })}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {tasks.map(task => (
                    <button
                      key={task._id}
                      onClick={() => {
                        setSelectedTask(task);
                        setTaskNote('');
                        setTaskImage(null);
                      }}
                      style={{
                        padding: '16px',
                        background: 'white',
                        borderRadius: '12px',
                        border: '2px solid var(--primary)',
                        textAlign: 'right',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '16px', fontWeight: 600 }}>{task.name}</div>
                        <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                          {t('child.dashboard.payment', { defaultValue: 'תשלום' })}: ₪{task.price.toFixed(2)}
                        </div>
                      </div>
                      <span style={{ fontSize: '20px' }}>→</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Task Request Modal */}
      {selectedTask && (
        <div className="calculator-overlay" onClick={() => {
          setSelectedTask(null);
          setTaskNote('');
          setTaskImage(null);
        }}>
          <div className="calculator-modal" onClick={(e) => e.stopPropagation()} dir={i18n.language === 'he' ? 'rtl' : 'ltr'} style={{ maxWidth: '500px' }}>
            <div className="calculator-header">
              <h2>{selectedTask.name}</h2>
              <button 
                className="calculator-close" 
                onClick={() => {
                  setSelectedTask(null);
                  setTaskNote('');
                  setTaskImage(null);
                }}
              >
                ✕
              </button>
            </div>
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  {t('child.dashboard.payment', { defaultValue: 'תשלום' })}
                </div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--primary)' }}>
                  ₪{selectedTask.price.toFixed(2)}
                </div>
              </div>
              
              <div>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
                  {t('child.dashboard.note', { defaultValue: 'הערה (אופציונלי)' })}
                </label>
                <textarea
                  value={taskNote}
                  onChange={(e) => setTaskNote(e.target.value)}
                  placeholder={t('child.dashboard.notePlaceholder', { defaultValue: 'הוסף הערה...' })}
                  style={{
                    width: '100%',
                    minHeight: '80px',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid rgba(0,0,0,0.1)',
                    fontSize: '14px',
                    fontFamily: 'inherit',
                    resize: 'vertical',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
                  {t('child.dashboard.image', { defaultValue: 'תמונה (אופציונלי)' })}
                </label>
                {taskImage ? (
                  <div style={{ position: 'relative' }}>
                    <img 
                      src={taskImage} 
                      alt="Task" 
                      style={{
                        width: '100%',
                        maxHeight: '200px',
                        borderRadius: '8px',
                        objectFit: 'contain'
                      }}
                    />
                    <button
                      onClick={async () => {
                        try {
                          const { Camera } = await import('@capacitor/camera');
                          
                          // Check permissions first
                          const permissions = await Camera.checkPermissions();
                          if (permissions.camera !== 'granted') {
                            const requestResult = await Camera.requestPermissions();
                            if (requestResult.camera !== 'granted') {
                              alert(t('child.dashboard.cameraPermissionDenied', { defaultValue: 'נדרשת הרשאה לגישה למצלמה' }));
                              return;
                            }
                          }
                          
                          const image = await Camera.getPhoto({
                            quality: 90,
                            allowEditing: false,
                            source: 'CAMERA',
                            resultType: 'base64'
                          });
                          if (image.base64String) {
                            setTaskImage(`data:image/${image.format};base64,${image.base64String}`);
                          }
                        } catch (error) {
                          console.error('Error taking photo:', error);
                          const errorMessage = error.message || 'Unknown error';
                          alert(t('child.dashboard.cameraError', { defaultValue: 'שגיאה בצילום תמונה' }) + ': ' + errorMessage);
                        }
                      }}
                      style={{
                        position: 'absolute',
                        top: '8px',
                        right: '8px',
                        padding: '8px',
                        background: 'rgba(0,0,0,0.7)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '50%',
                        cursor: 'pointer',
                        fontSize: '16px'
                      }}
                    >
                      📷
                    </button>
                    <button
                      onClick={() => setTaskImage(null)}
                      style={{
                        position: 'absolute',
                        top: '8px',
                        left: '8px',
                        padding: '8px',
                        background: '#EF4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '50%',
                        cursor: 'pointer',
                        fontSize: '16px'
                      }}
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={async () => {
                      try {
                        const { Camera } = await import('@capacitor/camera');
                        
                        // Check permissions first
                        const permissions = await Camera.checkPermissions();
                        if (permissions.camera !== 'granted') {
                          const requestResult = await Camera.requestPermissions();
                          if (requestResult.camera !== 'granted') {
                            alert(t('child.dashboard.cameraPermissionDenied', { defaultValue: 'נדרשת הרשאה לגישה למצלמה' }));
                            return;
                          }
                        }
                        
                        const image = await Camera.getPhoto({
                          quality: 90,
                          allowEditing: false,
                          source: 'CAMERA',
                          resultType: 'base64'
                        });
                        if (image.base64String) {
                          setTaskImage(`data:image/${image.format};base64,${image.base64String}`);
                        }
                      } catch (error) {
                        console.error('Error taking photo:', error);
                        const errorMessage = error.message || 'Unknown error';
                        alert(t('child.dashboard.cameraError', { defaultValue: 'שגיאה בצילום תמונה' }) + ': ' + errorMessage);
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '40px',
                      background: '#F9FAFB',
                      border: '2px dashed #D1D5DB',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontSize: '16px',
                      color: 'var(--text-muted)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    <span style={{ fontSize: '32px' }}>📷</span>
                    <span>{t('child.dashboard.takePhoto', { defaultValue: 'צלם תמונה' })}</span>
                  </button>
                )}
              </div>

              <button
                onClick={async () => {
                  if (!familyId || !selectedTask || !childId) return;
                  setSubmittingTaskRequest(true);
                  try {
                    await requestTaskPayment(familyId, selectedTask._id, childId, taskNote || null, taskImage || null);
                    setSelectedTask(null);
                    setTaskNote('');
                    setTaskImage(null);
                    setShowTasksList(false);
                    // Show success notification
                    const notification = document.createElement('div');
                    notification.textContent = t('child.dashboard.requestSent', { defaultValue: 'בקשת תשלום נשלחה בהצלחה!' });
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
                    alert(t('child.dashboard.requestError', { defaultValue: 'שגיאה בשליחת בקשה' }) + ': ' + error.message);
                  } finally {
                    setSubmittingTaskRequest(false);
                  }
                }}
                disabled={submittingTaskRequest}
                style={{
                  width: '100%',
                  padding: '16px',
                  background: submittingTaskRequest ? '#ccc' : 'var(--primary-gradient)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: submittingTaskRequest ? 'not-allowed' : 'pointer'
                }}
              >
                {submittingTaskRequest 
                  ? t('common.saving', { defaultValue: 'שולח...' })
                  : t('child.dashboard.sendRequest', { defaultValue: 'שלח בקשת תשלום' })
                }
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Guide Modal */}
      {showGuide && (
        <Guide 
          userType="child" 
          onClose={() => setShowGuide(false)} 
        />
      )}
    </div>
  );
};

export default ChildView;
