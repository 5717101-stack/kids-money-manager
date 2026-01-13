// Import cache utilities
import { getCached, setCached, clearCache, invalidateFamilyCache, invalidateChildCache } from './cache.js';

// Get API URL - check if we're in production, development, or mobile app
const getApiUrl = () => {
  // Production API URL (Render)
  const PRODUCTION_API = 'https://kids-money-manager-server.onrender.com/api';
  
  // If we're in a mobile app (Capacitor)
  if (typeof window !== 'undefined' && window.Capacitor?.isNativePlatform()) {
    // In native app, always use Render URL directly
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
  return PRODUCTION_API;
};

const API_BASE_URL = getApiUrl();

// Helper function for API calls with caching
async function apiCall(endpoint, options = {}, cacheOptions = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const method = options.method || 'GET';
  const useCache = cacheOptions.useCache !== false && method === 'GET';
  const cacheTTL = cacheOptions.cacheTTL || (5 * 60 * 1000); // 5 minutes default
  
  // Check cache for GET requests
  if (useCache) {
    const cached = getCached(endpoint, cacheTTL);
    if (cached !== null) {
      return cached;
    }
  }
  
  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds timeout
  
  try {
    let response;
    try {
      const fetchOptions = {
        method,
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
      
      response = await fetch(url, fetchOptions);
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
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
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    // Cache successful GET responses
    if (useCache && data) {
      setCached(endpoint, data, cacheTTL);
    }
    
    return data;
  } catch (error) {
    // Only log errors in development
    if (import.meta.env.DEV) {
      console.error('[API] Error:', endpoint, error.message);
    }
    
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

// Get all children data for a family (with cache)
export const getData = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/children`, {}, { 
      useCache: true, 
      cacheTTL: 2 * 60 * 1000 // 2 minutes cache
    });
    // Ensure response has children property
    if (!response || typeof response !== 'object') {
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
    // Return empty children object instead of throwing
    return { children: {} };
  }
};

// Get child data (with cache)
export const getChild = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}`, {}, {
    useCache: true,
    cacheTTL: 1 * 60 * 1000 // 1 minute cache
  });
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
  if (!familyId || !childId || !name || !phoneNumber) {
    throw new Error('Family ID, Child ID, name, and phone number are required');
  }
  
  try {
    const requestBody = { name: name.trim(), phoneNumber: phoneNumber.trim() };
    
    const response = await apiCall(`/families/${familyId}/children/${childId}`, {
      method: 'PUT',
      body: requestBody
    }, { useCache: false });
    
    // Invalidate cache for this child and family
    invalidateChildCache(familyId, childId);
    invalidateFamilyCache(familyId);
    
    return response;
  } catch (error) {
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
    }, { useCache: false });
    
    // Invalidate cache for this child and family
    invalidateChildCache(familyId, childId);
    invalidateFamilyCache(familyId);
    
    return response.transaction;
  } catch (error) {
    throw new Error(error.message || 'Failed to add transaction');
  }
};

// Get transactions for a child (optionally limited, with cache)
export const getChildTransactions = async (familyId, childId, limit = null) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const params = limit ? `?limit=${limit}` : '';
  const response = await apiCall(`/families/${familyId}/children/${childId}/transactions${params}`, {}, {
    useCache: true,
    cacheTTL: 1 * 60 * 1000 // 1 minute cache
  });
  return response.transactions || [];
};

// Get expenses by category for a child (with cache)
// Get expenses by category (with caching)
export const getExpensesByCategory = async (familyId, childId, days = 30) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/expenses-by-category?days=${days}`, {}, {
    useCache: true,
    cacheTTL: 2 * 60 * 1000 // 2 minutes cache
  });
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
    }, { useCache: false });
    
    // Invalidate cache
    invalidateChildCache(familyId, childId);
    invalidateFamilyCache(familyId);
    
    return response;
  } catch (error) {
    throw new Error(error.message || 'Failed to update cash box balance');
  }
};

// Categories API (with cache)
export const getCategories = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/categories`, {}, {
    useCache: true,
    cacheTTL: 5 * 60 * 1000 // 5 minutes cache (categories don't change often)
  });
  return response.categories || [];
};

