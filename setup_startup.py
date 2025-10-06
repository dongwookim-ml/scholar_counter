#!/usr/bin/env python3
"""
Setup script to configure Scholar Citation Tracker as a startup service
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def create_launchd_plist():
    """Create a launchd plist file for macOS startup"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = sys.executable
    app_path = os.path.join(current_dir, "app.py")
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.scholar-citation-tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{app_path}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{current_dir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{current_dir}/logs/scholar-tracker.log</string>
    <key>StandardErrorPath</key>
    <string>{current_dir}/logs/scholar-tracker-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>"""
    
    # Create logs directory
    logs_dir = os.path.join(current_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Write plist file
    plist_path = os.path.join(current_dir, "com.scholar-citation-tracker.plist")
    with open(plist_path, 'w') as f:
        f.write(plist_content)
    
    return plist_path

def install_launchd_service():
    """Install the launchd service"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    plist_path = os.path.join(current_dir, "com.scholar-citation-tracker.plist")
    
    # Copy to LaunchAgents directory
    home_dir = os.path.expanduser("~")
    launch_agents_dir = os.path.join(home_dir, "Library", "LaunchAgents")
    os.makedirs(launch_agents_dir, exist_ok=True)
    
    target_path = os.path.join(launch_agents_dir, "com.scholar-citation-tracker.plist")
    shutil.copy2(plist_path, target_path)
    
    # Load the service
    try:
        subprocess.run(["launchctl", "load", target_path], check=True)
        print(f"✅ Service installed and loaded successfully!")
        print(f"📁 Plist file: {target_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error loading service: {e}")
        return False

def uninstall_launchd_service():
    """Uninstall the launchd service"""
    home_dir = os.path.expanduser("~")
    target_path = os.path.join(home_dir, "Library", "LaunchAgents", "com.scholar-citation-tracker.plist")
    
    try:
        # Unload the service
        subprocess.run(["launchctl", "unload", target_path], check=True)
        # Remove the plist file
        os.remove(target_path)
        print("✅ Service uninstalled successfully!")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Error uninstalling service: {e}")
        return False

def create_shell_script():
    """Create a shell script for manual startup"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = sys.executable
    app_path = os.path.join(current_dir, "app.py")
    
    script_content = f"""#!/bin/bash
# Scholar Citation Tracker Startup Script

cd "{current_dir}"
export PYTHONPATH="{current_dir}:$PYTHONPATH"

echo "Starting Scholar Citation Tracker..."
echo "Working directory: {current_dir}"
echo "Python path: {python_path}"

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the application
exec {python_path} {app_path}
"""
    
    script_path = os.path.join(current_dir, "start_scholar_tracker.sh")
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_path, 0o755)
    
    return script_path

def create_desktop_entry():
    """Create a desktop entry for easy access"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, "start_scholar_tracker.sh")
    
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Scholar Citation Tracker
Comment=Track and visualize Google Scholar citations
Exec={script_path}
Icon=applications-education
Terminal=false
Categories=Education;Science;
"""
    
    desktop_path = os.path.join(current_dir, "scholar-citation-tracker.desktop")
    with open(desktop_path, 'w') as f:
        f.write(desktop_content)
    
    return desktop_path

def main():
    """Main setup function"""
    print("=" * 60)
    print("🎓 Scholar Citation Tracker - Startup Setup")
    print("=" * 60)
    
    while True:
        print("\nChoose an option:")
        print("1. Install as macOS startup service (launchd)")
        print("2. Create startup script")
        print("3. Create desktop entry")
        print("4. Uninstall startup service")
        print("5. Check service status")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            print("\n📦 Installing as macOS startup service...")
            plist_path = create_launchd_plist()
            print(f"✅ Created plist file: {plist_path}")
            
            if install_launchd_service():
                print("🎉 Service will start automatically on boot!")
                print("🌐 Access at: http://localhost:8080")
            else:
                print("❌ Installation failed. Check the error messages above.")
        
        elif choice == "2":
            print("\n📝 Creating startup script...")
            script_path = create_shell_script()
            print(f"✅ Created startup script: {script_path}")
            print("💡 To run manually: ./start_scholar_tracker.sh")
        
        elif choice == "3":
            print("\n🖥️ Creating desktop entry...")
            desktop_path = create_desktop_entry()
            print(f"✅ Created desktop entry: {desktop_path}")
            print("💡 Double-click to start the application")
        
        elif choice == "4":
            print("\n🗑️ Uninstalling startup service...")
            uninstall_launchd_service()
        
        elif choice == "5":
            print("\n📊 Checking service status...")
            try:
                result = subprocess.run(["launchctl", "list", "com.scholar-citation-tracker"], 
                                     capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Service is running")
                    print(result.stdout)
                else:
                    print("❌ Service is not running")
            except Exception as e:
                print(f"❌ Error checking status: {e}")
        
        elif choice == "6":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()