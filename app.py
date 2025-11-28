"""
adb-turbo - Flask Backend
A friendly web-based tool for Android performance optimization
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import signal
import atexit
import logging
from datetime import datetime, timezone
from adb_commands import (
    check_adb_available,
    get_connected_devices,
    execute_adb_command,
    get_categories_json,
    get_device_manufacturer,
    get_device_location,
    get_comprehensive_device_info,
    get_command_state,
    COMMAND_CATEGORIES
)
from config import config, setup_logging
from profiles import profile_manager

# Setup logging
setup_logging(config)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='static')
CORS(app, origins=config.CORS_ORIGINS)


# ============================================
# API Response Helpers
# ============================================

def api_success(data=None, message=None, status=200):
    """
    Standardized success response
    
    Args:
        data: Response data
        message: Optional success message
        status: HTTP status code
    
    Returns:
        JSON response tuple
    """
    response = {
        'success': True,
        'data': data,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    if message:
        response['message'] = message
    return jsonify(response), status


def api_error(error, status=400, details=None):
    """
    Standardized error response
    
    Args:
        error: Error message
        status: HTTP status code
        details: Optional additional error details
    
    Returns:
        JSON response tuple
    """
    response = {
        'success': False,
        'error': error,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    if details:
        response['details'] = details
    
    logger.error(f"API Error ({status}): {error}")
    return jsonify(response), status


@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory('static', 'index.html')


@app.route('/api/check-adb', methods=['GET'])
def check_adb():
    """Check if ADB is installed and available"""
    try:
        available, message = check_adb_available()
        return api_success(data={
            'available': available,
            'message': message
        })
    except Exception as e:
        return api_error(f"Failed to check ADB: {str(e)}", status=500)


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get list of connected ADB devices"""
    try:
        devices = get_connected_devices()
        return api_success(data={'devices': devices})
    except Exception as e:
        return api_error(f"Failed to get devices: {str(e)}", status=500)


