# Scholar Citation Tracker - Startup Setup Guide

## 🚀 **Multiple Ways to Set Up as Startup Program**

### **Method 1: macOS LaunchAgent (Recommended)**

This method automatically starts the service when you log in to your Mac.

#### **Quick Setup:**
```bash
python setup_startup.py
```
Choose option 1 to install as a macOS startup service.

#### **Manual Setup:**
1. **Create the plist file:**
   ```bash
   # The setup script creates this automatically
   # File location: ~/Library/LaunchAgents/com.scholar-citation-tracker.plist
   ```

2. **Load the service:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.scholar-citation-tracker.plist
   ```

3. **Check if it's running:**
   ```bash
   launchctl list com.scholar-citation-tracker
   ```

#### **Benefits:**
- ✅ Starts automatically on login
- ✅ Runs in background
- ✅ Auto-restarts if it crashes
- ✅ Logs output to files
- ✅ Native macOS integration

---

### **Method 2: Shell Script + Login Items**

#### **Create Startup Script:**
```bash
python setup_startup.py
```
Choose option 2 to create a startup script.

#### **Add to Login Items:**
1. Open **System Preferences** → **Users & Groups**
2. Select your user account
3. Click **Login Items** tab
4. Click **+** button
5. Navigate to your script: `start_scholar_tracker.sh`
6. Click **Add**

#### **Benefits:**
- ✅ Simple setup
- ✅ Visible in Login Items
- ✅ Easy to remove

---

### **Method 3: Desktop Entry (Linux-style)**

#### **Create Desktop Entry:**
```bash
python setup_startup.py
```
Choose option 3 to create a desktop entry.

#### **Benefits:**
- ✅ Double-click to start
- ✅ Easy access from desktop
- ✅ Portable across systems

---

### **Method 4: Cron Job (Advanced)**

#### **Edit crontab:**
```bash
crontab -e
```

#### **Add this line:**
```bash
@reboot cd /Users/dongwookim/Workspace/scholar_counter && python app.py > logs/cron.log 2>&1 &
```

#### **Benefits:**
- ✅ System-level startup
- ✅ Runs even before login
- ✅ Highly configurable

---

## 🛠️ **Setup Script Usage**

The `setup_startup.py` script provides an interactive menu:

```bash
python setup_startup.py
```

**Menu Options:**
1. **Install as macOS startup service** - Creates launchd service
2. **Create startup script** - Generates shell script
3. **Create desktop entry** - Makes desktop shortcut
4. **Uninstall startup service** - Removes launchd service
5. **Check service status** - Shows if service is running
6. **Exit** - Quit the script

---

## 📋 **Service Management Commands**

### **LaunchAgent Commands:**
```bash
# Load service
launchctl load ~/Library/LaunchAgents/com.scholar-citation-tracker.plist

# Unload service
launchctl unload ~/Library/LaunchAgents/com.scholar-citation-tracker.plist

# Check status
launchctl list com.scholar-citation-tracker

# View logs
tail -f ~/Library/Logs/scholar-citation-tracker.log
```

### **Manual Start/Stop:**
```bash
# Start manually
./start_scholar_tracker.sh

# Or directly
python app.py
```

---

## 🔧 **Configuration Options**

### **Change Port:**
Edit `config.py`:
```python
PORT = 8080  # Change to your preferred port
```

### **Change Google Scholar URL:**
Edit `config.py`:
```python
GOOGLE_SCHOLAR_URL = "https://scholar.google.com/citations?user=YOUR_USER_ID"
```

### **Enable/Disable Debug Mode:**
Edit `config.py`:
```python
DEBUG = False  # Set to False for production
```

---

## 📊 **Monitoring and Logs**

### **Log Files:**
- **Application logs:** `logs/scholar-tracker.log`
- **Error logs:** `logs/scholar-tracker-error.log`
- **Cron logs:** `logs/cron.log` (if using cron)

### **Check if Service is Running:**
```bash
# Check launchd service
launchctl list | grep scholar

# Check if port is in use
lsof -i :8080

# Check process
ps aux | grep "python.*app.py"
```

---

## 🚨 **Troubleshooting**

### **Service Won't Start:**
1. Check logs: `tail -f logs/scholar-tracker-error.log`
2. Verify Python path in plist file
3. Check file permissions
4. Ensure all dependencies are installed

### **Port Already in Use:**
1. Change port in `config.py`
2. Kill existing process: `lsof -ti:8080 | xargs kill`
3. Restart the service

### **Permission Issues:**
```bash
# Make scripts executable
chmod +x start_scholar_tracker.sh
chmod +x setup_startup.py

# Fix ownership
sudo chown -R $(whoami) /Users/dongwookim/Workspace/scholar_counter
```

---

## 🎯 **Recommended Setup**

For most users, I recommend **Method 1 (LaunchAgent)** because:

1. **Run the setup script:**
   ```bash
   python setup_startup.py
   ```

2. **Choose option 1** to install as startup service

3. **Verify it's working:**
   - Open browser to `http://localhost:8080`
   - Check service status with option 5

4. **Test auto-startup:**
   - Restart your Mac
   - The service should start automatically
   - Access the dashboard at `http://localhost:8080`

---

## 🔄 **Updating the Service**

When you update the application:

1. **Stop the service:**
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.scholar-citation-tracker.plist
   ```

2. **Update your code**

3. **Restart the service:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.scholar-citation-tracker.plist
   ```

---

## 📱 **Access Your Dashboard**

Once running, access your dashboard at:
- **Local:** `http://localhost:8080`
- **Network:** `http://YOUR_IP:8080` (if you want to access from other devices)

The service will automatically:
- ✅ Start on boot
- ✅ Restart if it crashes
- ✅ Log all activity
- ✅ Run in the background