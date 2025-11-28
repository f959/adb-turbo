"""
ADB Commands Library for Android Performance Optimization
Categorized by impact with detailed metadata and execution logic
"""

import subprocess
import json
from typing import Dict, List, Optional, Tuple


class ADBCommand:
    """Represents a single ADB command with metadata"""
    
    def __init__(self, name: str, description: str, enable_cmd: str, 
                 disable_cmd: str, explanation: str, impact: str = "medium",
                 device_check: Optional[str] = None, samsung_only: bool = False,
                 get_cmd: Optional[str] = None):
        self.name = name
        self.description = description
        self.enable_cmd = enable_cmd
        self.disable_cmd = disable_cmd
        self.get_cmd = get_cmd  # Command to read current state
        self.explanation = explanation
        self.impact = impact  # high, medium, low
        self.device_check = device_check
        self.samsung_only = samsung_only


class ADBCategory:
    """Represents a category of ADB commands"""
    
    def __init__(self, id: str, name: str, description: str, impact: str, commands: List[ADBCommand]):
        self.id = id
        self.name = name
        self.description = description
        self.impact = impact
        self.commands = commands


def execute_adb_command(device_id: str, command: str) -> Tuple[bool, str, str]:
    """
    Execute an ADB command on a specific device
    Returns: (success, stdout, stderr)
    """
    try:
        # Construct full ADB command
        if device_id:
            full_cmd = f"adb -s {device_id} {command}"
        else:
            full_cmd = f"adb {command}"
        
        # Execute command
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        success = result.returncode == 0
        return success, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out after 30 seconds"
    except Exception as e:
        return False, "", f"Error executing command: {str(e)}"


