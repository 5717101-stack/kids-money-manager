import express from 'express';
import cors from 'cors';
import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';
import crypto from 'crypto';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware - CORS configuration
app.use(cors({
  origin: '*', // Allow all origins in production (you can restrict this later)
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}));
app.use(express.json());

// Logging middleware for debugging
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Keep-alive endpoint for Railway
app.get('/keepalive', (req, res) => {
  res.json({ status: 'alive', timestamp: new Date().toISOString() });
});

// MongoDB connection
let db;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/kids-money-manager';

async function connectDB() {
  try {
    const client = new MongoClient(MONGODB_URI);
    await client.connect();
    db = client.db();
    console.log('Connected to MongoDB');
    
    // Initialize default data if needed
    await initializeData();
  } catch (error) {
    console.error('MongoDB connection error:', error);
    // Fallback to in-memory storage if MongoDB is not available
    console.log('Falling back to in-memory storage');
  }
}

async function initializeData() {
  try {
    const children = await db.collection('children').find({}).toArray();
    
    if (children.length === 0) {
      await db.collection('children').insertMany([
        {
          _id: 'child1',
          name: 'אדם',
          balance: 0,
          cashBoxBalance: 0,
          profileImage: null,
          weeklyAllowance: 0,
          transactions: []
        },
        {
          _id: 'child2',
          name: 'ג\'וּן',
          balance: 0,
          cashBoxBalance: 0,
          profileImage: null,
          weeklyAllowance: 0,
          transactions: []
        }
      ]);
      
      // Initialize default categories if they don't exist
      const existingCategories = await db.collection('categories').find({}).toArray();
      if (existingCategories.length === 0) {
        const defaultCategories = [
          { name: 'משחקים', activeFor: ['child1', 'child2'] },
          { name: 'ממתקים', activeFor: ['child1', 'child2'] },
          { name: 'בגדים', activeFor: ['child1', 'child2'] },
          { name: 'בילויים', activeFor: ['child1', 'child2'] },
          { name: 'אחר', activeFor: ['child1', 'child2'] }
        ];
        
        await db.collection('categories').insertMany(
          defaultCategories.map((cat, index) => ({
            _id: `cat_${index + 1}`,
            name: cat.name,
            activeFor: cat.activeFor
          }))
        );
        console.log('Initialized default categories');
      } else {
        // Update existing categories to be active for both children if not already
        for (const category of existingCategories) {
          const activeFor = category.activeFor || [];
          if (!activeFor.includes('child1') || !activeFor.includes('child2')) {
            const updatedActiveFor = [...new Set([...activeFor, 'child1', 'child2'])];
            await db.collection('categories').updateOne(
              { _id: category._id },
              { $set: { activeFor: updatedActiveFor } }
            );
          }
        }
        console.log('Updated existing categories to be active for both children');
      }
      console.log('Initialized default children data');
    } else {
      // Update names if they still have old default values
      await db.collection('children').updateOne(
        { _id: 'child1', name: 'ילד 1' },
        { $set: { name: 'אדם' } }
      );
      await db.collection('children').updateOne(
        { _id: 'child2', name: 'ילד 2' },
        { $set: { name: 'ג\'וּן' } }
      );
    }
  } catch (error) {
    console.error('Error initializing data:', error);
  }
}

// In-memory fallback storage (if MongoDB is not available)
let memoryStorage = {
  children: {
    child1: {
      _id: 'child1',
      name: 'אדם',
      balance: 0,
      cashBoxBalance: 0,
      profileImage: null,
      weeklyAllowance: 0,
      transactions: []
    },
    child2: {
      _id: 'child2',
      name: 'ג\'וּן',
      balance: 0,
      cashBoxBalance: 0,
      profileImage: null,
      weeklyAllowance: 0,
      transactions: []
    }
  },
  categories: [
    { _id: 'cat_1', name: 'משחקים', activeFor: ['child1', 'child2'] },
    { _id: 'cat_2', name: 'ממתקים', activeFor: ['child1', 'child2'] },
    { _id: 'cat_3', name: 'בגדים', activeFor: ['child1', 'child2'] },
    { _id: 'cat_4', name: 'בילויים', activeFor: ['child1', 'child2'] },
    { _id: 'cat_5', name: 'אחר', activeFor: ['child1', 'child2'] }
  ]
};

// Helper function to get collection or memory storage
async function getChild(childId) {
  if (db) {
    return await db.collection('children').findOne({ _id: childId });
  } else {
    return memoryStorage.children[childId] || null;
  }
}

