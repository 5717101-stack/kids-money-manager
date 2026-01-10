// Client-side caching utility for improved performance
// This cache stores API responses in localStorage with TTL (Time To Live)

const CACHE_PREFIX = 'km_cache_';
const CACHE_TIMESTAMP_PREFIX = 'km_cache_ts_';
const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes default

// Check if cache is enabled (can be disabled for debugging)
const isCacheEnabled = () => {
  if (typeof window === 'undefined') return false;
  const disabled = localStorage.getItem('km_cache_disabled');
  return !disabled;
};

// Get cache key
const getCacheKey = (endpoint) => {
  return `${CACHE_PREFIX}${endpoint}`;
};

// Get timestamp key
const getTimestampKey = (endpoint) => {
  return `${CACHE_TIMESTAMP_PREFIX}${endpoint}`;
};

// Get cached data
export const getCached = (endpoint, ttl = DEFAULT_TTL) => {
  if (!isCacheEnabled()) return null;
  
  try {
    const cacheKey = getCacheKey(endpoint);
    const timestampKey = getTimestampKey(endpoint);
    
    const cachedData = localStorage.getItem(cacheKey);
    const cachedTimestamp = localStorage.getItem(timestampKey);
    
    if (!cachedData || !cachedTimestamp) {
      return null;
    }
    
    const now = Date.now();
    const timestamp = parseInt(cachedTimestamp, 10);
    const age = now - timestamp;
    
    // Check if cache is expired
    if (age > ttl) {
      // Cache expired, remove it
      localStorage.removeItem(cacheKey);
      localStorage.removeItem(timestampKey);
      return null;
    }
    
    // Return cached data
    return JSON.parse(cachedData);
  } catch (error) {
    // If there's an error, clear cache and return null
    console.warn('[CACHE] Error reading cache:', error);
    clearCache(endpoint);
    return null;
  }
};

// Set cached data
export const setCached = (endpoint, data, ttl = DEFAULT_TTL) => {
  if (!isCacheEnabled()) return;
  
  try {
    const cacheKey = getCacheKey(endpoint);
    const timestampKey = getTimestampKey(endpoint);
    
    localStorage.setItem(cacheKey, JSON.stringify(data));
    localStorage.setItem(timestampKey, Date.now().toString());
  } catch (error) {
    // If localStorage is full, try to clear old cache
    console.warn('[CACHE] Error writing cache:', error);
    try {
      clearOldCache();
      // Try again
      localStorage.setItem(cacheKey, JSON.stringify(data));
      localStorage.setItem(timestampKey, Date.now().toString());
    } catch (retryError) {
      console.warn('[CACHE] Failed to write cache after cleanup:', retryError);
    }
  }
};

// Clear cache for specific endpoint
export const clearCache = (endpoint) => {
  try {
    const cacheKey = getCacheKey(endpoint);
    const timestampKey = getTimestampKey(endpoint);
    localStorage.removeItem(cacheKey);
    localStorage.removeItem(timestampKey);
  } catch (error) {
    console.warn('[CACHE] Error clearing cache:', error);
  }
};

// Clear all cache
export const clearAllCache = () => {
  try {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith(CACHE_PREFIX) || key.startsWith(CACHE_TIMESTAMP_PREFIX)) {
        localStorage.removeItem(key);
      }
    });
  } catch (error) {
    console.warn('[CACHE] Error clearing all cache:', error);
  }
};

// Clear old cache entries (older than 1 hour)
const clearOldCache = () => {
  try {
    const keys = Object.keys(localStorage);
    const now = Date.now();
    const oneHour = 60 * 60 * 1000;
    
    keys.forEach(key => {
      if (key.startsWith(CACHE_TIMESTAMP_PREFIX)) {
        const timestamp = parseInt(localStorage.getItem(key), 10);
        if (now - timestamp > oneHour) {
          // Remove old cache entry
          const endpoint = key.replace(CACHE_TIMESTAMP_PREFIX, '');
          clearCache(endpoint);
        }
      }
    });
  } catch (error) {
    console.warn('[CACHE] Error clearing old cache:', error);
  }
};

// Invalidate cache for family (clear all cache entries related to a family)
export const invalidateFamilyCache = (familyId) => {
  try {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.includes(`families/${familyId}`)) {
        if (key.startsWith(CACHE_PREFIX)) {
          const endpoint = key.replace(CACHE_PREFIX, '');
          clearCache(endpoint);
        }
      }
    });
  } catch (error) {
    console.warn('[CACHE] Error invalidating family cache:', error);
  }
};

// Invalidate cache for child (clear all cache entries related to a child)
export const invalidateChildCache = (familyId, childId) => {
  try {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.includes(`families/${familyId}/children/${childId}`)) {
        if (key.startsWith(CACHE_PREFIX)) {
          const endpoint = key.replace(CACHE_PREFIX, '');
          clearCache(endpoint);
        }
      }
    });
  } catch (error) {
    console.warn('[CACHE] Error invalidating child cache:', error);
  }
};

// Prefetch data (load in background)
export const prefetch = async (endpoint, fetchFn, ttl = DEFAULT_TTL) => {
  try {
    // Check if already cached and fresh
    const cached = getCached(endpoint, ttl);
    if (cached) {
      return cached;
    }
    
    // Fetch in background
    const data = await fetchFn();
    if (data) {
      setCached(endpoint, data, ttl);
    }
    return data;
  } catch (error) {
    console.warn('[CACHE] Prefetch error:', error);
    return null;
  }
};

// Initialize cache cleanup on app start
if (typeof window !== 'undefined') {
  // Clear old cache entries on app start
  clearOldCache();
  
  // Clear old cache every hour
  setInterval(clearOldCache, 60 * 60 * 1000);
}
