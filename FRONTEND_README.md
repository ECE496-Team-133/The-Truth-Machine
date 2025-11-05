# Frontend Setup Guide

This guide explains how to run the React frontend for The Truth Machine.

## Prerequisites

1. **Node.js** (v18 or higher) - [Download here](https://nodejs.org/)
2. **Python 3.8+** with dependencies installed
3. **Backend API** running (see below)

## Setup

### 1. Install Frontend Dependencies

```bash
npm install
```

### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Backend API

In one terminal:

```bash
# Make the script executable (first time only)
chmod +x start_api.sh

# Start the API server
./start_api.sh

# Or manually:
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. Start the Frontend

In another terminal:

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Features

- **Query Input**: Enter your query to fact-check
- **Tree Visualization**: See claims, prerequisites, and additional info in a hierarchical tree structure
- **Loading States**: Animated loading indicators as each component is being validated
- **Real-time Updates**: Watch as each claim is validated step by step
- **Status Indicators**: Color-coded status blocks (pending, validating, validated, failed)
- **Evidence Links**: Click to view source articles with highlighted evidence

## Project Structure

```
src/
├── api.py                 # FastAPI backend server
├── main.jsx               # React entry point
├── App.jsx               # Main app component
├── components/
│   ├── QueryInput.jsx    # Query input form
│   ├── FactCheckTree.jsx # Tree container
│   ├── ClaimNode.jsx     # Individual claim display
│   └── ValidationBlock.jsx # Validation status block
└── ...
```

## API Endpoints

- `POST /api/factcheck` - Process a query and return fact-checking results
  - Request body: `{ "query": "your query here", "top_n_urls": 1 }`
  - Response: Structured fact-checking data with claims, prerequisites, and validation results

