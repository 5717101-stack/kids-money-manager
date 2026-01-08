import React, { useState, useEffect } from 'react';
import { getChild, addTransaction, getChildTransactions, getData, getCategories } from '../utils/api';
import BalanceDisplay from './BalanceDisplay';
import TransactionList from './TransactionList';
import Settings from './Settings';

const CHILD_COLORS = {
  child1: '#3b82f6', // כחול
  child2: '#ec4899'  // ורוד
};

const ParentDashboard = ({ familyId, onChildrenUpdated }) => {
  const [selectedChild, setSelectedChild] = useState(null);
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
        if (!familyId) {
          setLoading(false);
          return;
        }
        
        const [dataResult, categoriesResult] = await Promise.allSettled([
          getData(familyId).catch(err => {
            console.error('Error loading data:', err);
            return null;
          }),
          getCategories(familyId).catch(err => {
            console.error('Error loading categories:', err);
            return [];
          })
        ]);
        
        if (!mounted) return;
        
        if (dataResult.status === 'fulfilled' && dataResult.value) {
          setAllData(dataResult.value);
          // Set first child as selected if none selected
          const children = Object.keys(dataResult.value.children || {});
          if (children.length > 0 && !selectedChild) {
            setSelectedChild(children[0]);
          }
        }
        
        if (categoriesResult.status === 'fulfilled') {
          const cats = categoriesResult.value || [];
          const activeCategories = selectedChild ? cats
            .filter(cat => (cat.activeFor || []).includes(selectedChild))
            .map(cat => cat.name) : [];
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
  }, [familyId]);

  const loadCategories = async () => {
    if (!familyId || !selectedChild) return;
    try {
      const cats = await getCategories(familyId);
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
      
      if (!familyId) return;
      const dataPromise = getData(familyId);
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
    if (!familyId || !selectedChild) return;
    try {
      const child = await getChild(familyId, selectedChild);
      if (child) {
        setChildData(child);
        const trans = await getChildTransactions(familyId, selectedChild);
        setTransactions(trans);
      }
      // Refresh all data to update balances (but don't set loading state)
      // Only update if we have valid data
      try {
        const data = await getData(familyId);
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

    if (!familyId || !selectedChild) return;
    try {
      setSubmitting(true);
      const transactionCategory = transactionType === 'expense' ? category : null;
      await addTransaction(familyId, selectedChild, transactionType, amount, description, transactionCategory);
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

    if (!familyId) return;
    try {
      setResetting(true);
      // Reset each child individually
      const children = Object.keys(allData.children || {});
      for (const childId of children) {
        await addTransaction(familyId, childId, 'deposit', 0, 'איפוס', null);
        // Set balance to 0 by adding a negative transaction equal to current balance
        const child = await getChild(familyId, childId);
        if (child && child.balance > 0) {
          await addTransaction(familyId, childId, 'expense', child.balance, 'איפוס יתרה', 'אחר');
        }
      }
      await loadAllData();
      await loadChildData();
      alert('כל הנתונים אופסו בהצלחה!');
    } catch (error) {
      alert('שגיאה באיפוס הנתונים: ' + error.message);
    } finally {
      setResetting(false);
    }
  };


  // Convert children object to array, ensuring we have valid children
  const childrenList = Object.values(allData.children || {}).filter(child => child && child._id);

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
        <h1>ממשק הורה - ניהול כסף ל<span className="kids-green">Kids</span></h1>
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
        <Settings 
          familyId={familyId}
          onClose={async () => {
            setShowSettings(false);
            // Reload all data to get new children
            await loadAllData();
            await loadCategories();
            // Update children list in parent component
            if (onChildrenUpdated) {
              await onChildrenUpdated();
            }
            // Update selected child if needed
            const children = Object.keys(allData.children || {});
            if (children.length > 0 && !selectedChild) {
              setSelectedChild(children[0]);
            }
          }} 
        />
      )}
      
      {/* Quick balance overview */}
      {childrenList.length > 0 && (
        <div className="balance-overview">
          {childrenList.map((child, index) => {
            const total = (child.balance || 0) + (child.cashBoxBalance || 0);
            const color = Object.values(CHILD_COLORS)[index % Object.keys(CHILD_COLORS).length];
            return (
              <div key={child._id} className="balance-card" style={{ borderColor: color }}>
                {child.profileImage && (
                  <img 
                    src={child.profileImage} 
                    alt={child.name}
                    className="profile-image-small"
                  />
                )}
                <h3>{child.name}</h3>
                <div className="balance-value" style={{ color: color }}>
                  ₪{total.toFixed(2)}
                </div>
                <div className="balance-subtitle">יתרה כוללת</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Child selection */}
      {childrenList.length > 0 && (
        <div className="child-selection">
          <h2>בחר ילד לניהול</h2>
          <div className="child-buttons">
            {childrenList.map((child, index) => {
              const color = Object.values(CHILD_COLORS)[index % Object.keys(CHILD_COLORS).length];
              return (
                <button
                  key={child._id}
                  className={selectedChild === child._id ? 'active' : ''}
                  onClick={() => setSelectedChild(child._id)}
                  style={{
                    backgroundColor: selectedChild === child._id ? color : '#e5e7eb',
                    color: selectedChild === child._id ? 'white' : 'black'
                  }}
                >
                  {child.name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {childData && (
        <>
          <BalanceDisplay
            balance={childData.balance}
            cashBoxBalance={childData.cashBoxBalance}
            childName={childData.name}
            color={selectedChild ? Object.values(CHILD_COLORS)[childrenList.findIndex(c => c._id === selectedChild) % Object.keys(CHILD_COLORS).length] : CHILD_COLORS.child1}
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