export const addCategory = async (familyId, name, activeFor = []) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/categories`, {
    method: 'POST',
    body: JSON.stringify({ name, activeFor })
  }, { useCache: false });
  
  // Invalidate categories cache
  clearCache(`/families/${familyId}/categories`);
  
  return response.category;
};

export const updateCategory = async (familyId, categoryId, name, activeFor) => {
  if (!familyId || !categoryId) {
    throw new Error('Family ID and Category ID are required');
  }
  const response = await apiCall(`/families/${familyId}/categories/${categoryId}`, {
    method: 'PUT',
    body: JSON.stringify({ name, activeFor })
  }, { useCache: false });
  
  // Invalidate categories cache
  clearCache(`/families/${familyId}/categories`);
  
  return response;
};

export const deleteCategory = async (familyId, categoryId) => {
  if (!familyId || !categoryId) {
    throw new Error('Family ID and Category ID are required');
  }
  const response = await apiCall(`/families/${familyId}/categories/${categoryId}`, {
    method: 'DELETE'
  }, { useCache: false });
  
  // Invalidate categories cache
  clearCache(`/families/${familyId}/categories`);
  
  return response;
};

// Tasks API
export const getTasks = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/tasks`, {}, {
    useCache: true,
    cacheTTL: 5 * 60 * 1000 // 5 minutes cache
  });
  return response.tasks || [];
};

export const addTask = async (familyId, name, price, activeFor = []) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/tasks`, {
    method: 'POST',
    body: JSON.stringify({ name, price, activeFor })
  }, { useCache: false });
  
  // Invalidate tasks cache
  clearCache(`/families/${familyId}/tasks`);
  
  return response.task;
};

export const updateTask = async (familyId, taskId, name, price, activeFor) => {
  if (!familyId || !taskId) {
    throw new Error('Family ID and Task ID are required');
  }
  const response = await apiCall(`/families/${familyId}/tasks/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify({ name, price, activeFor })
  }, { useCache: false });
  
  // Invalidate tasks cache
  clearCache(`/families/${familyId}/tasks`);
  
  return response;
};

export const deleteTask = async (familyId, taskId) => {
  if (!familyId || !taskId) {
    throw new Error('Family ID and Task ID are required');
  }
  const response = await apiCall(`/families/${familyId}/tasks/${taskId}`, {
    method: 'DELETE'
  }, { useCache: false });
  
  // Invalidate tasks cache
  clearCache(`/families/${familyId}/tasks`);
  
  return response;
};

// Payment Requests API
export const requestTaskPayment = async (familyId, taskId, childId, note, image) => {
  if (!familyId || !taskId || !childId) {
    throw new Error('Family ID, Task ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/tasks/${taskId}/request-payment`, {
    method: 'POST',
    body: JSON.stringify({ childId, note, image })
  }, { useCache: false });
  
  // Invalidate payment requests cache
  clearCache(`/families/${familyId}/payment-requests`);
  invalidateFamilyCache(familyId);
  
  return response.paymentRequest;
};

export const getPaymentRequests = async (familyId, status = null) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const params = status ? `?status=${status}` : '';
  const response = await apiCall(`/families/${familyId}/payment-requests${params}`, {}, {
    useCache: true,
    cacheTTL: 1 * 60 * 1000 // 1 minute cache
  });
  return response.paymentRequests || [];
};

export const approvePaymentRequest = async (familyId, requestId) => {
  if (!familyId || !requestId) {
    throw new Error('Family ID and Request ID are required');
  }
  const response = await apiCall(`/families/${familyId}/payment-requests/${requestId}/approve`, {
    method: 'PUT'
  }, { useCache: false });
  
  // Invalidate caches
  clearCache(`/families/${familyId}/payment-requests`);
  invalidateFamilyCache(familyId);
  
  return response;
};

export const rejectPaymentRequest = async (familyId, requestId) => {
  if (!familyId || !requestId) {
    throw new Error('Family ID and Request ID are required');
  }
  const response = await apiCall(`/families/${familyId}/payment-requests/${requestId}/reject`, {
    method: 'PUT'
  }, { useCache: false });
  
  // Invalidate caches
  clearCache(`/families/${familyId}/payment-requests`);
  invalidateFamilyCache(familyId);
  
  return response;
};

