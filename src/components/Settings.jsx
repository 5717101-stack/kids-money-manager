import React, { useState, useEffect } from 'react';
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
    if (!file) return;

    // Convert to base64
    const reader = new FileReader();
    reader.onloadend = async () => {
      try {
        const base64Image = reader.result;
        await updateProfileImage(childId, base64Image);
        await loadData();
        alert('תמונת הפרופיל עודכנה בהצלחה!');
      } catch (error) {
        alert('שגיאה בעדכון תמונת הפרופיל: ' + error.message);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleAllowanceUpdate = async (childId, allowance) => {
    try {
      await updateWeeklyAllowance(childId, allowance);
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
          דמי כיס שבועיים
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
                    <label className="file-upload-button">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => handleImageUpload(childId, e.target.files[0])}
                        style={{ display: 'none' }}
                      />
                      העלה תמונה
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
            <h2>דמי כיס שבועיים</h2>
            <p className="allowance-info">
              הסכום שתגדיר כאן יתווסף אוטומטית ליתרה אצל ההורים בכל יום ראשון ב-8 בבוקר.
            </p>
            
            {['child1', 'child2'].map(childId => {
              const child = allData.children[childId];
              if (!child) return null;

              return (
                <div key={childId} className="allowance-item">
                  <h3>{child.name}</h3>
                  <div className="allowance-input-group">
                    <input
                      type="number"
                      step="1"
                      min="0"
                      defaultValue={child.weeklyAllowance || 0}
                      onBlur={(e) => {
                        const value = parseInt(e.target.value) || 0;
                        if (value !== (child.weeklyAllowance || 0)) {
                          handleAllowanceUpdate(childId, value);
                        }
                      }}
                      className="allowance-input"
                    />
                    <span className="currency-label">₪</span>
                  </div>
                  {child.weeklyAllowance > 0 && (
                    <button
                      className="pay-allowance-button"
                      onClick={() => handlePayAllowance(childId, child.name)}
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

