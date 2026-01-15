#!/bin/bash
# Start both backend and frontend servers

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Backend stopped${NC}"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Frontend stopped${NC}"
    fi
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

echo -e "${BLUE}Starting The Truth Machine...${NC}\n"

# Check and fix Python dependencies
echo -e "${BLUE}Checking Python dependencies...${NC}"

# Check if uvicorn is installed
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install -r requirements.txt || {
        echo -e "${RED}Error: Failed to install Python dependencies${NC}"
        exit 1
    }
fi

# Check for pydantic_core architecture mismatch (common on Apple Silicon)
NEEDS_FIX=false
if python3 -c "import pydantic" 2>/dev/null; then
    # Try to import pydantic_core - if it fails, likely architecture issue
    if ! python3 -c "from pydantic_core import __version__" 2>/dev/null 2>&1; then
        NEEDS_FIX=true
    else
        # Double-check by trying to actually use it
        if ! python3 -c "from pydantic import BaseModel; BaseModel()" 2>/dev/null 2>&1; then
            NEEDS_FIX=true
        fi
    fi
fi

if [ "$NEEDS_FIX" = true ]; then
    echo -e "${YELLOW}Detected pydantic architecture issue. Fixing...${NC}"
    pip uninstall -y pydantic-core pydantic pydantic-settings 2>/dev/null || true
    pip install --no-cache-dir "pydantic>=2.8.2" "pydantic-settings>=2.4.0" || {
        echo -e "${RED}Error: Failed to fix pydantic dependencies${NC}"
        echo -e "${YELLOW}Try running manually: pip install --force-reinstall -r requirements.txt${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Dependencies fixed!${NC}"
fi

# Verify all critical imports work
echo -e "${BLUE}Verifying dependencies...${NC}"
if ! python3 -c "import uvicorn, fastapi, pydantic" 2>/dev/null; then
    echo -e "${YELLOW}Some dependencies missing. Installing all requirements...${NC}"
    pip install -r requirements.txt || {
        echo -e "${RED}Error: Failed to install dependencies${NC}"
        exit 1
    }
fi
echo -e "${GREEN}✓ Python dependencies OK${NC}\n"

# Check if Node dependencies are installed
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/vite" ]; then
    echo -e "${YELLOW}Installing Node dependencies...${NC}"
    npm install || {
        echo -e "${RED}Error: Failed to install Node dependencies${NC}"
        exit 1
    }
fi

# Verify vite is available
if [ ! -f "node_modules/.bin/vite" ]; then
    echo -e "${RED}Error: vite not found after installation${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node dependencies OK${NC}\n"

# Start backend
echo -e "${BLUE}Starting backend server on http://localhost:8000...${NC}"
export PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}"
python3 -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000 > /tmp/truth-machine-backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo -e "${YELLOW}Waiting for backend to start...${NC}"
RETRY_COUNT=0
MAX_RETRIES=1

for i in {1..30}; do
    # Check if process is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        # Process crashed - check if it's a dependency issue
        if grep -q "incompatible architecture\|ImportError.*pydantic_core" /tmp/truth-machine-backend.log 2>/dev/null; then
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                echo -e "\n${YELLOW}Backend crashed due to dependency issue. Fixing and retrying...${NC}"
                pip uninstall -y pydantic-core pydantic pydantic-settings 2>/dev/null || true
                pip install --no-cache-dir "pydantic>=2.8.2" "pydantic-settings>=2.4.0"
                RETRY_COUNT=$((RETRY_COUNT + 1))
                
                # Restart backend
                echo -e "${BLUE}Restarting backend...${NC}"
                python3 -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000 > /tmp/truth-machine-backend.log 2>&1 &
                BACKEND_PID=$!
                i=0  # Reset counter
                continue
            fi
        fi
        
        echo -e "\n${RED}Error: Backend process crashed!${NC}"
        echo -e "${YELLOW}Backend logs:${NC}"
        cat /tmp/truth-machine-backend.log
        echo ""
        exit 1
    fi
    
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready!${NC}"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e "\n${RED}Error: Backend failed to start after 30 seconds${NC}"
        echo -e "${YELLOW}Backend logs:${NC}"
        cat /tmp/truth-machine-backend.log
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    
    # Show progress every 5 seconds
    if [ $((i % 5)) -eq 0 ]; then
        echo -e "${YELLOW}Still waiting... (${i}/30 seconds)${NC}"
    fi
    
    sleep 1
done

# Start frontend
echo -e "${BLUE}Starting frontend server on http://localhost:5173...${NC}"
npm run dev > /tmp/truth-machine-frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo -e "${YELLOW}Waiting for frontend to start...${NC}"
for i in {1..20}; do
    # Check if process is still running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "\n${RED}Error: Frontend process crashed!${NC}"
        echo -e "${YELLOW}Frontend logs:${NC}"
        cat /tmp/truth-machine-frontend.log
        echo ""
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    
    # Check if frontend is responding
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is ready!${NC}"
        break
    fi
    
    if [ $i -eq 20 ]; then
        echo -e "\n${RED}Error: Frontend failed to start after 20 seconds${NC}"
        echo -e "${YELLOW}Frontend logs:${NC}"
        cat /tmp/truth-machine-frontend.log
        kill $FRONTEND_PID 2>/dev/null || true
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    
    sleep 1
done

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Both servers are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}Backend:${NC}  http://localhost:8000"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "\n${YELLOW}Press Ctrl+C to stop both servers${NC}\n"

# Show logs from both processes
tail -f /tmp/truth-machine-backend.log /tmp/truth-machine-frontend.log 2>/dev/null &
TAIL_PID=$!

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
kill $TAIL_PID 2>/dev/null || true