export const getTaskHistory = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}/tasks/history`, {}, {
    useCache: true,
    cacheTTL: 2 * 60 * 1000 // 2 minutes cache
  });
  return response.history || [];
};

export const updatePaymentRequestStatus = async (familyId, requestId, status) => {
  if (!familyId || !requestId || !status) {
    throw new Error('Family ID, Request ID and Status are required');
  }
  const response = await apiCall(`/families/${familyId}/payment-requests/${requestId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status })
  }, { useCache: false });
  
  // Invalidate caches
  clearCache(`/families/${familyId}/payment-requests`);
  clearCache(`/families/${familyId}/tasks/history`);
  invalidateFamilyCache(familyId);
  
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
    }, { useCache: false });
    
    // Invalidate cache
    invalidateChildCache(familyId, childId);
    invalidateFamilyCache(familyId);
    
    return response;
  } catch (error) {
    throw error;
  }
};

// Weekly allowance API
export const updateWeeklyAllowance = async (familyId, childId, weeklyAllowance, allowanceType, allowanceDay, allowanceTime, weeklyInterestRate) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const body = { 
    weeklyAllowance: parseFloat(weeklyAllowance),
    allowanceType: allowanceType || 'weekly',
    allowanceDay: allowanceDay !== undefined ? parseInt(allowanceDay) : 1,
    allowanceTime: allowanceTime || '08:00'
  };
  
  if (weeklyInterestRate !== undefined && weeklyInterestRate !== null && weeklyInterestRate !== '') {
    body.weeklyInterestRate = parseFloat(weeklyInterestRate);
  }
  
  const response = await apiCall(`/families/${familyId}/children/${childId}/weekly-allowance`, {
    method: 'PUT',
    body: JSON.stringify(body)
  }, { useCache: false });
  
  // Invalidate cache
  invalidateChildCache(familyId, childId);
  invalidateFamilyCache(familyId);
  
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
  }, { useCache: false });
  
  // Invalidate cache to ensure fresh data is loaded
  invalidateFamilyCache(familyId);
  
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

// Savings Goals API (with cache)
export const getSavingsGoal = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/savings-goal`, {}, {
    useCache: true,
    cacheTTL: 2 * 60 * 1000 // 2 minutes cache
  });
  return response.savingsGoal;
};

export const updateSavingsGoal = async (familyId, childId, name, targetAmount) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/savings-goal`, {
    method: 'PUT',
    body: JSON.stringify({ name, targetAmount: parseFloat(targetAmount) })
  }, { useCache: false });
  
  // Invalidate cache
  clearCache(`/families/${familyId}/children/${childId}/savings-goal`);
  invalidateChildCache(familyId, childId);
  
  return response.savingsGoal;
};

export const deleteSavingsGoal = async (familyId, childId) => {
  if (!familyId || !childId) {
    throw new Error('Family ID and Child ID are required');
  }
  const response = await apiCall(`/families/${familyId}/children/${childId}/savings-goal`, {
    method: 'DELETE'
  }, { useCache: false });
  
  // Invalidate cache
  clearCache(`/families/${familyId}/children/${childId}/savings-goal`);
  invalidateChildCache(familyId, childId);
  
  return response;
};

// Family/Parents API (with cache)
export const getFamilyInfo = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  const response = await apiCall(`/families/${familyId}`, {}, {
    useCache: true,
    cacheTTL: 5 * 60 * 1000 // 5 minutes cache
  });
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
    }, { useCache: false });
    
    // Invalidate cache
    clearCache(`/families/${familyId}`);
    invalidateFamilyCache(familyId);
    
    return response;
  } catch (error) {
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
  }, { useCache: false });
  
  // Invalidate cache for family data after adding parent
  invalidateFamilyCache(familyId);
  
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
    }, { useCache: false });
    
    // Invalidate all related cache
    invalidateChildCache(familyId, childId);
    invalidateFamilyCache(familyId);
    
    return response;
  } catch (error) {
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
    }, { useCache: false });
    
    // Invalidate cache
    clearCache(`/families/${familyId}`);
    invalidateFamilyCache(familyId);
    
    return response;
  } catch (error) {
    throw new Error(error.message || 'Failed to archive parent');
  }
};

// Archive entire family
export const archiveFamily = async (familyId) => {
  if (!familyId) {
    throw new Error('Family ID is required');
  }
  try {
    const response = await apiCall(`/families/${familyId}/archive`, {
      method: 'POST'
    }, { useCache: false });
    
    // Clear all cache
    invalidateFamilyCache(familyId);
    
    return response;
  } catch (error) {
    throw new Error(error.message || 'Failed to archive family');
  }
};
