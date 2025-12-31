import React, { useState, useEffect } from 'react';
import { getChild, addTransaction, getChildTransactions, getData, resetAllData } from '../utils/api';
import BalanceDisplay from './BalanceDisplay';
import TransactionList from './TransactionList';

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
  
  const CATEGORIES = ['משחקים', 'ממתקים', 'בגדים', 'בילויים', 'אחר'];

  useEffect(() => {
    loadAllData();
  }, []);

  useEffect(() => {
    if (selectedChild) {
      loadChildData();
    }
  }, [selectedChild]);

  const loadAllData = async () => {
    try {
      setLoading(true);
      const data = await getData();
      setAllData(data);
    } catch (error) {
      console.error('Error loading data:', error);
      alert('שגיאה בטעינת הנתונים: ' + error.message);
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
      // Refresh all data to update balances
      await loadAllData();
    } catch (error) {
      console.error('Error loading child data:', error);
      alert('שגיאה בטעינת נתוני הילד: ' + error.message);
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
  const child2Balance = allData.children.child2?.balance || 0;

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
        <button 
          className="reset-button" 
          onClick={handleReset}
          disabled={resetting}
          title="איפוס כל היתרות והפעולות"
        >
          {resetting ? 'מאפס...' : '🔄 איפוס יתרות'}
        </button>
      </div>
      
      {/* Quick balance overview */}
      <div className="balance-overview">
        <div className="balance-card" style={{ borderColor: CHILD_COLORS.child1 }}>
          <h3>{allData.children.child1.name}</h3>
          <div className="balance-value" style={{ color: CHILD_COLORS.child1 }}>
            ₪{child1Balance.toFixed(2)}
          </div>
        </div>
        <div className="balance-card" style={{ borderColor: CHILD_COLORS.child2 }}>
          <h3>{allData.children.child2.name}</h3>
          <div className="balance-value" style={{ color: CHILD_COLORS.child2 }}>
            ₪{child2Balance.toFixed(2)}
          </div>
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
                <input
                  type="number"
                  id="amount"
                  step="0.01"
                  min="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                  placeholder="הכנס סכום"
                />
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
                    {CATEGORIES.map(cat => (
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