def check_adb_available() -> Tuple[bool, str]:
    """Check if ADB is installed and available"""
    try:
        result = subprocess.run(
            ["adb", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, "ADB not responding correctly"
    except FileNotFoundError:
        return False, "ADB not found in PATH"
    except Exception as e:
        return False, f"Error checking ADB: {str(e)}"


def get_connected_devices() -> List[Dict[str, str]]:
    """Get list of connected ADB devices"""
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return []
        
        devices = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            if line.strip() and 'device' in line:
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    # Extract model if available
                    model = "Unknown"
                    for part in parts:
                        if part.startswith("model:"):
                            model = part.split(":")[1]
                            break
                    
                    devices.append({
                        "id": device_id,
                        "model": model,
                        "status": "connected"
                    })
        
        return devices
        
    except Exception as e:
        print(f"Error getting devices: {e}")
        return []


def get_device_manufacturer(device_id: str) -> str:
    """Get device manufacturer"""
    success, stdout, _ = execute_adb_command(
        device_id, 
        "shell getprop ro.product.manufacturer"
    )
    if success:
        return stdout.strip().lower()
    return "unknown"


def get_device_location(device_id: str) -> tuple:
    """
    Get device's last known location (latitude, longitude)
    Returns: (latitude, longitude) or (None, None) if unavailable
    """
    try:
        # Get location from dumpsys
        success, stdout, _ = execute_adb_command(
            device_id,
            "shell dumpsys location"
        )
        
        if not success or not stdout:
            return None, None
        
        # Parse location from output
        # Looking for pattern like: "last location: Location[fused 37.4219983,-122.084 ..."
        import re
        pattern = r'\[fused\s+([-\d.]+),([-\d.]+)'
        
        for line in stdout.split('\n'):
            if 'last location' in line.lower() and 'fused' in line.lower():
                match = re.search(pattern, line)
                if match:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
                    return lat, lon
        
        return None, None
        
    except Exception as e:
        print(f"Error getting device location: {e}")
        return None, None


def get_command_state(device_id: str, get_cmd: str) -> Optional[bool]:
    """
    Read the current state of a command using its get_cmd.
    Returns True if enabled, False if disabled, None if unknown/error.
    """
    if not get_cmd:
        return None
    
    success, stdout, stderr = execute_adb_command(device_id, get_cmd)
    if not success:
        return None
    
    value = stdout.strip()
    
    # Handle empty or null values
    if value == 'null' or value == '':
        return None
    
    # Handle boolean strings
    if value == '1' or value.lower() == 'true':
        return True
    elif value == '0' or value.lower() == 'false':
        return False
    
    # Handle complex outputs (like dumpsys)
    # Example: "mFixedPerformanceModeEnabled=true"
    if '=' in value:
        # Extract value after equals sign
        parts = value.split('=')
        if len(parts) >= 2:
            extracted_value = parts[-1].strip().lower()
            if extracted_value == 'true':
                return True
            elif extracted_value == 'false':
                return False
    
    # For float values (like animation scales)
    try:
        float_value = float(value)
        # Consider values > 0 as enabled, 0 as disabled
        return float_value > 0
    except ValueError:
        pass
    
    # For string values like DNS settings
    # If there's a non-empty string value, consider it enabled
    if value and value != 'off':
        return True
    
    # Unknown format
    return None


def get_comprehensive_device_info(device_id: str) -> dict:
    """
    Get comprehensive device information using read-only ADB commands
    Returns: Dictionary with all device information
    """
    info = {}
    
    try:
        # Battery Information
        success, stdout, _ = execute_adb_command(device_id, "shell dumpsys battery")
        if success:
            battery_info = {}
            for line in stdout.split('\n'):
                if 'level:' in line:
                    battery_info['level'] = line.split(':')[1].strip()
                elif 'temperature:' in line:
                    temp = int(line.split(':')[1].strip())
                    battery_info['temperature'] = f"{temp / 10}°C"
                elif 'health:' in line:
                    battery_info['health'] = line.split(':')[1].strip()
                elif 'status:' in line:
                    battery_info['status'] = line.split(':')[1].strip()
            info['battery'] = battery_info
        
        # Network Information
        success, stdout, _ = execute_adb_command(device_id, "shell ip addr show wlan0")
        if success:
            import re
            ip_match = re.search(r'inet\s+([\d.]+)', stdout)
            info['network'] = {
                'ip_address': ip_match.group(1) if ip_match else 'Not connected'
            }
        
        # Display Information
        success, stdout, _ = execute_adb_command(device_id, "shell wm size")
        if success:
            size_match = re.search(r'Physical size:\s*(\d+x\d+)', stdout)
            info['display'] = {
                'resolution': size_match.group(1) if size_match else 'Unknown'
            }
        
        success, stdout, _ = execute_adb_command(device_id, "shell wm density")
        if success:
            density_match = re.search(r'Physical density:\s*(\d+)', stdout)
            if density_match and info.get('display'):
                info['display']['density'] = f"{density_match.group(1)} dpi"
        
        # Memory Information
        success, stdout, _ = execute_adb_command(device_id, "shell cat /proc/meminfo")
        if success:
            mem_info = {}
            for line in stdout.split('\n'):
                if 'MemTotal:' in line:
                    mem_kb = int(line.split()[1])
                    mem_info['total'] = f"{mem_kb / 1024 / 1024:.1f} GB"
                elif 'MemAvailable:' in line:
                    mem_kb = int(line.split()[1])
                    mem_info['available'] = f"{mem_kb / 1024 / 1024:.1f} GB"
            info['memory'] = mem_info
        
        # CPU Information
        success, stdout, _ = execute_adb_command(device_id, "shell cat /proc/cpuinfo")
        if success:
            cpu_info = {}
            processor_count = 0
            for line in stdout.split('\n'):
                if 'processor' in line.lower():
                    processor_count += 1
                elif 'Hardware' in line:
                    cpu_info['hardware'] = line.split(':')[1].strip()
            cpu_info['cores'] = str(processor_count)
            info['cpu'] = cpu_info
        
        # Storage Information
        success, stdout, _ = execute_adb_command(device_id, "shell df -h /data")
        if success:
            lines = stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 4:
                    info['storage'] = {
                        'total': parts[1],
                        'used': parts[2],
                        'available': parts[3]
                    }
        
        # System Uptime
        success, stdout, _ = execute_adb_command(device_id, "shell uptime")
        if success:
            info['uptime'] = stdout.strip()
        
        # Current App
        success, stdout, _ = execute_adb_command(device_id, "shell dumpsys window | grep mCurrentFocus")
        if success:
            focus_match = re.search(r'mCurrentFocus=Window\{[^\s]+\s[^\s]+\s([^\s/]+)', stdout)
            info['current_app'] = focus_match.group(1) if focus_match else 'Unknown'
        
        return info
        
    except Exception as e:
        print(f"Error getting comprehensive device info: {e}")
        return info


# Define all command categories ordered by impact
COMMAND_CATEGORIES = [
    # HIGH IMPACT COMMANDS
    ADBCategory(
        id="animation_settings",
        name="Animation Settings",
        description="Adjust or disable system animations for faster UI response and reduced battery consumption",
        impact="high",
        commands=[
            ADBCommand(
                name="Window Animation Scale",
                description="Controls animation when opening/closing apps",
                enable_cmd="shell settings put global window_animation_scale 1.0",
                disable_cmd="shell settings put global window_animation_scale 0.0",
                get_cmd="shell settings get global window_animation_scale",
                explanation="Disabling window animations makes your device feel significantly faster by removing the visual delay when opening or closing applications. This can reduce perceived lag and improve battery life.",
                impact="high"
            ),
            ADBCommand(
                name="Transition Animation Scale",
                description="Controls animation when switching between apps",
                enable_cmd="shell settings put global transition_animation_scale 1.0",
                disable_cmd="shell settings put global transition_animation_scale 0.0",
                get_cmd="shell settings get global transition_animation_scale",
                explanation="Transition animations occur when switching between different apps. Disabling these results in instant transitions, making multitasking feel much snappier.",
                impact="high"
            ),
            ADBCommand(
                name="Animator Duration Scale",
                description="Controls how long animations play before transitioning",
                enable_cmd="shell settings put global animator_duration_scale 1.0",
                disable_cmd="shell settings put global animator_duration_scale 0.0",
                get_cmd="shell settings get global animator_duration_scale",
                explanation="This setting governs the duration of all system animations. Setting it to 0 eliminates animation delays entirely, providing the most responsive experience.",
                impact="high"
            ),
        ]
    ),
    
    ADBCategory(
        id="background_processes",
        name="Kill Background Apps",
        description="Manage and terminate background processes to free up RAM and CPU resources",
        impact="high",
        commands=[
            ADBCommand(
                name="Trim All Caches",
                description="Clear app caches to free up storage and improve performance",
                enable_cmd="",  # No enable for cache clearing
                disable_cmd="shell pm trim-caches 128G",
                explanation="Clearing app caches removes temporary files that can accumulate over time. This frees up storage space and can help apps run more smoothly. The command attempts to free 128GB, effectively clearing all caches.",
                impact="high"
            ),
        ]
    ),
    
    ADBCategory(
        id="fixed_performance",
        name="Fixed Performance Mode",
        description="Lock CPU and GPU to maximum performance, disabling thermal throttling",
        impact="high",
        commands=[
            ADBCommand(
                name="Fixed Performance Mode",
                description="Enable sustained high performance (may cause heating)",
                enable_cmd="shell cmd power set-fixed-performance-mode-enabled true",
                disable_cmd="shell cmd power set-fixed-performance-mode-enabled false",
                get_cmd="shell dumpsys power | grep 'mFixedPerformanceModeEnabled'",
                explanation="Fixed performance mode clocks the CPU and GPU with upper and lower bounds, disabling thermal throttling. This provides maximum performance for demanding tasks but may cause the device to heat up and drain battery faster. Use with caution.",
                impact="high"
            ),
        ]
    ),
    
    ADBCategory(
        id="ram_plus",
        name="Disable RAM Plus",
        description="Disable virtual RAM expansion to improve performance and save battery",
        impact="high",
        commands=[
            ADBCommand(
                name="ZRAM (Virtual RAM)",
                description="Disable compressed RAM (may improve performance on some devices)",
                enable_cmd="shell settings put global zram_enabled 1",
                disable_cmd="shell settings put global zram_enabled 0",
                get_cmd="shell settings get global zram_enabled",
                explanation="ZRAM creates virtual RAM by compressing memory. While it can help with multitasking, it uses CPU cycles for compression/decompression. Disabling it may improve performance on devices with sufficient physical RAM.",
                impact="high"
            ),
            ADBCommand(
                name="RAM Expansion",
                description="Disable RAM expansion feature (Samsung/some OEMs)",
                enable_cmd="shell settings put global ram_expand_size_list 4",
                disable_cmd="shell settings put global ram_expand_size_list 0",
                get_cmd="shell settings get global ram_expand_size_list",
                explanation="RAM expansion uses storage as virtual memory. While it helps keep more apps in memory, it's slower than physical RAM and can reduce storage lifespan. Disabling it may improve overall system responsiveness.",
                impact="high"
            ),
        ]
    ),
    
    # MEDIUM IMPACT COMMANDS
    ADBCategory(
        id="refresh_rate",
        name="Refresh Rate & Display",
        description="Adjust screen refresh rate, window blur, and transparency for better performance",
        impact="medium",
        commands=[
            ADBCommand(
                name="Peak Refresh Rate",
                description="Set maximum screen refresh rate (e.g., 120Hz)",
                enable_cmd="shell settings put system peak_refresh_rate 120.0",
                disable_cmd="shell settings put system peak_refresh_rate 60.0",
                get_cmd="shell settings get system peak_refresh_rate",
                explanation="Higher refresh rates (90Hz, 120Hz) provide smoother scrolling and animations but consume more battery. Lowering to 60Hz can significantly extend battery life on devices with high refresh rate displays.",
                impact="medium"
            ),
            ADBCommand(
                name="Minimum Refresh Rate",
                description="Set minimum screen refresh rate",
                enable_cmd="shell settings put system min_refresh_rate 120.0",
                disable_cmd="shell settings put system min_refresh_rate 60.0",
                get_cmd="shell settings get system min_refresh_rate",
                explanation="Setting a minimum refresh rate keeps the display at a constant rate. Lower minimum rates allow the system to reduce refresh rate when static content is displayed, saving battery.",
                impact="medium"
            ),
            ADBCommand(
                name="Window Blur Effects",
                description="Disable blur effects on windows and backgrounds",
                enable_cmd="shell settings put global disable_window_blurs 0",
                disable_cmd="shell settings put global disable_window_blurs 1",
                get_cmd="shell settings get global disable_window_blurs",
                explanation="Window blur effects require GPU processing. Disabling them reduces GPU load, potentially improving performance and battery life, especially on mid-range devices.",
                impact="medium"
            ),
            ADBCommand(
                name="Reduce Transparency",
                description="Reduce transparency effects for better performance",
                enable_cmd="shell settings put global accessibility_reduce_transparency 0",
                disable_cmd="shell settings put global accessibility_reduce_transparency 1",
                get_cmd="shell settings get global accessibility_reduce_transparency",
                explanation="Transparency effects require additional rendering. Reducing transparency can improve performance, especially on devices with limited GPU capabilities.",
                impact="medium"
            ),
        ]
    ),
    
    ADBCategory(
        id="app_launch_speed",
        name="Speed Up App Launch",
        description="Optimize app startup process for faster launch times",
        impact="medium",
        commands=[
            ADBCommand(
                name="Rakuten Denwa Service",
                description="Disable Rakuten phone service (if present)",
                enable_cmd="shell settings put system rakuten_denwa 1",
                disable_cmd="shell settings put system rakuten_denwa 0",
                get_cmd="shell settings get system rakuten_denwa",
                explanation="Disables Rakuten phone service which may slow down app launches on devices with this service installed.",
                impact="medium"
            ),
            ADBCommand(
                name="Security Reports",
                description="Disable automatic security report sending",
                enable_cmd="shell settings put system send_security_reports 1",
                disable_cmd="shell settings put system send_security_reports 0",
                get_cmd="shell settings get system send_security_reports",
                explanation="Prevents the system from automatically sending security reports, reducing background activity during app launches.",
                impact="medium"
            ),
            ADBCommand(
                name="App Error Reporting",
                description="Disable automatic app error reporting",
                enable_cmd="shell settings put secure send_action_app_error 1",
                disable_cmd="shell settings put secure send_action_app_error 0",
                get_cmd="shell settings get secure send_action_app_error",
                explanation="Disables automatic error reporting which can slow down app startup, especially when apps crash or encounter errors.",
                impact="medium"
            ),
            ADBCommand(
                name="Activity Start Logging",
                description="Disable activity start logging",
                enable_cmd="shell settings put global activity_starts_logging_enabled 1",
                disable_cmd="shell settings put global activity_starts_logging_enabled 0",
                get_cmd="shell settings get global activity_starts_logging_enabled",
                explanation="Disables logging of app activity starts, reducing overhead during app launches.",
                impact="medium"
            ),
        ]
    ),
    
    ADBCategory(
        id="game_optimization_samsung",
        name="Game Optimization (Samsung)",
        description="Disable Samsung's Game Optimizing Service that may throttle performance",
        impact="medium",
        commands=[
            ADBCommand(
                name="Game SDK",
                description="Disable Samsung Game SDK",
                enable_cmd="shell settings put secure gamesdk_version 1",
                disable_cmd="shell settings put secure gamesdk_version 0",
                get_cmd="shell settings get secure gamesdk_version",
                explanation="Samsung's Game SDK can throttle CPU/GPU performance. Disabling it may improve gaming performance but could cause overheating.",
                impact="medium",
                samsung_only=True
            ),
            ADBCommand(
                name="Game Home",
                description="Disable Samsung Game Launcher home",
                enable_cmd="shell settings put secure game_home_enable 1",
                disable_cmd="shell settings put secure game_home_enable 0",
                get_cmd="shell settings get secure game_home_enable",
                explanation="Disables the Game Launcher home feature, reducing background processes related to gaming.",
                impact="medium",
                samsung_only=True
            ),
            ADBCommand(
                name="Game Bixby Block",
                description="Block Bixby during gaming",
                enable_cmd="shell settings put secure game_bixby_block 0",
                disable_cmd="shell settings put secure game_bixby_block 1",
                get_cmd="shell settings get secure game_bixby_block",
                explanation="Prevents Bixby from activating during gaming sessions, avoiding interruptions.",
                impact="medium",
                samsung_only=True
            ),
            ADBCommand(
                name="Game Auto Temperature Control",
                description="Disable automatic temperature-based throttling in games",
                enable_cmd="shell settings put secure game_auto_temperature_control 1",
                disable_cmd="shell settings put secure game_auto_temperature_control 0",
                get_cmd="shell settings get secure game_auto_temperature_control",
                explanation="Disables automatic thermal throttling during gaming. May improve performance but monitor device temperature.",
                impact="medium",
                samsung_only=True
            ),
        ]
    ),
    
    ADBCategory(
        id="audio_quality",
        name="Audio Quality Enhancement",
        description="Enable advanced audio processing for better sound quality",
        impact="medium",
        commands=[
            ADBCommand(
                name="K2HD Audio Effect",
                description="Enable K2HD audio enhancement",
                enable_cmd="shell settings put system k2hd_effect 1",
                disable_cmd="shell settings put system k2hd_effect 0",
                get_cmd="shell settings get system k2hd_effect",
                explanation="K2HD (K2 High Definition) enhances audio quality by upsampling and improving sound clarity. May slightly increase CPU usage.",
                impact="medium"
            ),
            ADBCommand(
                name="Tube Amp Effect",
                description="Enable tube amplifier audio effect",
                enable_cmd="shell settings put system tube_amp_effect 1",
                disable_cmd="shell settings put system tube_amp_effect 0",
                get_cmd="shell settings get system tube_amp_effect",
                explanation="Tube amp effect simulates analog tube amplifier sound characteristics, adding warmth to audio output.",
                impact="medium"
            ),
        ]
    ),
    
    ADBCategory(
        id="touchscreen_latency",
        name="Touchscreen Response",
        description="Reduce touch latency and improve touchscreen responsiveness",
        impact="medium",
        commands=[
            ADBCommand(
                name="Long Press Timeout",
                description="Reduce long-press delay for faster response",
                enable_cmd="shell settings put secure long_press_timeout 500",
                disable_cmd="shell settings put secure long_press_timeout 250",
                get_cmd="shell settings get secure long_press_timeout",
                explanation="Reduces the time required to register a long press, making the touchscreen feel more responsive. Lower values mean faster recognition.",
                impact="medium"
            ),
            ADBCommand(
                name="Multi-Press Timeout",
                description="Reduce multi-press detection timeout",
                enable_cmd="shell settings put secure multi_press_timeout 500",
                disable_cmd="shell settings put secure multi_press_timeout 250",
                get_cmd="shell settings get secure multi_press_timeout",
                explanation="Reduces the timeout for detecting multiple presses (like double-tap), improving responsiveness.",
                impact="medium"
            ),
            ADBCommand(
                name="Tap Duration Threshold",
                description="Minimize tap duration threshold",
                enable_cmd="shell settings put secure tap_duration_threshold 0.1",
                disable_cmd="shell settings put secure tap_duration_threshold 0.0",
                get_cmd="shell settings get secure tap_duration_threshold",
                explanation="Reduces the minimum time a tap must be held to register, making touches feel more immediate.",
                impact="medium"
            ),
            ADBCommand(
                name="Touch Blocking Period",
                description="Minimize touch blocking period",
                enable_cmd="shell settings put secure touch_blocking_period 0.1",
                disable_cmd="shell settings put secure touch_blocking_period 0.0",
                get_cmd="shell settings get secure touch_blocking_period",
                explanation="Reduces the period during which touches are blocked after certain events, improving touch responsiveness.",
                impact="medium"
            ),
        ]
    ),
    
    # LOW IMPACT COMMANDS
    ADBCategory(
        id="system_optimization",
        name="System Optimization",
        description="Various system-level optimizations for CPU, GPU, and overall performance",
        impact="low",
        commands=[
            ADBCommand(
                name="Force OpenGL",
                description="Force GPU rendering with OpenGL",
                enable_cmd="shell setprop debug.force-opengl 1",
                disable_cmd="shell setprop debug.force-opengl 0",
                get_cmd="shell getprop debug.force-opengl",
                explanation="Forces the system to use OpenGL for rendering, which may improve graphics performance on some devices.",
                impact="low"
            ),
            ADBCommand(
                name="GPU VSync",
                description="Force GPU vertical sync",
                enable_cmd="shell setprop debug.hwc.force_gpu_vsync 1",
                disable_cmd="shell setprop debug.hwc.force_gpu_vsync 0",
                get_cmd="shell getprop debug.hwc.force_gpu_vsync",
                explanation="Forces GPU-based vertical sync, which can reduce screen tearing but may slightly increase latency.",
                impact="low"
            ),
            ADBCommand(
                name="Multicore Packet Scheduler",
                description="Enable multicore packet scheduling",
                enable_cmd="shell settings put system multicore_packet_scheduler 1",
                disable_cmd="shell settings put system multicore_packet_scheduler 0",
                get_cmd="shell settings get system multicore_packet_scheduler",
                explanation="Enables multicore packet scheduling for better network performance on multi-core processors.",
                impact="low"
            ),
            ADBCommand(
                name="Enhanced CPU Responsiveness",
                description="Enable enhanced CPU responsiveness (Samsung)",
                enable_cmd="shell settings put global sem_enhanced_cpu_responsiveness 1",
                disable_cmd="shell settings put global sem_enhanced_cpu_responsiveness 0",
                get_cmd="shell settings get global sem_enhanced_cpu_responsiveness",
                explanation="Allows the CPU to spike to peak speed without sacrificing optimized mode. Samsung-specific feature.",
                impact="low",
                samsung_only=True
            ),
        ]
    ),
    
    ADBCategory(
        id="private_dns",
        name="Private DNS",
        description="Configure private DNS for enhanced privacy and security",
        impact="low",
        commands=[
            ADBCommand(
                name="Private DNS Mode",
                description="Enable/disable private DNS",
                enable_cmd="shell settings put global private_dns_mode hostname",
                disable_cmd="shell settings put global private_dns_mode off",
                get_cmd="shell settings get global private_dns_mode",
                explanation="Private DNS encrypts DNS queries for enhanced privacy and security. May slightly impact connection speed.",
                impact="low"
            ),
            ADBCommand(
                name="AdGuard DNS",
                description="Use AdGuard DNS for ad blocking",
                enable_cmd="shell settings put global private_dns_specifier dns.adguard.com",
                disable_cmd="shell settings put global private_dns_specifier ''",
                get_cmd="shell settings get global private_dns_specifier",
                explanation="Configures AdGuard DNS which blocks ads and trackers at the DNS level, improving privacy and potentially reducing data usage.",
                impact="low"
            ),
        ]
    ),
    
    ADBCategory(
        id="network_performance",
        name="Network Performance",
        description="Optimize network settings to reduce background scanning and improve connectivity",
        impact="low",
        commands=[
            ADBCommand(
                name="WiFi Power Save",
                description="Disable WiFi power saving mode",
                enable_cmd="shell settings put global wifi_power_save 1",
                disable_cmd="shell settings put global wifi_power_save 0",
                get_cmd="shell settings get global wifi_power_save",
                explanation="Disabling WiFi power save mode keeps WiFi at full power, improving connection stability and speed at the cost of battery life.",
                impact="low"
            ),
            ADBCommand(
                name="Cellular on Boot",
                description="Enable cellular data on device boot",
                enable_cmd="shell settings put global enable_cellular_on_boot 1",
                disable_cmd="shell settings put global enable_cellular_on_boot 0",
                get_cmd="shell settings get global enable_cellular_on_boot",
                explanation="Automatically enables cellular data when the device boots, ensuring immediate connectivity.",
                impact="low"
            ),
            ADBCommand(
                name="Mobile Data Always On",
                description="Keep mobile data always active (even on WiFi)",
                enable_cmd="shell settings put global mobile_data_always_on 1",
                disable_cmd="shell settings put global mobile_data_always_on 0",
                get_cmd="shell settings get global mobile_data_always_on",
                explanation="Keeps mobile data active even when connected to WiFi for faster switching. Increases battery usage.",
                impact="low"
            ),
            ADBCommand(
                name="Tether Offload",
                description="Enable tethering hardware offload",
                enable_cmd="shell settings put global tether_offload_disabled 0",
                disable_cmd="shell settings put global tether_offload_disabled 1",
                get_cmd="shell settings get global tether_offload_disabled",
                explanation="Hardware offload improves tethering performance by using dedicated hardware instead of CPU.",
                impact="low"
            ),
            ADBCommand(
                name="BLE Scan Always Enabled",
                description="Disable constant Bluetooth LE scanning",
                enable_cmd="shell settings put global ble_scan_always_enabled 1",
                disable_cmd="shell settings put global ble_scan_always_enabled 0",
                get_cmd="shell settings get global ble_scan_always_enabled",
                explanation="Disabling constant BLE scanning reduces battery drain and CPU usage from background Bluetooth activity.",
                impact="low"
            ),
            ADBCommand(
                name="Network Scoring UI",
                description="Disable network scoring UI",
                enable_cmd="shell settings put global network_scoring_ui_enabled 1",
                disable_cmd="shell settings put global network_scoring_ui_enabled 0",
                get_cmd="shell settings get global network_scoring_ui_enabled",
                explanation="Disables the network quality scoring interface, reducing background network analysis.",
                impact="low"
            ),
            ADBCommand(
                name="Network Recommendations",
                description="Disable automatic network recommendations",
                enable_cmd="shell settings put global network_recommendations_enabled 1",
                disable_cmd="shell settings put global network_recommendations_enabled 0",
                get_cmd="shell settings get global network_recommendations_enabled",
                explanation="Prevents the system from automatically recommending networks, reducing background scanning.",
                impact="low"
            ),
        ]
    ),
    
    ADBCategory(
        id="power_management",
        name="Power Management",
        description="Configure power-saving features and battery optimization settings",
        impact="low",
        commands=[
            ADBCommand(
                name="Intelligent Sleep Mode",
                description="Disable intelligent sleep mode",
                enable_cmd="shell settings put system intelligent_sleep_mode 1",
                disable_cmd="shell settings put system intelligent_sleep_mode 0",
                get_cmd="shell settings get system intelligent_sleep_mode",
                explanation="Intelligent sleep mode uses sensors to detect if you're looking at the screen. Disabling it saves CPU cycles but screen may turn off while you're reading.",
                impact="low"
            ),
            ADBCommand(
                name="Adaptive Sleep",
                description="Disable adaptive sleep (screen attention)",
                enable_cmd="shell settings put secure adaptive_sleep 1",
                disable_cmd="shell settings put secure adaptive_sleep 0",
                get_cmd="shell settings get secure adaptive_sleep",
                explanation="Adaptive sleep keeps the screen on while you're looking at it. Disabling it may save battery but requires manual screen timeout management.",
                impact="low"
            ),
            ADBCommand(
                name="App Restrictions",
                description="Enable app restriction for background activity",
                enable_cmd="shell settings put global app_restriction_enabled true",
                disable_cmd="shell settings put global app_restriction_enabled false",
                get_cmd="shell settings get global app_restriction_enabled",
                explanation="Restricts background activity of apps to save battery and improve performance.",
                impact="low"
            ),
            ADBCommand(
                name="Automatic Power Save",
                description="Disable automatic power save mode",
                enable_cmd="shell settings put global automatic_power_save_mode 1",
                disable_cmd="shell settings put global automatic_power_save_mode 0",
                get_cmd="shell settings get global automatic_power_save_mode",
                explanation="Prevents the system from automatically enabling power save mode at low battery levels.",
                impact="low"
            ),
            ADBCommand(
                name="Adaptive Battery Management",
                description="Disable adaptive battery management",
                enable_cmd="shell settings put global adaptive_battery_management_enabled 1",
                disable_cmd="shell settings put global adaptive_battery_management_enabled 0",
                get_cmd="shell settings get global adaptive_battery_management_enabled",
                explanation="Adaptive battery learns your usage patterns to optimize battery life. Disabling it gives you more control but may reduce battery efficiency.",
                impact="low"
            ),
        ]
    ),
]


def get_categories_json() -> List[Dict]:
    """Convert categories to JSON-serializable format"""
    result = []
    for category in COMMAND_CATEGORIES:
        commands = []
        for cmd in category.commands:
            commands.append({
                "name": cmd.name,
                "description": cmd.description,
                "enable_cmd": cmd.enable_cmd,
                "disable_cmd": cmd.disable_cmd,
                "get_cmd": cmd.get_cmd,
                "explanation": cmd.explanation,
                "impact": cmd.impact,
                "samsung_only": cmd.samsung_only
            })
        
        result.append({
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "impact": category.impact,
            "commands": commands
        })
    
    return result

