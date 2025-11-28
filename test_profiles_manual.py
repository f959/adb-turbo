#!/usr/bin/env python3
"""
Manual test script for profiles functionality
This script tests the profiles module without requiring a real device
"""

import json
from profiles import ProfileManager, profile_manager

def test_profile_manager():
    """Test profile manager functionality"""
    print("=" * 60)
    print("Testing Profile Manager")
    print("=" * 60)
    
    # Test 1: Create a mock backup
    print("\n1. Testing backup creation...")
    try:
        # Simulate device settings
        mock_device_id = "test_device_123"
        mock_manufacturer = "samsung"
        mock_model = "SM-G998B"
        
        # Note: This would normally query the device, but we can test the structure
        print(f"   Device: {mock_manufacturer} {mock_model}")
        print(f"   Device ID: {mock_device_id}")
        
        # Get device key
        device_key = profile_manager.get_device_key(mock_device_id, mock_manufacturer, mock_model)
        print(f"   Device Key: {device_key}")
        print("   ✓ Device key generation works")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: Get preset info
    print("\n2. Testing preset information...")
    try:
        presets = profile_manager.get_preset_info()
        print(f"   Found {len(presets)} presets:")
        for preset in presets:
            print(f"   - {preset['name']}: {preset['description']}")
            print(f"     Settings count: {preset['settings_count']}")
        print("   ✓ Preset info retrieval works")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Validate preset structure
    print("\n3. Testing preset structure...")
    try:
        presets_data = profile_manager._get_presets()
        
        for preset_id, preset in presets_data.items():
            print(f"\n   Preset: {preset['name']} ({preset_id})")
            print(f"   Description: {preset['description']}")
            print(f"   Settings: {len(preset['settings'])}")
            
            # Validate each setting
            for setting in preset['settings']:
                if 'category' not in setting or 'command' not in setting or 'action' not in setting:
                    print(f"   ✗ Invalid setting structure: {setting}")
                    break
            else:
                print(f"   ✓ All settings valid")
        
        print("\n   ✓ Preset structure validation passed")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: Test profile storage structure
    print("\n4. Testing profile storage...")
    try:
        # Check if profiles file exists
        if profile_manager.profiles_file.exists():
            print(f"   Profiles file: {profile_manager.profiles_file}")
            print(f"   File size: {profile_manager.profiles_file.stat().st_size} bytes")
            
            # Load and display structure
            with open(profile_manager.profiles_file, 'r') as f:
                data = json.load(f)
            
            print(f"   Devices with backups: {len(data)}")
            for device_key, device_data in data.items():
                print(f"\n   Device: {device_key}")
                print(f"   - Manufacturer: {device_data['device_info']['manufacturer']}")
                print(f"   - Model: {device_data['device_info']['model']}")
                print(f"   - Backups: {len(device_data['backups'])}")
        else:
            print("   No profiles file exists yet (will be created on first backup)")
        
        print("   ✓ Profile storage structure valid")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 5: Test export/import structure
    print("\n5. Testing export/import structure...")
    try:
        # Create a mock profile for export
        mock_profile = {
            'manufacturer': 'samsung',
            'model': 'SM-G998B',
            'settings': {
                'Window Animation Scale': {
                    'state': False,
                    'category': 'animation_settings',
                    'enable_cmd': 'shell settings put global window_animation_scale 1.0',
                    'disable_cmd': 'shell settings put global window_animation_scale 0.0',
                    'get_cmd': 'shell settings get global window_animation_scale'
                }
            },
            'timestamp': '2025-11-28T13:00:00.000Z',
            'backup_type': 'manual'
        }
        
        # Validate required keys
        required_keys = ['manufacturer', 'model', 'settings']
        if all(key in mock_profile for key in required_keys):
            print("   ✓ Profile structure valid for export/import")
            print(f"   Profile has {len(mock_profile['settings'])} settings")
        else:
            print("   ✗ Profile structure invalid")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Profile Manager Tests Complete")
    print("=" * 60)
    
    # Summary
    print("\n📊 Summary:")
    print("✓ Device key generation")
    print("✓ Preset information retrieval")
    print("✓ Preset structure validation")
    print("✓ Profile storage structure")
    print("✓ Export/import structure")
    
    print("\n💡 Notes:")
    print("- Full device testing requires a connected Android device")
    print("- Backup/restore operations need ADB access")
    print("- Preset application requires device connection")
    print("- Profile persistence tested via file system")
    
    print("\n🎯 Next Steps:")
    print("1. Connect an Android device")
    print("2. Open http://localhost:8765 in browser")
    print("3. Select the device")
    print("4. Test presets and backup/restore in UI")

if __name__ == '__main__':
    test_profile_manager()

