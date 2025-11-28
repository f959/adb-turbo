# ADB Performance Optimizer

Professional web tool for Android performance tuning via ADB commands. 43 optimizations across 13 categories.

## Quick Start

```bash
./run.sh    # macOS/Linux
run.bat     # Windows
```

Opens **http://localhost:8765** automatically.

**Stop server:** Press `Ctrl+C` (port is automatically freed)

## Prerequisites

- Python 3.10+
- UV package manager (auto-installed if missing)
- ADB ([install guide](#installing-adb))
- USB debugging enabled on Android device

## Usage

1. **Enable Developer Mode** on Android:
   - Settings → About Phone → Tap "Build Number" 7 times
   - Settings → Developer Options → Enable "USB Debugging"

2. **Connect device** via USB and allow debugging prompt

3. **Run** `./run.sh` and select your device

4. **Toggle optimizations** - start with High Impact commands

## Command Categories

### High Impact
- **Animation Settings** (3) - Disable UI animations for instant response
- **Background Processes** (1) - Clear caches and kill background apps
- **Fixed Performance** (1) - Lock CPU/GPU to maximum (may heat up)
- **RAM Plus** (2) - Disable virtual RAM expansion

### Medium Impact
- **Display & Refresh** (4) - Adjust refresh rate, blur, transparency
- **App Launch Speed** (4) - Optimize startup process
- **Game Optimization** (4) - Disable Samsung throttling (Samsung only)
- **Audio Quality** (2) - Enable K2HD and Tube Amp effects
- **Touchscreen** (4) - Reduce touch latency

### Low Impact
- **System** (4) - CPU/GPU optimizations
- **DNS** (2) - Private DNS configuration
- **Network** (7) - WiFi and cellular settings
- **Power** (5) - Battery management

## Installing ADB

**macOS:**
```bash
brew install android-platform-tools
```

**Linux:**
```bash
sudo apt install android-tools-adb
```

**Windows:**
Download [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools) and add to PATH.

## Manual Setup

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and run
uv sync
uv run python app.py
```

Learn more about UV at [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/)

## Troubleshooting

**No devices found?**
- Check USB cable and connection
- Enable USB debugging in Developer Options
- Allow debugging prompt on device
- Run `adb devices` in terminal to verify

**ADB not found?**
- Install ADB (see above)
- Ensure it's in your PATH
- Restart terminal after installation

**Command failed?**
- Check console output for details
- Some commands need specific Android versions
- Samsung-only commands won't work on other devices
- Reboot device if needed

**Port already in use?**
- Run `./cleanup.sh` to free port 8765
- Or manually: `pkill -f "python.*app.py"`

## API Endpoints

```
GET  /                          # Web interface
GET  /api/check-adb             # Verify ADB installation
GET  /api/devices               # List connected devices
GET  /api/device-info/<id>      # Device details
GET  /api/categories            # All commands
POST /api/execute               # Run command
POST /api/get-setting           # Get current value
```

## Project Structure

```
├── app.py              # Flask API server
├── adb_commands.py     # Command definitions
├── run.sh / run.bat    # Launch scripts
└── static/
    ├── index.html      # Web interface
    ├── css/style.css   # Styling
    └── js/app.js       # Frontend logic
```

## Tech Stack

- **Backend:** Python 3.10+, Flask, Flask-CORS
- **Frontend:** Vanilla JS, HTML5, CSS3
- **Tools:** ADB, UV package manager

## Design Principles

- **Pragmatic** - One-click toggles, persistent preferences
- **Idiomatic** - RESTful API, standard patterns, semantic HTML
- **Excellent** - Error handling, loading states, accessibility

## Disclaimer

⚠️ These optimizations may affect battery life and stability. Some require device restart. Always understand commands before executing. Use at your own risk.

## Credits

Based on [Technastic's ADB Commands Guide](https://technastic.com/adb-commands-improve-performance-android/)

---

**MIT License** • Built for the Android community 💙
