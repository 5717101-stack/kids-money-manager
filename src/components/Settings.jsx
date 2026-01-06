import React, { useState, useEffect, useRef } from 'react';
import { getCategories, addCategory, updateCategory, deleteCategory, getData, updateProfileImage, updateWeeklyAllowance, payWeeklyAllowance, createChild, getChildPassword } from '../utils/api';
import ChildJoin from './ChildJoin';

const CHILD_COLORS = {
  child1: '#3b82f6', // כחול
  child2: '#ec4899'  // ורוד
};

const CHILD_NAMES = {
  child1: 'אדם',
  child2: 'ג\'וּן'
};

const Settings = ({ familyId, onClose }) => {
  const [activeTab, setActiveTab] = useState('categories'); // 'categories', 'profileImages', 'allowances', 'children'
  const [categories, setCategories] = useState([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [editingCategory, setEditingCategory] = useState(null);
  const [allData, setAllData] = useState({ children: {} });
  const [loading, setLoading] = useState(true);
  const [allowanceStates, setAllowanceStates] = useState({});
  const [uploadingImages, setUploadingImages] = useState({});
  const fileInputRefs = useRef({});
  const [showChildJoin, setShowChildJoin] = useState(false);
  const [newChildName, setNewChildName] = useState('');
  const [creatingChild, setCreatingChild] = useState(false);
  const [childPasswordModal, setChildPasswordModal] = useState(null); // { childId, childName, password }

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      if (!familyId) {
        setLoading(false);
        return;
      }
      
      const [categoriesData, childrenData] = await Promise.all([
        getCategories(familyId).catch(err => {
          console.error('Error loading categories:', err);
          return [];
        }),
        getData(familyId).catch(err => {
          console.error('Error loading children data:', err);
          return { children: {} };
        })
      ]);
      setCategories(Array.isArray(categoriesData) ? categoriesData : []);
      setAllData(childrenData && childrenData.children ? childrenData : { children: {} });
      
      // Initialize allowance states
      const states = {};
      Object.entries(childrenData?.children || {}).forEach(([childId, child]) => {
        states[childId] = {
          amount: child.weeklyAllowance || 0,
          type: child.allowanceType || 'weekly',
          day: child.allowanceDay !== undefined ? child.allowanceDay : 1,
          time: child.allowanceTime || '08:00'
        };
      });
      setAllowanceStates(states);
    } catch (error) {
      console.error('Error loading settings data:', error);
      // Don't show alert if it's just a network error - let user retry
      if (!error.message?.includes('Failed to fetch')) {
        alert('שגיאה בטעינת הנתונים: ' + (error.message || 'Unknown error'));
      }
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

    if (!familyId) return;
    try {
      const childrenIds = Object.keys(allData.children || {});
      const category = await addCategory(familyId, newCategoryName.trim(), childrenIds);
      setCategories([...categories, category]);
      setNewCategoryName('');
    } catch (error) {
      alert('שגיאה בהוספת קטגוריה: ' + error.message);
    }
  };

  const handleUpdateCategory = async (categoryId, name, activeFor) => {
    if (!familyId) return;
    try {
      await updateCategory(familyId, categoryId, name, activeFor);
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

    if (!familyId) return;
    try {
      await deleteCategory(familyId, categoryId);
      setCategories(categories.filter(cat => cat._id !== categoryId));
    } catch (error) {
      alert('שגיאה במחיקת קטגוריה: ' + error.message);
    }
  };

  const handleImageUpload = async (childId, file) => {
    // If file is null, remove the image
    if (!file) {
      if (!familyId) return;
      try {
        setUploadingImages(prev => ({ ...prev, [childId]: true }));
        await updateProfileImage(familyId, childId, null);
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

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      alert('גודל הקובץ גדול מדי. אנא בחר תמונה קטנה מ-10MB');
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
    
    // Function to compress image
    const compressImage = (file, maxWidth = 1920, maxHeight = 1920, quality = 0.8) => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const img = new Image();
          img.onload = () => {
            const canvas = document.createElement('canvas');
            let width = img.width;
            let height = img.height;
            
            // Calculate new dimensions
            if (width > height) {
              if (width > maxWidth) {
                height = (height * maxWidth) / width;
                width = maxWidth;
              }
            } else {
              if (height > maxHeight) {
                width = (width * maxHeight) / height;
                height = maxHeight;
              }
            }
            
            canvas.width = width;
            canvas.height = height;
            
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            
            // Convert to base64 with compression
            canvas.toBlob((blob) => {
              if (blob) {
                const reader2 = new FileReader();
                reader2.onloadend = () => {
                  resolve(reader2.result);
                };
                reader2.onerror = reject;
                reader2.readAsDataURL(blob);
              } else {
                reject(new Error('Failed to compress image'));
              }
            }, 'image/jpeg', quality);
          };
          img.onerror = reject;
          img.src = e.target.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    };

    // Set uploading state
    setUploadingImages(prev => ({ ...prev, [childId]: true }));

    try {
      // Compress image before uploading
      console.log('Compressing image, original size:', file.size, 'bytes');
      let base64Image = await compressImage(file);
      console.log('Compressed image size:', base64Image.length, 'bytes');
      
      // Check if compressed image is still too large (max 5MB base64 = ~3.75MB original)
      if (base64Image.length > 5 * 1024 * 1024) {
        // Try with lower quality
        console.log('Image still too large, trying lower quality...');
        const compressedImage = await compressImage(file, 1280, 1280, 0.6);
        if (compressedImage.length > 5 * 1024 * 1024) {
          throw new Error('התמונה גדולה מדי גם לאחר דחיסה. אנא בחר תמונה קטנה יותר.');
        }
        base64Image = compressedImage;
        console.log('Re-compressed image size:', base64Image.length, 'bytes');
      }
      
      console.log('Uploading image, final size:', base64Image.length, 'bytes');
      
      if (!familyId) return;
      // Add timeout to prevent hanging
      const uploadPromise = updateProfileImage(familyId, childId, base64Image);
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('העלאה ארכה יותר מדי זמן. נסה שוב.')), 60000)
      );
      
      const result = await Promise.race([uploadPromise, timeoutPromise]);
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
      
      // Reload data without showing loading state to avoid UI freeze
      try {
        const [categoriesData, childrenData] = await Promise.all([
          getCategories(familyId).catch(() => categories), // Keep current categories on error
          getData(familyId).catch(() => allData) // Keep current data on error
        ]);
        
        if (Array.isArray(categoriesData)) {
          setCategories(categoriesData);
        }
        if (childrenData && childrenData.children) {
          setAllData(childrenData);
        }
      } catch (reloadError) {
        console.error('Error reloading data after upload:', reloadError);
        // Don't show error to user, just log it
      }
      
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

  const handleAllowanceUpdate = async (childId, allowance, allowanceType, allowanceDay, allowanceTime) => {
    if (!familyId) return;
    try {
      await updateWeeklyAllowance(familyId, childId, allowance, allowanceType, allowanceDay, allowanceTime);
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
        <button
          className={activeTab === 'children' ? 'active' : ''}
          onClick={() => setActiveTab('children')}
        >
          ילדים
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
                    {Object.entries(allData.children || {}).map(([childId, child]) => (
                      <label key={childId}>
                        <input
                          type="checkbox"
                          checked={(category.activeFor || []).includes(childId)}
                          onChange={() => toggleCategoryForChild(category._id, childId)}
                        />
                        {child.name}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'profileImages' && (
          <div className="profile-images-section">
            <h2>תמונות פרופיל</h2>
            
            {Object.entries(allData.children || {}).map(([childId, child]) => {
              if (!child) return null;

              const childName = child?.name || 'ילד';
              const profileImage = child?.profileImage;

              return (
                <div key={childId} className="profile-image-item">
                  <div className="profile-image-preview">
                    {profileImage ? (
                      <img 
                        src={profileImage} 
                        alt={childName}
                        onError={(e) => {
                          console.error('Error loading profile image:', e);
                          e.target.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="profile-placeholder">
                        {childName.charAt(0)}
                      </div>
                    )}
                  </div>
                  <div className="profile-image-info">
                    <h3>{childName}</h3>
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
                    {profileImage && (
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
            
            {Object.entries(allData.children || {}).map(([childId, child]) => {
              if (!child) return null;

              const state = allowanceStates[childId] || {
                amount: child?.weeklyAllowance || 0,
                type: child?.allowanceType || 'weekly',
                day: child?.allowanceDay !== undefined ? child.allowanceDay : 1,
                time: child?.allowanceTime || '08:00'
              };

              const updateState = (updates) => {
                setAllowanceStates(prev => ({
                  ...prev,
                  [childId]: { ...state, ...updates }
                }));
              };

              const saveChanges = () => {
                const currentState = allowanceStates[childId] || state;
                if (currentState.amount !== (child?.weeklyAllowance || 0) || 
                    currentState.type !== (child?.allowanceType || 'weekly') ||
                    currentState.day !== (child?.allowanceDay !== undefined ? child.allowanceDay : 1) ||
                    currentState.time !== (child?.allowanceTime || '08:00')) {
                  handleAllowanceUpdate(childId, currentState.amount, currentState.type, currentState.day, currentState.time);
                }
              };

              return (
                <div key={childId} className="allowance-item">
                  <h3>{child?.name || 'ילד'}</h3>
                  
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

                  {(child?.weeklyAllowance || 0) > 0 && (
                    <button
                      className="pay-allowance-button"
                      onClick={async () => {
                        if (!familyId) return;
                        try {
                          await payWeeklyAllowance(familyId, childId);
                          await loadData();
                          alert(`דמי כיס שולמו ל${child?.name || 'ילד'}!`);
                        } catch (error) {
                          alert('שגיאה בתשלום דמי הכיס: ' + (error.message || 'Unknown error'));
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

        {activeTab === 'children' && (
          <div className="children-section">
            <h2>ניהול ילדים</h2>
            
            <div className="children-list">
              {Object.entries(allData.children || {}).map(([childId, child]) => (
                <div key={childId} className="child-item">
                  <div className="child-info">
                    {child.profileImage && (
                      <img src={child.profileImage} alt={child.name} className="child-avatar" />
                    )}
                    <div>
                      <h3>{child.name}</h3>
                      <p>יתרה: ₪{((child.balance || 0) + (child.cashBoxBalance || 0)).toFixed(2)}</p>
                    </div>
                  </div>
                  <button
                    className="recover-password-button"
                    onClick={async () => {
                      if (!familyId) return;
                      try {
                        const password = await getChildPassword(familyId, childId);
                        setChildPasswordModal({ childId, childName: child.name, password });
                      } catch (error) {
                        alert('שגיאה בקבלת סיסמה: ' + error.message);
                      }
                    }}
                  >
                    שחזר סיסמה
                  </button>
                </div>
              ))}
            </div>

            <div className="add-child-section">
              <h3>הוסף ילד חדש</h3>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!familyId || !newChildName.trim()) return;
                  
                  setCreatingChild(true);
                  try {
                    const result = await createChild(familyId, newChildName.trim());
                    setChildPasswordModal({
                      childId: result.child._id,
                      childName: result.child.name,
                      password: result.password,
                      joinCode: result.joinCode
                    });
                    setNewChildName('');
                    await loadData();
                    if (onClose) {
                      setTimeout(() => {
                        window.location.reload();
                      }, 1000);
                    }
                  } catch (error) {
                    alert('שגיאה ביצירת ילד: ' + error.message);
                  } finally {
                    setCreatingChild(false);
                  }
                }}
                className="add-child-form"
              >
                <input
                  type="text"
                  value={newChildName}
                  onChange={(e) => setNewChildName(e.target.value)}
                  placeholder="שם הילד"
                  className="child-name-input"
                  required
                />
                <button type="submit" className="add-child-button" disabled={creatingChild}>
                  {creatingChild ? 'יוצר...' : 'הוסף ילד'}
                </button>
              </form>
            </div>

            <div className="join-child-section">
              <h3>הצטרף לחשבון משפחתי קיים</h3>
              <button
                className="join-child-button"
                onClick={() => setShowChildJoin(true)}
              >
                הצטרף עם קוד
              </button>
            </div>
          </div>
        )}
      </div>

      {showChildJoin && (
        <ChildJoin
          familyId={familyId}
          onJoined={async (child) => {
            setShowChildJoin(false);
            await loadData();
            if (onClose) {
              setTimeout(() => {
                window.location.reload();
              }, 1000);
            }
          }}
          onCancel={() => setShowChildJoin(false)}
        />
      )}

      {childPasswordModal && (
        <div className="password-modal-overlay" onClick={() => setChildPasswordModal(null)}>
          <div className="password-modal" onClick={(e) => e.stopPropagation()}>
            <div className="password-modal-header">
              <h2>סיסמה ל{childPasswordModal.childName}</h2>
              <button className="close-button" onClick={() => setChildPasswordModal(null)}>×</button>
            </div>
            <div className="password-modal-content">
              <p className="password-label">סיסמה:</p>
              <div className="password-display">{childPasswordModal.password}</div>
              {childPasswordModal.joinCode && (
                <>
                  <p className="password-label">קוד הצטרפות:</p>
                  <div className="password-display">{childPasswordModal.joinCode}</div>
                  <p className="password-note">
                    שמור את הקוד הזה! הילד יכול להשתמש בו כדי להצטרף למשפחה ממכשיר אחר.
                  </p>
                </>
              )}
              <p className="password-note">
                שמור את הסיסמה הזו! היא תצטרך אם הילד ישכח אותה או יחליף מכשיר.
              </p>
            </div>
            <div className="password-modal-footer">
              <button className="password-close-button" onClick={() => setChildPasswordModal(null)}>
                סגור
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;

