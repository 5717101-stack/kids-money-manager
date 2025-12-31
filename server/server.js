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
          transactions: []
        },
        {
          _id: 'child2',
          name: 'ג\'וּן',
          balance: 0,
          transactions: []
        }
      ]);
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
      transactions: []
    },
    child2: {
      _id: 'child2',
      name: 'ג\'וּן',
      balance: 0,
      transactions: []
    }
  }
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

// API Routes

// Get all children
app.get('/api/children', async (req, res) => {
  try {
    if (db) {
      const children = await db.collection('children').find({}).toArray();
      res.json({ children: children.reduce((acc, child) => {
        acc[child._id] = {
          name: child.name,
          balance: child.balance,
          transactions: child.transactions || []
        };
        return acc;
      }, {}) });
    } else {
      const children = Object.values(memoryStorage.children).map(child => ({
        _id: child._id,
        name: child.name,
        balance: child.balance,
        transactions: child.transactions || []
      }));
      res.json({ children: children.reduce((acc, child) => {
        acc[child._id] = {
          name: child.name,
          balance: child.balance,
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
      balance: child.balance,
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
    const { childId, type, amount, description } = req.body;
    
    if (!childId || !type || !amount) {
      console.error('Missing required fields:', { childId, type, amount });
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    if (type !== 'deposit' && type !== 'expense') {
      console.error('Invalid transaction type:', type);
      return res.status(400).json({ error: 'Invalid transaction type' });
    }
    
    const child = await getChild(childId);
    if (!child) {
      console.error('Child not found:', childId);
      return res.status(404).json({ error: 'Child not found' });
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

