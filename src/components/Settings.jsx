import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { getCategories, addCategory, updateCategory, deleteCategory, getData, updateProfileImage, updateWeeklyAllowance, payWeeklyAllowance, createChild, updateChild, getFamilyInfo, updateParentInfo, addParent, archiveChild } from '../utils/api';
import { smartCompressImage } from '../utils/imageCompression';
import ChildJoin from './ChildJoin';

const CHILD_COLORS = {
  child1: '#3b82f6', // כחול
  child2: '#ec4899'  // ורוד
};

const CHILD_NAMES = {
  child1: 'אדם',
  child2: 'ג\'וּן'
};

const Settings = ({ familyId, onClose, onLogout, activeTab: externalActiveTab, hideTabs = false, inSidebar = false, asPage = false }) => {
  const { t, i18n } = useTranslation();
  const [internalActiveTab, setInternalActiveTab] = useState('categories'); // 'categories', 'profileImages', 'allowances', 'children', 'parents'
  const activeTab = externalActiveTab !== undefined ? externalActiveTab : internalActiveTab;
  const setActiveTab = externalActiveTab !== undefined ? () => {} : setInternalActiveTab;
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
  const [childPhoneModal, setChildPhoneModal] = useState(null); // { childId, childName, phoneNumber, createdAt, lastLogin }
  const [editingChild, setEditingChild] = useState(null); // { childId, childName, phoneNumber }
  const [editChildName, setEditChildName] = useState('');
  const [editChildPhone, setEditChildPhone] = useState('');
  const [updatingChild, setUpdatingChild] = useState(false);
  const [familyInfo, setFamilyInfo] = useState(null);
  const [editingParent, setEditingParent] = useState(null);
  const [editParentName, setEditParentName] = useState('');
  const [editParentPhone, setEditParentPhone] = useState('');
  const [updatingParent, setUpdatingParent] = useState(false);
  const [addingParent, setAddingParent] = useState(false);
  const [newParentName, setNewParentName] = useState('');
  const [newParentPhone, setNewParentPhone] = useState('');

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
      const [categoriesData, childrenData, familyData] = await Promise.all([
        getCategories(familyId).catch(err => {
          console.error('Error loading categories:', err);
          return [];
        }),
        getData(familyId).catch(err => {
          console.error('Error loading children data:', err);
          return { children: {} };
        }),
        getFamilyInfo(familyId).catch(err => {
          console.error('Error loading family info:', err);
          return null;
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
      setFamilyInfo(familyData);
      
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

    // Set uploading state
    setUploadingImages(prev => ({ ...prev, [childId]: true }));

    try {
      // Compress image before uploading using smart compression
      console.log('Compressing image, original size:', file.size, 'bytes');
      const base64Image = await smartCompressImage(file);
      console.log('Compressed image size:', base64Image.length, 'bytes');
      
      // Check if compressed image is still too large (max 1MB base64)
      if (base64Image.length > 1024 * 1024) {
        throw new Error(t('parent.settings.alerts.imageTooLargeAfterCompression', { defaultValue: 'התמונה גדולה מדי גם לאחר דחיסה. אנא בחר תמונה קטנה יותר.' }));
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
    if (inSidebar) {
      return <div className="loading">{t('common.loading', { defaultValue: 'טוען...' })}</div>;
    }
    return (
      <div className="modal-overlay" onClick={onClose} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div className="modal-content settings-container" onClick={(e) => e.stopPropagation()} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
          <div className="loading">{t('common.loading', { defaultValue: 'טוען...' })}</div>
        </div>
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

  const content = (
    <div dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      {!inSidebar && !asPage && (
        <div className="settings-header">
          <h1>{t('parent.settings.title', { defaultValue: 'הגדרות' })}</h1>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>
      )}

      {!hideTabs && (
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
          <button
            className={activeTab === 'parents' ? 'active' : ''}
            onClick={() => setActiveTab('parents')}
          >
            {t('parent.settings.tabs.parents', { defaultValue: 'הורים' })}
          </button>
        </div>
      )}

      <div className="settings-content">
        {activeTab === 'categories' && (
          <div className="categories-section" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {!asPage && <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>{t('parent.settings.categories.title', { defaultValue: 'ניהול קטגוריות' })}</h2>}
            
            {/* Input Group */}
            <form onSubmit={handleAddCategory} style={{ display: 'flex', gap: '10px', width: '100%', alignItems: 'center' }}>
              <input
                type="text"
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                placeholder={t('parent.settings.categories.categoryName', { defaultValue: 'שם קטגוריה' })}
                style={{
                  flex: 1,
                  height: '50px',
                  borderRadius: '12px',
                  border: '1px solid rgba(0,0,0,0.1)',
                  padding: '0 16px',
                  fontSize: '16px',
                  outline: 'none'
                }}
              />
              <button 
                type="submit" 
                style={{
                  width: 'auto',
                  height: '50px',
                  padding: '0 24px',
                  borderRadius: '12px',
                  background: 'var(--primary-gradient)',
                  color: 'white',
                  border: 'none',
                  fontWeight: 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                {t('parent.settings.categories.addCategory', { defaultValue: 'הוסף קטגוריה' })}
              </button>
            </form>

            {/* Categories List as Mini Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {categories.map(category => (
                <div 
                  key={category._id} 
                  style={{
                    background: 'white',
                    padding: '16px',
                    borderRadius: '16px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
                    display: 'flex',
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: '12px'
                  }}
                >
                  {editingCategory === category._id ? (
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
                      style={{
                        flex: 1,
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid rgba(0,0,0,0.1)',
                        fontSize: '16px',
                        outline: 'none'
                      }}
                    />
                  ) : (
                    <>
                      <button
                        onClick={() => handleDeleteCategory(category._id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          fontSize: '18px',
                          cursor: 'pointer',
                          padding: '4px',
                          flexShrink: 0
                        }}
                      >
                        🗑️
                      </button>
                      <span 
                        onClick={() => setEditingCategory(category._id)}
                        style={{
                          flex: 1,
                          fontSize: '16px',
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                      >
                        {category.name}
                      </span>
                      <div style={{ display: 'flex', flexDirection: 'row', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                        {Object.entries(allData.children || {}).map(([childId, child]) => (
                          <label 
                            key={childId}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              cursor: 'pointer',
                              fontSize: '14px'
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={(category.activeFor || []).includes(childId)}
                              onChange={() => toggleCategoryForChild(category._id, childId)}
                              style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                            />
                            {child.name}
                          </label>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'profileImages' && (
          <div className="profile-images-section">
            {!asPage && <h2>{t('parent.settings.profileImages.title', { defaultValue: 'תמונות פרופיל' })}</h2>}
            
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
            {!asPage && <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '16px' }}>{t('parent.settings.allowance.title', { defaultValue: 'דמי כיס' })}</h2>}
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

              const hasChanges = () => {
                const currentState = allowanceStates[childId] || state;
                return currentState.amount !== (child?.weeklyAllowance || 0) || 
                       currentState.type !== (child?.allowanceType || 'weekly') ||
                       currentState.day !== (child?.allowanceDay !== undefined ? child.allowanceDay : 1) ||
                       currentState.time !== (child?.allowanceTime || '08:00');
              };

              return (
                <div key={childId} className="fintech-card allowance-item">
                  <div className="allowance-item-header">
                    {child.profileImage && (
                      <img 
                        src={child.profileImage} 
                        alt={child.name}
                        className="allowance-child-avatar"
                        loading="lazy"
                        decoding="async"
                      />
                    )}
                    <h3 className="allowance-child-name">{child?.name || t('parent.settings.child', { defaultValue: 'ילד' })}</h3>
                  </div>
                  
                  <div className="allowance-config-group">
                    <label className="allowance-label">{t('parent.settings.allowance.amount', { defaultValue: 'סכום קצבה' })}</label>
                    <div className="allowance-input-group">
                      <span className="currency-label">₪</span>
                      <input
                        type="number"
                        inputMode="decimal"
                        step="0.01"
                        min="0"
                        value={state.amount === 0 ? '' : state.amount}
                        onChange={(e) => {
                          const val = e.target.value === '' ? 0 : parseFloat(e.target.value) || 0;
                          updateState({ amount: val });
                        }}
                        className="allowance-input"
                        placeholder="0.00"
                      />
                    </div>
                  </div>

                  <div className="allowance-config-group">
                    <label className="allowance-label">{t('parent.settings.allowance.frequency', { defaultValue: 'תדירות' })}</label>
                    <div className="frequency-toggle">
                      <button
                        type="button"
                        className={`frequency-button ${state.type === 'weekly' ? 'active' : ''}`}
                        onClick={() => {
                          const newDay = state.day === 0 ? 1 : state.day;
                          updateState({ type: 'weekly', day: newDay });
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
                      }
                    </label>
                    {state.type === 'weekly' ? (
                      <select
                        value={state.day}
                        onChange={(e) => {
                          updateState({ day: parseInt(e.target.value) });
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
                    <label className="allowance-label">{t('parent.settings.allowance.time', { defaultValue: 'שעה' })}</label>
                    <input
                      type="time"
                      value={state.time}
                      onChange={(e) => {
                        updateState({ time: e.target.value });
                      }}
                      className="allowance-input allowance-time-input"
                    />
                  </div>

                  <div className="allowance-actions">
                    <button
                      className={`update-allowance-button ${!hasChanges() ? 'disabled' : ''}`}
                      onClick={() => {
                        if (hasChanges()) {
                          saveChanges();
                        }
                      }}
                      disabled={!hasChanges()}
                    >
                      {t('parent.settings.allowance.update', { defaultValue: 'עדכן הגדרות' })}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'children' && (
          <div className="children-section" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {!asPage && <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>{t('parent.settings.manageChildren', { defaultValue: 'ניהול ילדים' })}</h2>}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {Object.entries(allData.children || {}).map(([childId, child]) => (
                <div key={childId}>
                  <div 
                    style={{
                      background: 'white',
                      padding: '16px',
                      borderRadius: '16px',
                      boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
                      display: 'flex',
                      flexDirection: 'row',
                      alignItems: 'center',
                      gap: '12px'
                    }}
                  >
                    {child.profileImage && (
                      <img 
                        src={child.profileImage} 
                        alt={child.name} 
                        style={{
                          width: '50px',
                          height: '50px',
                          borderRadius: '50%',
                          objectFit: 'cover',
                          flexShrink: 0
                        }}
                      />
                    )}
                    <div style={{ flex: 1 }}>
                      <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>{child.name}</h3>
                      <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: 'var(--text-muted)' }}>
                        {t('parent.settings.balance', { defaultValue: 'יתרה' })}: ₪{((child.balance || 0) + (child.cashBoxBalance || 0)).toFixed(2)}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                      <button
                        onClick={() => {
                          if (editingChild && editingChild.childId === childId) {
                            setEditingChild(null);
                            setEditChildName('');
                            setEditChildPhone('');
                          } else {
                            setEditingChild({ childId, childName: child.name, phoneNumber: child.phoneNumber || '' });
                            setEditChildName(child.name);
                            setEditChildPhone(child.phoneNumber || '');
                          }
                        }}
                        style={{
                          padding: '8px 16px',
                          borderRadius: '8px',
                          border: '1px solid rgba(0,0,0,0.1)',
                          background: (editingChild && editingChild.childId === childId) ? 'var(--primary)' : 'white',
                          color: (editingChild && editingChild.childId === childId) ? 'white' : 'var(--text-main)',
                          fontSize: '14px',
                          fontWeight: 500,
                          cursor: 'pointer'
                        }}
                      >
                        {(editingChild && editingChild.childId === childId) 
                          ? t('common.cancel', { defaultValue: 'ביטול' })
                          : t('common.edit', { defaultValue: 'ערוך' })
                        }
                      </button>
                      <button
                        onClick={() => {
                          if (childPhoneModal && childPhoneModal.childId === childId) {
                            setChildPhoneModal(null);
                          } else {
                            setChildPhoneModal({ 
                              childId, 
                              childName: child.name, 
                              phoneNumber: child.phoneNumber || '',
                              createdAt: child.createdAt,
                              lastLogin: child.lastLogin || child.lastAccess
                            });
                          }
                        }}
                        style={{
                          padding: '8px 16px',
                          borderRadius: '8px',
                          border: '1px solid rgba(0,0,0,0.1)',
                          background: (childPhoneModal && childPhoneModal.childId === childId) ? 'var(--primary)' : 'white',
                          color: (childPhoneModal && childPhoneModal.childId === childId) ? 'white' : 'var(--text-main)',
                          fontSize: '14px',
                          fontWeight: 500,
                          cursor: 'pointer'
                        }}
                      >
                        {(childPhoneModal && childPhoneModal.childId === childId) 
                          ? t('parent.settings.closeDetails', { defaultValue: 'סגור פרטים' })
                          : t('parent.settings.viewDetails', { defaultValue: 'הצג פרטים' })
                        }
                      </button>
                    </div>
                  </div>
                  {childPhoneModal && childPhoneModal.childId === childId && (
                    <div style={{
                      marginTop: '12px',
                      padding: '20px',
                      background: 'white',
                      borderRadius: '16px',
                      boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
                      border: '1px solid rgba(99, 102, 241, 0.2)'
                    }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div>
                          <p className="password-label" style={{ marginBottom: '8px' }}>{t('parent.settings.childDetails.phoneNumber', { defaultValue: 'מספר טלפון להרשמה' })}:</p>
                          <div className="password-display-container">
                            <div className="password-display" id="phone-display" style={{ flex: 1, direction: 'ltr', textAlign: 'left' }}>
                              {childPhoneModal.phoneNumber 
                                ? (childPhoneModal.phoneNumber.startsWith('+') 
                                    ? childPhoneModal.phoneNumber 
                                    : `+${childPhoneModal.phoneNumber}`)
                                : t('parent.settings.noPhoneNumber', { defaultValue: 'לא מוגדר' })
                              }
                            </div>
                            {childPhoneModal.phoneNumber && (
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
                            )}
                          </div>
                        </div>
                        
                        <div>
                          <p className="password-label" style={{ marginBottom: '8px' }}>{t('parent.settings.childDetails.firstLogin', { defaultValue: 'כניסה ראשונה' })}:</p>
                          <div style={{ 
                            padding: '16px', 
                            background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)', 
                            borderRadius: '12px', 
                            color: 'white',
                            fontSize: '16px',
                            fontWeight: 600,
                            textAlign: 'center'
                          }}>
                            {childPhoneModal.createdAt 
                              ? new Date(childPhoneModal.createdAt).toLocaleDateString('he-IL', { 
                                  year: 'numeric', 
                                  month: 'long', 
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })
                              : t('parent.settings.notAvailable', { defaultValue: 'לא זמין' })
                            }
                          </div>
                        </div>
                        
                        <div>
                          <p className="password-label" style={{ marginBottom: '8px' }}>{t('parent.settings.childDetails.lastLogin', { defaultValue: 'כניסה אחרונה' })}:</p>
                          <div style={{ 
                            padding: '16px', 
                            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', 
                            borderRadius: '12px', 
                            color: 'white',
                            fontSize: '16px',
                            fontWeight: 600,
                            textAlign: 'center'
                          }}>
                            {childPhoneModal.lastLogin 
                              ? new Date(childPhoneModal.lastLogin).toLocaleDateString('he-IL', { 
                                  year: 'numeric', 
                                  month: 'long', 
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })
                              : t('parent.settings.neverLoggedIn', { defaultValue: 'מעולם לא נכנס' })
                            }
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  {editingChild && editingChild.childId === childId && (
                    <div style={{
                      marginTop: '12px',
                      padding: '20px',
                      background: 'white',
                      borderRadius: '16px',
                      boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
                      border: '1px solid rgba(99, 102, 241, 0.2)'
                    }}>
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
                            const result = await updateChild(familyId, editingChild.childId, editChildName.trim(), editChildPhone.trim());
                            
                            if (result?.child) {
                              setAllData(prev => {
                                const updated = { ...prev };
                                if (updated.children && updated.children[editingChild.childId]) {
                                  updated.children[editingChild.childId] = {
                                    ...updated.children[editingChild.childId],
                                    name: result.child.name,
                                    phoneNumber: result.child.phoneNumber
                                  };
                                }
                                return updated;
                              });
                            }
                            
                            await loadData();
                            
                            setEditingChild(null);
                            setEditChildName('');
                            setEditChildPhone('');
                            alert(t('parent.settings.updateChildSuccess', { defaultValue: 'ילד עודכן בהצלחה!' }));
                            if (onClose) {
                              setTimeout(() => {
                                onClose();
                              }, 500);
                            }
                          } catch (error) {
                            const errorMessage = error.message || 'שגיאה לא ידועה';
                            alert(t('parent.settings.updateChildError', { defaultValue: 'שגיאה בעדכון ילד' }) + ': ' + errorMessage);
                          } finally {
                            setUpdatingChild(false);
                          }
                        }}
                        style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
                      >
                        <div className="allowance-config-group">
                          <label className="allowance-label">{t('parent.settings.childName', { defaultValue: 'שם הילד' })}</label>
                          <input
                            type="text"
                            value={editChildName}
                            onChange={(e) => setEditChildName(e.target.value)}
                            className="allowance-input"
                            placeholder={t('parent.settings.enterChildName', { defaultValue: 'הכנס שם ילד' })}
                            required
                          />
                        </div>
                        
                        <div className="allowance-config-group">
                          <label className="allowance-label">{t('parent.settings.childPhone', { defaultValue: 'מספר טלפון' })}</label>
                          <input
                            type="tel"
                            value={editChildPhone}
                            onChange={(e) => setEditChildPhone(e.target.value)}
                            className="allowance-input"
                            placeholder={t('parent.settings.enterChildPhone', { defaultValue: 'הכנס מספר טלפון' })}
                            style={{ direction: 'ltr', textAlign: 'left' }}
                            required
                          />
                        </div>
                        
                        <div className="allowance-actions">
                          <button
                            type="submit"
                            className="update-allowance-button"
                            disabled={updatingChild}
                          >
                            {updatingChild 
                              ? t('common.saving', { defaultValue: 'שומר...' })
                              : t('common.save', { defaultValue: 'שמור' })
                            }
                          </button>
                          
                          <button
                            type="button"
                            onClick={async () => {
                              if (!confirm(t('parent.settings.deleteChildConfirm', { 
                                defaultValue: 'האם אתה בטוח שברצונך למחוק את {name}? פעולה זו תעביר את כל הנתונים לארכיון ולא ניתן לבטל אותה.',
                                name: child.name
                              }).replace('{name}', child.name))) {
                                return;
                              }
                              
                              try {
                                await archiveChild(familyId, childId);
                                await loadData();
                                setEditingChild(null);
                                setEditChildName('');
                                setEditChildPhone('');
                                alert(t('parent.settings.deleteChildSuccess', { 
                                  defaultValue: 'הילד נמחק והועבר לארכיון בהצלחה',
                                  name: child.name
                                }).replace('{name}', child.name));
                                if (onClose) {
                                  setTimeout(() => {
                                    onClose();
                                  }, 500);
                                }
                              } catch (error) {
                                alert(t('parent.settings.deleteChildError', { defaultValue: 'שגיאה במחיקת הילד' }) + ': ' + (error.message || 'Unknown error'));
                              }
                            }}
                            className="pay-allowance-button"
                            style={{ background: '#EF4444' }}
                          >
                            🗑️ {t('parent.settings.deleteChild', { defaultValue: 'מחק ילד' })}
                          </button>
                        </div>
                      </form>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>{t('parent.settings.addChild', { defaultValue: 'הוסף ילד חדש' })}</h3>
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
                style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
              >
                <input
                  type="text"
                  value={newChildName}
                  onChange={(e) => setNewChildName(e.target.value)}
                  placeholder={t('parent.settings.childName', { defaultValue: 'שם הילד' })}
                  style={{
                    width: '100%',
                    height: '50px',
                    borderRadius: '12px',
                    border: '1px solid rgba(0,0,0,0.1)',
                    padding: '0 16px',
                    fontSize: '16px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                  required
                />
                <input
                  type="tel"
                  value={newChildPhone}
                  onChange={(e) => setNewChildPhone(e.target.value)}
                  placeholder={t('parent.settings.childPhone', { defaultValue: 'מספר טלפון לילד' })}
                  inputMode="numeric"
                  style={{
                    width: '100%',
                    height: '50px',
                    borderRadius: '12px',
                    border: '1px solid rgba(0,0,0,0.1)',
                    padding: '0 16px',
                    fontSize: '16px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                  required
                />
                <button 
                  type="submit" 
                  disabled={creatingChild}
                  style={{
                    width: '100%',
                    height: '50px',
                    borderRadius: '12px',
                    background: creatingChild ? '#ccc' : 'var(--primary-gradient)',
                    color: 'white',
                    border: 'none',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: creatingChild ? 'not-allowed' : 'pointer'
                  }}
                >
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
                    console.log('[UPDATE-CHILD] Starting update:', {
                      familyId,
                      childId: editingChild.childId,
                      name: editChildName.trim(),
                      phoneNumber: editChildPhone.trim()
                    });
                    const result = await updateChild(familyId, editingChild.childId, editChildName.trim(), editChildPhone.trim());
                    console.log('[UPDATE-CHILD] Update successful:', result);
                    
                    // Update local state immediately if we have the updated child data
                    if (result?.child) {
                      console.log('[UPDATE-CHILD] Updating local state with new data:', result.child);
                      setAllData(prev => {
                        const updated = { ...prev };
                        if (updated.children && updated.children[editingChild.childId]) {
                          updated.children[editingChild.childId] = {
                            ...updated.children[editingChild.childId],
                            name: result.child.name,
                            phoneNumber: result.child.phoneNumber
                          };
                        }
                        return updated;
                      });
                    }
                    
                    // Reload data from server to ensure consistency
                    await loadData();
                    
                    setEditingChild(null);
                    setEditChildName('');
                    setEditChildPhone('');
                    alert(t('parent.settings.updateChildSuccess', { defaultValue: 'ילד עודכן בהצלחה!' }));
                    if (onClose) {
                      setTimeout(() => {
                        onClose();
                      }, 500);
                    }
                  } catch (error) {
                    console.error('[UPDATE-CHILD] Error updating child:', {
                      error: error,
                      message: error.message,
                      stack: error.stack,
                      name: error.name
                    });
                    const errorMessage = error.message || 'שגיאה לא ידועה';
                    alert(t('parent.settings.updateChildError', { defaultValue: 'שגיאה בעדכון ילד' }) + ': ' + errorMessage);
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

        {activeTab === 'parents' && (
          <div className="parents-section">
            <div className="parents-header">
              {!asPage && <h2>{t('parent.settings.parents.title', { defaultValue: 'ניהול הורים' })}</h2>}
              {!addingParent && (
                <button
                  className="add-parent-button"
                  onClick={() => {
                    setAddingParent(true);
                    setNewParentName('');
                    setNewParentPhone('');
                  }}
                >
                  + {t('parent.settings.parents.addParent', { defaultValue: 'הוסף הורה' })}
                </button>
              )}
            </div>
            
            {addingParent && (
              <div className="parent-item parent-item-new">
                <div className="parent-edit">
                  <div className="form-group">
                    <label>{t('parent.settings.parents.name', { defaultValue: 'שם' })}:</label>
                    <input
                      type="text"
                      value={newParentName}
                      onChange={(e) => setNewParentName(e.target.value)}
                      placeholder={t('parent.settings.parents.namePlaceholder', { defaultValue: 'שם ההורה' })}
                      className="parent-input"
                    />
                  </div>
                  <div className="form-group">
                    <label>{t('parent.settings.parents.phone', { defaultValue: 'טלפון' })}:</label>
                    <input
                      type="tel"
                      inputMode="numeric"
                      value={newParentPhone}
                      onChange={(e) => setNewParentPhone(e.target.value)}
                      placeholder={t('parent.settings.parents.phonePlaceholder', { defaultValue: 'מספר טלפון' })}
                      className="parent-input"
                    />
                  </div>
                  <div className="parent-actions">
                    <button
                      className="save-button"
                      onClick={async () => {
                        if (!newParentName.trim() || !newParentPhone.trim()) {
                          alert(t('parent.settings.parents.fillAllFields', { defaultValue: 'אנא מלא את כל השדות' }));
                          return;
                        }
                        try {
                          setUpdatingParent(true);
                          await addParent(familyId, newParentName.trim(), newParentPhone.trim());
                          await loadData();
                          setAddingParent(false);
                          setNewParentName('');
                          setNewParentPhone('');
                          alert(t('parent.settings.parents.addSuccess', { defaultValue: 'הורה נוסף בהצלחה!' }));
                        } catch (error) {
                          alert(t('parent.settings.parents.addError', { defaultValue: 'שגיאה בהוספת הורה' }) + ': ' + (error.message || 'Unknown error'));
                        } finally {
                          setUpdatingParent(false);
                        }
                      }}
                      disabled={updatingParent || !newParentName.trim() || !newParentPhone.trim()}
                    >
                      {updatingParent 
                        ? t('common.saving', { defaultValue: 'שומר...' })
                        : t('common.save', { defaultValue: 'שמור' })
                      }
                    </button>
                    <button
                      className="cancel-button"
                      onClick={() => {
                        setAddingParent(false);
                        setNewParentName('');
                        setNewParentPhone('');
                      }}
                    >
                      {t('common.cancel', { defaultValue: 'ביטול' })}
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {familyInfo && familyInfo.parents && familyInfo.parents.length > 0 ? (
              <div className="parents-list">
                {familyInfo.parents.map((parent, index) => (
                  <div key={index} className="parent-item">
                    {editingParent === index ? (
                      <div className="parent-edit">
                        <div className="form-group">
                          <label>{t('parent.settings.parents.name', { defaultValue: 'שם' })}:</label>
                          <input
                            type="text"
                            value={editParentName}
                            onChange={(e) => setEditParentName(e.target.value)}
                            placeholder={t('parent.settings.parents.namePlaceholder', { defaultValue: 'שם ההורה' })}
                            className="parent-input"
                          />
                        </div>
                        <div className="form-group">
                          <label>{t('parent.settings.parents.phone', { defaultValue: 'טלפון' })}:</label>
                          <input
                            type="tel"
                            inputMode="numeric"
                            value={editParentPhone}
                            onChange={(e) => setEditParentPhone(e.target.value)}
                            placeholder={t('parent.settings.parents.phonePlaceholder', { defaultValue: 'מספר טלפון' })}
                            className="parent-input"
                          />
                        </div>
                        <div className="parent-actions">
                          <button
                            className="save-button"
                            onClick={async () => {
                              try {
                                setUpdatingParent(true);
                                await updateParentInfo(familyId, editParentName, editParentPhone, parent.isMain);
                                await loadData();
                                setEditingParent(null);
                                setEditParentName('');
                                setEditParentPhone('');
                                alert(t('parent.settings.parents.updateSuccess', { defaultValue: 'פרטי ההורה עודכנו בהצלחה!' }));
                              } catch (error) {
                                alert(t('parent.settings.parents.updateError', { defaultValue: 'שגיאה בעדכון פרטי ההורה' }) + ': ' + error.message);
                              } finally {
                                setUpdatingParent(false);
                              }
                            }}
                            disabled={updatingParent}
                          >
                            {updatingParent 
                              ? t('common.saving', { defaultValue: 'שומר...' })
                              : t('common.save', { defaultValue: 'שמור' })
                            }
                          </button>
                          <button
                            className="cancel-button"
                            onClick={() => {
                              setEditingParent(null);
                              setEditParentName('');
                              setEditParentPhone('');
                            }}
                          >
                            {t('common.cancel', { defaultValue: 'ביטול' })}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="parent-display">
                        <div className="parent-info">
                          <div className="parent-name">
                            <strong>{parent.name || 'הורה1'}</strong>
                            {parent.isMain && (
                              <span className="main-parent-badge">
                                {t('parent.settings.parents.mainParent', { defaultValue: 'הורה ראשי' })}
                              </span>
                            )}
                          </div>
                          <div className="parent-phone">{parent.phoneNumber || 'לא זמין'}</div>
                        </div>
                        <button
                          className="edit-button"
                          onClick={() => {
                            setEditingParent(index);
                            setEditParentName(parent.name || 'הורה1');
                            setEditParentPhone(parent.phoneNumber || '');
                          }}
                        >
                          {t('common.edit', { defaultValue: 'ערוך' })}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-parents-message">
                {t('parent.settings.parents.noParents', { defaultValue: 'אין הורים רשומים' })}
              </div>
            )}
          </div>
        )}
      </div>
  );

  if (inSidebar) {
    return content;
  }

  if (asPage) {
    // Render as full page, not modal
    return (
      <div className="settings-page-container" dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div className="settings-page-content">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
      <div className="modal-content settings-container" onClick={(e) => e.stopPropagation()} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        {content}
      </div>
    </div>
  );
};

export default Settings;

