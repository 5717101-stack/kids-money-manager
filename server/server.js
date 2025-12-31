import express from 'express';
import cors from 'cors';
import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

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
    return await db.collection('children').updateOne(
      { _id: childId },
      { $set: update }
    );
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
    const { childId, type, amount, description } = req.body;
    
    if (!childId || !type || !amount) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    if (type !== 'deposit' && type !== 'expense') {
      return res.status(400).json({ error: 'Invalid transaction type' });
    }
    
    const child = await getChild(childId);
    if (!child) {
      return res.status(404).json({ error: 'Child not found' });
    }
    
    const transaction = {
      id: crypto.randomUUID(),
      date: new Date().toISOString(),
      type: type,
      amount: parseFloat(amount),
      description: description || '',
      childId: childId
    };
    
    const transactions = [...(child.transactions || []), transaction];
    
    // Recalculate balance
    const balance = transactions.reduce((total, t) => {
      if (t.type === 'deposit') {
        return total + t.amount;
      } else {
        return total - t.amount;
      }
    }, 0);
    
    await updateChild(childId, {
      balance: balance,
      transactions: transactions
    });
    
    res.json({ transaction, balance });
  } catch (error) {
    console.error('Error adding transaction:', error);
    res.status(500).json({ error: 'Failed to add transaction' });
  }
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', db: db ? 'connected' : 'memory' });
});

// Start server
connectDB().then(() => {
  app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
});

