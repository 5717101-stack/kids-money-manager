// Get API URL - check if we're in production, development, or mobile app
const getApiUrl = () => {
  // Production API URL (Render)
  const PRODUCTION_API = 'https://kids-money-manager-server.onrender.com/api';
  
  // If we're in a mobile app (Capacitor)
  if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
    // In native app, always use Render URL directly
    console.log('[API] Using Render API URL for native app:', PRODUCTION_API);
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
  console.warn('[API] VITE_API_URL not set, using Render fallback:', PRODUCTION_API);
  return PRODUCTION_API;
};

const API_BASE_URL = getApiUrl();

// Helper function for API calls
async function apiCall(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds timeout
  
  try {
    let response;
    try {
      const fetchOptions = {
        method: options.method || 'GET',
        mode: 'cors',
        credentials: 'omit',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...options.headers
        },
        signal: controller.signal,
        ...options
      };
      
      // Set body after spreading options to ensure it's not overridden
      if (options.body) {
        fetchOptions.body = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
      }
      
      console.log('[API] Fetch options:', {
        method: fetchOptions.method,
        url: url,
        hasBody: !!fetchOptions.body,
        bodyType: typeof fetchOptions.body,
        bodyPreview: fetchOptions.body ? (typeof fetchOptions.body === 'string' ? fetchOptions.body.substring(0, 100) : JSON.stringify(fetchOptions.body).substring(0, 100)) : 'none'
      });
      
      response = await fetch(url, fetchOptions);
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      console.error('[API] Fetch error details:', {
        name: fetchError.name,
        message: fetchError.message,
        stack: fetchError.stack,
        url: url,
        isNative: typeof window !== 'undefined' && window.Capacitor?.isNativePlatform(),
        apiBaseUrl: API_BASE_URL
      });
      
      // Handle specific iOS/WebView errors
      if (fetchError.name === 'TypeError' && (fetchError.message === 'Load failed' || fetchError.message.includes('Failed to fetch'))) {
        const errorMsg = typeof window !== 'undefined' && window.Capacitor?.isNativePlatform() 
          ? `שגיאת רשת ב-iOS: לא ניתן להתחבר לשרת.\nURL: ${url}\nודא שהשרת רץ ב-Render.`
          : `לא ניתן להתחבר לשרת. בדוק:\n1. שהשרת רץ ב-Render\n2. ש-VITE_API_URL מוגדר ב-Vercel: ${API_BASE_URL}\n3. שהכתובת נכונה ומסתיימת ב-/api`;
        throw new Error(errorMsg);
      }
      if (fetchError.name === 'AbortError') {
        throw new Error('הבקשה בוטלה: השרת לא הגיב בזמן. נסה שוב.');
      }
      throw fetchError;
    }

    if (!response.ok) {
      let errorData;
      try {
        const text = await response.text();
        try {
          errorData = JSON.parse(text);
        } catch {
          errorData = { error: text || `HTTP error! status: ${response.status}` };
        }
      } catch (e) {
        errorData = { error: `HTTP error! status: ${response.status}` };
      }
      console.error('[API] Response error:', {
        status: response.status,
        statusText: response.statusText,
        error: errorData,
        url: url
      });
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[API] API call error:', {
      url,
      error: error.message,
      apiBaseUrl: API_BASE_URL,
      envVar: import.meta.env.VITE_API_URL,
      isNative: typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()
    });
    
    // Don't override the error if it's already a custom error message
    if (error.message && (error.message.includes('שגיאת רשת') || error.message.includes('הבקשה בוטלה'))) {
      throw error;
    }
    
    if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
      const errorMsg = typeof window !== 'undefined' && window.Capacitor?.isNativePlatform() 
        ? `שגיאת רשת ב-iOS: לא ניתן להתחבר לשרת.\nURL: ${url}\nודא שהשרת רץ ב-Render.`
        : `לא ניתן להתחבר לשרת. בדוק:\n1. שהשרת רץ ב-Render\n2. ש-VITE_API_URL מוגדר ב-Vercel: ${API_BASE_URL}\n3. שהכתובת נכונה ומסתיימת ב-/api`;
      throw new Error(errorMsg);
    }
    
    throw error;
  }
}

