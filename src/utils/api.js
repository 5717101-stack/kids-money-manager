// Get API URL - check if we're in production or development
const getApiUrl = () => {
  // In production (Vercel), use the environment variable
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // In development, use localhost
  if (import.meta.env.DEV) {
    return 'http://localhost:3001/api';
  }
  
  // Fallback - try to detect if we're on a deployed frontend
  // If frontend is on Vercel but API URL not set, this will fail
  // User needs to set VITE_API_URL in Vercel
  console.warn('VITE_API_URL not set! Please configure it in Vercel environment variables.');
  return 'http://localhost:3001/api';
};

const API_BASE_URL = getApiUrl();

// Helper function for API calls
async function apiCall(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  console.log('API Call:', url); // Debug log
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API call error:', {
      url,
      error: error.message,
      apiBaseUrl: API_BASE_URL,
      envVar: import.meta.env.VITE_API_URL
    });
    
    // Provide more helpful error message
    if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
      throw new Error(
        `לא ניתן להתחבר לשרת. בדוק:\n` +
        `1. שהשרת רץ ב-Railway\n` +
        `2. ש-VITE_API_URL מוגדר ב-Vercel: ${API_BASE_URL}\n` +
        `3. שהכתובת נכונה ומסתיימת ב-/api`
      );
    }
    
    throw error;
  }
}

// Get all children data
export const getData = async () => {
  const response = await apiCall('/children');
  return {
    children: response.children
  };
};

// Get child data
export const getChild = async (childId) => {
  const response = await apiCall(`/children/${childId}`);
  return {
    name: response.name,
    balance: response.balance,
    transactions: response.transactions || []
  };
};

// Add transaction (deposit or expense)
export const addTransaction = async (childId, type, amount, description, category = null) => {
  try {
    const response = await apiCall('/transactions', {
      method: 'POST',
      body: JSON.stringify({
        childId,
        type,
        amount: parseFloat(amount),
        description: description || '',
        category: category || null
      })
    });
    return response.transaction;
  } catch (error) {
    console.error('addTransaction error:', error);
    // Re-throw with more details
    throw new Error(error.message || 'Failed to add transaction');
  }
};

// Get transactions for a child (optionally limited)
export const getChildTransactions = async (childId, limit = null) => {
  const params = limit ? `?limit=${limit}` : '';
  const response = await apiCall(`/children/${childId}/transactions${params}`);
  return response.transactions || [];
};

// Reset all data (balances and transactions)
export const resetAllData = async () => {
  const response = await apiCall('/reset', {
    method: 'POST'
  });
  return response;
};

// Get expenses by category for a child
export const getExpensesByCategory = async (childId, days = 30) => {
  const response = await apiCall(`/children/${childId}/expenses-by-category?days=${days}`);
  return response.expensesByCategory || [];
};

