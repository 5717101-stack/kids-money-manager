import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Capacitor } from '@capacitor/core';
import { getCategories, addCategory, updateCategory, deleteCategory, getData, updateProfileImage, updateWeeklyAllowance, payWeeklyAllowance, createChild, updateChild, getFamilyInfo, updateParentInfo, addParent, archiveChild, archiveParent, getTasks, addTask, updateTask, deleteTask, getTaskHistory, updatePaymentRequestStatus } from '../utils/api';
import { smartCompressImage } from '../utils/imageCompression';
import { invalidateFamilyCache } from '../utils/cache';

const CHILD_COLORS = {
  child1: '#3b82f6', // כחול
  child2: '#ec4899'  // ורוד
};

const CHILD_NAMES = {
  child1: 'אדם',
  child2: 'ג\'וּן'
};

const Settings = ({ familyId, isNewFamily, onClose, onLogout, activeTab: externalActiveTab, hideTabs = false, inSidebar = false, asPage = false, onChildrenUpdated, onTabChange, onParentSaved }) => {
  const { t, i18n } = useTranslation();
  const [internalActiveTab, setInternalActiveTab] = useState('categories'); // 'categories', 'profileImages', 'allowances', 'children', 'parents', 'tasks'
  const activeTab = externalActiveTab !== undefined ? externalActiveTab : internalActiveTab;
  const setActiveTab = externalActiveTab !== undefined ? (tab) => {
    if (onTabChange) {
      onTabChange(tab);
    }
  } : setInternalActiveTab;
  const [categories, setCategories] = useState([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [editingCategory, setEditingCategory] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [newTaskName, setNewTaskName] = useState('');
  const [newTaskPrice, setNewTaskPrice] = useState('');
  const [editingTask, setEditingTask] = useState(null);
  const [showTaskHistory, setShowTaskHistory] = useState(false);
  const [taskHistory, setTaskHistory] = useState([]);
  const [selectedHistoryRequest, setSelectedHistoryRequest] = useState(null);
  const [updatingTaskStatus, setUpdatingTaskStatus] = useState(null); // Track which task status is being updated
  const [allData, setAllData] = useState({ children: {} });
  const [loading, setLoading] = useState(true);
  const [allowanceStates, setAllowanceStates] = useState({});
  const [savingAllowance, setSavingAllowance] = useState({}); // Track which child's allowance is being saved
  const [uploadingImages, setUploadingImages] = useState({});
  const fileInputRefs = useRef({});
  const [newChildName, setNewChildName] = useState('');
  const [newChildPhone, setNewChildPhone] = useState('');
  const [creatingChild, setCreatingChild] = useState(false);
  const [newChildAllowance, setNewChildAllowance] = useState({
    amount: 0,
    type: 'weekly',
    day: 1,
    time: '08:00',
    interestRate: 0
  });
  const newChildNameInputRef = useRef(null);
  const [childPhoneModal, setChildPhoneModal] = useState(null); // { childId, child object with all details }
  const [editingChild, setEditingChild] = useState(null); // childId
  const [editChildName, setEditChildName] = useState('');
  const [editChildPhone, setEditChildPhone] = useState('');
  const [updatingChild, setUpdatingChild] = useState(false);
  const [familyInfo, setFamilyInfo] = useState(null);
  const [editingParent, setEditingParent] = useState(null);
  const [editParentName, setEditParentName] = useState('');
  const [editParentPhone, setEditParentPhone] = useState('');
  const [updatingParent, setUpdatingParent] = useState(false);
  const [addingParent, setAddingParent] = useState(false);
  const [parentPhoneModal, setParentPhoneModal] = useState(null); // { parentIndex, parentName, phoneNumber, createdAt, lastLogin }
  const [newParentName, setNewParentName] = useState('');
  const [newParentPhone, setNewParentPhone] = useState('');
  const newParentNameInputRef = useRef(null);
  const editParentNameInputRef = useRef(null);
  const [showChildJoin, setShowChildJoin] = useState(false);
  const [showGoToChildrenButton, setShowGoToChildrenButton] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  // Auto-edit main parent for new families (only if name is still "הורה1" or empty)
  useEffect(() => {
    if (isNewFamily && activeTab === 'parents' && familyInfo && familyInfo.parents && familyInfo.parents.length > 0) {
      const mainParentIndex = familyInfo.parents.findIndex(p => p.isMain);
      if (mainParentIndex !== -1 && editingParent !== mainParentIndex) {
        const mainParent = familyInfo.parents[mainParentIndex];
        // Only auto-open edit mode if name is still "הורה1" or empty/undefined
        const parentName = mainParent.name || '';
        if (parentName === 'הורה1' || parentName === '' || !parentName.trim()) {
          setEditingParent(mainParentIndex);
          setEditParentName('');
          setEditParentPhone(mainParent.phoneNumber || '');
        }
      }
    }
  }, [isNewFamily, activeTab, familyInfo, editingParent]);

  // Auto-focus on parent name input for new families
  useEffect(() => {
    if (isNewFamily && activeTab === 'parents' && editingParent === 0 && editParentNameInputRef.current) {
      // Multiple attempts to ensure focus works on mobile
      const focusInput = () => {
        if (editParentNameInputRef.current) {
          editParentNameInputRef.current.value = '';
          editParentNameInputRef.current.focus();
          editParentNameInputRef.current.select();
          
          // For mobile, try clicking to trigger keyboard
          if (typeof window !== 'undefined' && Capacitor.isNativePlatform()) {
            editParentNameInputRef.current.click();
          }
        }
      };
      
      // Try immediately
      requestAnimationFrame(() => {
        focusInput();
        // Try again after a delay for mobile
        setTimeout(() => {
          focusInput();
        }, 700);
      });
    }
  }, [isNewFamily, activeTab, editingParent]);

  // Auto-focus on child name input when form opens
  useEffect(() => {
    if (showChildJoin && newChildNameInputRef.current) {
      // Small delay to ensure the input is rendered
      const timer = setTimeout(() => {
        if (newChildNameInputRef.current) {
          newChildNameInputRef.current.focus();
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [showChildJoin]);

  // Auto-focus on parent name input when form opens
  useEffect(() => {
    if (addingParent && newParentNameInputRef.current) {
      // Small delay to ensure the input is rendered
      const timer = setTimeout(() => {
        if (newParentNameInputRef.current) {
          newParentNameInputRef.current.focus();
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [addingParent]);

  const loadData = async () => {
    try {
      setLoading(true);
      if (!familyId) {
        setLoading(false);
        return;
      }
      
      console.log('[SETTINGS] Loading data for family:', familyId);
      const [categoriesData, childrenData, familyData, tasksData] = await Promise.all([
        getCategories(familyId).catch(err => {
          console.error('Error loading categories:', err);
          return [];
        }),
        getData(familyId).catch(err => {
          console.error('[SETTINGS] Error loading children data:', err);
          console.error('[SETTINGS] Error details:', {
            message: err?.message,
            stack: err?.stack,
            name: err?.name,
            error: err
          });
          // Return empty children object to prevent crash
          return { children: {} };
        }),
        getFamilyInfo(familyId).catch(err => {
          console.error('Error loading family info:', err);
          return null;
        }),
        getTasks(familyId).catch(err => {
          console.error('Error loading tasks:', err);
          return [];
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
      setTasks(Array.isArray(tasksData) ? tasksData : []);
      
      // Debug: Log family info to see what we're getting
      console.log('[SETTINGS] Family info loaded:', familyData);
      console.log('[SETTINGS] Family info parents:', familyData?.parents);
      console.log('[SETTINGS] Family info parents length:', familyData?.parents?.length || 0);
      
      // Initialize allowance states
      const states = {};
      Object.entries(childrenData?.children || {}).forEach(([childId, child]) => {
        states[childId] = {
          amount: child.weeklyAllowance || 0,
          type: child.allowanceType || 'weekly',
          day: child.allowanceDay !== undefined ? child.allowanceDay : 1,
          time: child.allowanceTime || '08:00',
          interestRate: child.weeklyInterestRate || 0
        };
      });
      setAllowanceStates(states);
    } catch (error) {
      console.error('[SETTINGS] Error loading settings data:', error);
      console.error('[SETTINGS] Error details:', {
        message: error?.message,
        stack: error?.stack,
        name: error?.name,
        error: error
      });
      // Set empty data to prevent white screen
      setCategories([]);
      setAllData({ children: {} });
      setFamilyInfo(null);
      setAllowanceStates({});
      // Don't show alert if it's just a network error - let user retry
      if (!error.message?.includes('Failed to fetch') && !error.message?.includes('aborted')) {
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
      
      // Show success notification
      const notification = document.createElement('div');
      notification.textContent = t('parent.settings.alerts.updateCategorySuccess', { defaultValue: 'קטגוריה עודכנה בהצלחה!' });
      const isRTL = i18n.language === 'he';
      const animationName = isRTL ? 'slideInRTL' : 'slideIn';
      const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
      const rightOrLeft = isRTL ? 'left' : 'right';
      notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        ${rightOrLeft}: 20px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        z-index: 10005;
        font-weight: 600;
        animation: ${animationName} 0.3s ease;
        max-width: calc(100% - 40px);
      `;
      document.body.appendChild(notification);
      setTimeout(() => {
        notification.style.animation = `${animationOutName} 0.3s ease`;
        setTimeout(() => notification.remove(), 300);
      }, 2000);
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
      
      // Show success notification
      const notification = document.createElement('div');
      notification.textContent = t('parent.settings.alerts.deleteCategorySuccess', { defaultValue: 'קטגוריה נמחקה בהצלחה!' });
      const isRTL = i18n.language === 'he';
      const animationName = isRTL ? 'slideInRTL' : 'slideIn';
      const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
      const rightOrLeft = isRTL ? 'left' : 'right';
      notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        ${rightOrLeft}: 20px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        z-index: 10005;
        font-weight: 600;
        animation: ${animationName} 0.3s ease;
        max-width: calc(100% - 40px);
      `;
      document.body.appendChild(notification);
      setTimeout(() => {
        notification.style.animation = `${animationOutName} 0.3s ease`;
        setTimeout(() => notification.remove(), 300);
      }, 2000);
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
        
        // Show success notification
        const notification = document.createElement('div');
        notification.textContent = t('parent.settings.alerts.removeImageSuccess', { defaultValue: 'תמונת הפרופיל הוסרה בהצלחה!' });
        const isRTL = i18n.language === 'he';
        const animationName = isRTL ? 'slideInRTL' : 'slideIn';
        const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
        const rightOrLeft = isRTL ? 'left' : 'right';
        notification.style.cssText = `
          position: fixed;
          bottom: 100px;
          ${rightOrLeft}: 20px;
          background: linear-gradient(135deg, #10B981 0%, #059669 100%);
          color: white;
          padding: 16px 24px;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
          z-index: 10005;
          font-weight: 600;
          animation: ${animationName} 0.3s ease;
          max-width: calc(100% - 40px);
        `;
        document.body.appendChild(notification);
        setTimeout(() => {
          notification.style.animation = `${animationOutName} 0.3s ease`;
          setTimeout(() => notification.remove(), 300);
        }, 2000);
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
      
      // Show success notification
      const notification = document.createElement('div');
      notification.textContent = t('parent.settings.alerts.updateImageSuccess', { defaultValue: 'תמונת הפרופיל עודכנה בהצלחה!' });
      const isRTL = i18n.language === 'he';
      const animationName = isRTL ? 'slideInRTL' : 'slideIn';
      const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
      const rightOrLeft = isRTL ? 'left' : 'right';
      notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        ${rightOrLeft}: 20px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        z-index: 10005;
        font-weight: 600;
        animation: ${animationName} 0.3s ease;
        max-width: calc(100% - 40px);
      `;
      document.body.appendChild(notification);
      setTimeout(() => {
        notification.style.animation = `${animationOutName} 0.3s ease`;
        setTimeout(() => notification.remove(), 300);
      }, 2000);
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

  const handleAllowanceUpdate = async (childId, allowance, allowanceType, allowanceDay, allowanceTime, weeklyInterestRate) => {
    setSavingAllowance(prev => ({ ...prev, [childId]: true }));
    if (!familyId) return;
    try {
      await updateWeeklyAllowance(familyId, childId, allowance, allowanceType, allowanceDay, allowanceTime, weeklyInterestRate);
      // Reload data without showing loading spinner
      const wasLoading = loading;
      if (!wasLoading) {
        // Load data silently without showing loading state
        try {
          const [categoriesData, childrenData, familyData] = await Promise.all([
            getCategories(familyId).catch(() => []),
            getData(familyId).catch(() => ({ children: {} })),
            getFamilyInfo(familyId).catch(() => null)
          ]);
          
          setCategories(Array.isArray(categoriesData) ? categoriesData : []);
          setAllData(childrenData && childrenData.children ? childrenData : { children: {} });
          setFamilyInfo(familyData);
          
          // Update allowance states
          const states = {};
          Object.entries(childrenData?.children || {}).forEach(([id, child]) => {
            states[id] = {
              amount: child.weeklyAllowance || 0,
              type: child.allowanceType || 'weekly',
              day: child.allowanceDay !== undefined ? child.allowanceDay : 1,
              time: child.allowanceTime || '08:00',
              interestRate: child.weeklyInterestRate || 0
            };
          });
          setAllowanceStates(states);
        } catch (err) {
          console.error('Error silently reloading data:', err);
        }
      } else {
        await loadData();
      }
      
      // Show success notification
      const notification = document.createElement('div');
      notification.textContent = t('parent.settings.alerts.updateAllowanceSuccess', { defaultValue: 'דמי הכיס עודכנו בהצלחה!' });
      const isRTL = i18n.language === 'he';
      const animationName = isRTL ? 'slideInRTL' : 'slideIn';
      const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
      const rightOrLeft = isRTL ? 'left' : 'right';
      notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        ${rightOrLeft}: 20px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        z-index: 10005;
        font-weight: 600;
        animation: ${animationName} 0.3s ease;
        max-width: calc(100% - 40px);
      `;
      document.body.appendChild(notification);
      setTimeout(() => {
        notification.style.animation = `${animationOutName} 0.3s ease`;
        setTimeout(() => notification.remove(), 300);
      }, 2000);
    } catch (error) {
      alert(t('parent.settings.alerts.updateAllowanceError', { defaultValue: 'שגיאה בעדכון דמי הכיס' }) + ': ' + error.message);
    } finally {
      setSavingAllowance(prev => ({ ...prev, [childId]: false }));
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

  const handleAddTask = async (e) => {
    e.preventDefault();
    if (!newTaskName.trim() || !newTaskPrice.trim()) {
      alert(t('parent.settings.tasks.enterTaskDetails', { defaultValue: 'אנא הכנס שם מטלה ומחיר' }));
      return;
    }

    if (!familyId) return;
    try {
      console.log('[SETTINGS] Adding task:', {
        familyId,
        name: newTaskName.trim(),
        price: parseFloat(newTaskPrice),
        childrenIds: Object.keys(allData.children || {})
      });
      
      const childrenIds = Object.keys(allData.children || {});
      const task = await addTask(familyId, newTaskName.trim(), parseFloat(newTaskPrice), childrenIds);
      setTasks([...tasks, task]);
      setNewTaskName('');
      setNewTaskPrice('');
    } catch (error) {
      console.error('[SETTINGS] Error adding task:', error);
      console.error('[SETTINGS] Error details:', {
        message: error.message,
        stack: error.stack,
        name: error.name
      });
      const errorMessage = error.message || 'Unknown error';
      alert(t('parent.settings.tasks.addTaskError', { defaultValue: 'שגיאה בהוספת מטלה' }) + ': ' + errorMessage);
    }
  };

  const handleUpdateTask = async (taskId, name, price, activeFor) => {
    if (!familyId) return;
    try {
      await updateTask(familyId, taskId, name, price, activeFor);
      setTasks(tasks.map(t => 
        t._id === taskId ? { ...t, name, price, activeFor } : t
      ));
      setEditingTask(null);
      
      // Show success notification
      const notification = document.createElement('div');
      notification.textContent = t('parent.settings.tasks.updateTaskSuccess', { defaultValue: 'מטלה עודכנה בהצלחה!' });
      const isRTL = i18n.language === 'he';
      const animationName = isRTL ? 'slideInRTL' : 'slideIn';
      const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
      const rightOrLeft = isRTL ? 'left' : 'right';
      notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        ${rightOrLeft}: 20px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        z-index: 10005;
        font-weight: 600;
        animation: ${animationName} 0.3s ease;
        max-width: calc(100% - 40px);
      `;
      document.body.appendChild(notification);
      setTimeout(() => {
        notification.style.animation = `${animationOutName} 0.3s ease`;
        setTimeout(() => notification.remove(), 300);
      }, 2000);
    } catch (error) {
      alert(t('parent.settings.tasks.updateTaskError', { defaultValue: 'שגיאה בעדכון מטלה' }) + ': ' + error.message);
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm(t('parent.settings.tasks.deleteTaskConfirm', { defaultValue: 'האם אתה בטוח שברצונך למחוק את המטלה?' }))) {
      return;
    }

    if (!familyId) return;
    try {
      await deleteTask(familyId, taskId);
      setTasks(tasks.filter(t => t._id !== taskId));
      
      // Show success notification
      const notification = document.createElement('div');
      notification.textContent = t('parent.settings.tasks.deleteTaskSuccess', { defaultValue: 'מטלה נמחקה בהצלחה!' });
      const isRTL = i18n.language === 'he';
      const animationName = isRTL ? 'slideInRTL' : 'slideIn';
      const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
      const rightOrLeft = isRTL ? 'left' : 'right';
      notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        ${rightOrLeft}: 20px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        z-index: 10005;
        font-weight: 600;
        animation: ${animationName} 0.3s ease;
        max-width: calc(100% - 40px);
      `;
      document.body.appendChild(notification);
      setTimeout(() => {
        notification.style.animation = `${animationOutName} 0.3s ease`;
        setTimeout(() => notification.remove(), 300);
      }, 2000);
    } catch (error) {
      alert(t('parent.settings.tasks.deleteTaskError', { defaultValue: 'שגיאה במחיקת מטלה' }) + ': ' + error.message);
    }
  };

  const toggleTaskForChild = (taskId, childId) => {
    const task = tasks.find(t => t._id === taskId);
    if (!task) return;

    const activeFor = task.activeFor || [];
    const newActiveFor = activeFor.includes(childId)
      ? activeFor.filter(id => id !== childId)
      : [...activeFor, childId];

    handleUpdateTask(taskId, task.name, task.price, newActiveFor);
  };

  const loadTaskHistory = async () => {
    if (!familyId) return;
    try {
      const history = await getTaskHistory(familyId);
      setTaskHistory(history);
    } catch (error) {
      console.error('Error loading task history:', error);
      alert(t('parent.settings.tasks.loadHistoryError', { defaultValue: 'שגיאה בטעינת היסטוריית מטלות' }) + ': ' + error.message);
    }
  };

  const handleUpdateTaskStatus = async (requestId, newStatus) => {
    if (!familyId) return;
    try {
      setUpdatingTaskStatus(requestId);
      await updatePaymentRequestStatus(familyId, requestId, newStatus);
      await loadTaskHistory();
      await loadData(); // Reload to update balances
    } catch (error) {
      alert(t('parent.settings.tasks.updateStatusError', { defaultValue: 'שגיאה בעדכון סטטוס' }) + ': ' + error.message);
    } finally {
      setUpdatingTaskStatus(null);
    }
  };

  if (loading) {
    if (inSidebar) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 20px',
          gap: '20px'
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            border: '5px solid rgba(99, 102, 241, 0.2)',
            borderTopColor: '#6366F1',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite'
          }}></div>
          <div style={{ color: 'var(--text-muted)', fontSize: '16px', fontWeight: 500 }}>
            {t('common.loading', { defaultValue: 'טוען...' })}
          </div>
        </div>
      );
    }
    return (
      <div className="modal-overlay" onClick={onClose} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
        <div className="modal-content settings-container" onClick={(e) => e.stopPropagation()} dir={i18n.language === 'he' ? 'rtl' : 'ltr'}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '60px 20px',
            gap: '20px'
          }}>
            <div style={{
              width: '48px',
              height: '48px',
              border: '5px solid rgba(99, 102, 241, 0.2)',
              borderTopColor: '#6366F1',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }}></div>
            <div style={{ color: 'var(--text-muted)', fontSize: '16px', fontWeight: 500 }}>
              {t('common.loading', { defaultValue: 'טוען...' })}
            </div>
          </div>
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
            className={activeTab === 'tasks' ? 'active' : ''}
            onClick={() => {
              setActiveTab('tasks');
              setShowTaskHistory(false);
            }}
          >
            {t('parent.settings.tabs.tasks', { defaultValue: 'מטלות' })}
          </button>
          <button
            className={activeTab === 'profileImages' ? 'active' : ''}
            onClick={() => setActiveTab('profileImages')}
          >
            {t('parent.settings.tabs.profileImages', { defaultValue: 'תמונות פרופיל' })}
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

        {activeTab === 'tasks' && (
          <div className="tasks-section" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              {!asPage && (
                <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>
                  {showTaskHistory 
                    ? t('parent.settings.tasks.history', { defaultValue: 'היסטוריית מטלות' })
                    : t('parent.settings.tasks.title', { defaultValue: 'ניהול מטלות' })
                  }
                </h2>
              )}
              {asPage && !showTaskHistory && (
                <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>
                  {t('parent.settings.tasks.title', { defaultValue: 'ניהול מטלות' })}
                </h2>
              )}
              {asPage && showTaskHistory && (
                <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>
                  {t('parent.settings.tasks.history', { defaultValue: 'היסטוריית מטלות' })}
                </h2>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {!showTaskHistory ? (
                  <button
                    onClick={async () => {
                      await loadTaskHistory();
                      setShowTaskHistory(true);
                      setSelectedHistoryRequest(null);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      fontSize: '28px',
                      cursor: 'pointer',
                      padding: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--primary)',
                      minWidth: '44px',
                      minHeight: '44px'
                    }}
                    title={t('parent.settings.tasks.history', { defaultValue: 'היסטוריית מטלות' })}
                  >
                    📋
                  </button>
                ) : (
                      <button
                    onClick={() => {
                      setShowTaskHistory(false);
                      setSelectedHistoryRequest(null);
                    }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '8px',
                      background: 'white',
                      color: 'var(--primary)',
                      border: '1px solid var(--primary)',
                      fontSize: '14px',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    {t('parent.settings.tasks.backToTasks', { defaultValue: 'חזרה למטלות' })}
                      </button>
                    )}
                  </div>
                </div>
            
            {!showTaskHistory ? (
              <>
                {/* Input Group */}
                <form onSubmit={handleAddTask} style={{ display: 'flex', gap: '10px', width: '100%', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    value={newTaskName}
                    onChange={(e) => setNewTaskName(e.target.value)}
                    placeholder={t('parent.settings.tasks.taskName', { defaultValue: 'שם המטלה' })}
                    style={{
                      flex: '1 1 200px',
                      minWidth: '150px',
                      height: '50px',
                      borderRadius: '12px',
                      border: '1px solid rgba(0,0,0,0.1)',
                      padding: '0 16px',
                      fontSize: '16px',
                      outline: 'none'
                    }}
                  />
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flex: '0 0 auto' }}>
                      <input
                        type="number"
                        inputMode="decimal"
                        step="0.01"
                        min="0"
                      value={newTaskPrice}
                      onChange={(e) => setNewTaskPrice(e.target.value)}
                      placeholder={t('parent.settings.tasks.price', { defaultValue: 'מחיר' })}
                        style={{ 
                        width: '120px',
                        height: '50px',
                        borderRadius: '12px',
                        border: '1px solid rgba(0,0,0,0.1)',
                        padding: '0 16px',
                        fontSize: '16px',
                        outline: 'none',
                        direction: 'ltr',
                        textAlign: 'left'
                      }}
                    />
                    <span style={{ fontSize: '16px', fontWeight: 600 }}>₪</span>
                    </div>
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
                    {t('parent.settings.tasks.addTask', { defaultValue: 'הוסף מטלה' })}
                      </button>
                </form>

                {/* Tasks List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {tasks.map(task => (
                    <div 
                      key={task._id} 
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
                      {editingTask === task._id ? (
                        <>
                          <input
                            type="text"
                            defaultValue={task.name}
                            onBlur={(e) => {
                              if (e.target.value !== task.name) {
                                handleUpdateTask(task._id, e.target.value, task.price, task.activeFor);
                              } else {
                                setEditingTask(null);
                              }
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.target.blur();
                              } else if (e.key === 'Escape') {
                                setEditingTask(null);
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
                      <input
                        type="number"
                        inputMode="decimal"
                        step="0.01"
                        min="0"
                            defaultValue={task.price}
                            onBlur={(e) => {
                              const newPrice = parseFloat(e.target.value) || 0;
                              if (newPrice !== task.price) {
                                handleUpdateTask(task._id, task.name, newPrice, task.activeFor);
                              }
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.target.blur();
                              } else if (e.key === 'Escape') {
                                setEditingTask(null);
                              }
                            }}
                        style={{ 
                              width: '100px',
                              padding: '8px 12px',
                              borderRadius: '8px',
                              border: '1px solid rgba(0,0,0,0.1)',
                              fontSize: '16px',
                              outline: 'none',
                              direction: 'ltr',
                              textAlign: 'left'
                            }}
                          />
                          <span style={{ fontSize: '16px', fontWeight: 600 }}>₪</span>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => handleDeleteTask(task._id)}
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
                          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <span 
                              onClick={() => setEditingTask(task._id)}
                              style={{
                                fontSize: '16px',
                                fontWeight: 600,
                                cursor: 'pointer'
                              }}
                            >
                              {task.name}
                            </span>
                            <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                              ₪{task.price.toFixed(2)}
                            </span>
                    </div>
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
                                  checked={(task.activeFor || []).includes(childId)}
                                  onChange={() => toggleTaskForChild(task._id, childId)}
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
                  {tasks.length === 0 && (
                    <div style={{ 
                      padding: '40px', 
                      textAlign: 'center', 
                      color: 'var(--text-muted)',
                      fontSize: '16px'
                    }}>
                      {t('parent.settings.tasks.noTasks', { defaultValue: 'אין מטלות. הוסף מטלה חדשה למעלה.' })}
                    </div>
                        )}
                      </div>
              </>
            ) : selectedHistoryRequest ? (
              <div style={{ 
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                maxHeight: '80vh',
                overflow: 'hidden'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexShrink: 0 }}>
                  <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>{selectedHistoryRequest.taskName}</h3>
                  <button
                    onClick={() => setSelectedHistoryRequest(null)}
                    style={{
                      background: 'none',
                      border: 'none',
                      fontSize: '24px',
                      cursor: 'pointer',
                      padding: '4px',
                      color: 'var(--text-muted)'
                    }}
                  >
                    ✕
                  </button>
                </div>
                <div style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '16px',
                  overflowY: 'auto',
                  flex: 1,
                  minHeight: 0,
                  paddingRight: '8px'
                }}>
                        <div>
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {t('parent.dashboard.child', { defaultValue: 'ילד' })}
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 600 }}>{selectedHistoryRequest.childName}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {t('parent.dashboard.amount', { defaultValue: 'סכום' })}
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--primary)' }}>
                      ₪{selectedHistoryRequest.taskPrice.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {t('parent.dashboard.requestedAt', { defaultValue: 'זמן ביצוע' })}
                    </div>
                    <div style={{ fontSize: '14px' }}>
                      {new Date(selectedHistoryRequest.requestedAt).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US', {
                            year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {t('parent.settings.tasks.status', { defaultValue: 'סטטוס' })}
                    </div>
                    <div style={{
                      display: 'inline-block',
                      padding: '6px 12px',
                      borderRadius: '8px',
                      background: selectedHistoryRequest.status === 'approved' ? '#10B981' : selectedHistoryRequest.status === 'rejected' ? '#EF4444' : '#F59E0B',
                      color: 'white',
                      fontSize: '14px',
                      fontWeight: 600
                    }}>
                      {selectedHistoryRequest.status === 'approved' 
                        ? t('parent.settings.tasks.statusApproved', { defaultValue: 'אושר' })
                        : selectedHistoryRequest.status === 'rejected'
                        ? t('parent.settings.tasks.statusRejected', { defaultValue: 'נדחה' })
                        : t('parent.settings.tasks.statusPending', { defaultValue: 'ממתין' })
                      }
                    </div>
                  </div>
                  {selectedHistoryRequest.note && (
                    <div>
                      <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        {t('parent.dashboard.note', { defaultValue: 'הערה' })}
                      </div>
                      <div style={{ fontSize: '14px', padding: '12px', background: '#F9FAFB', borderRadius: '8px' }}>
                        {selectedHistoryRequest.note}
                      </div>
                    </div>
                  )}
                  {selectedHistoryRequest.image && (
                    <div>
                      <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        {t('parent.dashboard.image', { defaultValue: 'תמונה' })}
                      </div>
                      <img 
                        src={selectedHistoryRequest.image} 
                        alt="Task completion" 
                        style={{
                          maxWidth: '100%',
                          maxHeight: '200px',
                          width: 'auto',
                          height: 'auto',
                          borderRadius: '8px',
                          objectFit: 'contain',
                          display: 'block'
                        }}
                      />
                    </div>
                  )}
                </div>
                <div style={{ 
                  display: 'flex', 
                  gap: '12px', 
                  marginTop: '20px',
                  flexShrink: 0,
                  paddingTop: '16px',
                  borderTop: '1px solid rgba(0,0,0,0.1)'
                }}>
                    <button
                    onClick={async () => {
                      const newStatus = selectedHistoryRequest.status === 'approved' ? 'rejected' : 'approved';
                      await handleUpdateTaskStatus(selectedHistoryRequest._id, newStatus);
                      // Update local state
                      const updated = { ...selectedHistoryRequest, status: newStatus };
                      setSelectedHistoryRequest(updated);
                      // Update in history list
                      setTaskHistory(taskHistory.map(r => r._id === selectedHistoryRequest._id ? updated : r));
                    }}
                    disabled={updatingTaskStatus === selectedHistoryRequest._id}
                    style={{
                      flex: 1,
                      padding: '12px',
                      borderRadius: '8px',
                      background: selectedHistoryRequest.status === 'approved' ? '#EF4444' : '#10B981',
                      color: 'white',
                      border: 'none',
                      fontSize: '16px',
                      fontWeight: 600,
                      cursor: updatingTaskStatus === selectedHistoryRequest._id ? 'not-allowed' : 'pointer',
                      opacity: updatingTaskStatus === selectedHistoryRequest._id ? 0.6 : 1,
                      animation: updatingTaskStatus === selectedHistoryRequest._id ? 'pulse 1.5s ease-in-out infinite' : 'none'
                    }}
                  >
                    {updatingTaskStatus === selectedHistoryRequest._id
                      ? t('common.saving', { defaultValue: 'שומר...' })
                      : selectedHistoryRequest.status === 'approved' 
                      ? t('parent.settings.tasks.reject', { defaultValue: 'דחה' })
                      : t('parent.settings.tasks.approve', { defaultValue: 'אשר' })
                    }
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {taskHistory.map(request => (
                  <button
                    key={request._id}
                    onClick={() => setSelectedHistoryRequest(request)}
                    style={{
                      background: 'white',
                      padding: '16px',
                      borderRadius: '16px',
                      boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
                      border: 'none',
                      cursor: 'pointer',
                      textAlign: 'right',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '12px'
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '4px' }}>{request.taskName}</div>
                      <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                        {request.childName} - ₪{request.taskPrice.toFixed(2)}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        {new Date(request.requestedAt).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                      <div style={{
                        padding: '6px 12px',
                        borderRadius: '8px',
                        background: request.status === 'approved' ? '#10B981' : request.status === 'rejected' ? '#EF4444' : '#F59E0B',
                        color: 'white',
                        fontSize: '12px',
                        fontWeight: 600
                      }}>
                        {request.status === 'approved' 
                          ? t('parent.settings.tasks.statusApproved', { defaultValue: 'אושר' })
                          : request.status === 'rejected'
                          ? t('parent.settings.tasks.statusRejected', { defaultValue: 'נדחה' })
                          : t('parent.settings.tasks.statusPending', { defaultValue: 'ממתין' })
                        }
                      </div>
                      <span style={{ fontSize: '20px', color: 'var(--text-muted)' }}>→</span>
                    </div>
                  </button>
                ))}
                {taskHistory.length === 0 && (
                  <div style={{ 
                    padding: '40px', 
                    textAlign: 'center', 
                    color: 'var(--text-muted)',
                    fontSize: '16px'
                  }}>
                    {t('parent.settings.tasks.noHistory', { defaultValue: 'אין היסטוריית מטלות.' })}
                  </div>
                )}
              </div>
            )}
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
                  <div className="profile-image-preview" style={{ position: 'relative' }}>
                    {profileImage ? (
                      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                        <img 
                          src={profileImage} 
                          alt={childName}
                          onError={(e) => {
                            console.error('Error loading profile image:', e);
                            e.target.style.display = 'none';
                          }}
                          style={{
                            opacity: uploadingImages[childId] ? 0.5 : 1,
                            transition: 'opacity 0.2s'
                          }}
                        />
                        {uploadingImages[childId] && (
                          <div style={{
                            position: 'absolute',
                            top: '50%',
                            left: '50%',
                            transform: 'translate(-50%, -50%)',
                            width: '30px',
                            height: '30px',
                            border: '3px solid rgba(255, 255, 255, 0.3)',
                            borderTop: '3px solid white',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite'
                          }} />
                        )}
                      </div>
                    ) : (
                      <div className="profile-placeholder" style={{
                        opacity: uploadingImages[childId] ? 0.5 : 1,
                        transition: 'opacity 0.2s',
                        position: 'relative'
                      }}>
                        {!uploadingImages[childId] && childName.charAt(0)}
                        {uploadingImages[childId] && (
                          <div style={{
                            width: '30px',
                            height: '30px',
                            border: '3px solid rgba(255, 255, 255, 0.3)',
                            borderTop: '3px solid white',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite'
                          }} />
                        )}
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

        {activeTab === 'children' && (
          <div className="children-section" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {!asPage && <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>{t('parent.settings.manageChildren', { defaultValue: 'הגדרת ילדים' })}</h2>}
            
            {showChildJoin && (
              <div style={{
                background: 'white',
                padding: '24px',
                borderRadius: '16px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
                border: '1px solid rgba(99, 102, 241, 0.2)',
                marginBottom: '16px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>{t('parent.settings.addChild', { defaultValue: 'הוסף ילד חדש' })}</h3>
                  <button
                    onClick={() => setShowChildJoin(false)}
                    style={{
                      background: 'none',
                      border: 'none',
                      fontSize: '24px',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '0',
                      width: '32px',
                      height: '32px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    ×
                  </button>
                </div>
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
                    
                    // Update allowance settings for the new child
                    if (newChildAllowance.amount > 0 || newChildAllowance.interestRate > 0) {
                      await updateWeeklyAllowance(
                        familyId,
                        result.child._id,
                        newChildAllowance.amount,
                        newChildAllowance.type,
                        newChildAllowance.day,
                        newChildAllowance.time,
                        newChildAllowance.interestRate
                      );
                    }
                    
                    setChildPhoneModal({
                      childId: result.child._id,
                      child: result.child
                    });
                    setNewChildName('');
                    setNewChildPhone('');
                    setNewChildAllowance({
                      amount: 0,
                      type: 'weekly',
                      day: 1,
                      time: '08:00',
                      interestRate: 0
                    });
                    
                    // Reload data to get updated allowance settings
                    await loadData();
                    
                    // Close the form
                    setShowChildJoin(false);
                    
                    // Show success notification
                    const notification = document.createElement('div');
                    notification.textContent = t('parent.settings.createChildSuccess', { defaultValue: 'ילד נוסף בהצלחה!' });
                    const isRTL = i18n.language === 'he';
                    const animationName = isRTL ? 'slideInRTL' : 'slideIn';
                    const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
                    const rightOrLeft = isRTL ? 'left' : 'right';
                    notification.style.cssText = `
                      position: fixed;
                      bottom: 100px;
                      ${rightOrLeft}: 20px;
                      background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                      color: white;
                      padding: 16px 24px;
                      border-radius: 12px;
                      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                      z-index: 10005;
                      font-weight: 600;
                      animation: ${animationName} 0.3s ease;
                      max-width: calc(100% - 40px);
                    `;
                    document.body.appendChild(notification);
                    setTimeout(() => {
                      notification.style.animation = `${animationOutName} 0.3s ease`;
                      setTimeout(() => notification.remove(), 300);
                    }, 2000);
                    
                    // Notify parent component to refresh children list (without closing the page)
                    if (onChildrenUpdated && typeof onChildrenUpdated === 'function') {
                      try {
                        await onChildrenUpdated();
                      } catch (err) {
                        console.warn('[CREATE-CHILD] Error calling onChildrenUpdated:', err);
                        // Don't fail the whole operation if this callback fails
                      }
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
                {/* Child Name */}
                <div className="allowance-config-group">
                  <label className="allowance-label">{t('parent.settings.childName', { defaultValue: 'שם הילד' })}</label>
                <input
                  ref={newChildNameInputRef}
                  type="text"
                  value={newChildName}
                  onChange={(e) => setNewChildName(e.target.value)}
                  placeholder={t('parent.settings.childName', { defaultValue: 'שם הילד' })}
                    className="allowance-input"
                  autoFocus
                  required
                />
                </div>

                {/* Child Phone */}
                <div className="allowance-config-group">
                  <label className="allowance-label">{t('parent.settings.childPhone', { defaultValue: 'מספר טלפון לילד' })}</label>
                <input
                  type="tel"
                  value={newChildPhone}
                  onChange={(e) => setNewChildPhone(e.target.value)}
                  placeholder={t('parent.settings.childPhone', { defaultValue: 'מספר טלפון לילד' })}
                  inputMode="numeric"
                    className="allowance-input"
                    style={{ direction: 'ltr', textAlign: 'left' }}
                    required
                  />
                </div>

                {/* Allowance Amount */}
                <div className="allowance-config-group">
                  <label className="allowance-label">{t('parent.settings.allowance.amount', { defaultValue: 'סכום קצבה' })}</label>
                  <div className="allowance-input-group" style={{ direction: i18n.language === 'he' ? 'rtl' : 'ltr' }}>
                    {i18n.language === 'he' && <span className="currency-label" style={{ right: '16px', left: 'auto' }}>₪</span>}
                    <input
                      type="number"
                      inputMode="decimal"
                      step="0.01"
                      min="0"
                      value={newChildAllowance.amount === 0 ? '' : newChildAllowance.amount}
                      onChange={(e) => {
                        const val = e.target.value === '' ? 0 : parseFloat(e.target.value) || 0;
                        setNewChildAllowance(prev => ({ ...prev, amount: val }));
                      }}
                      className="allowance-input"
                      placeholder="0.00"
                  style={{
                        maxWidth: '200px',
                        paddingRight: i18n.language === 'he' ? '40px' : undefined, 
                        paddingLeft: i18n.language === 'he' ? undefined : '40px' 
                      }}
                    />
                    {i18n.language !== 'he' && <span className="currency-label">₪</span>}
                  </div>
                </div>

                {/* Frequency */}
                <div className="allowance-config-group">
                  <label className="allowance-label">{t('parent.settings.allowance.frequency', { defaultValue: 'תדירות' })}</label>
                  <div className="frequency-toggle">
                <button
                      type="button"
                      className={`frequency-button ${newChildAllowance.type === 'weekly' ? 'active' : ''}`}
                      onClick={() => {
                        const newDay = newChildAllowance.day === 0 ? 1 : newChildAllowance.day;
                        setNewChildAllowance(prev => ({ ...prev, type: 'weekly', day: newDay }));
                      }}
                    >
                      {t('parent.settings.allowance.weekly', { defaultValue: 'שבועי' })}
                    </button>
                    <button
                      type="button"
                      className={`frequency-button ${newChildAllowance.type === 'monthly' ? 'active' : ''}`}
                      onClick={() => {
                        const newDay = newChildAllowance.day === 0 ? 1 : newChildAllowance.day;
                        setNewChildAllowance(prev => ({ ...prev, type: 'monthly', day: newDay }));
                      }}
                    >
                      {t('parent.settings.allowance.monthly', { defaultValue: 'חודשי' })}
                    </button>
                  </div>
                </div>

                {/* Day/Date and Time - Same Row */}
                <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', width: '100%' }}>
                  <div style={{ flex: '1 1 60%', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <label className="allowance-label">
                      {newChildAllowance.type === 'weekly' 
                        ? t('parent.settings.allowance.dayOfWeek', { defaultValue: 'יום בשבוע' })
                        : t('parent.settings.allowance.dateOfMonth', { defaultValue: 'תאריך בחודש' })
                      }
                    </label>
                    {newChildAllowance.type === 'weekly' ? (
                      <select
                        value={newChildAllowance.day}
                        onChange={(e) => {
                          setNewChildAllowance(prev => ({ ...prev, day: parseInt(e.target.value) }));
                        }}
                        className="allowance-select"
                        style={{ width: '100%', maxWidth: '200px' }}
                      >
                        {dayNames.map((dayName, index) => (
                          <option key={index} value={index}>{dayName}</option>
                        ))}
                      </select>
                    ) : (
                      <select
                        value={newChildAllowance.day}
                        onChange={(e) => {
                          setNewChildAllowance(prev => ({ ...prev, day: parseInt(e.target.value) }));
                        }}
                        className="allowance-select"
                        style={{ width: '100%', maxWidth: '200px' }}
                      >
                        {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
                          <option key={day} value={day}>
                            {day}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                  <div style={{ flex: '1 1 40%', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <label className="allowance-label">{t('parent.settings.allowance.time', { defaultValue: 'שעה' })}</label>
                    <input
                      type="time"
                      value={newChildAllowance.time}
                      onChange={(e) => {
                        setNewChildAllowance(prev => ({ ...prev, time: e.target.value }));
                      }}
                      className="allowance-input allowance-time-input"
                      style={{ width: '100%', maxWidth: '150px' }}
                    />
                  </div>
                </div>

                {/* Interest Rate */}
                <div className="allowance-config-group">
                  <label className="allowance-label">{t('parent.settings.allowance.interestRate', { defaultValue: 'ריבית שבועית (%)' })}</label>
                  <div className="allowance-input-group" style={{ direction: i18n.language === 'he' ? 'rtl' : 'ltr' }}>
                    {i18n.language === 'he' && <span className="currency-label" style={{ right: '16px', left: 'auto' }}>%</span>}
                    <input
                      type="number"
                      inputMode="decimal"
                      step="0.01"
                      min="0"
                      max="100"
                      value={newChildAllowance.interestRate === 0 ? '' : newChildAllowance.interestRate}
                      onChange={(e) => {
                        const val = e.target.value === '' ? 0 : parseFloat(e.target.value) || 0;
                        setNewChildAllowance(prev => ({ ...prev, interestRate: val }));
                      }}
                      className="allowance-input"
                      placeholder="0.00"
                  style={{
                        maxWidth: '200px',
                        paddingRight: i18n.language === 'he' ? '40px' : undefined, 
                        paddingLeft: i18n.language === 'he' ? undefined : '40px' 
                      }}
                    />
                    {i18n.language !== 'he' && <span className="currency-label">%</span>}
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {t('parent.settings.allowance.interestDescription', { defaultValue: 'ריבית שבועית על הכסף שנמצא אצל ההורים' })}
                  </p>
                </div>

                {/* Actions */}
                <div className="allowance-actions">
                  <button
                    type="submit"
                    disabled={creatingChild || !newChildName.trim() || !newChildPhone.trim()}
                    className="update-allowance-button"
                >
                  {creatingChild ? (
                    <span style={{
                      display: 'inline-block',
                      animation: 'pulse 1.5s ease-in-out infinite'
                    }}>
                      {t('common.saving', { defaultValue: 'שומר...' })}
                    </span>
                    ) : (
                      t('common.save', { defaultValue: 'שמור' })
                    )}
                </button>
                </div>
              </form>
              </div>
            )}
            
            {!showChildJoin && (
              <button
                className="add-child-button"
                onClick={() => {
                  setShowChildJoin(true);
                  setNewChildName('');
                  setNewChildPhone('');
                  setNewChildAllowance({
                    amount: 0,
                    type: 'weekly',
                    day: 1,
                    time: '08:00',
                    interestRate: 0
                  });
                  // Focus on name input after form opens
                  setTimeout(() => {
                    if (newChildNameInputRef.current) {
                      newChildNameInputRef.current.focus();
                    }
                  }, 100);
                }}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  border: '2px dashed rgba(99, 102, 241, 0.3)',
                  background: 'white',
                  color: 'var(--primary)',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  alignSelf: 'flex-start'
                }}
              >
                + {t('parent.settings.addChild', { defaultValue: 'הוסף ילד' })}
              </button>
            )}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {Object.entries(allData.children || {})
                .filter(([childId, child]) => child && childId) // Filter out null/undefined children
                .map(([childId, child]) => (
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
                    {child?.profileImage && (
                      <img 
                        src={child.profileImage} 
                        alt={child?.name || 'ילד'} 
                        style={{
                          width: '50px',
                          height: '50px',
                          borderRadius: '50%',
                          objectFit: 'cover',
                          flexShrink: 0
                        }}
                        onError={(e) => {
                          console.error('[SETTINGS] Error loading child profile image:', e);
                          e.target.style.display = 'none';
                        }}
                      />
                    )}
                    <div style={{ flex: 1 }}>
                      <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>{child?.name || 'ילד ללא שם'}</h3>
                      <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: 'var(--text-muted)' }}>
                        {t('parent.settings.balance', { defaultValue: 'יתרה' })}: ₪{((child?.balance || 0) + (child?.cashBoxBalance || 0)).toFixed(2)}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                      <button
                        onClick={() => {
                          if (editingChild === childId) {
                            setEditingChild(null);
                            setEditChildName('');
                            setEditChildPhone('');
                            // Reset allowance state to original values
                            setAllowanceStates(prev => ({
                              ...prev,
                              [childId]: {
                                amount: child?.weeklyAllowance || 0,
                                type: child?.allowanceType || 'weekly',
                                day: child?.allowanceDay !== undefined ? child.allowanceDay : 1,
                                time: child?.allowanceTime || '08:00',
                                interestRate: child?.weeklyInterestRate || 0
                              }
                            }));
                          } else {
                            // Close details if open
                            if (childPhoneModal && childPhoneModal.childId === childId) {
                              setChildPhoneModal(null);
                            }
                            setEditingChild(childId);
                            setEditChildName(child?.name || '');
                            setEditChildPhone(child?.phoneNumber || '');
                            // Initialize allowance state for this child
                            setAllowanceStates(prev => ({
                              ...prev,
                              [childId]: {
                                amount: child?.weeklyAllowance || 0,
                                type: child?.allowanceType || 'weekly',
                                day: child?.allowanceDay !== undefined ? child.allowanceDay : 1,
                                time: child?.allowanceTime || '08:00',
                                interestRate: child?.weeklyInterestRate || 0
                              }
                            }));
                          }
                        }}
                        style={{
                          padding: '8px 16px',
                          borderRadius: '8px',
                          border: '1px solid rgba(0,0,0,0.1)',
                          background: (editingChild === childId) ? 'var(--primary)' : 'white',
                          color: (editingChild === childId) ? 'white' : 'var(--text-main)',
                          fontSize: '14px',
                          fontWeight: 500,
                          cursor: 'pointer'
                        }}
                      >
                        {(editingChild === childId) 
                          ? t('common.cancel', { defaultValue: 'ביטול' })
                          : t('common.edit', { defaultValue: 'ערוך' })
                        }
                      </button>
                      <button
                        onClick={() => {
                          if (childPhoneModal && childPhoneModal.childId === childId) {
                            setChildPhoneModal(null);
                          } else {
                            // Close edit if open
                            if (editingChild === childId) {
                              setEditingChild(null);
                              setEditChildName('');
                              setEditChildPhone('');
                            }
                            setChildPhoneModal({ 
                              childId, 
                              child: child
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
                  {childPhoneModal && childPhoneModal.childId === childId && (() => {
                    const modalChild = childPhoneModal.child || child;
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
                    <div style={{
                      marginTop: '12px',
                        padding: '16px',
                      background: 'white',
                        borderRadius: '12px',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                        border: '1px solid rgba(99, 102, 241, 0.15)'
                      }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {/* Phone Number */}
                          <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '10px 12px',
                            background: '#F9FAFB',
                            borderRadius: '8px',
                            border: '1px solid #E5E7EB'
                          }}>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
                              {t('parent.settings.childDetails.phoneNumber', { defaultValue: 'מספר טלפון' })}:
                            </span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-main)', direction: 'ltr', textAlign: 'left' }}>
                                {modalChild?.phoneNumber 
                                  ? (modalChild.phoneNumber.startsWith('+') 
                                      ? modalChild.phoneNumber 
                                      : `+${modalChild.phoneNumber}`)
                                : t('parent.settings.noPhoneNumber', { defaultValue: 'לא מוגדר' })
                              }
                              </span>
                              {modalChild?.phoneNumber && (
                              <button 
                                onClick={() => {
                                    navigator.clipboard.writeText(modalChild.phoneNumber);
                                    alert(t('parent.settings.passwordModal.copied', { defaultValue: 'הועתק!' }));
                                  }}
                                  style={{
                                    padding: '4px 8px',
                                    background: 'var(--primary)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '11px',
                                    cursor: 'pointer',
                                    fontWeight: 500
                                }}
                                title={t('parent.settings.phoneModal.copyPhone', { defaultValue: 'העתק מספר טלפון' })}
                              >
                                  📋
                              </button>
                            )}
                          </div>
                        </div>
                        
                          {/* Allowance */}
                          {modalChild?.weeklyAllowance > 0 && (
                          <div style={{ 
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '10px 12px',
                              background: '#F0F4FF',
                              borderRadius: '8px',
                              border: '1px solid #C7D2FE'
                            }}>
                              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
                                {t('parent.settings.allowance.amount', { defaultValue: 'דמי כיס' })}:
                              </span>
                              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                                <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--primary)' }}>
                                  ₪{(modalChild?.weeklyAllowance || 0).toFixed(2)}
                                </span>
                                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                  {modalChild?.allowanceType === 'weekly' 
                                    ? t('parent.settings.allowance.weekly', { defaultValue: 'שבועי' })
                                    : t('parent.settings.allowance.monthly', { defaultValue: 'חודשי' })
                                  }
                                  {' - '}
                                  {modalChild?.allowanceType === 'weekly'
                                    ? dayNames[modalChild?.allowanceDay !== undefined ? modalChild.allowanceDay : 1]
                                    : `${modalChild?.allowanceDay !== undefined ? modalChild.allowanceDay : 1} ${t('common.ofMonth', { defaultValue: 'בחודש' })}`
                                  }
                                  {' '}
                                  {modalChild?.allowanceTime || '08:00'}
                                </span>
                              </div>
                            </div>
                          )}

                          {/* Interest Rate */}
                          {(modalChild?.weeklyInterestRate > 0 || modalChild?.totalInterestEarned > 0) && (
                            <div style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '10px 12px',
                              background: '#FFF7ED',
                              borderRadius: '8px',
                              border: '1px solid #FED7AA'
                            }}>
                              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
                                {t('parent.settings.allowance.interestRate', { defaultValue: 'ריבית שבועית' })}:
                              </span>
                              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                                <span style={{ fontSize: '14px', fontWeight: 600, color: '#F59E0B' }}>
                                  {(modalChild?.weeklyInterestRate || 0).toFixed(2)}%
                                </span>
                                {modalChild?.totalInterestEarned > 0 && (
                                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                    {t('parent.settings.totalInterestEarned', { defaultValue: 'סה״כ ריבית' })}: ₪{(modalChild?.totalInterestEarned || 0).toFixed(2)}
                                  </span>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Created At */}
                          <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '10px 12px',
                            background: '#F9FAFB',
                            borderRadius: '8px',
                            border: '1px solid #E5E7EB'
                          }}>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
                              {t('parent.settings.childDetails.firstLogin', { defaultValue: 'כניסה ראשונה' })}:
                            </span>
                            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-main)' }}>
                              {modalChild?.createdAt 
                                ? new Date(modalChild.createdAt).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US', { 
                                  year: 'numeric', 
                                    month: 'short', 
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })
                              : t('parent.settings.notAvailable', { defaultValue: 'לא זמין' })
                            }
                            </span>
                        </div>
                        
                          {/* Last Login */}
                          <div style={{ 
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '10px 12px',
                            background: '#F9FAFB',
                            borderRadius: '8px',
                            border: '1px solid #E5E7EB'
                          }}>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
                              {t('parent.settings.childDetails.lastLogin', { defaultValue: 'כניסה אחרונה' })}:
                            </span>
                            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-main)' }}>
                              {modalChild?.lastLogin || modalChild?.lastAccess
                                ? new Date(modalChild.lastLogin || modalChild.lastAccess).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US', { 
                                  year: 'numeric', 
                                    month: 'short', 
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })
                              : t('parent.settings.neverLoggedIn', { defaultValue: 'מעולם לא נכנס' })
                            }
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                  
                  {editingChild === childId && (() => {
                    const state = allowanceStates[childId] || {
                      amount: child?.weeklyAllowance || 0,
                      type: child?.allowanceType || 'weekly',
                      day: child?.allowanceDay !== undefined ? child.allowanceDay : 1,
                      time: child?.allowanceTime || '08:00',
                      interestRate: child?.weeklyInterestRate || 0
                    };

                    const updateState = (updates) => {
                      setAllowanceStates(prev => ({
                        ...prev,
                        [childId]: { ...state, ...updates }
                      }));
                    };

                    const hasChanges = () => {
                      const nameChanged = editChildName.trim() !== (child?.name || '');
                      const phoneChanged = editChildPhone.trim() !== (child?.phoneNumber || '');
                      const currentState = allowanceStates[childId] || state;
                      const allowanceChanged = currentState.amount !== (child?.weeklyAllowance || 0) || 
                                             currentState.type !== (child?.allowanceType || 'weekly') ||
                                             currentState.day !== (child?.allowanceDay !== undefined ? child.allowanceDay : 1) ||
                                             currentState.time !== (child?.allowanceTime || '08:00') ||
                                             currentState.interestRate !== (child?.weeklyInterestRate || 0);
                      return nameChanged || phoneChanged || allowanceChanged;
                    };

                    return (
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
                          if (!editChildName.trim() || !editChildPhone.trim()) {
                            alert(t('parent.settings.parents.fillAllFields', { defaultValue: 'אנא מלא את כל השדות' }));
                            return;
                          }
                          
                          setUpdatingChild(true);
                            setSavingAllowance(prev => ({ ...prev, [childId]: true }));
                            try {
                              // Update child name and phone
                              const childResult = await updateChild(familyId, editingChild, editChildName.trim(), editChildPhone.trim());
                              
                              // Update allowance settings
                              const currentState = allowanceStates[childId] || state;
                              await updateWeeklyAllowance(
                              familyId,
                                editingChild, 
                                currentState.amount, 
                                currentState.type, 
                                currentState.day, 
                                currentState.time, 
                                currentState.interestRate
                              );
                              
                              // Reload data
                              await loadData();
                              
                              // Update local state
                              if (childResult?.child) {
                              setAllData(prev => {
                                const updated = { ...prev };
                                if (updated.children && updated.children[editingChild]) {
                                  updated.children[editingChild] = {
                                    ...updated.children[editingChild],
                                      name: childResult.child.name,
                                      phoneNumber: childResult.child.phoneNumber
                                  };
                                }
                                return updated;
                              });
                            }
                            
                              // Invalidate cache
                            invalidateFamilyCache(familyId);
                            
                            setEditingChild(null);
                            setEditChildName('');
                            setEditChildPhone('');
                            
                              // Show success notification
                            const notification = document.createElement('div');
                              notification.textContent = t('parent.settings.updateChildSuccess', { defaultValue: 'הגדרות הילד עודכנו בהצלחה!' });
                            const isRTL = i18n.language === 'he';
                            const animationName = isRTL ? 'slideInRTL' : 'slideIn';
                            const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
                            const rightOrLeft = isRTL ? 'left' : 'right';
                            notification.style.cssText = `
                              position: fixed;
                              bottom: 100px;
                              ${rightOrLeft}: 20px;
                              background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                              color: white;
                              padding: 16px 24px;
                              border-radius: 12px;
                              box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                              z-index: 10005;
                              font-weight: 600;
                              animation: ${animationName} 0.3s ease;
                              max-width: calc(100% - 40px);
                            `;
                            document.body.appendChild(notification);
                            setTimeout(() => {
                              notification.style.animation = `${animationOutName} 0.3s ease`;
                              setTimeout(() => notification.remove(), 300);
                            }, 2000);
                              
                              if (onChildrenUpdated) {
                                await onChildrenUpdated();
                            }
                          } catch (error) {
                              console.error('[UPDATE-CHILD] Error updating child:', error);
                            const errorMessage = error.message || 'שגיאה לא ידועה';
                            alert(t('parent.settings.updateChildError', { defaultValue: 'שגיאה בעדכון ילד' }) + ': ' + errorMessage);
                          } finally {
                            setUpdatingChild(false);
                              setSavingAllowance(prev => ({ ...prev, [childId]: false }));
                          }
                        }}
                        style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
                      >
                          {/* Child Name */}
                        <div className="allowance-config-group">
                          <label className="allowance-label">{t('parent.settings.childName', { defaultValue: 'שם הילד' })}</label>
                          <input
                            type="text"
                            value={editChildName}
                            onChange={(e) => setEditChildName(e.target.value)}
                            placeholder={t('parent.settings.childName', { defaultValue: 'שם הילד' })}
                            className="allowance-input"
                            required
                          />
                        </div>

                          {/* Child Phone */}
                        <div className="allowance-config-group">
                          <label className="allowance-label">{t('parent.settings.childPhone', { defaultValue: 'מספר טלפון לילד' })}</label>
                          <input
                            type="tel"
                            inputMode="numeric"
                            value={editChildPhone}
                            onChange={(e) => setEditChildPhone(e.target.value)}
                            placeholder={t('parent.settings.childPhone', { defaultValue: 'מספר טלפון לילד' })}
                            className="allowance-input"
                            style={{ direction: 'ltr', textAlign: 'left' }}
                            required
                          />
                        </div>

                          {/* Allowance Amount */}
                          <div className="allowance-config-group">
                            <label className="allowance-label">{t('parent.settings.allowance.amount', { defaultValue: 'סכום קצבה' })}</label>
                            <div className="allowance-input-group" style={{ direction: i18n.language === 'he' ? 'rtl' : 'ltr' }}>
                              {i18n.language === 'he' && <span className="currency-label" style={{ right: '16px', left: 'auto' }}>₪</span>}
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
                                style={{ 
                                  maxWidth: '200px',
                                  paddingRight: i18n.language === 'he' ? '40px' : undefined, 
                                  paddingLeft: i18n.language === 'he' ? undefined : '40px' 
                                }}
                              />
                              {i18n.language !== 'he' && <span className="currency-label">₪</span>}
                            </div>
                          </div>

                          {/* Frequency */}
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

                          {/* Day/Date and Time - Same Row */}
                          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', width: '100%' }}>
                            <div style={{ flex: '1 1 60%', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
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
                                  style={{ width: '100%', maxWidth: '200px' }}
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
                                  style={{ width: '100%', maxWidth: '200px' }}
                                >
                                  {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
                                    <option key={day} value={day}>
                                      {day}
                                    </option>
                                  ))}
                                </select>
                              )}
                            </div>
                            <div style={{ flex: '1 1 40%', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              <label className="allowance-label">{t('parent.settings.allowance.time', { defaultValue: 'שעה' })}</label>
                              <input
                                type="time"
                                value={state.time}
                                onChange={(e) => {
                                  updateState({ time: e.target.value });
                                }}
                                className="allowance-input allowance-time-input"
                                style={{ width: '100%', maxWidth: '150px' }}
                              />
                            </div>
                          </div>

                          {/* Interest Rate */}
                          <div className="allowance-config-group">
                            <label className="allowance-label">{t('parent.settings.allowance.interestRate', { defaultValue: 'ריבית שבועית (%)' })}</label>
                            <div className="allowance-input-group" style={{ direction: i18n.language === 'he' ? 'rtl' : 'ltr' }}>
                              {i18n.language === 'he' && <span className="currency-label" style={{ right: '16px', left: 'auto' }}>%</span>}
                              <input
                                type="number"
                                inputMode="decimal"
                                step="0.01"
                                min="0"
                                max="100"
                                value={state.interestRate === 0 ? '' : state.interestRate}
                                onChange={(e) => {
                                  const val = e.target.value === '' ? 0 : parseFloat(e.target.value) || 0;
                                  updateState({ interestRate: val });
                                }}
                                className="allowance-input"
                                placeholder="0.00"
                                style={{ 
                                  maxWidth: '200px',
                                  paddingRight: i18n.language === 'he' ? '40px' : undefined, 
                                  paddingLeft: i18n.language === 'he' ? undefined : '40px' 
                                }}
                              />
                              {i18n.language !== 'he' && <span className="currency-label">%</span>}
                            </div>
                            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                              {t('parent.settings.allowance.interestDescription', { defaultValue: 'ריבית שבועית על הכסף שנמצא אצל ההורים' })}
                            </p>
                          </div>

                          {/* Actions */}
                        <div className="allowance-actions">
                          <button
                            type="submit"
                              className={`update-allowance-button ${!hasChanges() || (updatingChild || savingAllowance[childId]) ? 'disabled' : ''}`}
                              disabled={!hasChanges() || updatingChild || savingAllowance[childId] || !editChildName.trim() || !editChildPhone.trim()}
                          >
                              {(updatingChild || savingAllowance[childId]) ? (
                              <span style={{
                                display: 'inline-block',
                                animation: 'pulse 1.5s ease-in-out infinite'
                              }}>
                                  {t('common.saving', { defaultValue: 'שומר...' })}
                              </span>
                              ) : (
                                t('common.saveChanges', { defaultValue: 'שמור שינויים' })
                              )}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setEditingChild(null);
                                setEditChildName('');
                                setEditChildPhone('');
                                // Reset allowance state to original values
                                setAllowanceStates(prev => ({
                                  ...prev,
                                  [childId]: {
                                    amount: child?.weeklyAllowance || 0,
                                    type: child?.allowanceType || 'weekly',
                                    day: child?.allowanceDay !== undefined ? child.allowanceDay : 1,
                                    time: child?.allowanceTime || '08:00',
                                    interestRate: child?.weeklyInterestRate || 0
                                  }
                                }));
                              }}
                              className="pay-allowance-button"
                              style={{ background: '#6B7280' }}
                            >
                              {t('common.cancel', { defaultValue: 'ביטול' })}
                          </button>
                          <button
                            type="button"
                            onClick={async () => {
                              const childName = child?.name || t('parent.settings.child', { defaultValue: 'ילד' });
                              const confirmMessage = t('parent.settings.deleteChildConfirm', { 
                                defaultValue: 'האם אתה בטוח שברצונך למחוק את {name}? פעולה זו תעביר את כל הנתונים לארכיון ולא ניתן לבטל אותה.',
                                name: childName
                              }).replace(/\{name\}/g, childName);
                              
                              if (!confirm(confirmMessage)) {
                                return;
                              }
                              
                              try {
                                await archiveChild(familyId, childId);
                                await loadData();
                                setEditingChild(null);
                                setEditChildName('');
                                setEditChildPhone('');
                                
                                // Show success notification
                                const notification = document.createElement('div');
                                const successMessage = t('parent.settings.deleteChildSuccess', { 
                                  defaultValue: 'הילד {name} נמחק והועבר לארכיון בהצלחה',
                                  name: childName
                                }).replace(/\{name\}/g, childName);
                                notification.textContent = successMessage;
                                const isRTL = i18n.language === 'he';
                                const animationName = isRTL ? 'slideInRTL' : 'slideIn';
                                const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
                                const rightOrLeft = isRTL ? 'left' : 'right';
                                notification.style.cssText = `
                                  position: fixed;
                                  bottom: 100px;
                                  ${rightOrLeft}: 20px;
                                  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                                  color: white;
                                  padding: 16px 24px;
                                  border-radius: 12px;
                                  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                                  z-index: 10005;
                                  font-weight: 600;
                                  animation: ${animationName} 0.3s ease;
                                  max-width: calc(100% - 40px);
                                `;
                                document.body.appendChild(notification);
                                setTimeout(() => {
                                  notification.style.animation = `${animationOutName} 0.3s ease`;
                                  setTimeout(() => notification.remove(), 300);
                                }, 2000);
                                
                                if (onChildrenUpdated) {
                                  await onChildrenUpdated();
                                }
                              } catch (error) {
                                alert(t('parent.settings.deleteChildError', { defaultValue: 'שגיאה במחיקת ילד' }) + ': ' + (error.message || 'Unknown error'));
                              }
                            }}
                            className="pay-allowance-button"
                            style={{ background: '#EF4444' }}
                          >
                            🗑️ {t('parent.settings.deleteChild', { defaultValue: 'מחיקת ילד' })}
                          </button>
                        </div>
                      </form>
                    </div>
                    );
                  })()}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

        {activeTab === 'parents' && (
          <div className="children-section" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {!asPage && <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>{t('parent.settings.parents.title', { defaultValue: 'הגדרת הורים' })}</h2>}
            
            {!addingParent && (
              <button
                className="add-child-button"
                onClick={() => {
                  setAddingParent(true);
                  setNewParentName('');
                  setNewParentPhone('');
                }}
                style={{
                  padding: '12px 24px',
                  borderRadius: '12px',
                  border: '2px dashed rgba(99, 102, 241, 0.3)',
                  background: 'white',
                  color: 'var(--primary)',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  alignSelf: 'flex-start'
                }}
              >
                + {t('parent.settings.parents.addParent', { defaultValue: 'הוסף הורה' })}
              </button>
            )}
            
            {addingParent && (
              <div style={{
                background: 'white',
                padding: '20px',
                borderRadius: '16px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
                border: '1px solid rgba(99, 102, 241, 0.2)'
              }}>
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (!newParentName.trim() || !newParentPhone.trim()) {
                      alert(t('parent.settings.parents.fillAllFields', { defaultValue: 'אנא מלא את כל השדות' }));
                      return;
                    }
                    try {
                      setUpdatingParent(true);
                      const newParentResult = await addParent(familyId, newParentName.trim(), newParentPhone.trim());
                      
                      // Update state directly with new parent - no need to reload everything
                      if (newParentResult && familyInfo) {
                        setFamilyInfo(prev => ({
                          ...prev,
                          parents: prev.parents ? [...prev.parents, newParentResult] : [newParentResult]
                        }));
                      }
                      
                      // Invalidate cache for future loads
                      invalidateFamilyCache(familyId);
                      
                      setAddingParent(false);
                      setNewParentName('');
                      setNewParentPhone('');
                      
                      // Show success notification at bottom
                      const notification = document.createElement('div');
                      notification.textContent = t('parent.settings.parents.addSuccess', { defaultValue: 'הורה נוסף בהצלחה!' });
                      const isRTL = i18n.language === 'he';
                      const animationName = isRTL ? 'slideInRTL' : 'slideIn';
                      const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
                      const rightOrLeft = isRTL ? 'left' : 'right';
                      notification.style.cssText = `
                        position: fixed;
                        bottom: 100px;
                        ${rightOrLeft}: 20px;
                        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                        color: white;
                        padding: 16px 24px;
                        border-radius: 12px;
                        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                        z-index: 10005;
                        font-weight: 600;
                        animation: ${animationName} 0.3s ease;
                        max-width: calc(100% - 40px);
                      `;
                      document.body.appendChild(notification);
                      setTimeout(() => {
                        notification.style.animation = `${animationOutName} 0.3s ease`;
                        setTimeout(() => notification.remove(), 300);
                      }, 2000);
                    } catch (error) {
                      alert(t('parent.settings.parents.addError', { defaultValue: 'שגיאה בהוספת הורה' }) + ': ' + (error.message || 'Unknown error'));
                    } finally {
                      setUpdatingParent(false);
                    }
                  }}
                  style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
                >
                  <div className="allowance-config-group">
                    <label className="allowance-label">{t('parent.settings.parents.name', { defaultValue: 'שם' })}</label>
                    <input
                      ref={newParentNameInputRef}
                      type="text"
                      value={newParentName}
                      onChange={(e) => setNewParentName(e.target.value)}
                      placeholder={t('parent.settings.parents.namePlaceholder', { defaultValue: 'שם ההורה' })}
                      className="allowance-input"
                      autoFocus
                      required
                    />
                  </div>
                  <div className="allowance-config-group">
                    <label className="allowance-label">{t('parent.settings.parents.phone', { defaultValue: 'טלפון' })}</label>
                    <input
                      type="tel"
                      inputMode="numeric"
                      value={newParentPhone}
                      onChange={(e) => setNewParentPhone(e.target.value)}
                      placeholder={t('parent.settings.parents.phonePlaceholder', { defaultValue: 'מספר טלפון' })}
                      className="allowance-input"
                      style={{ direction: 'ltr', textAlign: 'left' }}
                      required
                    />
                  </div>
                  <div className="allowance-actions">
                    <button
                      type="submit"
                      className="update-allowance-button"
                      disabled={updatingParent || !newParentName.trim() || !newParentPhone.trim()}
                    >
                      {updatingParent ? (
                        <span style={{
                          display: 'inline-block',
                          animation: 'pulse 1.5s ease-in-out infinite'
                        }}>
                          {t('common.saving', { defaultValue: 'Saving...' })}
                        </span>
                      ) : t('common.save', { defaultValue: 'Save' })}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setAddingParent(false);
                        setNewParentName('');
                        setNewParentPhone('');
                      }}
                      className="pay-allowance-button"
                      style={{ background: '#6B7280' }}
                    >
                      {t('common.cancel', { defaultValue: 'ביטול' })}
                    </button>
                  </div>
                </form>
              </div>
            )}
            
            {(() => {
              // Debug: Log what we have
              console.log('[SETTINGS-PARENTS] familyInfo:', familyInfo);
              console.log('[SETTINGS-PARENTS] familyInfo?.parents:', familyInfo?.parents);
              console.log('[SETTINGS-PARENTS] parents length:', familyInfo?.parents?.length || 0);
              
              // Show parents if they exist
              if (familyInfo && familyInfo.parents && familyInfo.parents.length > 0) {
                return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {familyInfo.parents.map((parent, index) => (
                  <div key={index}>
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
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>{parent.name || 'הורה1'}</h3>
                          {parent.isMain && (
                            <span style={{
                              padding: '4px 8px',
                              borderRadius: '8px',
                              background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                              color: 'white',
                              fontSize: '12px',
                              fontWeight: 600
                            }}>
                              {t('parent.settings.parents.mainParent', { defaultValue: 'הורה ראשי' })}
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                        <button
                          onClick={() => {
                            if (editingParent === index) {
                              setEditingParent(null);
                              setEditParentName('');
                              setEditParentPhone('');
                            } else {
                              // Close details if open
                              if (parentPhoneModal && parentPhoneModal.parentIndex === index) {
                                setParentPhoneModal(null);
                              }
                              setEditingParent(index);
                              setEditParentName(parent.name || 'הורה1');
                              setEditParentPhone(parent.phoneNumber || '');
                            }
                          }}
                          style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            border: '1px solid rgba(0,0,0,0.1)',
                            background: (editingParent === index) ? 'var(--primary)' : 'white',
                            color: (editingParent === index) ? 'white' : 'var(--text-main)',
                            fontSize: '14px',
                            fontWeight: 500,
                            cursor: 'pointer'
                          }}
                        >
                          {(editingParent === index) 
                            ? t('common.cancel', { defaultValue: 'ביטול' })
                            : t('common.edit', { defaultValue: 'ערוך' })
                          }
                        </button>
                        <button
                          onClick={() => {
                            if (parentPhoneModal && parentPhoneModal.parentIndex === index) {
                              setParentPhoneModal(null);
                            } else {
                              // Close edit if open
                              if (editingParent === index) {
                              setEditingParent(null);
                              setEditParentName('');
                              setEditParentPhone('');
                            }
                              setParentPhoneModal({ 
                                parentIndex: index,
                                parentName: parent.name || 'הורה1', 
                                phoneNumber: parent.phoneNumber || '',
                                createdAt: familyInfo.createdAt,
                                lastLogin: familyInfo.lastLoginAt
                              });
                            }
                          }}
                          style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            border: '1px solid rgba(0,0,0,0.1)',
                            background: (parentPhoneModal && parentPhoneModal.parentIndex === index) ? 'var(--primary)' : 'white',
                            color: (parentPhoneModal && parentPhoneModal.parentIndex === index) ? 'white' : 'var(--text-main)',
                            fontSize: '14px',
                            fontWeight: 500,
                            cursor: 'pointer'
                          }}
                        >
                          {(parentPhoneModal && parentPhoneModal.parentIndex === index) 
                            ? t('parent.settings.closeDetails', { defaultValue: 'סגור פרטים' })
                            : t('parent.settings.viewDetails', { defaultValue: 'הצג פרטים' })
                          }
                        </button>
                      </div>
                    </div>
                    
                    {parentPhoneModal && parentPhoneModal.parentIndex === index && (
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
                                {parentPhoneModal.phoneNumber 
                                  ? (parentPhoneModal.phoneNumber.startsWith('+') 
                                      ? parentPhoneModal.phoneNumber 
                                      : `+${parentPhoneModal.phoneNumber}`)
                                  : t('parent.settings.noPhoneNumber', { defaultValue: 'לא מוגדר' })
                                }
                              </div>
                              {parentPhoneModal.phoneNumber && (
                                <button 
                                  className="copy-button"
                                  onClick={() => {
                                    navigator.clipboard.writeText(parentPhoneModal.phoneNumber);
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
                              {parentPhoneModal.createdAt 
                                ? new Date(parentPhoneModal.createdAt).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US', { 
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
                              {parentPhoneModal.lastLogin 
                                ? new Date(parentPhoneModal.lastLogin).toLocaleDateString(i18n.language === 'he' ? 'he-IL' : 'en-US', { 
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
                    
                    {editingParent === index && (
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
                            if (!editParentName.trim() || !editParentPhone.trim()) {
                              alert(t('parent.settings.parents.fillAllFields', { defaultValue: 'אנא מלא את כל השדות' }));
                              return;
                            }
                            try {
                              setUpdatingParent(true);
                              
                              const updatedParentResult = await updateParentInfo(familyId, editParentName.trim(), editParentPhone.trim(), parent.isMain);
                              
                              // Update state directly with updated parent - no need to reload everything
                              if (updatedParentResult && familyInfo) {
                                setFamilyInfo(prev => ({
                                  ...prev,
                                  parents: prev.parents ? prev.parents.map((p, idx) => 
                                    idx === index ? { ...p, name: editParentName.trim(), phoneNumber: editParentPhone.trim() } : p
                                  ) : []
                                }));
                              }
                              
                              // Close edit mode BEFORE updating cache to prevent useEffect from reopening it
                              setEditingParent(null);
                              setEditParentName('');
                              setEditParentPhone('');
                              
                              // Invalidate cache for future loads
                              invalidateFamilyCache(familyId);
                              
                              // For new families, show "Go to Child Settings" button after saving main parent
                              if (isNewFamily && parent.isMain && index === 0) {
                                setShowGoToChildrenButton(true);
                                if (onParentSaved) {
                                  onParentSaved();
                                }
                              }
                              
                              // Show success notification at bottom
                              const notification = document.createElement('div');
                              notification.textContent = t('parent.settings.parents.updateSuccess', { defaultValue: 'פרטי ההורה עודכנו בהצלחה!' });
                              const isRTL = i18n.language === 'he';
                              const animationName = isRTL ? 'slideInRTL' : 'slideIn';
                              const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
                              const rightOrLeft = isRTL ? 'left' : 'right';
                              notification.style.cssText = `
                                position: fixed;
                                bottom: 100px;
                                ${rightOrLeft}: 20px;
                                background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                                color: white;
                                padding: 16px 24px;
                                border-radius: 12px;
                                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                                z-index: 10005;
                                font-weight: 600;
                                animation: ${animationName} 0.3s ease;
                                max-width: calc(100% - 40px);
                              `;
                              document.body.appendChild(notification);
                              setTimeout(() => {
                                notification.style.animation = `${animationOutName} 0.3s ease`;
                                setTimeout(() => notification.remove(), 300);
                              }, 2000);
                            } catch (error) {
                              alert(t('parent.settings.parents.updateError', { defaultValue: 'שגיאה בעדכון פרטי ההורה' }) + ': ' + error.message);
                            } finally {
                              setUpdatingParent(false);
                            }
                          }}
                          style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
                        >
                          <div className="allowance-config-group">
                            <label className="allowance-label">{t('parent.settings.parents.name', { defaultValue: 'שם' })}</label>
                            <input
                              ref={index === 0 && isNewFamily ? editParentNameInputRef : null}
                              type="text"
                              value={editParentName}
                              onChange={(e) => setEditParentName(e.target.value)}
                              className="allowance-input"
                              placeholder={t('parent.settings.parents.namePlaceholder', { defaultValue: 'שם ההורה' })}
                              required
                            />
                          </div>
                          
                          <div className="allowance-config-group">
                            <label className="allowance-label">{t('parent.settings.parents.phone', { defaultValue: 'טלפון' })}</label>
                            <input
                              type="tel"
                              inputMode="numeric"
                              value={editParentPhone}
                              onChange={(e) => setEditParentPhone(e.target.value)}
                              className="allowance-input"
                              placeholder={t('parent.settings.parents.phonePlaceholder', { defaultValue: 'מספר טלפון' })}
                              style={{ direction: 'ltr', textAlign: 'left' }}
                              required
                            />
                          </div>
                          
                          <div className="allowance-actions">
                            <button
                              type="submit"
                              className="update-allowance-button"
                              disabled={updatingParent}
                            >
                              {updatingParent ? (
                                <span style={{
                                  display: 'inline-block',
                                  animation: 'pulse 1.5s ease-in-out infinite'
                                }}>
                                  {t('common.saving', { defaultValue: 'Saving...' })}
                                </span>
                              ) : t('common.save', { defaultValue: 'Save' })}
                            </button>
                            {!parent.isMain && (
                              <button
                                type="button"
                                onClick={async () => {
                                  const parentName = parent.name || t('parent.settings.parent', { defaultValue: 'הורה' });
                                  const confirmMessage = t('parent.settings.parents.deleteParentConfirm', { 
                                    defaultValue: 'האם אתה בטוח שברצונך למחוק את {name}? פעולה זו תעביר את כל הנתונים לארכיון ולא ניתן לבטל אותה.',
                                    name: parentName
                                  }).replace(/\{name\}/g, parentName);
                                  
                                  if (!confirm(confirmMessage)) {
                                    return;
                                  }
                                  
                                  try {
                                    // Calculate the correct parentIndex for additionalParents array
                                    // If there's a main parent (index 0), additionalParents start at index 1 in the parents array
                                    // So we need to subtract 1 from the index to get the correct additionalParents index
                                    // If there's no main parent, the index is already correct
                                    const hasMainParent = familyInfo.parents && familyInfo.parents.length > 0 && familyInfo.parents[0]?.isMain;
                                    const parentIndex = hasMainParent ? index - 1 : index;
                                    
                                    // Verify this is not the main parent
                                    if (parent.isMain) {
                                      alert(t('parent.settings.parents.deleteParentError', { defaultValue: 'שגיאה במחיקת הורה' }) + ': ' + t('parent.settings.parents.cannotDeleteMainParent', { defaultValue: 'לא ניתן למחוק את ההורה הראשי' }));
                                      return;
                                    }
                                    
                                    await archiveParent(familyId, parentIndex, false);
                                    await loadData();
                                    setEditingParent(null);
                                    setEditParentName('');
                                    setEditParentPhone('');
                                    
                                    // Show success notification
                                    const notification = document.createElement('div');
                                    const successMessage = t('parent.settings.parents.deleteParentSuccess', { 
                                      defaultValue: 'ההורה {name} נמחק והועבר לארכיון בהצלחה',
                                      name: parentName
                                    }).replace(/\{name\}/g, parentName);
                                    notification.textContent = successMessage;
                                    const isRTL = i18n.language === 'he';
                                    const animationName = isRTL ? 'slideInRTL' : 'slideIn';
                                    const animationOutName = isRTL ? 'slideOutRTL' : 'slideOut';
                                    const rightOrLeft = isRTL ? 'left' : 'right';
                                    notification.style.cssText = `
                                      position: fixed;
                                      bottom: 100px;
                                      ${rightOrLeft}: 20px;
                                      background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                                      color: white;
                                      padding: 16px 24px;
                                      border-radius: 12px;
                                      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
                                      z-index: 10005;
                                      font-weight: 600;
                                      animation: ${animationName} 0.3s ease;
                                      max-width: calc(100% - 40px);
                                    `;
                                    document.body.appendChild(notification);
                                    setTimeout(() => {
                                      notification.style.animation = `${animationOutName} 0.3s ease`;
                                      setTimeout(() => notification.remove(), 300);
                                    }, 3000);
                                  } catch (error) {
                                    alert(t('parent.settings.parents.deleteParentError', { defaultValue: 'שגיאה במחיקת הורה' }) + ': ' + (error.message || 'Unknown error'));
                                  }
                                }}
                                className="pay-allowance-button"
                                style={{ background: '#EF4444' }}
                              >
                                🗑️ {t('parent.settings.parents.deleteParent', { defaultValue: 'מחיקת הורה' })}
                              </button>
                            )}
                          </div>
                        </form>
                      </div>
                    )}
                  </div>
                ))}
              </div>
                );
              } else {
                // Show message if no parents or familyInfo is null
                console.log('[SETTINGS-PARENTS] No parents found, showing message');
                return (
              <div style={{
                padding: '40px 20px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: '16px'
              }}>
                {t('parent.settings.parents.noParents', { defaultValue: 'אין הורים רשומים' })}
                  </div>
                );
              }
            })()}
            
            {/* Go to Child Settings button for new families */}
            {showGoToChildrenButton && isNewFamily && (
              <div style={{ marginTop: '20px' }}>
                <button
                  onClick={() => {
                    setShowGoToChildrenButton(false);
                    if (onTabChange) {
                      onTabChange('children');
                    } else {
                      setActiveTab('children');
                    }
                  }}
                  style={{
                    width: '100%',
                    padding: '16px',
                    borderRadius: '12px',
                    background: 'var(--primary-gradient)',
                    color: 'white',
                    border: 'none',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
                  }}
                >
                  {t('parent.settings.parents.goToChildren', { defaultValue: 'מעבר להגדרת ילדים במערכת' })}
                </button>
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

