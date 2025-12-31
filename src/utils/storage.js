const STORAGE_KEY = 'kids-money-manager';

// Initialize default data structure
const getDefaultData = () => ({
  children: {
    child1: {
      name: "אדם",
      balance: 0,
      transactions: []
    },
    child2: {
      name: "ג'וּן",
      balance: 0,
      transactions: []
    }
  }
});

// Get all data from localStorage
export const getData = () => {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (data) {
      const parsedData = JSON.parse(data);
      // Update names if they still have old default values
      if (parsedData.children) {
        if (parsedData.children.child1 && parsedData.children.child1.name === "ילד 1") {
          parsedData.children.child1.name = "אדם";
        }
        if (parsedData.children.child2 && parsedData.children.child2.name === "ילד 2") {
          parsedData.children.child2.name = "ג'וּן";
        }
        saveData(parsedData);
      }
      return parsedData;
    }
  } catch (error) {
    console.error('Error reading from localStorage:', error);
  }
  // Return default data if nothing exists
  const defaultData = getDefaultData();
  saveData(defaultData);
  return defaultData;
};

// Save all data to localStorage
export const saveData = (data) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (error) {
    console.error('Error saving to localStorage:', error);
  }
};

// Get child data
export const getChild = (childId) => {
  const data = getData();
  return data.children[childId] || null;
};

// Add transaction (deposit or expense)
export const addTransaction = (childId, type, amount, description) => {
  const data = getData();
  const child = data.children[childId];
  
  if (!child) {
    throw new Error(`Child ${childId} not found`);
  }

  const transaction = {
    id: crypto.randomUUID(),
    date: new Date().toISOString(),
    type: type, // 'deposit' or 'expense'
    amount: parseFloat(amount),
    description: description || '',
    childId: childId
  };

  child.transactions.push(transaction);
  
  // Recalculate balance
  child.balance = child.transactions.reduce((total, t) => {
    if (t.type === 'deposit') {
      return total + t.amount;
    } else {
      return total - t.amount;
    }
  }, 0);

  saveData(data);
  return transaction;
};

// Get transactions for a child (optionally limited)
export const getChildTransactions = (childId, limit = null) => {
  const child = getChild(childId);
  if (!child) return [];
  
  const transactions = [...child.transactions].sort((a, b) => 
    new Date(b.date) - new Date(a.date)
  );
  
  return limit ? transactions.slice(0, limit) : transactions;
};

