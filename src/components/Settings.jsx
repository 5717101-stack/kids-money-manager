import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { getCategories, addCategory, updateCategory, deleteCategory, getData, updateProfileImage, updateWeeklyAllowance, payWeeklyAllowance, createChild, updateChild } from '../utils/api';
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
  const { t, i18n } = useTranslation();
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
  const [newChildPhone, setNewChildPhone] = useState('');
  const [creatingChild, setCreatingChild] = useState(false);
  const [childPhoneModal, setChildPhoneModal] = useState(null); // { childId, childName, phoneNumber }
  const [editingChild, setEditingChild] = useState(null); // { childId, childName, phoneNumber }
  const [editChildName, setEditChildName] = useState('');
  const [editChildPhone, setEditChildPhone] = useState('');
  const [updatingChild, setUpdatingChild] = useState(false);

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
      
      console.log('[SETTINGS] Loading data for family:', familyId);
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
      
      console.log('[SETTINGS] Categories loaded:', categoriesData?.length || 0);
      console.log('[SETTINGS] Children data:', childrenData);
      console.log('[SETTINGS] Children count:', Object.keys(childrenData?.children || {}).length);
      if (childrenData?.children) {
        console.log('[SETTINGS] Children IDs:', Object.keys(childrenData.children));
        console.log('[SETTINGS] Children names:', Object.values(childrenData.children).map(c => c.name));
      }
      
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
        alert(t('parent.settings.alerts.loadDataError', { defaultValue: 'שגיאה בטעינת הנתונים' }) + ': ' + (error.message || 'Unknown error'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAddCategory = async (e) => {
    e.preventDefault();
    if (!newCategoryName.trim()) {
      alert(t('parent.settings.alerts.enterCategoryName', { defaultValue: 'אנא הכנס שם קטגוריה' }));
      return;
    }

    if (!familyId) return;
    try {
      const childrenIds = Object.keys(allData.children || {});
      const category = await addCategory(familyId, newCategoryName.trim(), childrenIds);
      setCategories([...categories, category]);
      setNewCategoryName('');
    } catch (error) {
      alert(t('parent.settings.alerts.addCategoryError', { defaultValue: 'שגיאה בהוספת קטגוריה' }) + ': ' + error.message);
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
      alert(t('parent.settings.alerts.updateCategoryError', { defaultValue: 'שגיאה בעדכון קטגוריה' }) + ': ' + error.message);
    }
  };

  const handleDeleteCategory = async (categoryId) => {
    if (!window.confirm(t('parent.settings.alerts.deleteCategoryConfirm', { defaultValue: 'האם אתה בטוח שברצונך למחוק את הקטגוריה?' }))) {
      return;
    }

    if (!familyId) return;
    try {
      await deleteCategory(familyId, categoryId);
      setCategories(categories.filter(cat => cat._id !== categoryId));
    } catch (error) {
      alert(t('parent.settings.alerts.deleteCategoryError', { defaultValue: 'שגיאה במחיקת קטגוריה' }) + ': ' + error.message);
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
        alert(t('parent.settings.alerts.removeImageSuccess', { defaultValue: 'תמונת הפרופיל הוסרה בהצלחה!' }));
      } catch (error) {
        console.error('Error removing profile image:', error);
        alert(t('parent.settings.alerts.removeImageError', { defaultValue: 'שגיאה בהסרת תמונת הפרופיל' }) + ': ' + (error.message || 'Unknown error'));
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
      alert(t('parent.settings.alerts.invalidFileType', { defaultValue: 'אנא בחר קובץ תמונה בלבד' }));
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
      alert(t('parent.settings.alerts.fileTooLarge', { defaultValue: 'גודל הקובץ גדול מדי. אנא בחר תמונה קטנה מ-10MB' }));
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
          throw new Error(t('parent.settings.alerts.imageTooLargeAfterCompression', { defaultValue: 'התמונה גדולה מדי גם לאחר דחיסה. אנא בחר תמונה קטנה יותר.' }));
        }
        base64Image = compressedImage;
        console.log('Re-compressed image size:', base64Image.length, 'bytes');
      }
      
      console.log('Uploading image, final size:', base64Image.length, 'bytes');
      
      if (!familyId) return;
      // Add timeout to prevent hanging
      const uploadPromise = updateProfileImage(familyId, childId, base64Image);
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error(t('parent.settings.alerts.uploadTimeout', { defaultValue: 'העלאה ארכה יותר מדי זמן. נסה שוב.' }))), 60000)
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
      
      alert(t('parent.settings.alerts.updateImageSuccess', { defaultValue: 'תמונת הפרופיל עודכנה בהצלחה!' }));
    } catch (error) {
      console.error('Error updating profile image:', error);
      console.error('Error details:', {
        message: error.message,
        stack: error.stack,
        name: error.name
      });
      const errorMessage = error.message || 'Unknown error';
      alert(t('parent.settings.alerts.updateImageError', { defaultValue: 'שגיאה בעדכון תמונת הפרופיל' }) + ': ' + errorMessage);
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
      alert(t('parent.settings.alerts.updateAllowanceSuccess', { defaultValue: 'דמי הכיס עודכנו בהצלחה!' }));
    } catch (error) {
      alert(t('parent.settings.alerts.updateAllowanceError', { defaultValue: 'שגיאה בעדכון דמי הכיס' }) + ': ' + error.message);
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
      <div className="settings-container" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div className="loading">{t('common.loading', { defaultValue: 'טוען...' })}</div>
      </div>
    );
  }

  const dayNames = [
    t('days.sunday', { defaultValue: 'ראשון' }),
    t('days.monday', { defaultValue: 'שני' }),
    t('days.tuesday', { defaultValue: 'שלישי' }),
    t('days.wednesday', { defaultValue: 'רביעי' }),
    t('days.thursday', { defaultValue: 'חמישי' }),
    t('days.friday', { defaultValue: 'שישי' }),
    t('days.saturday', { defaultValue: 'שבת' })
  ];

  return (
    <div className="modal-overlay" onClick={onClose} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      <div className="modal-content settings-container" onClick={(e) => e.stopPropagation()} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div className="settings-header">
          <h1>{t('parent.settings.title', { defaultValue: 'הגדרות' })}</h1>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>

      <div className="settings-tabs">
        <button
          className={activeTab === 'categories' ? 'active' : ''}
          onClick={() => setActiveTab('categories')}
        >
          {t('parent.settings.tabs.categories', { defaultValue: 'קטגוריות הוצאות' })}
        </button>
        <button
          className={activeTab === 'profileImages' ? 'active' : ''}
          onClick={() => setActiveTab('profileImages')}
        >
          {t('parent.settings.tabs.profileImages', { defaultValue: 'תמונות פרופיל' })}
        </button>
        <button
          className={activeTab === 'allowances' ? 'active' : ''}
          onClick={() => setActiveTab('allowances')}
        >
          {t('parent.settings.tabs.allowances', { defaultValue: 'דמי כיס' })}
        </button>
        <button
          className={activeTab === 'children' ? 'active' : ''}
          onClick={() => setActiveTab('children')}
        >
          {t('parent.settings.tabs.children', { defaultValue: 'ילדים' })}
        </button>
      </div>

      <div className="settings-content">
        {activeTab === 'categories' && (
          <div className="categories-section">
            <h2>{t('parent.settings.categories.title', { defaultValue: 'ניהול קטגוריות' })}</h2>
            
            <form onSubmit={handleAddCategory} className="add-category-form">
              <input
                type="text"
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                placeholder={t('parent.settings.categories.categoryName', { defaultValue: 'שם קטגוריה חדשה' })}
                className="category-input"
              />
              <button type="submit" className="add-button">{t('parent.settings.categories.addCategory', { defaultValue: 'הוסף קטגוריה' })}</button>
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
            <h2>{t('parent.settings.profileImages.title', { defaultValue: 'תמונות פרופיל' })}</h2>
            
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
                      {uploadingImages[childId] 
                        ? t('parent.settings.profileImages.uploading', { defaultValue: 'מעלה...' })
                        : t('parent.settings.profileImages.upload', { defaultValue: 'העלה תמונה' })}
                    </label>
                    {profileImage && (
                      <button
                        className="remove-image-button"
                        onClick={() => handleImageUpload(childId, null)}
                      >
                        {t('parent.settings.profileImages.remove', { defaultValue: 'הסר תמונה' })}
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
            <h2>{t('parent.settings.allowance.title', { defaultValue: 'קצבה אוטומטית' })}</h2>
            <p className="allowance-info">
              {t('parent.settings.allowance.description', { 
                defaultValue: 'הגדר את הסכום, תדירות (שבועי/חודשי), יום/תאריך ושעה. הסכום יתווסף אוטומטית ליתרה אצל ההורים. ניתן גם לשלם ידנית באמצעות הכפתור למטה.' 
              })}
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
                  <h3>{child?.name || t('parent.settings.child', { defaultValue: 'ילד' })}</h3>
                  
                  <div className="allowance-config-group">
                    <label className="allowance-label">{t('parent.settings.allowance.amount', { defaultValue: 'סכום קצבה' })}:</label>
                    <div className="allowance-input-group">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={state.amount}
                        onChange={(e) => updateState({ amount: parseFloat(e.target.value) || 0 })}
                        onBlur={saveChanges}
                        className="allowance-input"
                        inputMode="numeric"
                      />
                      <span className="currency-label">₪</span>
                    </div>
                  </div>

                  <div className="allowance-config-group">
                    <label className="allowance-label">{t('parent.settings.allowance.frequency', { defaultValue: 'תדירות' })}:</label>
                    <div className="frequency-toggle">
                      <button
                        type="button"
                        className={`frequency-button ${state.type === 'weekly' ? 'active' : ''}`}
                        onClick={() => {
                          const newDay = state.day === 0 ? 1 : state.day;
                          updateState({ type: 'weekly', day: newDay });
                          setTimeout(saveChanges, 0);
                        }}
                      >
                        {t('parent.settings.allowance.weekly', { defaultValue: 'שבועי' })}
                      </button>
                      <button
                        type="button"
                        className={`frequency-button ${state.type === 'monthly' ? 'active' : ''}`}
                        onClick={() => {
                          const newDay = state.day === 0 ? 1 : state.day;
                          updateState({ type: 'monthly', day: newDay });
                          setTimeout(saveChanges, 0);
                        }}
                      >
                        {t('parent.settings.allowance.monthly', { defaultValue: 'חודשי' })}
                      </button>
                    </div>
                  </div>

                  <div className="allowance-config-group">
                    <label className="allowance-label">
                      {state.type === 'weekly' 
                        ? t('parent.settings.allowance.dayOfWeek', { defaultValue: 'יום בשבוע' })
                        : t('parent.settings.allowance.dateOfMonth', { defaultValue: 'תאריך בחודש' })
                      }:
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
                        {dayNames.map((dayName, index) => (
                          <option key={index} value={index}>{dayName}</option>
                        ))}
                      </select>
                    ) : (
                      <select
                        value={state.day}
                        onChange={(e) => {
                          updateState({ day: parseInt(e.target.value) });
                          setTimeout(saveChanges, 0);
                        }}
                        className="allowance-select"
                      >
                        {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
                          <option key={day} value={day}>
                            {day}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  <div className="allowance-config-group">
                    <label className="allowance-label">{t('parent.settings.allowance.time', { defaultValue: 'שעה' })}:</label>
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
                          alert(t('parent.settings.allowance.paid', { 
                            defaultValue: 'דמי כיס שולמו ל{name}!',
                            name: child?.name || t('parent.settings.child', { defaultValue: 'ילד' })
                          }));
                        } catch (error) {
                          alert(t('parent.settings.allowance.error', { defaultValue: 'שגיאה בתשלום דמי הכיס' }) + ': ' + (error.message || 'Unknown error'));
                        }
                      }}
                    >
                      💰 {t('parent.settings.allowance.payNow', { defaultValue: 'שלם דמי כיס עכשיו' })}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'children' && (
          <div className="children-section">
            <h2>{t('parent.settings.manageChildren', { defaultValue: 'ניהול ילדים' })}</h2>
            
            <div className="children-list">
              {Object.entries(allData.children || {}).map(([childId, child]) => (
                <div key={childId} className="child-item">
                  <div className="child-info">
                    {child.profileImage && (
                      <img src={child.profileImage} alt={child.name} className="child-avatar" />
                    )}
                    <div>
                      <h3>{child.name}</h3>
                      <p>{t('parent.settings.balance', { defaultValue: 'יתרה' })}: ₪{((child.balance || 0) + (child.cashBoxBalance || 0)).toFixed(2)}</p>
                    </div>
                  </div>
                  <div className="child-actions">
                    <button
                      className="edit-child-button"
                      onClick={() => {
                        setEditingChild({ childId, childName: child.name, phoneNumber: child.phoneNumber || '' });
                        setEditChildName(child.name);
                        setEditChildPhone(child.phoneNumber || '');
                      }}
                    >
                      {t('common.edit', { defaultValue: 'ערוך' })}
                    </button>
                    <button
                      className="view-phone-button"
                      onClick={() => {
                        const childPhone = child.phoneNumber || '';
                        if (childPhone) {
                          setChildPhoneModal({ childId, childName: child.name, phoneNumber: childPhone });
                        } else {
                          alert(t('parent.settings.noPhoneNumber', { defaultValue: 'לילד זה אין מספר טלפון מוגדר' }));
                        }
                      }}
                    >
                      {t('parent.settings.viewPhone', { defaultValue: 'צפה בטלפון' })}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="add-child-section">
              <h3>{t('parent.settings.addChild', { defaultValue: 'הוסף ילד חדש' })}</h3>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  console.log('[CREATE-CHILD] ========================================');
                  console.log('[CREATE-CHILD] Form submitted');
                  console.log('[CREATE-CHILD] Family ID:', familyId);
                  console.log('[CREATE-CHILD] Child Name:', newChildName.trim());
                  console.log('[CREATE-CHILD] ========================================');
                  
                  if (!familyId || !newChildName.trim()) {
                    console.error('[CREATE-CHILD] ❌ Missing familyId or child name');
                    alert(t('parent.settings.enterChildName', { defaultValue: 'אנא הכנס שם ילד' }));
                    return;
                  }
                  
                  if (!newChildPhone.trim()) {
                    console.error('[CREATE-CHILD] ❌ Missing child phone number');
                    alert(t('parent.settings.enterChildPhone', { defaultValue: 'אנא הכנס מספר טלפון לילד' }));
                    return;
                  }
                  
                  setCreatingChild(true);
                  try {
                    console.log('[CREATE-CHILD] Calling createChild API...');
                    const result = await createChild(familyId, newChildName.trim(), newChildPhone.trim());
                    console.log('[CREATE-CHILD] ✅ API call successful');
                    console.log('[CREATE-CHILD] Result:', JSON.stringify(result, null, 2));
                    
                    if (!result || !result.child) {
                      throw new Error(t('parent.settings.invalidResponse', { defaultValue: 'תגובה לא תקינה מהשרת' }));
                    }
                    
                    setChildPhoneModal({
                      childId: result.child._id,
                      childName: result.child.name,
                      phoneNumber: result.phoneNumber
                    });
                    setNewChildName('');
                    setNewChildPhone('');
                    
                    console.log('[CREATE-CHILD] Reloading data...');
                    await loadData();
                    console.log('[CREATE-CHILD] ✅ Data reloaded');
                    
                    // Notify parent component to refresh children list
                    if (onClose) {
                      // Call onClose to trigger refresh in ParentDashboard
                      setTimeout(() => {
                        onClose();
                      }, 500);
                    }
                  } catch (error) {
                    console.error('[CREATE-CHILD] ========================================');
                    console.error('[CREATE-CHILD] ❌❌❌ ERROR ❌❌❌');
                    console.error('[CREATE-CHILD] Error Name:', error.name);
                    console.error('[CREATE-CHILD] Error Message:', error.message);
                    console.error('[CREATE-CHILD] Error Stack:', error.stack);
                    console.error('[CREATE-CHILD] Full Error:', error);
                    console.error('[CREATE-CHILD] ========================================');
                    alert(t('parent.settings.createChildError', { defaultValue: 'שגיאה ביצירת ילד' }) + ': ' + error.message);
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
                  placeholder={t('parent.settings.childName', { defaultValue: 'שם הילד' })}
                  className="child-name-input"
                  required
                />
                <input
                  type="tel"
                  value={newChildPhone}
                  onChange={(e) => setNewChildPhone(e.target.value)}
                  placeholder={t('parent.settings.childPhone', { defaultValue: 'מספר טלפון לילד' })}
                  className="child-name-input"
                  inputMode="numeric"
                  required
                />
                <button type="submit" className="add-child-button" disabled={creatingChild}>
                  {creatingChild 
                    ? t('common.saving', { defaultValue: 'שומר...' })
                    : t('parent.settings.addChild', { defaultValue: 'הוסף ילד' })
                  }
                </button>
              </form>
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

      {childPhoneModal && (
        <div className="password-modal-overlay" onClick={() => setChildPhoneModal(null)}>
          <div className="password-modal" onClick={(e) => e.stopPropagation()}>
            <div className="password-modal-header">
              <h2>{t('parent.settings.phoneModal.title', { name: childPhoneModal.childName, defaultValue: 'מספר טלפון ל{name}' })}</h2>
              <button className="close-button" onClick={() => setChildPhoneModal(null)}>×</button>
            </div>
            <div className="password-modal-content">
              <p className="password-label">{t('parent.settings.phoneModal.phoneNumber', { defaultValue: 'מספר טלפון' })}:</p>
              <div className="password-display-container">
                <div className="password-display" id="phone-display">{childPhoneModal.phoneNumber}</div>
                <button 
                  className="copy-button"
                  onClick={() => {
                    navigator.clipboard.writeText(childPhoneModal.phoneNumber);
                    const btn = document.querySelector('.copy-button');
                    const originalText = btn.textContent;
                    btn.textContent = '✅ ' + t('parent.settings.passwordModal.copied', { defaultValue: 'הועתק!' });
                    setTimeout(() => {
                      btn.textContent = originalText;
                    }, 2000);
                  }}
                  title={t('parent.settings.phoneModal.copyPhone', { defaultValue: 'העתק מספר טלפון' })}
                >
                  📋 {t('parent.settings.passwordModal.copy', { defaultValue: 'העתק' })}
                </button>
              </div>
              <p className="password-note">
                {t('parent.settings.phoneModal.note', { defaultValue: 'הילד יכול להשתמש במספר הטלפון הזה כדי להתחבר לדף שלו.' })}
              </p>
            </div>
            <div className="password-modal-footer">
              <button className="password-close-button" onClick={() => setChildPhoneModal(null)}>
                {t('parent.settings.passwordModal.close', { defaultValue: 'סגור' })}
              </button>
            </div>
          </div>
        </div>
      )}

      {editingChild && (
        <div className="password-modal-overlay" onClick={() => {
          setEditingChild(null);
          setEditChildName('');
          setEditChildPhone('');
        }}>
          <div className="password-modal" onClick={(e) => e.stopPropagation()}>
            <div className="password-modal-header">
              <h2>{t('parent.settings.editChildModal.title', { defaultValue: 'ערוך ילד' })}</h2>
              <button className="close-button" onClick={() => {
                setEditingChild(null);
                setEditChildName('');
                setEditChildPhone('');
              }}>×</button>
            </div>
            <div className="password-modal-content">
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!editChildName.trim()) {
                    alert(t('parent.settings.enterChildName', { defaultValue: 'אנא הכנס שם ילד' }));
                    return;
                  }
                  if (!editChildPhone.trim()) {
                    alert(t('parent.settings.enterChildPhone', { defaultValue: 'אנא הכנס מספר טלפון לילד' }));
                    return;
                  }
                  
                  setUpdatingChild(true);
                  try {
                    await updateChild(familyId, editingChild.childId, editChildName.trim(), editChildPhone.trim());
                    await loadData();
                    setEditingChild(null);
                    setEditChildName('');
                    setEditChildPhone('');
                    if (onClose) {
                      setTimeout(() => {
                        onClose();
                      }, 500);
                    }
                  } catch (error) {
                    console.error('Error updating child:', error);
                    alert(t('parent.settings.updateChildError', { defaultValue: 'שגיאה בעדכון ילד' }) + ': ' + error.message);
                  } finally {
                    setUpdatingChild(false);
                  }
                }}
              >
                <div className="form-group">
                  <label>{t('parent.settings.childName', { defaultValue: 'שם הילד' })}:</label>
                  <input
                    type="text"
                    value={editChildName}
                    onChange={(e) => setEditChildName(e.target.value)}
                    placeholder={t('parent.settings.childName', { defaultValue: 'שם הילד' })}
                    className="child-name-input"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>{t('parent.settings.childPhone', { defaultValue: 'מספר טלפון לילד' })}:</label>
                  <input
                    type="tel"
                    value={editChildPhone}
                    onChange={(e) => setEditChildPhone(e.target.value)}
                    placeholder={t('parent.settings.childPhone', { defaultValue: 'מספר טלפון לילד' })}
                    className="child-name-input"
                    inputMode="numeric"
                    required
                  />
                </div>
                <div className="password-modal-footer" style={{ marginTop: '20px', display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    className="password-close-button"
                    onClick={() => {
                      setEditingChild(null);
                      setEditChildName('');
                      setEditChildPhone('');
                    }}
                    disabled={updatingChild}
                  >
                    {t('common.cancel', { defaultValue: 'ביטול' })}
                  </button>
                  <button
                    type="submit"
                    className="child-password-button"
                    disabled={updatingChild || !editChildName.trim() || !editChildPhone.trim()}
                  >
                    {updatingChild ? t('common.saving', { defaultValue: 'שומר...' }) : t('common.save', { defaultValue: 'שמור' })}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

export default Settings;