async function updateChild(childId, update) {
  if (db) {
    const result = await db.collection('children').updateOne(
      { _id: childId },
      { $set: update }
    );
    console.log(`Updated child ${childId}:`, result);
    return result;
  } else {
    if (memoryStorage.children[childId]) {
      Object.assign(memoryStorage.children[childId], update);
    }
    return { modifiedCount: 1 };
  }
}

// Helper function to check and process weekly allowances
async function processWeeklyAllowances() {
  try {
    // Get current time in Israel timezone using Intl API
    const now = new Date();
    const israelTime = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Jerusalem',
      weekday: 'long',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false
    }).formatToParts(now);
    
    const dayOfWeek = now.toLocaleString('en-US', { timeZone: 'Asia/Jerusalem', weekday: 'long' });
    const hour = parseInt(israelTime.find(part => part.type === 'hour').value);
    const minute = parseInt(israelTime.find(part => part.type === 'minute').value);
    
    console.log(`Checking weekly allowances - Israel time: ${dayOfWeek} ${hour}:${minute.toString().padStart(2, '0')}`);
    
    // Check if it's Monday at 14:35 Israel time (or within 14:35-14:36 to catch it)
    const isMonday = dayOfWeek === 'Monday';
    const isTime = hour === 14 && minute >= 35 && minute < 36;
    
    if (isMonday && isTime) {
      console.log('Processing weekly allowances...');
      const children = db 
        ? await db.collection('children').find({}).toArray()
        : Object.values(memoryStorage.children);
      
      for (const child of children) {
        if (child.weeklyAllowance && child.weeklyAllowance > 0) {
          // Check if allowance was already added this week
          const oneWeekAgo = new Date();
          oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
          
          const recentAllowance = (child.transactions || []).find(t => 
            t.type === 'deposit' && 
            t.description === 'דמי כיס שבועיים' &&
            new Date(t.date) > oneWeekAgo
          );
          
          if (recentAllowance) {
            console.log(`Allowance already added for ${child.name} this week`);
            continue;
          }
          
          // Add allowance as a deposit transaction
          const transaction = {
            id: `allowance_${Date.now()}_${child._id}`,
            date: new Date().toISOString(),
            type: 'deposit',
            amount: child.weeklyAllowance,
            description: 'דמי כיס שבועיים',
            category: null,
            childId: child._id
          };
          
          const transactions = [...(child.transactions || []), transaction];
          const balance = transactions.reduce((total, t) => {
            if (t.type === 'deposit') {
              return total + t.amount;
            } else {
              return total - t.amount;
            }
          }, 0);
          
          await updateChild(child._id, {
            balance: balance,
            transactions: transactions
          });
          
          console.log(`✅ Added weekly allowance of ${child.weeklyAllowance} to ${child.name}`);
        }
      }
    }
  } catch (error) {
    console.error('Error processing weekly allowances:', error);
  }
}

// Check weekly allowances every minute to catch the exact time (14:15)
setInterval(processWeeklyAllowances, 60 * 1000); // Check every minute

// API Routes

// Get all children
app.get('/api/children', async (req, res) => {
  try {
    if (db) {
      const children = await db.collection('children').find({}).toArray();
      res.json({ children: children.reduce((acc, child) => {
        acc[child._id] = {
          name: child.name,
          balance: child.balance || 0,
          cashBoxBalance: child.cashBoxBalance || 0,
          profileImage: child.profileImage || null,
          weeklyAllowance: child.weeklyAllowance || 0,
          transactions: child.transactions || []
        };
        return acc;
      }, {}) });
    } else {
      const children = Object.values(memoryStorage.children).map(child => ({
        _id: child._id,
        name: child.name,
        balance: child.balance || 0,
        cashBoxBalance: child.cashBoxBalance || 0,
        profileImage: child.profileImage || null,
        weeklyAllowance: child.weeklyAllowance || 0,
        transactions: child.transactions || []
      }));
      res.json({ children: children.reduce((acc, child) => {
        acc[child._id] = {
          name: child.name,
          balance: child.balance || 0,
          cashBoxBalance: child.cashBoxBalance || 0,
          profileImage: child.profileImage || null,
          weeklyAllowance: child.weeklyAllowance || 0,
          transactions: child.transactions || []
        };
        return acc;
      }, {}) });
    }
  } catch (error) {
    console.error('Error fetching children:', error);
    res.status(500).json({ error: 'Failed to fetch children' });
  }
});

