import React, { useState, useEffect, useRef } from 'react';
import { getCategories, addCategory, updateCategory, deleteCategory, getData, updateProfileImage, updateWeeklyAllowance, payWeeklyAllowance } from '../utils/api';

const CHILD_COLORS = {
  child1: '#3b82f6', // כחול
  child2: '#ec4899'  // ורוד
};

const CHILD_NAMES = {
  child1: 'אדם',
  child2: 'ג\'וּן'
};

const Settings = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState('categories'); // 'categories', 'profileImages', 'allowances'
  const [categories, setCategories] = useState([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [editingCategory, setEditingCategory] = useState(null);
  const [allData, setAllData] = useState({ children: {} });
  const [loading, setLoading] = useState(true);
  const [allowanceStates, setAllowanceStates] = useState({});
  const [uploadingImages, setUploadingImages] = useState({});
  const fileInputRefs = useRef({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [categoriesData, childrenData] = await Promise.all([
        getCategories(),
        getData()
      ]);
      setCategories(categoriesData);
      setAllData(childrenData);
      
      // Initialize allowance states
      const states = {};
      ['child1', 'child2'].forEach(childId => {
        const child = childrenData.children[childId];
        if (child) {
          states[childId] = {
            amount: child.weeklyAllowance || 0,
            type: child.allowanceType || 'weekly',
            day: child.allowanceDay !== undefined ? child.allowanceDay : 1,
            time: child.allowanceTime || '08:00'
          };
        }
      });
      setAllowanceStates(states);
    } catch (error) {
      console.error('Error loading settings data:', error);
      alert('שגיאה בטעינת הנתונים: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCategory = async (e) => {
    e.preventDefault();
    if (!newCategoryName.trim()) {
      alert('אנא הכנס שם קטגוריה');
      return;
    }

    try {
      const category = await addCategory(newCategoryName.trim(), ['child1', 'child2']);
      setCategories([...categories, category]);
      setNewCategoryName('');
    } catch (error) {
      alert('שגיאה בהוספת קטגוריה: ' + error.message);
    }
  };

  const handleUpdateCategory = async (categoryId, name, activeFor) => {
    try {
      await updateCategory(categoryId, name, activeFor);
      setCategories(categories.map(cat => 
        cat._id === categoryId ? { ...cat, name, activeFor } : cat
      ));
      setEditingCategory(null);
    } catch (error) {
      alert('שגיאה בעדכון קטגוריה: ' + error.message);
    }
  };

  const handleDeleteCategory = async (categoryId) => {
    if (!window.confirm('האם אתה בטוח שברצונך למחוק את הקטגוריה?')) {
      return;
    }

    try {
      await deleteCategory(categoryId);
      setCategories(categories.filter(cat => cat._id !== categoryId));
    } catch (error) {
      alert('שגיאה במחיקת קטגוריה: ' + error.message);
    }
  };

  const handleImageUpload = async (childId, file) => {
    // If file is null, remove the image
    if (!file) {
      try {
        setUploadingImages(prev => ({ ...prev, [childId]: true }));
        await updateProfileImage(childId, null);
        await loadData();
        alert('תמונת הפרופיל הוסרה בהצלחה!');
      } catch (error) {
        console.error('Error removing profile image:', error);
        alert('שגיאה בהסרת תמונת הפרופיל: ' + (error.message || 'Unknown error'));
      } finally {
        setUploadingImages(prev => ({ ...prev, [childId]: false }));
      }
      return;
    }

    // Prevent multiple uploads
    if (uploadingImages[childId]) {
      console.log('Upload already in progress for', childId);
      return;
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('אנא בחר קובץ תמונה בלבד');
      // Reset input
      const input = fileInputRefs.current?.[childId];
      if (input) {
        try {
          input.value = '';
        } catch (e) {
          console.warn('Could not reset input:', e);
        }
      }
      return;
    }

    // Validate file size (max 5MB)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      alert('גודל הקובץ גדול מדי. אנא בחר תמונה קטנה מ-5MB');
      // Reset input
      const input = fileInputRefs.current?.[childId];
      if (input) {
        try {
          input.value = '';
        } catch (e) {
          console.warn('Could not reset input:', e);
        }
      }
      return;
    }

    // Set uploading state
    setUploadingImages(prev => ({ ...prev, [childId]: true }));

    // Convert to base64
    const reader = new FileReader();
    
    reader.onerror = (error) => {
      console.error('FileReader error:', error);
      setUploadingImages(prev => ({ ...prev, [childId]: false }));
      // Reset input
      const input = fileInputRefs.current?.[childId];
      if (input) {
        try {
          input.value = '';
        } catch (e) {
          console.warn('Could not reset input:', e);
        }
      }
      alert('שגיאה בקריאת הקובץ: ' + (error.message || 'Unknown error'));
    };

    reader.onloadend = async () => {
      try {
        if (reader.error) {
          throw new Error('Failed to read file: ' + (reader.error.message || 'Unknown error'));
        }
        
        const base64Image = reader.result;
        if (!base64Image) {
          throw new Error('Failed to convert image to base64');
        }
        
        console.log('Uploading image, size:', base64Image.length, 'bytes');
        const result = await updateProfileImage(childId, base64Image);
        console.log('Image upload result:', result);
        
        // Reset input to allow selecting the same file again
        const input = fileInputRefs.current?.[childId];
        if (input) {
          try {
            input.value = '';
          } catch (e) {
            console.warn('Could not reset input:', e);
          }
        }
        
        await loadData();
        alert('תמונת הפרופיל עודכנה בהצלחה!');
      } catch (error) {
        console.error('Error updating profile image:', error);
        console.error('Error details:', {
          message: error.message,
          stack: error.stack,
          name: error.name
        });
        const errorMessage = error.message || 'Unknown error';
        alert('שגיאה בעדכון תמונת הפרופיל: ' + errorMessage);
        // Reset input on error
        const input = fileInputRefs.current?.[childId];
        if (input) {
          try {
            input.value = '';
          } catch (e) {
            console.warn('Could not reset input:', e);
          }
        }
      } finally {
        setUploadingImages(prev => ({ ...prev, [childId]: false }));
      }
    };
    
    reader.readAsDataURL(file);
  };

  const handleAllowanceUpdate = async (childId, allowance, allowanceType, allowanceDay, allowanceTime) => {
    try {
      await updateWeeklyAllowance(childId, allowance, allowanceType, allowanceDay, allowanceTime);
      await loadData();
      alert('דמי הכיס עודכנו בהצלחה!');
    } catch (error) {
      alert('שגיאה בעדכון דמי הכיס: ' + error.message);
    }
  };

  const toggleCategoryForChild = (categoryId, childId) => {
    const category = categories.find(c => c._id === categoryId);
    if (!category) return;

    const activeFor = category.activeFor || [];
    const newActiveFor = activeFor.includes(childId)
      ? activeFor.filter(id => id !== childId)
      : [...activeFor, childId];

    handleUpdateCategory(categoryId, category.name, newActiveFor);
  };

  if (loading) {
    return (
      <div className="settings-container">
        <div className="loading">טוען הגדרות...</div>
      </div>
    );
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h1>הגדרות</h1>
        <button className="close-button" onClick={onClose}>✕</button>
      </div>

      <div className="settings-tabs">
        <button
          className={activeTab === 'categories' ? 'active' : ''}
          onClick={() => setActiveTab('categories')}
        >
          קטגוריות הוצאות
        </button>
        <button
          className={activeTab === 'profileImages' ? 'active' : ''}
          onClick={() => setActiveTab('profileImages')}
        >
          תמונות פרופיל
        </button>
        <button
          className={activeTab === 'allowances' ? 'active' : ''}
          onClick={() => setActiveTab('allowances')}
        >
          דמי כיס
        </button>
      </div>

      <div className="settings-content">
        {activeTab === 'categories' && (
          <div className="categories-section">
            <h2>ניהול קטגוריות</h2>
            
            <form onSubmit={handleAddCategory} className="add-category-form">
              <input
                type="text"
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                placeholder="שם קטגוריה חדשה"
                className="category-input"
              />
              <button type="submit" className="add-button">הוסף קטגוריה</button>
            </form>

            <div className="categories-list">
              {categories.map(category => (
                <div key={category._id} className="category-item">
                  {editingCategory === category._id ? (
                    <div className="category-edit">
                      <input
                        type="text"
                        defaultValue={category.name}
                        onBlur={(e) => {
                          if (e.target.value !== category.name) {
                            handleUpdateCategory(category._id, e.target.value, category.activeFor);
                          } else {
                            setEditingCategory(null);
                          }
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.target.blur();
                          } else if (e.key === 'Escape') {
                            setEditingCategory(null);
                          }
                        }}
                        autoFocus
                        className="category-name-input"
                      />
                    </div>
                  ) : (
                    <div className="category-header">
                      <span 
                        className="category-name"
                        onClick={() => setEditingCategory(category._id)}
                      >
                        {category.name}
                      </span>
                      <button
                        className="delete-button"
                        onClick={() => handleDeleteCategory(category._id)}
                      >
                        🗑️
                      </button>
                    </div>
                  )}
                  
                  <div className="category-children">
                    <label>
                      <input
                        type="checkbox"
                        checked={(category.activeFor || []).includes('child1')}
                        onChange={() => toggleCategoryForChild(category._id, 'child1')}
                      />
                      {CHILD_NAMES.child1}
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={(category.activeFor || []).includes('child2')}
                        onChange={() => toggleCategoryForChild(category._id, 'child2')}
                      />
                      {CHILD_NAMES.child2}
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'profileImages' && (
          <div className="profile-images-section">
            <h2>תמונות פרופיל</h2>
            
            {['child1', 'child2'].map(childId => {
              const child = allData.children[childId];
              if (!child) return null;

              return (
                <div key={childId} className="profile-image-item">
                  <div className="profile-image-preview">
                    {child.profileImage ? (
                      <img src={child.profileImage} alt={child.name} />
                    ) : (
                      <div className="profile-placeholder">
                        {child.name.charAt(0)}
                      </div>
                    )}
                  </div>
                  <div className="profile-image-info">
                    <h3>{child.name}</h3>
                    <label className="file-upload-button" style={{ opacity: uploadingImages[childId] ? 0.6 : 1, pointerEvents: uploadingImages[childId] ? 'none' : 'auto' }}>
                      <input
                        ref={el => {
                          if (el) {
                            fileInputRefs.current[childId] = el;
                          }
                        }}
                        type="file"
                        accept="image/*"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            handleImageUpload(childId, file);
                          }
                        }}
                        disabled={uploadingImages[childId]}
                        style={{ display: 'none' }}
                      />
                      {uploadingImages[childId] ? 'מעלה...' : 'העלה תמונה'}
                    </label>
                    {child.profileImage && (
                      <button
                        className="remove-image-button"
                        onClick={() => handleImageUpload(childId, null)}
                      >
                        הסר תמונה
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'allowances' && (
          <div className="allowances-section">
            <h2>תצורת דמי כיס</h2>
            <p className="allowance-info">
              הגדר את הסכום, תדירות (שבועי/חודשי), יום/תאריך ושעה. הסכום יתווסף אוטומטית ליתרה אצל ההורים.
              ניתן גם לשלם ידנית באמצעות הכפתור למטה.
            </p>
            
            {['child1', 'child2'].map(childId => {
              const child = allData.children[childId];
              if (!child) return null;

              const state = allowanceStates[childId] || {
                amount: child.weeklyAllowance || 0,
                type: child.allowanceType || 'weekly',
                day: child.allowanceDay !== undefined ? child.allowanceDay : 1,
                time: child.allowanceTime || '08:00'
              };

              const updateState = (updates) => {
                setAllowanceStates(prev => ({
                  ...prev,
                  [childId]: { ...state, ...updates }
                }));
              };

              const saveChanges = () => {
                const currentState = allowanceStates[childId] || state;
                if (currentState.amount !== (child.weeklyAllowance || 0) || 
                    currentState.type !== (child.allowanceType || 'weekly') ||
                    currentState.day !== (child.allowanceDay !== undefined ? child.allowanceDay : 1) ||
                    currentState.time !== (child.allowanceTime || '08:00')) {
                  handleAllowanceUpdate(childId, currentState.amount, currentState.type, currentState.day, currentState.time);
                }
              };

              return (
                <div key={childId} className="allowance-item">
                  <h3>{child.name}</h3>
                  
                  <div className="allowance-config-group">
                    <label className="allowance-label">סכום:</label>
                    <div className="allowance-input-group">
                      <input
                        type="number"
                        step="1"
                        min="0"
                        value={state.amount}
                        onChange={(e) => updateState({ amount: parseInt(e.target.value) || 0 })}
                        onBlur={saveChanges}
                        className="allowance-input"
                      />
                      <span className="currency-label">₪</span>
                    </div>
                  </div>

                  <div className="allowance-config-group">
                    <label className="allowance-label">תדירות:</label>
                    <select
                      value={state.type}
                      onChange={(e) => {
                        const newType = e.target.value;
                        const newDay = newType === 'monthly' && state.day === 0 ? 1 : state.day;
                        updateState({ type: newType, day: newDay });
                        setTimeout(saveChanges, 0);
                      }}
                      className="allowance-select"
                    >
                      <option value="weekly">שבועי</option>
                      <option value="monthly">חודשי</option>
                    </select>
                  </div>

                  <div className="allowance-config-group">
                    <label className="allowance-label">
                      {state.type === 'weekly' ? 'יום בשבוע:' : 'תאריך בחודש:'}
                    </label>
                    {state.type === 'weekly' ? (
                      <select
                        value={state.day}
                        onChange={(e) => {
                          updateState({ day: parseInt(e.target.value) });
                          setTimeout(saveChanges, 0);
                        }}
                        className="allowance-select"
                      >
                        <option value="0">ראשון</option>
                        <option value="1">שני</option>
                        <option value="2">שלישי</option>
                        <option value="3">רביעי</option>
                        <option value="4">חמישי</option>
                        <option value="5">שישי</option>
                        <option value="6">שבת</option>
                      </select>
                    ) : (
                      <input
                        type="number"
                        min="1"
                        max="31"
                        value={state.day}
                        onChange={(e) => {
                          const dayValue = parseInt(e.target.value) || 1;
                          if (dayValue >= 1 && dayValue <= 31) {
                            updateState({ day: dayValue });
                          }
                        }}
                        onBlur={saveChanges}
                        className="allowance-input"
                        style={{ width: '80px' }}
                      />
                    )}
                  </div>

                  <div className="allowance-config-group">
                    <label className="allowance-label">שעה:</label>
                    <input
                      type="time"
                      value={state.time}
                      onChange={(e) => {
                        updateState({ time: e.target.value });
                        setTimeout(saveChanges, 0);
                      }}
                      className="allowance-input"
                      style={{ width: '120px' }}
                    />
                  </div>

                  {child.weeklyAllowance > 0 && (
                    <button
                      className="pay-allowance-button"
                      onClick={async () => {
                        try {
                          await payWeeklyAllowance(childId);
                          await loadData();
                          alert(`דמי כיס שולמו ל${child.name}!`);
                        } catch (error) {
                          alert('שגיאה בתשלום דמי הכיס: ' + error.message);
                        }
                      }}
                    >
                      💰 שלם דמי כיס עכשיו
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;

