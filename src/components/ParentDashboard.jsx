import React, { useState, useEffect } from 'react';
import { getChild, addTransaction, getChildTransactions, getData, resetAllData, getCategories } from '../utils/api';
import BalanceDisplay from './BalanceDisplay';
import TransactionList from './TransactionList';
import Settings from './Settings';

const CHILD_COLORS = {
  child1: '#3b82f6', // כחול
  child2: '#ec4899'  // ורוד
};

const ParentDashboard = () => {
  const [selectedChild, setSelectedChild] = useState('child1');
  const [childData, setChildData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [transactionType, setTransactionType] = useState('deposit');
  const [category, setCategory] = useState('אחר');
  const [allData, setAllData] = useState({ children: { child1: { name: 'אדם חיים שלי', balance: 0 }, child2: { name: 'ג\'וּן חיים שלי', balance: 0 } } });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [categories, setCategories] = useState(['משחקים', 'ממתקים', 'בגדים', 'בילויים', 'אחר']);

  useEffect(() => {
    let mounted = true;
    
    const initialize = async () => {
      try {
        setLoading(true);
        // Load data in parallel
        const [dataResult, categoriesResult] = await Promise.allSettled([
          getData().catch(err => {
            console.error('Error loading data:', err);
            return null;
          }),
          getCategories().catch(err => {
            console.error('Error loading categories:', err);
            return [];
          })
        ]);
        
        if (!mounted) return;
        
        if (dataResult.status === 'fulfilled' && dataResult.value) {
          setAllData(dataResult.value);
        }
        
        if (categoriesResult.status === 'fulfilled') {
          const cats = categoriesResult.value || [];
          const activeCategories = cats
            .filter(cat => (cat.activeFor || []).includes(selectedChild))
            .map(cat => cat.name);
          if (activeCategories.length > 0) {
            setCategories(activeCategories);
            // Only update category if current one is not in list
            setCategory(prevCat => {
              if (!activeCategories.includes(prevCat)) {
                return activeCategories[0];
              }
              return prevCat;
            });
          } else {
            // Fallback to default categories
            const defaultCategories = ['משחקים', 'ממתקים', 'בגדים', 'בילויים', 'אחר'];
            setCategories(defaultCategories);
          }
        }
      } catch (error) {
        console.error('Error initializing:', error);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    
    initialize();
    
    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadCategories = async () => {
    try {
      const cats = await getCategories();
      // Filter categories that are active for the selected child
      const activeCategories = cats
        .filter(cat => (cat.activeFor || []).includes(selectedChild))
        .map(cat => cat.name);
      if (activeCategories.length > 0) {
        setCategories(activeCategories);
        // Reset category to first available if current is not in list
        if (!activeCategories.includes(category)) {
          setCategory(activeCategories[0]);
        }
      } else {
        // Fallback to default categories if none found
        const defaultCategories = ['משחקים', 'ממתקים', 'בגדים', 'בילויים', 'אחר'];
        setCategories(defaultCategories);
        if (!defaultCategories.includes(category)) {
          setCategory(defaultCategories[0]);
        }
      }
    } catch (error) {
      console.error('Error loading categories:', error);
      // Fallback to default categories on error
      const defaultCategories = ['משחקים', 'ממתקים', 'בגדים', 'בילויים', 'אחר'];
      setCategories(defaultCategories);
      if (!defaultCategories.includes(category)) {
        setCategory(defaultCategories[0]);
      }
    }
  };

  useEffect(() => {
    if (selectedChild) {
      loadChildData();
      loadCategories();
    }
  }, [selectedChild]);

  const loadAllData = async () => {
    try {
      setLoading(true);
      
      // Add timeout to prevent infinite loading
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('טעינת הנתונים ארכה יותר מדי זמן. נסה לרענן את הדף.')), 10000)
      );
      
      const dataPromise = getData();
      const data = await Promise.race([dataPromise, timeoutPromise]);
      
      if (data && data.children) {
        setAllData(data);
      } else {
        console.warn('Invalid data received:', data);
        // Keep existing data if new data is invalid
      }
    } catch (error) {
      console.error('Error loading data:', error);
      // Don't show alert for timeout or network errors - just log
      if (!error.message?.includes('זמן') && !error.message?.includes('Failed to fetch')) {
        alert('שגיאה בטעינת הנתונים: ' + (error.message || 'Unknown error'));
      }
      // Keep existing data on error
    } finally {
      setLoading(false);
    }
  };

  const loadChildData = async () => {
    try {
      const child = await getChild(selectedChild);
      if (child) {
        setChildData(child);
        const trans = await getChildTransactions(selectedChild);
        setTransactions(trans);
      }
      // Refresh all data to update balances (but don't set loading state)
      // Only update if we have valid data
      try {
        const data = await getData();
        if (data && data.children) {
          setAllData(data);
        }
      } catch (refreshError) {
        console.error('Error refreshing all data:', refreshError);
        // Don't show error - just log it
      }
    } catch (error) {
      console.error('Error loading child data:', error);
      // Don't show alert for network errors
      if (!error.message?.includes('Failed to fetch')) {
        alert('שגיאה בטעינת נתוני הילד: ' + (error.message || 'Unknown error'));
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!amount || parseFloat(amount) <= 0) {
      alert('אנא הכנס סכום תקין');
      return;
    }

    try {
      setSubmitting(true);
      const transactionCategory = transactionType === 'expense' ? category : null;
      await addTransaction(selectedChild, transactionType, amount, description, transactionCategory);
      setAmount('');
      setDescription('');
      setCategory('אחר'); // Reset to default
      await loadChildData(); // Reload to get updated balance and transactions
    } catch (error) {
      alert('שגיאה בהוספת הפעולה: ' + error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('האם אתה בטוח שברצונך לאפס את כל היתרות והפעולות? פעולה זו לא ניתנת לביטול!')) {
      return;
    }

    try {
      setResetting(true);
      await resetAllData();
      await loadAllData();
      await loadChildData();
      alert('כל הנתונים אופסו בהצלחה!');
    } catch (error) {
      alert('שגיאה באיפוס הנתונים: ' + error.message);
    } finally {
      setResetting(false);
    }
  };


  const child1Balance = allData.children.child1?.balance || 0;
  const child1CashBox = allData.children.child1?.cashBoxBalance || 0;
  const child1Total = child1Balance + child1CashBox;
  
  const child2Balance = allData.children.child2?.balance || 0;
  const child2CashBox = allData.children.child2?.cashBoxBalance || 0;
  const child2Total = child2Balance + child2CashBox;

  if (loading) {
    return (
      <div className="parent-dashboard">
        <div className="loading">טוען נתונים...</div>
      </div>
    );
  }

  return (
    <div className="parent-dashboard">
      <div className="dashboard-header">
        <h1>ממשק הורה - ניהול כסף</h1>
        <div className="header-buttons">
          <button 
            className="settings-button" 
            onClick={() => setShowSettings(true)}
            title="הגדרות"
          >
            ⚙️ הגדרות
          </button>
          <button 
            className="reset-button" 
            onClick={handleReset}
            disabled={resetting}
            title="איפוס כל היתרות והפעולות"
          >
            {resetting ? 'מאפס...' : '🔄 איפוס יתרות'}
          </button>
        </div>
      </div>
      
      {showSettings && (
        <Settings onClose={() => {
          setShowSettings(false);
          loadCategories();
          loadAllData();
        }} />
      )}
      
      {/* Quick balance overview */}
      <div className="balance-overview">
        <div className="balance-card" style={{ borderColor: CHILD_COLORS.child1 }}>
          {allData.children.child1?.profileImage && (
            <img 
              src={allData.children.child1.profileImage} 
              alt={allData.children.child1.name}
              className="profile-image-small"
            />
          )}
          <h3>{allData.children.child1.name}</h3>
          <div className="balance-value" style={{ color: CHILD_COLORS.child1 }}>
            ₪{child1Total.toFixed(2)}
          </div>
          <div className="balance-subtitle">יתרה כוללת</div>
        </div>
        <div className="balance-card" style={{ borderColor: CHILD_COLORS.child2 }}>
          {allData.children.child2?.profileImage && (
            <img 
              src={allData.children.child2.profileImage} 
              alt={allData.children.child2.name}
              className="profile-image-small"
            />
          )}
          <h3>{allData.children.child2.name}</h3>
          <div className="balance-value" style={{ color: CHILD_COLORS.child2 }}>
            ₪{child2Total.toFixed(2)}
          </div>
          <div className="balance-subtitle">יתרה כוללת</div>
        </div>
      </div>

      {/* Child selection */}
      <div className="child-selection">
        <h2>בחר ילד לניהול</h2>
        <div className="child-buttons">
          <button
            className={selectedChild === 'child1' ? 'active' : ''}
            onClick={() => setSelectedChild('child1')}
            style={{
              backgroundColor: selectedChild === 'child1' ? CHILD_COLORS.child1 : '#e5e7eb',
              color: selectedChild === 'child1' ? 'white' : 'black'
            }}
          >
            {allData.children.child1.name}
          </button>
          <button
            className={selectedChild === 'child2' ? 'active' : ''}
            onClick={() => setSelectedChild('child2')}
            style={{
              backgroundColor: selectedChild === 'child2' ? CHILD_COLORS.child2 : '#e5e7eb',
              color: selectedChild === 'child2' ? 'white' : 'black'
            }}
          >
            {allData.children.child2.name}
          </button>
        </div>
      </div>

      {childData && (
        <>
          <BalanceDisplay
            balance={childData.balance}
            cashBoxBalance={childData.cashBoxBalance}
            childName={childData.name}
            color={CHILD_COLORS[selectedChild]}
          />

          {/* Transaction form */}
          <div className="transaction-form-container">
            <h2>הוסף פעולה</h2>
            <form onSubmit={handleSubmit} className="transaction-form">
              <div className="form-group">
                <label>סוג פעולה:</label>
                <div className="radio-group">
                  <label>
                    <input
                      type="radio"
                      value="deposit"
                      checked={transactionType === 'deposit'}
                      onChange={(e) => setTransactionType(e.target.value)}
                    />
                    הפקדת כסף
                  </label>
                  <label>
                    <input
                      type="radio"
                      value="expense"
                      checked={transactionType === 'expense'}
                      onChange={(e) => setTransactionType(e.target.value)}
                    />
                    הוצאה
                  </label>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="amount">סכום (₪):</label>
                <div className="amount-input-wrapper">
                  <span style={{ 
                    fontSize: '24px', 
                    fontWeight: '700', 
                    color: 'var(--text-primary)',
                    minWidth: '35px',
                    textAlign: 'center'
                  }}>₪</span>
                  <input
                    type="number"
                    id="amount"
                    step="1"
                    min="1"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                    placeholder="0"
                    style={{
                      flex: 1,
                      padding: '16px 20px',
                      border: 'none',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '20px',
                      fontWeight: '700',
                      textAlign: 'center',
                      background: 'transparent',
                      minHeight: '56px',
                      letterSpacing: '1px'
                    }}
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="description">תיאור:</label>
                <input
                  type="text"
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="תיאור הפעולה (אופציונלי)"
                />
              </div>

              {transactionType === 'expense' && (
                <div className="form-group">
                  <label htmlFor="category">קטגוריה:</label>
                  <select
                    id="category"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="category-select"
                  >
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              )}

              <button type="submit" className="submit-button" disabled={submitting}>
                {submitting ? 'שומר...' : (transactionType === 'deposit' ? 'הוסף כסף' : 'דווח על הוצאה')}
              </button>
            </form>
          </div>

          <TransactionList transactions={transactions} showAll={true} />
        </>
      )}
    </div>
  );
};

export default ParentDashboard;