// Get single child
app.get('/api/children/:childId', async (req, res) => {
  try {
    const child = await getChild(req.params.childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    res.json({
      name: child.name,
      balance: child.balance || 0,
      cashBoxBalance: child.cashBoxBalance || 0,
      profileImage: child.profileImage || null,
      weeklyAllowance: child.weeklyAllowance || 0,
      transactions: child.transactions || []
    });
  } catch (error) {
    console.error('Error fetching child:', error);
    res.status(500).json({ error: 'Failed to fetch child' });
  }
});

// Get transactions for a child
app.get('/api/children/:childId/transactions', async (req, res) => {
  try {
    const child = await getChild(req.params.childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    const limit = req.query.limit ? parseInt(req.query.limit) : null;
    let transactions = [...(child.transactions || [])].sort((a, b) => 
      new Date(b.date) - new Date(a.date)
    );
    
    if (limit) {
      transactions = transactions.slice(0, limit);
    }
    
    res.json({ transactions });
  } catch (error) {
    console.error('Error fetching transactions:', error);
    res.status(500).json({ error: 'Failed to fetch transactions' });
  }
});

// Add transaction
app.post('/api/transactions', async (req, res) => {
  try {
    console.log('Received transaction request:', req.body);
    const { childId, type, amount, description, category } = req.body;
    
    if (!childId || !type || !amount) {
      console.error('Missing required fields:', { childId, type, amount });
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    if (type !== 'deposit' && type !== 'expense') {
      console.error('Invalid transaction type:', type);
      return res.status(400).json({ error: 'Invalid transaction type' });
    }
    
    // Validate category for expenses - check against database
    if (type === 'expense' && category) {
      let validCategories = [];
      if (db) {
        const categories = await db.collection('categories').find({}).toArray();
        validCategories = categories
          .filter(cat => (cat.activeFor || []).includes(childId))
          .map(cat => cat.name);
      } else {
        validCategories = (memoryStorage.categories || [])
          .filter(cat => (cat.activeFor || []).includes(childId))
          .map(cat => cat.name);
      }
      
      if (!validCategories.includes(category)) {
        console.error('Invalid category:', category, 'Valid categories:', validCategories);
        return res.status(400).json({ error: 'Invalid category' });
      }
    }
    
    console.log('Found child:', child);
    
    // Generate UUID - use crypto.randomUUID() if available, otherwise fallback
    let transactionId;
    try {
      // In Node.js, crypto.randomUUID() is available in v14.17.0+
      if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        transactionId = crypto.randomUUID();
      } else {
        // Fallback: generate UUID manually
        transactionId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          const r = Math.random() * 16 | 0;
          const v = c === 'x' ? r : (r & 0x3 | 0x8);
          return v.toString(16);
        });
      }
    } catch (e) {
      // Fallback if crypto.randomUUID fails
      transactionId = 'txn_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    const transaction = {
      id: transactionId,
      date: new Date().toISOString(),
      type: type,
      amount: parseFloat(amount),
      description: description || '',
      category: type === 'expense' ? (category || 'אחר') : null,
      childId: childId
    };
    
    console.log('Created transaction:', transaction);
    
    const transactions = [...(child.transactions || []), transaction];
    
    // Recalculate balance
    const balance = transactions.reduce((total, t) => {
      if (t.type === 'deposit') {
        return total + t.amount;
      } else {
        return total - t.amount;
      }
    }, 0);
    
    console.log('New balance:', balance);
    console.log('Updating child with:', { balance, transactionsCount: transactions.length });
    
    const updateResult = await updateChild(childId, {
      balance: balance,
      transactions: transactions
    });
    
    console.log('Update result:', updateResult);
    
    // Verify the update
    const updatedChild = await getChild(childId);
    console.log('Updated child:', updatedChild);
    
    res.json({ transaction, balance, updated: true });
  } catch (error) {
    console.error('Error adding transaction:', error);
    console.error('Error stack:', error.stack);
    res.status(500).json({ 
      error: 'Failed to add transaction',
      details: error.message 
    });
  }
});

