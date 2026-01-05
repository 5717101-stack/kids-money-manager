import React, { useState, useEffect } from 'react';
import { getChild, getChildTransactions, getExpensesByCategory, updateCashBoxBalance } from '../utils/api';
import BalanceDisplay from './BalanceDisplay';
import TransactionList from './TransactionList';
import ExpensePieChart from './ExpensePieChart';

const CHILD_COLORS = {
  child1: '#3b82f6', // כחול
  child2: '#ec4899'  // ורוד
};

const ChildView = ({ childId }) => {
  const [childData, setChildData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [expenses7Days, setExpenses7Days] = useState([]);
  const [expenses30Days, setExpenses30Days] = useState([]);

  useEffect(() => {
    loadChildData();
    // Refresh every 5 seconds to show updated balance
    const interval = setInterval(loadChildData, 5000);
    return () => clearInterval(interval);
  }, [childId]);

  const loadChildData = async () => {
    try {
      const child = await getChild(childId);
      if (child) {
        setChildData(child);
        // Show last 15 transactions
        const trans = await getChildTransactions(childId, 15);
        setTransactions(trans);
        
        // Load expense statistics
        const expenses7 = await getExpensesByCategory(childId, 7);
        const expenses30 = await getExpensesByCategory(childId, 30);
        setExpenses7Days(expenses7);
        setExpenses30Days(expenses30);
      }
    } catch (error) {
      console.error('Error loading child data:', error);
    }
  };

  const handleCashBoxUpdate = async (newValue) => {
    try {
      await updateCashBoxBalance(childId, newValue);
      await loadChildData();
    } catch (error) {
      alert('שגיאה בעדכון יתרת הקופה: ' + error.message);
      throw error; // Re-throw to let BalanceDisplay handle it
    }
  };

  if (!childData) {
    return <div className="loading">טוען...</div>;
  }

  const color = CHILD_COLORS[childId];

  return (
    <div className="child-view" style={{ borderColor: color }}>
      <div className="child-header">
        {childData.profileImage && (
          <img 
            src={childData.profileImage} 
            alt={childData.name}
            className="profile-image-large"
          />
        )}
        <h1>שלום {childData.name}! 👋</h1>
      </div>
      
      <BalanceDisplay
        balance={childData.balance}
        cashBoxBalance={childData.cashBoxBalance}
        childName={childData.name}
        color={color}
        editable={true}
        onCashBoxUpdate={handleCashBoxUpdate}
      />

      {/* Expense Charts */}
      <div className="charts-section">
        <ExpensePieChart 
          expensesByCategory={expenses7Days} 
          title="הוצאות ב-7 הימים האחרונים"
          days={7}
        />
        <ExpensePieChart 
          expensesByCategory={expenses30Days} 
          title="הוצאות ב-30 הימים האחרונים"
          days={30}
        />
      </div>

      <TransactionList transactions={transactions} showAll={false} />
    </div>
  );
};

export default ChildView;

