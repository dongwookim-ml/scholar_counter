#!/usr/bin/env python3
"""
Scholar Citation Tracker Web Application
Startup script for the Flask application
"""

import os
import sys
from app import app
from config import HOST, PORT

if __name__ == '__main__':
    print("=" * 60)
    print("🎓 Scholar Citation Tracker Web Application")
    print("=" * 60)
    print("📊 Starting web server...")
    print(f"🌐 Dashboard will be available at: http://localhost:{PORT}")
    print("📈 Features:")
    print("   • Real-time citation tracking")
    print("   • Interactive charts and visualizations")
    print("   • Advanced analytics and insights")
    print("   • Data export capabilities")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        app.run(debug=True, host=HOST, port=PORT)
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Goodbye!")
        sys.exit(0)