// Get expense statistics by category
app.get('/api/children/:childId/expenses-by-category', async (req, res) => {
  try {
    const { childId } = req.params;
    const days = parseInt(req.query.days) || 30;
    
    const child = await getChild(childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    // Calculate cutoff date - include today by using start of today
    const cutoffDate = new Date();
    cutoffDate.setHours(0, 0, 0, 0); // Start of today
    cutoffDate.setDate(cutoffDate.getDate() - days + 1); // Include today, so -days+1
    
    console.log(`Fetching expenses for ${childId}, days: ${days}, cutoff: ${cutoffDate.toISOString()}`);
    
    const expenses = (child.transactions || [])
      .filter(t => {
        if (t.type !== 'expense') return false;
        const transactionDate = new Date(t.date);
        transactionDate.setHours(0, 0, 0, 0);
        return transactionDate >= cutoffDate;
      });
    
    console.log(`Found ${expenses.length} expenses`);
    
    const categoryTotals = {
      'משחקים': 0,
      'ממתקים': 0,
      'בגדים': 0,
      'בילויים': 0,
      'אחר': 0
    };
    
    expenses.forEach(expense => {
      const category = expense.category || 'אחר';
      if (categoryTotals.hasOwnProperty(category)) {
        categoryTotals[category] += expense.amount;
      } else {
        categoryTotals['אחר'] += expense.amount;
      }
    });
    
    // Filter out categories with 0 expenses
    const result = Object.entries(categoryTotals)
      .filter(([_, amount]) => amount > 0)
      .map(([category, amount]) => ({ category, amount }));
    
    console.log('Expenses by category:', result);
    
    res.json({ expensesByCategory: result, totalDays: days });
  } catch (error) {
    console.error('Error fetching expenses by category:', error);
    res.status(500).json({ error: 'Failed to fetch expenses by category' });
  }
});

// Reset all data (reset balances and transactions)
app.post('/api/reset', async (req, res) => {
  try {
    console.log('Resetting all children data...');
    
    // Reset child1
    await updateChild('child1', {
      balance: 0,
      cashBoxBalance: 0,
      transactions: []
    });
    
    // Reset child2
    await updateChild('child2', {
      balance: 0,
      cashBoxBalance: 0,
      transactions: []
    });
    
    console.log('All data reset successfully');
    res.json({ 
      success: true, 
      message: 'All balances and transactions have been reset' 
    });
  } catch (error) {
    console.error('Error resetting data:', error);
    res.status(500).json({ 
      error: 'Failed to reset data',
      details: error.message 
    });
  }
});

// Update cash box balance for a child
app.put('/api/children/:childId/cashbox', async (req, res) => {
  try {
    const { childId } = req.params;
    const { cashBoxBalance } = req.body;
    
    if (cashBoxBalance === undefined || cashBoxBalance === null) {
      return res.status(400).json({ error: 'cashBoxBalance is required' });
    }
    
    const amount = parseFloat(cashBoxBalance);
    if (isNaN(amount) || amount < 0) {
      return res.status(400).json({ error: 'cashBoxBalance must be a valid non-negative number' });
    }
    
    const child = await getChild(childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    await updateChild(childId, {
      cashBoxBalance: amount
    });
    
    const updatedChild = await getChild(childId);
    res.json({
      success: true,
      cashBoxBalance: updatedChild.cashBoxBalance || 0,
      message: 'Cash box balance updated successfully'
    });
  } catch (error) {
    console.error('Error updating cash box balance:', error);
    res.status(500).json({
      error: 'Failed to update cash box balance',
      details: error.message
    });
  }
});

// Categories API
// Get all categories
app.get('/api/categories', async (req, res) => {
  try {
    if (db) {
      const categories = await db.collection('categories').find({}).toArray();
      res.json({ categories });
    } else {
      res.json({ categories: memoryStorage.categories || [] });
    }
  } catch (error) {
    console.error('Error fetching categories:', error);
    res.status(500).json({ error: 'Failed to fetch categories' });
  }
});

// Add new category
app.post('/api/categories', async (req, res) => {
  try {
    const { name, activeFor } = req.body;
    
    if (!name) {
      return res.status(400).json({ error: 'Category name is required' });
    }
    
    const category = {
      _id: `cat_${Date.now()}`,
      name: name.trim(),
      activeFor: activeFor || []
    };
    
    if (db) {
      await db.collection('categories').insertOne(category);
    } else {
      memoryStorage.categories.push(category);
    }
    
    res.json({ category });
  } catch (error) {
    console.error('Error adding category:', error);
    res.status(500).json({ error: 'Failed to add category' });
  }
});

// Update category
app.put('/api/categories/:categoryId', async (req, res) => {
  try {
    const { categoryId } = req.params;
    const { name, activeFor } = req.body;
    
    const update = {};
    if (name !== undefined) update.name = name.trim();
    if (activeFor !== undefined) update.activeFor = activeFor;
    
    if (db) {
      const result = await db.collection('categories').updateOne(
        { _id: categoryId },
        { $set: update }
      );
      if (result.matchedCount === 0) {
        return res.status(404).json({ error: 'Category not found' });
      }
    } else {
      const category = memoryStorage.categories.find(c => c._id === categoryId);
      if (!category) {
        return res.status(404).json({ error: 'Category not found' });
      }
      Object.assign(category, update);
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error updating category:', error);
    res.status(500).json({ error: 'Failed to update category' });
  }
});

// Delete category
app.delete('/api/categories/:categoryId', async (req, res) => {
  try {
    const { categoryId } = req.params;
    
    if (db) {
      const result = await db.collection('categories').deleteOne({ _id: categoryId });
      if (result.deletedCount === 0) {
        return res.status(404).json({ error: 'Category not found' });
      }
    } else {
      const index = memoryStorage.categories.findIndex(c => c._id === categoryId);
      if (index === -1) {
        return res.status(404).json({ error: 'Category not found' });
      }
      memoryStorage.categories.splice(index, 1);
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error deleting category:', error);
    res.status(500).json({ error: 'Failed to delete category' });
  }
});

// Update child profile image
app.put('/api/children/:childId/profile-image', async (req, res) => {
  try {
    const { childId } = req.params;
    const { profileImage } = req.body;
    
    const child = await getChild(childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    await updateChild(childId, { profileImage: profileImage || null });
    
    res.json({ success: true, profileImage: profileImage || null });
  } catch (error) {
    console.error('Error updating profile image:', error);
    res.status(500).json({ error: 'Failed to update profile image' });
  }
});

// Update child weekly allowance
app.put('/api/children/:childId/weekly-allowance', async (req, res) => {
  try {
    const { childId } = req.params;
    const { weeklyAllowance } = req.body;
    
    const amount = parseFloat(weeklyAllowance);
    if (isNaN(amount) || amount < 0) {
      return res.status(400).json({ error: 'Weekly allowance must be a valid non-negative number' });
    }
    
    const child = await getChild(childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    await updateChild(childId, { weeklyAllowance: amount });
    
    res.json({ success: true, weeklyAllowance: amount });
  } catch (error) {
    console.error('Error updating weekly allowance:', error);
    res.status(500).json({ error: 'Failed to update weekly allowance' });
  }
});

// Manually trigger weekly allowance payment
app.post('/api/children/:childId/pay-allowance', async (req, res) => {
  try {
    const { childId } = req.params;
    const child = await getChild(childId);
    
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    if (!child.weeklyAllowance || child.weeklyAllowance <= 0) {
      return res.status(400).json({ error: 'Weekly allowance is not set for this child' });
    }
    
    // Check if allowance was already added this week
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    
    const recentAllowance = (child.transactions || []).find(t => 
      t.type === 'deposit' && 
      t.description === 'דמי כיס שבועיים' &&
      new Date(t.date) > oneWeekAgo
    );
    
    if (recentAllowance) {
      return res.status(400).json({ error: 'Allowance already added this week' });
    }
    
    // Add allowance as a deposit transaction
    const transaction = {
      id: `allowance_${Date.now()}_${child._id}`,
      date: new Date().toISOString(),
      type: 'deposit',
      amount: child.weeklyAllowance,
      description: 'דמי כיס שבועיים',
      category: null,
      childId: child._id
    };
    
    const transactions = [...(child.transactions || []), transaction];
    const balance = transactions.reduce((total, t) => {
      if (t.type === 'deposit') {
        return total + t.amount;
      } else {
        return total - t.amount;
      }
    }, 0);
    
    await updateChild(child._id, {
      balance: balance,
      transactions: transactions
    });
    
    res.json({ success: true, transaction, balance });
  } catch (error) {
    console.error('Error paying allowance:', error);
    res.status(500).json({ error: 'Failed to pay allowance' });
  }
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', db: db ? 'connected' : 'memory' });
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({ 
    message: 'Kids Money Manager API',
    status: 'running',
    version: '1.0.0'
  });
});

// Start server
let server;

connectDB().then(() => {
  server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
    console.log(`Health check available at http://0.0.0.0:${PORT}/api/health`);
  });
  
  // Handle graceful shutdown
  process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down gracefully...');
    server.close(() => {
      console.log('Server closed');
      process.exit(0);
    });
  });
  
  process.on('SIGINT', () => {
    console.log('SIGINT received, shutting down gracefully...');
    server.close(() => {
      console.log('Server closed');
      process.exit(0);
    });
  });
}).catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});

