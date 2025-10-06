# 🚀 Quick Start - Scholar Citation Tracker as Startup

## **For macOS (Recommended):**

### **1. Run Setup Script:**
```bash
python setup_startup.py
```

### **2. Choose Option 1:**
- Installs as macOS startup service
- Starts automatically on login
- Runs in background

### **3. Access Dashboard:**
- Open browser to: `http://localhost:8080`
- Service runs automatically in background

---

## **For Linux:**

### **1. Create systemd service:**
```bash
# Edit the service file
sudo nano /etc/systemd/system/scholar-citation-tracker.service

# Update paths in the file:
# - User: your username
# - Group: your group
# - WorkingDirectory: /path/to/scholar_counter
# - ExecStart: /path/to/python /path/to/scholar_counter/app.py

# Enable and start
sudo systemctl enable scholar-citation-tracker
sudo systemctl start scholar-citation-tracker
```

---

## **For Windows:**

### **1. Use Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: "When the computer starts"
4. Set action: "Start a program"
5. Program: `python.exe`
6. Arguments: `C:\path\to\scholar_counter\app.py`
7. Start in: `C:\path\to\scholar_counter`

### **2. Or use the batch file:**
- Double-click `start_scholar_tracker.bat`
- Add to Windows Startup folder

---

## **Quick Commands:**

```bash
# Check if running
lsof -i :8080

# View logs
tail -f logs/scholar-tracker.log

# Manual start
python app.py

# Stop service (macOS)
launchctl unload ~/Library/LaunchAgents/com.scholar-citation-tracker.plist
```

---

## **Access Your Dashboard:**
🌐 **http://localhost:8080**

The service will start automatically every time you boot your computer! 🎉