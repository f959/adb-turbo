#!/bin/bash

# ============================================
# adb-turbo - Launch Script
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PORT=8765
HOST="localhost"
URL="http://${HOST}:${PORT}"

# ============================================
# Print Banner
# ============================================
print_banner() {
    echo -e "${PURPLE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        adb-turbo                                             ║
║        Friendly Android Performance Tool                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# ============================================
# Check and Install UV
# ============================================
check_uv() {
    echo -e "${CYAN}Checking for UV...${NC}"
    
    if command -v uv &> /dev/null; then
        echo -e "${GREEN}✓ UV is installed${NC}"
        uv --version
        return 0
    else
        echo -e "${YELLOW}UV not found. Installing UV...${NC}"
        install_uv
    fi
}

install_uv() {
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "${CYAN}Installing UV via curl...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        # Add UV to PATH for current session
        export PATH="$HOME/.local/bin:$PATH"
        
        if command -v uv &> /dev/null; then
            echo -e "${GREEN}✓ UV installed successfully${NC}"
        else
            echo -e "${RED}✗ Failed to install UV. Please install manually:${NC}"
            echo -e "${YELLOW}  curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Unsupported OS for automatic UV installation${NC}"
        echo -e "${YELLOW}Please install UV manually from: https://docs.astral.sh/uv/getting-started/${NC}"
        exit 1
    fi
}

# ============================================
# Check Python
# ============================================
check_python() {
    echo -e "${CYAN}Checking Python version...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"
    else
        echo -e "${RED}✗ Python 3 not found${NC}"
        echo -e "${YELLOW}Please install Python 3.10 or higher${NC}"
        exit 1
    fi
}

# ============================================
# Check ADB
# ============================================
check_adb() {
    echo -e "${CYAN}Checking for ADB...${NC}"
    
    if command -v adb &> /dev/null; then
        ADB_VERSION=$(adb version | head -n1)
        echo -e "${GREEN}✓ ADB found: ${ADB_VERSION}${NC}"
    else
        echo -e "${YELLOW}⚠ ADB not found in PATH${NC}"
        echo -e "${YELLOW}The application will still run, but you'll need to install ADB to use it.${NC}"
        echo -e "${YELLOW}Installation instructions will be shown in the web interface.${NC}"
    fi
}

# ============================================
# Install Dependencies
# ============================================
install_dependencies() {
    echo -e "${CYAN}Installing dependencies with UV...${NC}"
    
    if uv sync --quiet --no-install-project; then
        echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
    else
        echo -e "${RED}✗ Failed to install dependencies${NC}"
        exit 1
    fi
}

# ============================================
# Open Browser
# ============================================
open_browser() {
    echo -e "${CYAN}Opening browser...${NC}"
    
    # Wait a moment for server to start
    sleep 2
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$URL" 2>/dev/null || true
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open "$URL" 2>/dev/null || true
        elif command -v gnome-open &> /dev/null; then
            gnome-open "$URL" 2>/dev/null || true
        fi
    fi
}

# ============================================
# Start Server
# ============================================
start_server() {
    echo -e "${CYAN}Starting Flask server...${NC}"
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║  🚀 Server running at: ${BLUE}${URL}${GREEN}                      ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║  📱 Make sure:                                               ║${NC}"
    echo -e "${GREEN}║     • ADB is installed and in your PATH                      ║${NC}"
    echo -e "${GREEN}║     • USB debugging is enabled on your device                ║${NC}"
    echo -e "${GREEN}║     • Your device is connected via USB                       ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║  Press Ctrl+C to stop the server                             ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Open browser in background
    open_browser &
    
    # Start the Flask app with UV
    uv run python app.py
}

# ============================================
# Cleanup on Exit
# ============================================
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down server...${NC}"
    
    # Kill any Python processes running app.py
    pkill -f "python.*app.py" 2>/dev/null || true
    
    # Wait a moment for port to be released
    sleep 1
    
    echo -e "${GREEN}✓ Port ${PORT} is now free${NC}"
    echo -e "${GREEN}👋 Thank you for using adb-turbo!${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# ============================================
# Main Execution
# ============================================
main() {
    print_banner
    
    echo -e "${CYAN}Starting adb-turbo...${NC}"
    echo ""
    
    # Check prerequisites
    check_python
    check_uv
    check_adb
    
    echo ""
    
    # Install dependencies
    install_dependencies
    
    echo ""
    
    # Start server
    start_server
}

# Run main function
main

