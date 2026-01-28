import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { getChild, getChildTransactions, updateCashBoxBalance, getSavingsGoal, updateSavingsGoal, deleteSavingsGoal, updateProfileImage, getExpensesByCategory, addTransaction, getCategories, getTasks, requestTaskPayment } from '../utils/api';
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
  const [uploadingImage, setUploadingImage] = useState(false);
  const fileInputRef = React.useRef(null);
  const [expensesPeriod, setExpensesPeriod] = useState('month'); // 'week' or 'month'
  const [expensesByCategory, setExpensesByCategory] = useState([]);
  const [loadingExpenses, setLoadingExpenses] = useState(false);
  const [chartType, setChartType] = useState('expenses'); // 'expenses' or 'income'
  const [incomeByCategory, setIncomeByCategory] = useState([]);
  const [loadingIncome, setLoadingIncome] = useState(false);
  const [filteredCategory, setFilteredCategory] = useState(null); // Category to filter transactions
  const [filteredChartType, setFilteredChartType] = useState(null); // Track which chart type the filter is from ('expenses' or 'income')
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
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [activeTasks, setActiveTasks] = useState([]);
  const [showTasksList, setShowTasksList] = useState(false);
  const [showTaskRequest, setShowTaskRequest] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [taskNote, setTaskNote] = useState('');
  const [taskImage, setTaskImage] = useState(null);
  const [submittingTaskRequest, setSubmittingTaskRequest] = useState(false);
  const taskImageInputRef = useRef(null);

  // Load active tasks for this child
  const loadActiveTasks = useCallback(async () => {
    if (!familyId || !childId) return;
    try {
      const tasks = await getTasks(familyId);
      // Filter tasks that are active for this child
      const childActiveTasks = (tasks || []).filter(task => 
        task.activeFor && task.activeFor.includes(childId)
      );
      setActiveTasks(childActiveTasks);
    } catch (error) {
      console.error('Error loading active tasks:', error);
      setActiveTasks([]);
    }
  }, [familyId, childId]);

  useEffect(() => {
    loadActiveTasks();
  }, [loadActiveTasks]);

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
        const [child, trans, goal] = await Promise.all([
          getChild(familyId, childId),
          getChildTransactions(familyId, childId, transactionLimit),
          getSavingsGoal(familyId, childId)
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

  // Load expenses/income when period or chart type changes or on initial load
  useEffect(() => {
    if (familyId && childId) {
      if (chartType === 'expenses') {
        loadExpensesByCategory();
      } else {
        loadIncomeByCategory();
      }
      loadCategories();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expensesPeriod, familyId, childId, chartType]);

  const loadCategories = async () => {
    if (!familyId || !childId) return;
    try {
      const cats = await getCategories(familyId);
      // Filter categories that are active for this child
      const activeCategories = (cats || [])
        .filter(cat => (cat.activeFor || []).includes(childId))
        .map(cat => cat.name);
      
      if (activeCategories.length > 0) {
        setCategories(activeCategories);
        // Reset category if current one is not in the active list
        if (transactionCategory && !activeCategories.includes(transactionCategory)) {
          setTransactionCategory('');
        }
      } else {
        // Fallback to default categories if none found
        const defaultCategories = ['משחקים', 'ממתקים', 'בגדים', 'בילויים', 'אחר'];
        setCategories(defaultCategories);
        if (transactionCategory && !defaultCategories.includes(transactionCategory)) {
          setTransactionCategory('');
        }
      }
    } catch (error) {
      console.error('Error loading categories:', error);
      // Fallback to default categories on error
      const defaultCategories = ['משחקים', 'ממתקים', 'בגדים', 'בילויים', 'אחר'];
      setCategories(defaultCategories);
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

  const loadIncomeByCategory = async () => {
    if (!familyId || !childId) return;
    
    const days = expensesPeriod === 'week' ? 7 : 30;
    const cacheKey = `income_by_category_${familyId}_${childId}_${days}`;
    const cacheTTL = 10 * 60 * 1000; // 10 minutes cache
    
    // Check cache first
    const cached = getCached(cacheKey, cacheTTL);
    if (cached !== null) {
      setIncomeByCategory(cached);
      setLoadingIncome(false);
      return;
    }
    
    try {
      setLoadingIncome(true);
      
      // Load all transactions
      const allTransactions = await getChildTransactions(familyId, childId, null);
      
      // Calculate date range
      const cutoffDate = new Date();
      cutoffDate.setHours(0, 0, 0, 0);
      cutoffDate.setDate(cutoffDate.getDate() - days + 1);
      
      // Filter deposits within date range
      const deposits = (allTransactions || []).filter(t => {
        if (!t || t.type !== 'deposit') return false;
        const transactionDate = new Date(t.date || t.createdAt);
        transactionDate.setHours(0, 0, 0, 0);
        return transactionDate >= cutoffDate;
      });
      
      // Categorize deposits
      const incomeCategories = {
        'ריבית': 0,
        'מטלות': 0,
        'אחר': 0
      };
      
      deposits.forEach(deposit => {
        const description = (deposit.description || '').toLowerCase();
        const id = deposit.id || '';
        
        // Check if it's interest
        if (description.includes('ריבית') || description.includes('interest') || id.startsWith('interest_')) {
          incomeCategories['ריבית'] += deposit.amount || 0;
        }
        // Check if it's from tasks
        else if (description.includes('תשלום על משימה') || description.includes('משימה') || description.includes('task') || id.startsWith('task_')) {
          incomeCategories['מטלות'] += deposit.amount || 0;
        }
        // Everything else (allowances, manual deposits, etc.)
        else {
          incomeCategories['אחר'] += deposit.amount || 0;
        }
      });
      
      // Convert to array format
      const incomeArray = Object.entries(incomeCategories)
        .filter(([_, amount]) => amount > 0)
        .map(([category, amount]) => ({ category, amount }));
      
      setIncomeByCategory(incomeArray);
      
      // Cache the result
      setCached(cacheKey, incomeArray, cacheTTL);
    } catch (error) {
      console.error('Error loading income by category:', error);
      setIncomeByCategory([]);
    } finally {
      setLoadingIncome(false);
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
      setUploadingImage(true);
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
    } finally {
      setUploadingImage(false);
    }
  };

  const handleRemoveImage = async () => {
    try {
      setUploadingImage(true);
      await updateProfileImage(familyId, childId, null);
      await loadChildData();
    } catch (error) {
      alert(t('child.profile.errorRemoving', { defaultValue: 'Error removing image' }) + ': ' + error.message);
    } finally {
      setUploadingImage(false);
    }
  };

  const handleBottomNavAction = (type) => {
    console.log('🔵🔵🔵 [ChildView] handleBottomNavAction CALLED with type:', type);
    console.log('🔵🔵🔵 [ChildView] Setting transactionType to:', type);
    setTransactionType(type);
    setTransactionAmount('');
    setTransactionDescription('');
    setTransactionCategory('');
    console.log('🔵🔵🔵 [ChildView] Opening transaction modal...');
    setShowTransactionModal(true);
    console.log('🔵🔵🔵 [ChildView] showTransactionModal should be true now');
  };

  const handleCalculatorClick = () => {
    console.log('[ChildView] handleCalculatorClick called');
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
    console.log('🔵🔵🔵 [ChildView] ========== handleSubmitTransaction CALLED ==========');
    console.log('🔵🔵🔵 [ChildView] transactionAmount:', transactionAmount);
    console.log('🔵🔵🔵 [ChildView] transactionType:', transactionType);
    console.log('🔵🔵🔵 [ChildView] familyId:', familyId);
    console.log('🔵🔵🔵 [ChildView] childId:', childId);
    
    if (!transactionAmount || parseFloat(transactionAmount) <= 0) {
      console.log('🔵🔵🔵 [ChildView] Invalid amount, returning');
      alert(t('parent.dashboard.invalidAmount', { defaultValue: 'אנא הכנס סכום תקין' }));
      return;
    }

    if (transactionType === 'expense' && categories.length > 0 && !transactionCategory) {
      console.log('🔵🔵🔵 [ChildView] Missing category, returning');
      alert(t('parent.dashboard.selectCategory', { defaultValue: 'אנא בחר קטגוריה' }));
      return;
    }

    try {
      console.log('🔵🔵🔵 [ChildView] Setting submittingTransaction to true');
      setSubmittingTransaction(true);
      const amount = parseFloat(transactionAmount);
      const currentCashBox = childData?.cashBoxBalance || 0;
      const currentBalance = childData?.balance || 0;
      
      console.log('🔵🔵🔵 [ChildView] ========== Transaction Details ==========');
      console.log('🔵🔵🔵 [ChildView] Type:', transactionType);
      console.log('🔵🔵🔵 [ChildView] Amount:', amount);
      console.log('🔵🔵🔵 [ChildView] Before update - cashBoxBalance:', currentCashBox);
      console.log('🔵🔵🔵 [ChildView] Before update - balance:', currentBalance);
      
      // Update cashBoxBalance based on transaction type
      // Deposit adds to cash box, expense subtracts from cash box
      const newCashBoxBalance = transactionType === 'deposit' 
        ? currentCashBox + amount 
        : Math.max(0, currentCashBox - amount);
      
      console.log('🔵🔵🔵 [ChildView] New cashBoxBalance:', newCashBoxBalance);
      console.log('🔵🔵🔵 [ChildView] ============================================');
      
      // Update cash box balance
      console.log('🔵🔵🔵 [ChildView] STEP 1: Calling updateCashBoxBalance...');
      await updateCashBoxBalance(familyId, childId, newCashBoxBalance);
      console.log('🔵🔵🔵 [ChildView] STEP 1: updateCashBoxBalance completed');
      
      // Add transaction to history WITHOUT updating balance (only for display purposes)
      // We use a special flag to indicate this is a cash box transaction that shouldn't affect balance
      const category = transactionType === 'expense' ? transactionCategory : null;
      console.log('🔵🔵🔵 [ChildView] STEP 2: Calling addTransaction with cashBoxOnly=true');
      console.log('🔵🔵🔵 [ChildView] Parameters:', { 
        familyId, 
        childId, 
        type: transactionType, 
        amount: transactionAmount, 
        description: transactionDescription, 
        category, 
        cashBoxOnly: true 
      });
      await addTransaction(familyId, childId, transactionType, transactionAmount, transactionDescription, category, true); // true = cashBoxOnly
      console.log('🔵🔵🔵 [ChildView] STEP 2: addTransaction completed');
      
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
            onClick={() => setShowLogoutConfirm(true)}
            title={t('common.logout', { defaultValue: 'התנתק' })}
            style={{
              position: 'absolute',
              [i18n.language === 'he' ? 'right' : 'left']: '20px',
              top: '50%',
              transform: 'translateY(-50%)',
              fontSize: '14px',
              fontWeight: 600,
              padding: '10px 16px',
              borderRadius: '12px',
              border: 'none',
              background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
              color: 'white',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              boxShadow: '0 2px 8px rgba(239, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              whiteSpace: 'nowrap',
              zIndex: 10
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(239, 68, 68, 0.4)';
              e.currentTarget.style.transform = 'translateY(-50%) scale(1.05)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)';
              e.currentTarget.style.boxShadow = '0 2px 8px rgba(239, 68, 68, 0.3)';
              e.currentTarget.style.transform = 'translateY(-50%) scale(1)';
            }}
            onMouseDown={(e) => {
              e.currentTarget.style.transform = 'translateY(-50%) scale(0.98)';
            }}
            onMouseUp={(e) => {
              e.currentTarget.style.transform = 'translateY(-50%) scale(1.05)';
            }}
          >
            <span style={{ fontSize: '16px' }}>🚪</span>
            <span>{t('common.logout', { defaultValue: 'התנתקות' })}</span>
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
            <div style={{ position: 'relative', width: '120px', height: '120px' }}>
              <img 
                src={childData.profileImage} 
                alt={childData.name}
                loading="lazy"
                decoding="async"
                onError={(e) => {
                  console.error('[CHILD-VIEW] Error loading profile image:', e);
                  console.error('[CHILD-VIEW] Image src length:', childData.profileImage?.length);
                  console.error('[CHILD-VIEW] Image src preview:', childData.profileImage?.substring(0, 50));
                  // Hide broken image
                  e.target.style.display = 'none';
                  // Optionally clear the broken image from state
                  setChildData(prev => prev ? { ...prev, profileImage: null } : null);
                }}
                onLoad={() => {
                  console.log('[CHILD-VIEW] Profile image loaded successfully');
                }}
                style={{
                  width: '120px',
                  height: '120px',
                  borderRadius: '50%',
                  objectFit: 'cover',
                  border: '4px solid white',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  opacity: uploadingImage ? 0.5 : 1,
                  transition: 'opacity 0.2s'
                }}
              />
              {uploadingImage && (
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: '40px',
                  height: '40px',
                  border: '3px solid rgba(255, 255, 255, 0.3)',
                  borderTop: '3px solid white',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
              )}
            </div>
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
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              position: 'relative',
              opacity: uploadingImage ? 0.5 : 1,
              transition: 'opacity 0.2s'
            }}>
              {!uploadingImage && (childData?.name?.charAt(0)?.toUpperCase() || '?')}
              {uploadingImage && (
                <div style={{
                  width: '40px',
                  height: '40px',
                  border: '3px solid rgba(255, 255, 255, 0.3)',
                  borderTop: '3px solid white',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
              )}
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

      {/* Expenses/Income Distribution Chart */}
      <div className="fintech-card">
        <div className="expenses-chart-header" style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
            <div className="period-toggle">
              <button
                className={`period-button ${chartType === 'expenses' ? 'active' : ''}`}
                onClick={() => {
                  setChartType('expenses');
                  setFilteredCategory(null);
                  setFilteredChartType(null);
                }}
              >
                {t('child.expenses.title', { defaultValue: 'הוצאות' })}
              </button>
              <button
                className={`period-button ${chartType === 'income' ? 'active' : ''}`}
                onClick={() => {
                  setChartType('income');
                  setFilteredCategory(null);
                  setFilteredChartType(null);
                }}
              >
                {t('child.income.title', { defaultValue: 'הכנסות' })}
              </button>
            </div>
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
        </div>
        {(chartType === 'expenses' ? loadingExpenses : loadingIncome) ? (
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
        ) : (chartType === 'expenses' 
          ? (expensesByCategory && expensesByCategory.length > 0)
          : (incomeByCategory && incomeByCategory.length > 0)
        ) ? (
          <ExpensePieChart
            expensesByCategory={chartType === 'expenses' ? expensesByCategory : incomeByCategory}
            title={chartType === 'expenses'
              ? t('child.expenses.chartTitle', { 
                  period: expensesPeriod === 'week' 
                    ? t('child.expenses.week', { defaultValue: 'Last Week' })
                    : t('child.expenses.month', { defaultValue: 'Last Month' }),
                  defaultValue: 'Expenses - {period}'
                })
              : t('child.income.chartTitle', { 
                  period: expensesPeriod === 'week' 
                    ? t('child.expenses.week', { defaultValue: 'Last Week' })
                    : t('child.expenses.month', { defaultValue: 'Last Month' }),
                  defaultValue: 'Income - {period}'
                })
            }
            days={expensesPeriod === 'week' ? 7 : 30}
            onCategorySelect={(category) => {
              setFilteredCategory(category);
              setFilteredChartType(chartType);
            }}
            selectedCategory={filteredCategory}
          />
        ) : (
          <div className="no-expenses-message">
            {chartType === 'expenses'
              ? t('child.expenses.noExpenses', { defaultValue: 'אין הוצאות בתקופה זו' })
              : t('child.income.noIncome', { defaultValue: 'אין הכנסות בתקופה זו' })
            }
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
              ? transactions.filter(t => {
                  if (filteredChartType === 'expenses') {
                    // Filter expenses by category
                    return t.type === 'expense' && t.category === filteredCategory;
                  } else if (filteredChartType === 'income') {
                    // Filter income by income category (ריבית, מטלות, אחר)
                    if (t.type !== 'deposit') return false;
                    
                    const description = (t.description || '').toLowerCase();
                    const id = t.id || '';
                    
                    if (filteredCategory === 'ריבית') {
                      return description.includes('ריבית') || description.includes('interest') || id.startsWith('interest_');
                    } else if (filteredCategory === 'מטלות') {
                      return description.includes('תשלום על משימה') || description.includes('משימה') || description.includes('task') || id.startsWith('task_');
                    } else if (filteredCategory === 'אחר') {
                      // Everything else (allowances, manual deposits, etc.)
                      const isInterest = description.includes('ריבית') || description.includes('interest') || id.startsWith('interest_');
                      const isTask = description.includes('תשלום על משימה') || description.includes('משימה') || description.includes('task') || id.startsWith('task_');
                      return !isInterest && !isTask;
                    }
                    return false;
                  }
                  return false;
                })
              : transactions;
            
            // Apply limit if not null
            const limited = historyLimit === null ? filtered : filtered.slice(0, historyLimit);
            
            if (limited.length === 0) {
              return (
                <div className="no-transactions-message">
                  {filteredCategory 
                    ? (filteredChartType === 'income'
                        ? t('child.history.noIncomeForCategory', { defaultValue: `אין הכנסות בקטגוריה "${filteredCategory}"` }).replace('{category}', filteredCategory)
                        : t('child.history.noTransactionsForCategory', { category: filteredCategory }).replace('{category}', filteredCategory)
                      )
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
            setUploadingImage(true);
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
          } finally {
            setUploadingImage(false);
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

            <form onSubmit={(e) => { 
              console.log('🔵🔵🔵 [ChildView] FORM SUBMIT triggered!');
              e.preventDefault(); 
              console.log('🔵🔵🔵 [ChildView] Calling handleSubmitTransaction...');
              handleSubmitTransaction(); 
            }} className="quick-action-form">
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
                      <option key={cat} value={cat}>{cat}</option>
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
        
        {/* Center: Tasks (if active) or Calculator */}
        {activeTasks.length > 0 ? (
          <button 
            className="fab-btn"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setShowTasksList(true);
            }}
            type="button"
            title={t('child.tasks.title', { defaultValue: 'מטלות' })}
          >
            ✅
          </button>
        ) : (
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
        )}
        
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
      {showTasksList && (
        <div className="modal-overlay" onClick={() => setShowTasksList(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px', maxHeight: '80vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <h2>{t('child.tasks.title', { defaultValue: 'מטלות פעילות' })}</h2>
              <button className="close-button" onClick={() => setShowTasksList(false)}>✕</button>
            </div>
            <div style={{ padding: '20px' }}>
              {activeTasks.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
                  {t('child.tasks.noTasks', { defaultValue: 'אין מטלות פעילות' })}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {activeTasks.map((task) => (
                    <button
                      key={task._id}
                      onClick={() => {
                        setSelectedTask(task);
                        setTaskNote('');
                        setTaskImage(null);
                        setShowTasksList(false);
                        setShowTaskRequest(true);
                      }}
                      style={{
                        padding: '16px',
                        background: 'white',
                        border: '1px solid #E5E7EB',
                        borderRadius: '12px',
                        textAlign: 'right',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#F9FAFB';
                        e.currentTarget.style.borderColor = 'var(--primary)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'white';
                        e.currentTarget.style.borderColor = '#E5E7EB';
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-main)' }}>
                          {task.name}
                        </span>
                        <span style={{ fontSize: '16px', fontWeight: 600, color: 'var(--primary)' }}>
                          ₪{task.price?.toFixed(2) || '0.00'}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Task Request Modal */}
      {showTaskRequest && selectedTask && (
        <div className="modal-overlay" onClick={() => setShowTaskRequest(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px', maxHeight: '80vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <h2>{t('child.tasks.requestPayment', { defaultValue: 'בקשת תשלום' })}</h2>
              <button className="close-button" onClick={() => setShowTaskRequest(false)}>✕</button>
            </div>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (submittingTaskRequest) return;
                
                try {
                  setSubmittingTaskRequest(true);
                  
                  let imageBase64 = null;
                  if (taskImage) {
                    // Compress image before sending
                    imageBase64 = await smartCompressImage(taskImage);
                  }
                  
                  await requestTaskPayment(familyId, selectedTask._id, childId, taskNote.trim(), imageBase64);
                  
                  // Show success notification
                  alert(t('child.tasks.requestSent', { defaultValue: 'בקשת התשלום נשלחה בהצלחה!' }));
                  
                  // Reset and close
                  setShowTaskRequest(false);
                  setSelectedTask(null);
                  setTaskNote('');
                  setTaskImage(null);
                  setShowTasksList(false);
                  
                  // Reload tasks
                  await loadActiveTasks();
                } catch (error) {
                  alert(t('child.tasks.requestError', { defaultValue: 'שגיאה בשליחת בקשת התשלום' }) + ': ' + error.message);
                } finally {
                  setSubmittingTaskRequest(false);
                }
              }}
              style={{ 
                padding: '20px', 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '16px',
                height: '100%',
                maxHeight: 'calc(80vh - 60px)'
              }}
            >
              <div style={{ flex: '1 1 auto', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
                  {t('child.tasks.task', { defaultValue: 'מטלה' })}:
                </label>
                <div style={{ padding: '12px', background: '#F9FAFB', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '16px', fontWeight: 600 }}>{selectedTask.name}</span>
                    <span style={{ fontSize: '16px', fontWeight: 600, color: 'var(--primary)' }}>
                      ₪{selectedTask.price?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                </div>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
                  {t('child.tasks.note', { defaultValue: 'הערה' })} ({t('common.optional', { defaultValue: 'אופציונלי' })}):
                </label>
                <textarea
                  value={taskNote}
                  onChange={(e) => setTaskNote(e.target.value)}
                  placeholder={t('child.tasks.notePlaceholder', { defaultValue: 'הוסף הערה...' })}
                  style={{
                    width: '100%',
                    minHeight: '80px',
                    padding: '12px',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontFamily: 'inherit',
                    resize: 'vertical'
                  }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
                  {t('child.tasks.photo', { defaultValue: 'תמונה' })} ({t('common.optional', { defaultValue: 'אופציונלי' })}):
                </label>
                <input
                  ref={taskImageInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setTaskImage(file);
                    }
                  }}
                  style={{ display: 'none' }}
                />
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={() => taskImageInputRef.current?.click()}
                    style={{
                      padding: '10px 20px',
                      background: 'var(--primary)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: 600
                    }}
                  >
                    {taskImage ? t('child.tasks.changePhoto', { defaultValue: 'שנה תמונה' }) : t('child.tasks.takePhoto', { defaultValue: 'צלם תמונה' })}
                  </button>
                  {taskImage && (
                    <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                      {taskImage.name}
                    </span>
                  )}
                </div>
                {taskImage && (
                  <div style={{ marginTop: '12px' }}>
                    <img
                      src={URL.createObjectURL(taskImage)}
                      alt="Task"
                      style={{
                        maxWidth: '100%',
                        maxHeight: '200px',
                        borderRadius: '8px',
                        border: '1px solid #E5E7EB',
                        objectFit: 'contain'
                      }}
                    />
                  </div>
                )}
              </div>
              </div>
              
              <div style={{ display: 'flex', gap: '12px', flexShrink: 0, paddingTop: '16px', borderTop: '1px solid rgba(0,0,0,0.1)' }}>
                <button
                  type="button"
                  onClick={() => {
                    setShowTaskRequest(false);
                    setSelectedTask(null);
                    setTaskNote('');
                    setTaskImage(null);
                  }}
                  style={{
                    flex: 1,
                    padding: '12px',
                    background: 'white',
                    color: 'var(--text-main)',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: 600
                  }}
                >
                  {t('common.cancel', { defaultValue: 'ביטול' })}
                </button>
                <button
                  type="submit"
                  disabled={submittingTaskRequest}
                  style={{
                    flex: 1,
                    padding: '12px',
                    background: 'var(--primary)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: submittingTaskRequest ? 'not-allowed' : 'pointer',
                    fontSize: '14px',
                    fontWeight: 600,
                    opacity: submittingTaskRequest ? 0.6 : 1
                  }}
                >
                  {submittingTaskRequest
                    ? t('common.saving', { defaultValue: 'שומר...' })
                    : t('child.tasks.sendRequest', { defaultValue: 'שלח בקשת תשלום' })
                  }
                </button>
              </div>
            </form>
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

      {/* Logout Confirmation Modal */}
      {showLogoutConfirm && (
        <div 
          className="modal-overlay"
          onClick={() => setShowLogoutConfirm(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000
          }}
        >
          <div 
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: 'white',
              borderRadius: '16px',
              padding: '24px',
              maxWidth: '400px',
              width: '90%',
              boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
              textAlign: i18n.language === 'he' ? 'right' : 'left'
            }}
          >
            <h2 style={{ 
              margin: '0 0 16px 0', 
              fontSize: '20px', 
              fontWeight: 600,
              color: 'var(--text-color)'
            }}>
              {t('common.confirmLogout', { defaultValue: 'אישור התנתקות' })}
            </h2>
            <p style={{ 
              margin: '0 0 24px 0', 
              fontSize: '16px', 
              color: 'var(--text-muted)',
              lineHeight: '1.5'
            }}>
              {t('common.confirmLogoutMessage', { defaultValue: 'האם אתה בטוח שברצונך להתנתק?' })}
            </p>
            <div style={{
              display: 'flex',
              gap: '12px',
              justifyContent: i18n.language === 'he' ? 'flex-start' : 'flex-end',
              flexDirection: i18n.language === 'he' ? 'row-reverse' : 'row'
            }}>
              <button
                onClick={() => setShowLogoutConfirm(false)}
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: '1px solid rgba(0,0,0,0.2)',
                  background: 'white',
                  color: 'var(--text-color)',
                  fontSize: '16px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(0,0,0,0.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'white';
                }}
              >
                {t('common.cancel', { defaultValue: 'ביטול' })}
              </button>
              <button
                onClick={() => {
                  setShowLogoutConfirm(false);
                  if (onLogout) {
                    onLogout();
                  }
                }}
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#EF4444',
                  color: 'white',
                  fontSize: '16px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#DC2626';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#EF4444';
                }}
              >
                {t('common.logout', { defaultValue: 'התנתקות' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChildView;