@app.route('/api/device-info/<device_id>', methods=['GET'])
def get_device_info(device_id):
    """Get device information and capabilities"""
    try:
        manufacturer = get_device_manufacturer(device_id)
        
        # Get device model
        success, model, _ = execute_adb_command(device_id, "shell getprop ro.product.model")
        model = model.strip() if success else "Unknown"
        
        # Get Android version
        success, android_version, _ = execute_adb_command(device_id, "shell getprop ro.build.version.release")
        android_version = android_version.strip() if success else "Unknown"
        
        # Get SDK version
        success, sdk_version, _ = execute_adb_command(device_id, "shell getprop ro.build.version.sdk")
        sdk_version = sdk_version.strip() if success else "Unknown"
        
        # Get device location
        latitude, longitude = get_device_location(device_id)
        
        # Get comprehensive device information
        comprehensive_info = get_comprehensive_device_info(device_id)
        
        return api_success(data={
            'device_id': device_id,
            'manufacturer': manufacturer,
            'model': model,
            'android_version': android_version,
            'sdk_version': sdk_version,
            'is_samsung': manufacturer == 'samsung',
            'location': {
                'latitude': latitude,
                'longitude': longitude,
                'available': latitude is not None and longitude is not None
            },
            'details': comprehensive_info
        })
    except Exception as e:
        return api_error(f"Failed to get device info: {str(e)}", status=500)


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all command categories with their commands"""
    try:
        categories = get_categories_json()
        return api_success(data={'categories': categories})
    except Exception as e:
        return api_error(f"Failed to get categories: {str(e)}", status=500)


@app.route('/api/command-states/<device_id>', methods=['GET'])
def get_command_states(device_id):
    """Get the current state of all commands for a device"""
    try:
        states = {}
        
        # Iterate through all categories and commands
        for category in COMMAND_CATEGORIES:
            for cmd in category.commands:
                if cmd.get_cmd:
                    # Get the current state
                    state = get_command_state(device_id, cmd.get_cmd)
                    # Use command name as key
                    states[cmd.name] = state
        
        return api_success(data={'states': states})
    except Exception as e:
        return api_error(f"Failed to get command states: {str(e)}", status=500)


@app.route('/api/execute', methods=['POST'])
def execute_command():
    """Execute an ADB command on a device"""
    try:
        data = request.json
        device_id = data.get('device_id')
        command = data.get('command')
        action = data.get('action', 'disable')  # enable or disable
        
        if not device_id:
            return api_error('No device selected', status=400)
        
        if not command:
            return api_error('No command provided', status=400)
        
        # Execute the command
        logger.info(f"Executing command on {device_id}: {command} ({action})")
        success, stdout, stderr = execute_adb_command(device_id, command)
        
        # Prepare output
        output = stdout if stdout else stderr
        if not output:
            output = "Command executed successfully" if success else "Command failed with no output"
        
        if success:
            return api_success(data={
                'output': output,
                'action': action
            })
        else:
            return api_error(
                error="Command execution failed",
                status=400,
                details={'output': output, 'stderr': stderr}
            )
        
    except Exception as e:
        return api_error(f"Failed to execute command: {str(e)}", status=500)


@app.route('/api/get-setting', methods=['POST'])
def get_setting():
    """Get current value of a setting"""
    try:
        data = request.json
        device_id = data.get('device_id')
        namespace = data.get('namespace', 'global')  # global, secure, system
        key = data.get('key')
        
        if not device_id or not key:
            return api_error('Missing device_id or key', status=400)
        
        # Get the setting value
        command = f"shell settings get {namespace} {key}"
        success, stdout, stderr = execute_adb_command(device_id, command)
        
        value = stdout.strip() if success else None
        
        if success:
            return api_success(data={'value': value, 'namespace': namespace, 'key': key})
        else:
            return api_error(
                error="Failed to get setting",
                status=400,
                details={'stderr': stderr}
            )
        
    except Exception as e:
        return api_error(f"Failed to get setting: {str(e)}", status=500)


# ============================================
# Profile Management API
# ============================================

@app.route('/api/profiles/backup', methods=['POST'])
def backup_profile():
    """Backup current device settings"""
    try:
        data = request.json
        device_id = data.get('device_id')
        manufacturer = data.get('manufacturer')
        model = data.get('model')
        
        if not all([device_id, manufacturer, model]):
            return api_error('Missing required fields: device_id, manufacturer, model', status=400)
        
        profile = profile_manager.backup_device_settings(device_id, manufacturer, model)
        
        return api_success(
            data={'profile': profile},
            message=f"Backed up {len(profile['settings'])} settings"
        )
        
    except Exception as e:
        return api_error(f"Failed to backup settings: {str(e)}", status=500)


@app.route('/api/profiles/restore', methods=['POST'])
def restore_profile():
    """Restore device settings from backup"""
    try:
        data = request.json
        device_id = data.get('device_id')
        manufacturer = data.get('manufacturer')
        model = data.get('model')
        backup_index = data.get('backup_index', 0)
        
        if not all([device_id, manufacturer, model]):
            return api_error('Missing required fields: device_id, manufacturer, model', status=400)
        
        results = profile_manager.restore_device_settings(
            device_id, manufacturer, model, backup_index
        )
        
        return api_success(
            data={'results': results},
            message=f"Restored {len(results['success'])} settings"
        )
        
    except ValueError as e:
        return api_error(str(e), status=404)
    except Exception as e:
        return api_error(f"Failed to restore settings: {str(e)}", status=500)


@app.route('/api/profiles/list', methods=['POST'])
def list_profiles():
    """Get all backups for a device"""
    try:
        data = request.json
        manufacturer = data.get('manufacturer')
        model = data.get('model')
        
        if not all([manufacturer, model]):
            return api_error('Missing required fields: manufacturer, model', status=400)
        
        backups = profile_manager.get_device_backups(manufacturer, model)
        
        return api_success(data={'backups': backups})
        
    except Exception as e:
        return api_error(f"Failed to list profiles: {str(e)}", status=500)


@app.route('/api/profiles/export', methods=['POST'])
def export_profile():
    """Export a profile for sharing"""
    try:
        data = request.json
        manufacturer = data.get('manufacturer')
        model = data.get('model')
        backup_index = data.get('backup_index', 0)
        
        if not all([manufacturer, model]):
            return api_error('Missing required fields: manufacturer, model', status=400)
        
        profile = profile_manager.export_profile(manufacturer, model, backup_index)
        
        return api_success(data={'profile': profile})
        
    except ValueError as e:
        return api_error(str(e), status=404)
    except Exception as e:
        return api_error(f"Failed to export profile: {str(e)}", status=500)


@app.route('/api/profiles/import', methods=['POST'])
def import_profile():
    """Import a profile from external source"""
    try:
        data = request.json
        profile_data = data.get('profile')
        device_id = data.get('device_id')
        
        if not profile_data or not device_id:
            return api_error('Missing required fields: profile, device_id', status=400)
        
        profile = profile_manager.import_profile(profile_data, device_id)
        
        return api_success(
            data={'profile': profile},
            message="Profile imported successfully"
        )
        
    except ValueError as e:
        return api_error(str(e), status=400)
    except Exception as e:
        return api_error(f"Failed to import profile: {str(e)}", status=500)


@app.route('/api/profiles/presets', methods=['GET'])
def get_presets():
    """Get available preset configurations"""
    try:
        presets = profile_manager.get_preset_info()
        return api_success(data={'presets': presets})
    except Exception as e:
        return api_error(f"Failed to get presets: {str(e)}", status=500)


@app.route('/api/profiles/apply-preset', methods=['POST'])
def apply_preset():
    """Apply a preset configuration"""
    try:
        data = request.json
        device_id = data.get('device_id')
        preset_name = data.get('preset_name')
        
        if not device_id or not preset_name:
            return api_error('Missing required fields: device_id, preset_name', status=400)
        
        results = profile_manager.apply_preset(device_id, preset_name)
        
        return api_success(
            data={'results': results},
            message=f"Applied preset: {len(results['success'])} settings changed"
        )
        
    except ValueError as e:
        return api_error(str(e), status=400)
    except Exception as e:
        return api_error(f"Failed to apply preset: {str(e)}", status=500)


def print_banner(url):
    """Print a nice banner with the server URL"""
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        adb-turbo                                             ║
║        Friendly Android Performance Tool                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

🚀 Server running at: {url}

📱 Make sure:
   • ADB is installed and in your PATH
   • USB debugging is enabled on your Android device
   • Your device is connected via USB

💡 The web interface will open automatically in your browser

Press Ctrl+C to stop the server
"""
    print(banner)
    logger.info(f"Server started at {url}")


def cleanup():
    """Cleanup function to run on exit"""
    print(f"\n\n👋 Server stopped. Port {config.PORT} is now free.")
    print("Thank you for using adb-turbo!")
    logger.info("Server stopped")


def signal_handler(sig, frame):
    """Handle interrupt signals gracefully"""
    cleanup()
    sys.exit(0)


if __name__ == '__main__':
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print banner
    print_banner(config.url)
    
    # Run the Flask app
    try:
        logger.info(f"Starting Flask server on {config.HOST}:{config.PORT}")
        app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        pass  # Cleanup handled by signal_handler

