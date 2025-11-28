"""
Profile Management for adb-turbo
Handles device setting profiles with backup/restore and presets
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path
from adb_commands import execute_adb_command, get_command_state, COMMAND_CATEGORIES

logger = logging.getLogger(__name__)

# Profile storage directory
PROFILES_DIR = Path(__file__).parent / "profiles_data"
PROFILES_DIR.mkdir(exist_ok=True)


class ProfileManager:
    """Manages device profiles with backup/restore functionality"""
    
    def __init__(self):
        self.profiles_file = PROFILES_DIR / "profiles.json"
        self.profiles = self._load_profiles()
    
    def _load_profiles(self) -> Dict:
        """Load profiles from disk"""
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading profiles: {e}")
                return {}
        return {}
    
    def _save_profiles(self):
        """Save profiles to disk"""
        try:
            with open(self.profiles_file, 'w') as f:
                json.dump(self.profiles, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving profiles: {e}")
            raise
    
    def get_device_key(self, device_id: str, manufacturer: str, model: str) -> str:
        """Generate unique key for device (survives reconnection)"""
        # Use manufacturer + model as key (device_id changes on reconnect)
        return f"{manufacturer}_{model}".replace(" ", "_").lower()
    
    def backup_device_settings(self, device_id: str, manufacturer: str, model: str) -> Dict:
        """
        Backup all current device settings
        Returns the backed up profile
        """
        device_key = self.get_device_key(device_id, manufacturer, model)
        
        logger.info(f"Backing up settings for device: {device_key}")
        
        settings = {}
        
        # Iterate through all categories and commands
        for category in COMMAND_CATEGORIES:
            for cmd in category.commands:
                if cmd.get_cmd:
                    # Get the current state
                    state = get_command_state(device_id, cmd.get_cmd)
                    settings[cmd.name] = {
                        'state': state,
                        'category': category.id,
                        'enable_cmd': cmd.enable_cmd,
                        'disable_cmd': cmd.disable_cmd,
                        'get_cmd': cmd.get_cmd
                    }
        
        # Create profile
        profile = {
            'device_id': device_id,
            'manufacturer': manufacturer,
            'model': model,
            'settings': settings,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'backup_type': 'automatic'
        }
        
        # Store in profiles dict
        if device_key not in self.profiles:
            self.profiles[device_key] = {
                'device_info': {
                    'manufacturer': manufacturer,
                    'model': model
                },
                'backups': []
            }
        
        # Add to backups list (keep last 10)
        self.profiles[device_key]['backups'].insert(0, profile)
        self.profiles[device_key]['backups'] = self.profiles[device_key]['backups'][:10]
        
        # Save to disk
        self._save_profiles()
        
        logger.info(f"Backed up {len(settings)} settings for {device_key}")
        
        return profile
    
    def restore_device_settings(self, device_id: str, manufacturer: str, model: str, 
                                backup_index: int = 0) -> Dict:
        """
        Restore device settings from backup
        Returns dict with success/failure for each setting
        """
        device_key = self.get_device_key(device_id, manufacturer, model)
        
        if device_key not in self.profiles:
            raise ValueError(f"No backups found for device: {device_key}")
        
        backups = self.profiles[device_key]['backups']
        if backup_index >= len(backups):
            raise ValueError(f"Backup index {backup_index} not found")
        
        backup = backups[backup_index]
        settings = backup['settings']
        
        logger.info(f"Restoring {len(settings)} settings for {device_key}")
        
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        for setting_name, setting_data in settings.items():
            state = setting_data['state']
            
            # Skip if state is unknown
            if state is None:
                results['skipped'].append(setting_name)
                continue
            
            # Determine which command to execute
            cmd = setting_data['enable_cmd'] if state else setting_data['disable_cmd']
            
            if not cmd:
                results['skipped'].append(setting_name)
                continue
            
            # Execute command
            success, stdout, stderr = execute_adb_command(device_id, cmd)
            
            if success:
                results['success'].append(setting_name)
            else:
                results['failed'].append({
                    'name': setting_name,
                    'error': stderr or 'Unknown error'
                })
        
        logger.info(f"Restore complete: {len(results['success'])} success, "
                   f"{len(results['failed'])} failed, {len(results['skipped'])} skipped")
        
        return results
    
    def get_device_backups(self, manufacturer: str, model: str) -> List[Dict]:
        """Get all backups for a device"""
        device_key = self.get_device_key("", manufacturer, model)
        
        if device_key not in self.profiles:
            return []
        
        return self.profiles[device_key]['backups']
    
    def export_profile(self, manufacturer: str, model: str, backup_index: int = 0) -> Dict:
        """Export a profile for sharing"""
        device_key = self.get_device_key("", manufacturer, model)
        
        if device_key not in self.profiles:
            raise ValueError(f"No backups found for device: {device_key}")
        
        backups = self.profiles[device_key]['backups']
        if backup_index >= len(backups):
            raise ValueError(f"Backup index {backup_index} not found")
        
        return backups[backup_index]
    
    def import_profile(self, profile_data: Dict, device_id: str) -> Dict:
        """
        Import a profile from external source
        Returns the imported profile
        """
        # Validate profile data
        required_keys = ['manufacturer', 'model', 'settings']
        if not all(key in profile_data for key in required_keys):
            raise ValueError("Invalid profile data format")
        
        manufacturer = profile_data['manufacturer']
        model = profile_data['model']
        device_key = self.get_device_key("", manufacturer, model)
        
        # Create profile entry
        profile = {
            'device_id': device_id,
            'manufacturer': manufacturer,
            'model': model,
            'settings': profile_data['settings'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'backup_type': 'imported',
            'original_timestamp': profile_data.get('timestamp', 'unknown')
        }
        
        # Store in profiles dict
        if device_key not in self.profiles:
            self.profiles[device_key] = {
                'device_info': {
                    'manufacturer': manufacturer,
                    'model': model
                },
                'backups': []
            }
        
        # Add to backups list
        self.profiles[device_key]['backups'].insert(0, profile)
        self.profiles[device_key]['backups'] = self.profiles[device_key]['backups'][:10]
        
        # Save to disk
        self._save_profiles()
        
        logger.info(f"Imported profile for {device_key}")
        
        return profile
    
    def apply_preset(self, device_id: str, preset_name: str) -> Dict:
        """
        Apply a preset configuration
        Presets: 'high_performance', 'medium_performance', 'max_battery', 'recommended'
        """
        presets = self._get_presets()
        
        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        preset = presets[preset_name]
        
        logger.info(f"Applying preset '{preset_name}' to device {device_id}")
        
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        # Apply each setting in the preset
        for setting in preset['settings']:
            category_id = setting['category']
            command_name = setting['command']
            action = setting['action']  # 'enable' or 'disable'
            
            # Find the command
            cmd_obj = self._find_command(category_id, command_name)
            if not cmd_obj:
                results['skipped'].append(command_name)
                continue
            
            # Get the appropriate command
            cmd = cmd_obj.enable_cmd if action == 'enable' else cmd_obj.disable_cmd
            
            if not cmd:
                results['skipped'].append(command_name)
                continue
            
            # Execute command
            success, stdout, stderr = execute_adb_command(device_id, cmd)
            
            if success:
                results['success'].append(command_name)
            else:
                results['failed'].append({
                    'name': command_name,
                    'error': stderr or 'Unknown error'
                })
        
        logger.info(f"Preset '{preset_name}' applied: {len(results['success'])} success, "
                   f"{len(results['failed'])} failed, {len(results['skipped'])} skipped")
        
        return results
    
    def _find_command(self, category_id: str, command_name: str):
        """Find a command object by category and name"""
        for category in COMMAND_CATEGORIES:
            if category.id == category_id:
                for cmd in category.commands:
                    if cmd.name == command_name:
                        return cmd
        return None
    
    def _get_presets(self) -> Dict:
        """Define preset configurations"""
        return {
            'high_performance': {
                'name': 'High Performance',
                'description': 'Maximum speed and responsiveness (no thermal throttling)',
                'settings': [
                    # Disable all animations for instant response
                    {'category': 'animation_settings', 'command': 'Window Animation Scale', 'action': 'disable'},
                    {'category': 'animation_settings', 'command': 'Transition Animation Scale', 'action': 'disable'},
                    {'category': 'animation_settings', 'command': 'Animator Duration Scale', 'action': 'disable'},
                    # DO NOT enable fixed performance mode - it causes throttling!
                    {'category': 'fixed_performance', 'command': 'Fixed Performance Mode', 'action': 'disable'},
                    # Disable ZRAM for better performance
                    {'category': 'ram_plus', 'command': 'ZRAM (Virtual RAM)', 'action': 'disable'},
                    {'category': 'ram_plus', 'command': 'RAM Expansion', 'action': 'disable'},
                    # Max refresh rate
                    {'category': 'refresh_rate', 'command': 'Peak Refresh Rate', 'action': 'enable'},
                    {'category': 'refresh_rate', 'command': 'Minimum Refresh Rate', 'action': 'enable'},
                    # Disable window blur and transparency
                    {'category': 'refresh_rate', 'command': 'Window Blur Effects', 'action': 'disable'},
                    {'category': 'refresh_rate', 'command': 'Reduce Transparency', 'action': 'disable'},
                    # Disable WiFi power save
                    {'category': 'network_performance', 'command': 'WiFi Power Save', 'action': 'disable'},
                    # Reduce touch latency
                    {'category': 'touchscreen_latency', 'command': 'Long Press Timeout', 'action': 'disable'},
                    {'category': 'touchscreen_latency', 'command': 'Multi-Press Timeout', 'action': 'disable'},
                ]
            },
            'medium_performance': {
                'name': 'Medium Performance',
                'description': 'Balanced performance and battery life',
                'settings': [
                    # Reduce animations (0.5x speed)
                    {'category': 'animation_settings', 'command': 'Window Animation Scale', 'action': 'enable'},
                    {'category': 'animation_settings', 'command': 'Transition Animation Scale', 'action': 'enable'},
                    {'category': 'animation_settings', 'command': 'Animator Duration Scale', 'action': 'enable'},
                    # Disable fixed performance mode
                    {'category': 'fixed_performance', 'command': 'Fixed Performance Mode', 'action': 'disable'},
                    # Keep ZRAM enabled
                    {'category': 'ram_plus', 'command': 'ZRAM (Virtual RAM)', 'action': 'enable'},
                    # Adaptive refresh rate
                    {'category': 'refresh_rate', 'command': 'Peak Refresh Rate', 'action': 'enable'},
                    {'category': 'refresh_rate', 'command': 'Minimum Refresh Rate', 'action': 'disable'},
                    # Disable window blur
                    {'category': 'refresh_rate', 'command': 'Window Blur Effects', 'action': 'disable'},
                ]
            },
            'max_battery': {
                'name': 'Max Battery',
                'description': 'Extended battery life (surprisingly snappy!)',
                'settings': [
                    # Disable all animations - feels faster AND saves battery
                    {'category': 'animation_settings', 'command': 'Window Animation Scale', 'action': 'disable'},
                    {'category': 'animation_settings', 'command': 'Transition Animation Scale', 'action': 'disable'},
                    {'category': 'animation_settings', 'command': 'Animator Duration Scale', 'action': 'disable'},
                    # Disable fixed performance mode
                    {'category': 'fixed_performance', 'command': 'Fixed Performance Mode', 'action': 'disable'},
                    # Enable ZRAM for memory efficiency
                    {'category': 'ram_plus', 'command': 'ZRAM (Virtual RAM)', 'action': 'enable'},
                    # 60Hz refresh rate
                    {'category': 'refresh_rate', 'command': 'Peak Refresh Rate', 'action': 'disable'},
                    {'category': 'refresh_rate', 'command': 'Minimum Refresh Rate', 'action': 'disable'},
                    # Disable window blur
                    {'category': 'refresh_rate', 'command': 'Window Blur Effects', 'action': 'disable'},
                    # Enable WiFi power save
                    {'category': 'network_performance', 'command': 'WiFi Power Save', 'action': 'enable'},
                    # Disable BLE scanning
                    {'category': 'network_performance', 'command': 'BLE Scan Always Enabled', 'action': 'disable'},
                    # Disable mobile data always on
                    {'category': 'network_performance', 'command': 'Mobile Data Always On', 'action': 'disable'},
                ]
            },
            'max_quality': {
                'name': 'Max Quality',
                'description': 'Best visual quality and audio fidelity',
                'settings': [
                    # Keep animations for smooth visuals
                    {'category': 'animation_settings', 'command': 'Window Animation Scale', 'action': 'enable'},
                    {'category': 'animation_settings', 'command': 'Transition Animation Scale', 'action': 'enable'},
                    {'category': 'animation_settings', 'command': 'Animator Duration Scale', 'action': 'enable'},
                    # Disable fixed performance mode
                    {'category': 'fixed_performance', 'command': 'Fixed Performance Mode', 'action': 'disable'},
                    # Disable ZRAM for better performance
                    {'category': 'ram_plus', 'command': 'ZRAM (Virtual RAM)', 'action': 'disable'},
                    # Max refresh rate for smoothness
                    {'category': 'refresh_rate', 'command': 'Peak Refresh Rate', 'action': 'enable'},
                    {'category': 'refresh_rate', 'command': 'Minimum Refresh Rate', 'action': 'enable'},
                    # ENABLE window blur for visual quality
                    {'category': 'refresh_rate', 'command': 'Window Blur Effects', 'action': 'enable'},
                    # Keep transparency effects
                    {'category': 'refresh_rate', 'command': 'Reduce Transparency', 'action': 'enable'},
                    # Enable K2HD audio enhancement
                    {'category': 'audio_quality', 'command': 'K2HD Audio Effect', 'action': 'enable'},
                    # Enable Tube Amp effect
                    {'category': 'audio_quality', 'command': 'Tube Amp Effect', 'action': 'enable'},
                    # Disable WiFi power save for better streaming
                    {'category': 'network_performance', 'command': 'WiFi Power Save', 'action': 'disable'},
                    # Keep mobile data always on for seamless switching
                    {'category': 'network_performance', 'command': 'Mobile Data Always On', 'action': 'enable'},
                ]
            },
            'recommended': {
                'name': 'Recommended',
                'description': 'Optimized settings for best overall experience',
                'settings': [
                    # Reduce animations (0.5x speed)
                    {'category': 'animation_settings', 'command': 'Window Animation Scale', 'action': 'enable'},
                    {'category': 'animation_settings', 'command': 'Transition Animation Scale', 'action': 'enable'},
                    {'category': 'animation_settings', 'command': 'Animator Duration Scale', 'action': 'enable'},
                    # Disable fixed performance mode
                    {'category': 'fixed_performance', 'command': 'Fixed Performance Mode', 'action': 'disable'},
                    # Disable ZRAM for better performance
                    {'category': 'ram_plus', 'command': 'ZRAM (Virtual RAM)', 'action': 'disable'},
                    # Adaptive refresh rate
                    {'category': 'refresh_rate', 'command': 'Peak Refresh Rate', 'action': 'enable'},
                    {'category': 'refresh_rate', 'command': 'Minimum Refresh Rate', 'action': 'disable'},
                    # Disable window blur for performance
                    {'category': 'refresh_rate', 'command': 'Window Blur Effects', 'action': 'disable'},
                    {'category': 'refresh_rate', 'command': 'Reduce Transparency', 'action': 'disable'},
                    # Disable BLE scanning
                    {'category': 'network_performance', 'command': 'BLE Scan Always Enabled', 'action': 'disable'},
                    # Disable network recommendations
                    {'category': 'network_performance', 'command': 'Network Recommendations', 'action': 'disable'},
                    # Reduce touch latency
                    {'category': 'touchscreen_latency', 'command': 'Long Press Timeout', 'action': 'disable'},
                ]
            }
        }
    
    def get_preset_info(self) -> List[Dict]:
        """Get information about all available presets"""
        presets = self._get_presets()
        return [
            {
                'id': key,
                'name': preset['name'],
                'description': preset['description'],
                'settings_count': len(preset['settings'])
            }
            for key, preset in presets.items()
        ]


# Global profile manager instance
profile_manager = ProfileManager()

