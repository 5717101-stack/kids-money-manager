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
  
  // Fallback
  console.warn('VITE_API_URL not set! Please configure it in Vercel environment variables.');
  return 'http://localhost:3001/api';
};

const API_BASE_URL = getApiUrl();

// Helper function for API calls
async function apiCall(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
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

// Get all children data for a family
export const getData = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/children`);
  return {
    children: response.children
  };
};

// Get child data
export const getChild = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}`);
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
export const addTransaction = async (familyId, childId, type, amount, description, category = null) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/transactions`, {
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
    throw new Error(error.message || 'Failed to add transaction');
  }
};

// Get transactions for a child (optionally limited)
export const getChildTransactions = async (familyId, childId, limit = null) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const params = limit ? `?limit=${limit}` : '';
  const response = await apiCall(`/families/${familyId}/children/${childId}/transactions${params}`);
  return response.transactions || [];
};

// Get expenses by category for a child
export const getExpensesByCategory = async (familyId, childId, days = 30) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/expenses-by-category?days=${days}`);
  return response.expensesByCategory || [];
};

// Update cash box balance for a child
export const updateCashBoxBalance = async (familyId, childId, cashBoxBalance) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/children/${childId}/cashbox`, {
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
export const getCategories = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/categories`);
  return response.categories || [];
};

export const addCategory = async (familyId, name, activeFor = []) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/categories`, {
    method: 'POST',
    body: JSON.stringify({ name, activeFor })
  });
  return response.category;
};

export const updateCategory = async (familyId, categoryId, name, activeFor) => {
  if (!familyId || !categoryId) {
    throw new Error('Family ID and Category ID are required');
  }
  const response = await apiCall(`/families/${familyId}/categories/${categoryId}`, {
    method: 'PUT',
    body: JSON.stringify({ name, activeFor })
  });
  return response;
};

export const deleteCategory = async (familyId, categoryId) => {
  if (!familyId || !categoryId) {
    throw new Error('Family ID and Category ID are required');
  }
  const response = await apiCall(`/families/${familyId}/categories/${categoryId}`, {
    method: 'DELETE'
  });
  return response;
};

// Profile image API
export const updateProfileImage = async (familyId, childId, profileImage) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/children/${childId}/profile-image`, {
      method: 'PUT',
      body: JSON.stringify({ profileImage })
    });
    return response;
  } catch (error) {
    console.error('updateProfileImage error:', error);
    throw error;
  }
};

// Weekly allowance API
export const updateWeeklyAllowance = async (familyId, childId, weeklyAllowance, allowanceType, allowanceDay, allowanceTime) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/weekly-allowance`, {
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
export const payWeeklyAllowance = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/pay-allowance`, {
    method: 'POST'
  });
  return response;
};

// Create child
export const createChild = async (familyId, name) => {
  if (!familyId || !name) {
    throw new Error('Family ID and name are required');
  }
  const response = await apiCall(`/families/${familyId}/children`, {
    method: 'POST',
    body: JSON.stringify({ name })
  });
  return response;
};

// Get child password (for recovery)
export const getChildPassword = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/password`);
  return response.password;
};
