const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api';

// Helper function for API calls
async function apiCall(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
    console.error('API call error:', error);
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
export const addTransaction = async (childId, type, amount, description) => {
  const response = await apiCall('/transactions', {
    method: 'POST',
    body: JSON.stringify({
      childId,
      type,
      amount: parseFloat(amount),
      description: description || ''
    })
  });
  return response.transaction;
};

// Get transactions for a child (optionally limited)
export const getChildTransactions = async (childId, limit = null) => {
  const params = limit ? `?limit=${limit}` : '';
  const response = await apiCall(`/children/${childId}/transactions${params}`);
  return response.transactions || [];
};

