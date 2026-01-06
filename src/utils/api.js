// Get API URL - check if we're in production, development, or mobile app
const getApiUrl = () => {
  // Production API URL
  const PRODUCTION_API = 'https://kids-money-manager-production.up.railway.app/api';
  
  // If we're in a mobile app (Capacitor)
  if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
    return PRODUCTION_API;
  }
  
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
    balance: response.balance || 0,
    cashBoxBalance: response.cashBoxBalance || 0,
    profileImage: response.profileImage || null,
    weeklyAllowance: response.weeklyAllowance || 0,
    allowanceType: response.allowanceType || 'weekly',
    allowanceDay: response.allowanceDay !== undefined ? response.allowanceDay : 1,
    allowanceTime: response.allowanceTime || '08:00',
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

// Update cash box balance for a child
export const updateCashBoxBalance = async (childId, cashBoxBalance) => {
  try {
    const response = await apiCall(`/children/${childId}/cashbox`, {
      method: 'PUT',
      body: JSON.stringify({
        cashBoxBalance: parseFloat(cashBoxBalance)
      })
    });
    return response;
  } catch (error) {
    console.error('updateCashBoxBalance error:', error);
    throw new Error(error.message || 'Failed to update cash box balance');
  }
};

// Categories API
export const getCategories = async () => {
  const response = await apiCall('/categories');
  return response.categories || [];
};

export const addCategory = async (name, activeFor = []) => {
  const response = await apiCall('/categories', {
    method: 'POST',
    body: JSON.stringify({ name, activeFor })
  });
  return response.category;
};

export const updateCategory = async (categoryId, name, activeFor) => {
  const response = await apiCall(`/categories/${categoryId}`, {
    method: 'PUT',
    body: JSON.stringify({ name, activeFor })
  });
  return response;
};

export const deleteCategory = async (categoryId) => {
  const response = await apiCall(`/categories/${categoryId}`, {
    method: 'DELETE'
  });
  return response;
};

// Profile image API
export const updateProfileImage = async (childId, profileImage) => {
  try {
    console.log('Calling updateProfileImage for', childId, 'image length:', profileImage ? profileImage.length : 0);
    const response = await apiCall(`/children/${childId}/profile-image`, {
      method: 'PUT',
      body: JSON.stringify({ profileImage })
    });
    console.log('updateProfileImage response:', response);
    return response;
  } catch (error) {
    console.error('updateProfileImage error:', error);
    throw error;
  }
};

// Weekly allowance API
export const updateWeeklyAllowance = async (childId, weeklyAllowance, allowanceType, allowanceDay, allowanceTime) => {
  const response = await apiCall(`/children/${childId}/weekly-allowance`, {
    method: 'PUT',
    body: JSON.stringify({ 
      weeklyAllowance: parseFloat(weeklyAllowance),
      allowanceType: allowanceType || 'weekly',
      allowanceDay: allowanceDay !== undefined ? parseInt(allowanceDay) : 1,
      allowanceTime: allowanceTime || '08:00'
    })
  });
  return response;
};

// Manually pay weekly allowance
export const payWeeklyAllowance = async (childId) => {
  const response = await apiCall(`/children/${childId}/pay-allowance`, {
    method: 'POST'
  });
  return response;
};

