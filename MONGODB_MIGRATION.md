# PostgreSQL to MongoDB Migration Guide

## Migration Overview

This document outlines the successful migration of the bookings application from PostgreSQL with SQLAlchemy to MongoDB with PyMongo.

## Changes Made

### 1. Dependencies Updated
- **Removed**: `flask-sqlalchemy`, `psycopg2-binary`, `flask-migrate`
- **Added**: `pymongo`, `flask-pymongo`

### 2. Configuration Changes
- Updated `config.py` to use MongoDB connection string
- Replaced `SQLALCHEMY_DATABASE_URI` with `MONGO_URI`
- Default connection: `mongodb://localhost:27017/bookings_db`

### 3. Database Models Redesigned

#### New MongoDB Models (`app/mongodb_models.py`)

**BaseModel Class:**
- Provides common functionality for all models
- Handles CRUD operations with MongoDB
- Automatic timestamp management (`created_at`, `updated_at`)

**User Model:**
- Collection: `users`
- Fields: `_id`, `username`, `email`, `password_hash`, `first_name`, `last_name`, `role`, `is_active`, `created_at`, `updated_at`
- Methods: `create_user()`, `find_by_username()`, `find_by_email()`, `check_password()`, etc.

**Agent Model:**
- Collection: `agents`
- Fields: `_id`, `name`, `company`, `email`, `phone`, `country`, `address`, `notes`, `is_active`, `user_id`, `created_at`, `updated_at`
- Methods: `create_agent()`, `find_by_email()`, `find_by_name()`, `get_active()`, etc.

**Booking Model:**
- Collection: `bookings`
- Fields: `_id`, `name`, `date_from`, `date_to`, `country`, `pax`, `ladies`, `men`, `children`, `teens`, `agent_id`, `consultant`, `user_id`, `created_at`, `updated_at`
- Methods: `create_booking()`, `find_by_user()`, `find_by_agent()`, etc.

### 4. API Endpoints Updated

#### Authentication (`authbp.py`)
- All user operations converted to MongoDB queries
- JWT token handling updated to work with ObjectId
- User registration, login, profile management all migrated

#### Agent Management (`agentsbp.py`)
- CRUD operations converted to MongoDB
- Agent filtering and search functionality preserved
- CSV import functionality updated

#### Booking Management (`bookingsbp.py`)
- Complex filtering queries converted to MongoDB aggregation
- Relationship data fetching updated (no joins, manual lookups)
- CSV import and export functionality preserved

### 5. Key Technical Changes

**ID Handling:**
- PostgreSQL integer IDs → MongoDB ObjectId
- All ID comparisons updated to handle ObjectId conversion
- API routes updated to accept string IDs instead of integers

**Relationships:**
- No foreign key constraints (MongoDB doesn't support them)
- Manual relationship fetching in `to_dict()` methods
- ObjectId references stored as fields

**Querying:**
- SQLAlchemy Query objects → MongoDB query dictionaries
- Complex filters translated to MongoDB query syntax
- Date filtering with `$gte` and `$lte` operators

**Transactions:**
- Removed SQLAlchemy session management
- MongoDB operations are atomic at document level
- No explicit transaction handling needed for single operations

## Database Schema Comparison

### Before (PostgreSQL)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    -- ... other fields
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    -- ... other fields
);

CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    agent_id INTEGER REFERENCES agents(id),
    user_id INTEGER REFERENCES users(id),
    -- ... other fields
);
```

### After (MongoDB)
```javascript
// users collection
{
  _id: ObjectId,
  username: "string",
  email: "string",
  password_hash: "string",
  role: "string",
  is_active: boolean,
  created_at: ISODate,
  updated_at: ISODate
}

// agents collection
{
  _id: ObjectId,
  name: "string",
  email: "string",
  country: "string",
  user_id: ObjectId, // reference to users collection
  is_active: boolean,
  created_at: ISODate,
  updated_at: ISODate
}

// bookings collection
{
  _id: ObjectId,
  name: "string",
  date_from: ISODate,
  date_to: ISODate,
  country: "string",
  agent_id: ObjectId, // reference to agents collection
  user_id: ObjectId,  // reference to users collection
  pax: number,
  created_at: ISODate,
  updated_at: ISODate
}
```

## Migration Steps to Run

1. **Install Dependencies:**
   ```bash
   cd backend
   pipenv install
   ```

2. **Start MongoDB:**
   ```bash
   # On Windows
   mongod

   # On macOS with Homebrew
   brew services start mongodb/brew/mongodb-community

   # On Linux
   sudo systemctl start mongod
   ```

3. **Test Migration:**
   ```bash
   python test_migration.py
   ```

4. **Start Application:**
   ```bash
   python run.py
   ```

## Data Migration (Optional)

If you have existing PostgreSQL data to migrate:

1. **Export PostgreSQL Data:**
   ```bash
   pg_dump -h localhost -U username -d bookings_db --data-only --column-inserts > backup.sql
   ```

2. **Write Migration Script:**
   Create a script to read PostgreSQL data and insert into MongoDB using the new models.

3. **Example Migration Script:**
   ```python
   # Import existing data from PostgreSQL backup
   # Convert to MongoDB format
   # Use mongodb_models to insert data
   ```

## Testing Checklist

- [ ] User registration and authentication
- [ ] Agent CRUD operations
- [ ] Booking CRUD operations  
- [ ] CSV import functionality
- [ ] User permissions and authorization
- [ ] API filtering and search
- [ ] Error handling and logging

## Benefits of MongoDB Migration

1. **Flexibility**: Schema-less design allows for easier field additions
2. **Scalability**: Better horizontal scaling capabilities
3. **Performance**: Faster for read-heavy workloads
4. **Development Speed**: No migrations needed for schema changes
5. **JSON Native**: Better alignment with REST API JSON responses

## Considerations

1. **No ACID Transactions**: MongoDB doesn't have multi-document ACID transactions (in older versions)
2. **No Foreign Key Constraints**: Manual relationship integrity management
3. **Storage Overhead**: Field names stored with each document
4. **Query Complexity**: Some complex queries may be less intuitive than SQL

## Environment Variables

Update your `.env` file:
```env
# Replace PostgreSQL connection
MONGO_URI=mongodb://localhost:27017/bookings_db

# For production with authentication
MONGO_URI=mongodb://username:password@host:port/database
```

## Troubleshooting

**Connection Issues:**
- Ensure MongoDB is running
- Check firewall settings
- Verify connection string format

**ObjectId Errors:**
- All ID fields now use ObjectId
- Convert string IDs to ObjectId when querying
- Use `str(ObjectId)` when returning IDs in API

**Missing Data:**
- Manual relationship fetching required
- Check that related documents exist
- Handle None cases in `to_dict()` methods