import React, { useState, useEffect } from 'react';
import { getChild, getChildTransactions } from '../utils/api';
import BalanceDisplay from './BalanceDisplay';
import TransactionList from './TransactionList';

const CHILD_COLORS = {
  child1: '#3b82f6', // כחול
  child2: '#ec4899'  // ורוד
};

const ChildView = ({ childId }) => {
  const [childData, setChildData] = useState(null);
  const [transactions, setTransactions] = useState([]);

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
      }
    } catch (error) {
      console.error('Error loading child data:', error);
    }
  };

  if (!childData) {
    return <div className="loading">טוען...</div>;
  }

  const color = CHILD_COLORS[childId];

  return (
    <div className="child-view" style={{ borderColor: color }}>
      <div className="child-header">
        <h1>שלום {childData.name}! 👋</h1>
      </div>
      
      <BalanceDisplay
        balance={childData.balance}
        childName={childData.name}
        color={color}
      />

      <TransactionList transactions={transactions} showAll={false} />
    </div>
  );
};

export default ChildView;

