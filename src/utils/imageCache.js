/**
 * Image caching utility using IndexedDB for local storage
 * This improves performance by storing images locally and avoiding repeated server requests
 */

const DB_NAME = 'kidsMoneyManager';
const DB_VERSION = 1;
const STORE_NAME = 'images';

let db = null;

// Initialize IndexedDB
const initDB = () => {
  return new Promise((resolve, reject) => {
    if (db) {
      resolve(db);
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      console.error('[IMAGE-CACHE] Failed to open IndexedDB');
      reject(request.error);
    };

    request.onsuccess = () => {
      db = request.result;
      resolve(db);
    };

    request.onupgradeneeded = (event) => {
      const database = event.target.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME, { keyPath: 'key' });
      }
    };
  });
};

// Get image from cache
export const getCachedImage = async (key) => {
  try {
    const database = await initDB();
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.get(key);

      request.onsuccess = () => {
        if (request.result) {
          // Check if cache is still valid (7 days)
          const cacheAge = Date.now() - request.result.timestamp;
          const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
          
          if (cacheAge < maxAge) {
            resolve(request.result.data);
          } else {
            // Cache expired, remove it
            deleteCachedImage(key);
            resolve(null);
          }
        } else {
          resolve(null);
        }
      };

      request.onerror = () => {
        console.warn('[IMAGE-CACHE] Error reading from cache:', request.error);
        resolve(null); // Don't fail, just return null
      };
    });
  } catch (error) {
    console.warn('[IMAGE-CACHE] Error accessing IndexedDB:', error);
    return null;
  }
};

// Save image to cache
export const setCachedImage = async (key, imageData) => {
  try {
    const database = await initDB();
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.put({
        key,
        data: imageData,
        timestamp: Date.now()
      });

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        console.warn('[IMAGE-CACHE] Error writing to cache:', request.error);
        resolve(); // Don't fail, just continue
      };
    });
  } catch (error) {
    console.warn('[IMAGE-CACHE] Error accessing IndexedDB:', error);
    // Don't throw - caching is optional
  }
};

// Delete image from cache
export const deleteCachedImage = async (key) => {
  try {
    const database = await initDB();
    return new Promise((resolve) => {
      const transaction = database.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.delete(key);

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        console.warn('[IMAGE-CACHE] Error deleting from cache:', request.error);
        resolve(); // Don't fail
      };
    });
  } catch (error) {
    console.warn('[IMAGE-CACHE] Error accessing IndexedDB:', error);
  }
};

// Clear all cached images
export const clearImageCache = async () => {
  try {
    const database = await initDB();
    return new Promise((resolve) => {
      const transaction = database.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.clear();

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        console.warn('[IMAGE-CACHE] Error clearing cache:', request.error);
        resolve();
      };
    });
  } catch (error) {
    console.warn('[IMAGE-CACHE] Error accessing IndexedDB:', error);
  }
};

// Get cache key for image
export const getImageCacheKey = (familyId, childId = null, isParent = false) => {
  if (isParent) {
    return `profile_${familyId}_parent`;
  }
  if (childId) {
    return `profile_${familyId}_child_${childId}`;
  }
  return null;
};