// Get all children data for a family
export const getData = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/children`);
    // Ensure response has children property
    if (!response || typeof response !== 'object') {
      console.error('[API] Invalid response from getData:', response);
      return { children: {} };
    }
    // Ensure children is an object (not array)
    if (Array.isArray(response.children)) {
      // Convert array to object if needed
      const childrenObj = {};
      response.children.forEach((child, index) => {
        if (child._id) {
          childrenObj[child._id] = child;
        }
      });
      return { children: childrenObj };
    }
    return {
      children: response.children || {}
    };
  } catch (error) {
    console.error('[API] Error in getData:', error);
    // Return empty children object instead of throwing
    return { children: {} };
  }
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

// Update child (name and phone number)
export const updateChild = async (familyId, childId, name, phoneNumber) => {
  console.log('[UPDATE-CHILD-API] Starting updateChild:', {
    familyId,
    childId,
    name: name.trim(),
    phoneNumber: phoneNumber.trim()
  });
  
  if (!familyId || !childId || !name || !phoneNumber) {
    const error = 'Family ID, Child ID, name, and phone number are required';
    console.error('[UPDATE-CHILD-API] Validation error:', error);
    throw new Error(error);
  }
  
  try {
    const requestBody = { name: name.trim(), phoneNumber: phoneNumber.trim() };
    console.log('[UPDATE-CHILD-API] Request body:', requestBody);
    
    const response = await apiCall(`/families/${familyId}/children/${childId}`, {
      method: 'PUT',
      body: requestBody
    });
    
    console.log('[UPDATE-CHILD-API] Response received:', response);
    return response;
  } catch (error) {
    console.error('[UPDATE-CHILD-API] Error in updateChild:', {
      error: error,
      message: error.message,
      stack: error.stack
    });
    throw error;
  }
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
export const createChild = async (familyId, name, phoneNumber) => {
  if (!familyId || !name || !phoneNumber) {
    throw new Error('Family ID, name, and phone number are required');
  }
  const response = await apiCall(`/families/${familyId}/children`, {
    method: 'POST',
    body: JSON.stringify({ name, phoneNumber })
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

// Savings Goals API
export const getSavingsGoal = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/savings-goal`);
  return response.savingsGoal;
};

export const updateSavingsGoal = async (familyId, childId, name, targetAmount) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/savings-goal`, {
    method: 'PUT',
    body: JSON.stringify({ name, targetAmount: parseFloat(targetAmount) })
  });
  return response.savingsGoal;
};

export const deleteSavingsGoal = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/savings-goal`, {
    method: 'DELETE'
  });
  return response;
};

// Family/Parents API
export const getFamilyInfo = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}`);
  return response;
};

export const updateParentInfo = async (familyId, name, phoneNumber, isMain = true) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/parent`, {
    method: 'PUT',
    body: JSON.stringify({ name, phoneNumber, isMain })
  });
  return response;
};

// Update parent profile image
export const updateParentProfileImage = async (familyId, profileImage) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/parent/profile-image`, {
      method: 'PUT',
      body: JSON.stringify({ profileImage })
    });
    return response;
  } catch (error) {
    console.error('updateParentProfileImage error:', error);
    throw new Error(error.message || 'Failed to update parent profile image');
  }
};

export const addParent = async (familyId, name, phoneNumber) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  if (!name || !phoneNumber) {
    throw new Error('Parent name and phone number are required');
  }
  const response = await apiCall(`/families/${familyId}/parent`, {
    method: 'POST',
    body: JSON.stringify({ name, phoneNumber })
  });
  return response;
};

// Admin functions
export const getAllUsers = async () => {
  return await apiCall('/admin/all-users');
};

export const deleteFamily = async (familyId) => {
  return await apiCall(`/admin/families/${familyId}`, {
    method: 'DELETE'
  });
};

export const deleteChild = async (familyId, childId) => {
  return await apiCall(`/admin/families/${familyId}/children/${childId}`, {
    method: 'DELETE'
  });
};

export const archiveChild = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/children/${childId}/archive`, {
      method: 'POST'
    });
    return response;
  } catch (error) {
    console.error('archiveChild error:', error);
    throw new Error(error.message || 'Failed to archive child');
  }
};

export const archiveParent = async (familyId, parentIndex, isMain) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/parent/archive`, {
      method: 'POST',
      body: JSON.stringify({ parentIndex, isMain })
    });
    return response;
  } catch (error) {
    console.error('archiveParent error:', error);
    throw new Error(error.message || 'Failed to archive parent');
  }
};
