#!/usr/bin/env python3
"""
Startup script for Aviation Weather Briefing System
"""
import os
import sys
from app import app

def main():
    """Main entry point"""
    # Set environment variables for development
    os.environ.setdefault('FLASK_ENV', 'development')
    
    # Get port from command line or environment
    port = 5001
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    port = int(os.environ.get('PORT', port))
    
    print("=" * 60)
    print("🛩️  Aviation Weather Briefing System")
    print("=" * 60)
    print(f"🌐 Server starting on http://localhost:{port}")
    print("🌦️  Using LIVE weather data from aviationweather.gov")
    print("🔧 Debug mode enabled")
    print("=" * 60)
    print("\n📋 Quick Start Guide:")
    print("1. Open your browser to the URL above")
    print("2. Enter any valid ICAO airport codes (e.g., KJFK, KLAX, KORD, KDEN)")
    print("3. Use Manual Entry tab for quick testing")
    print("4. Example route: KJFK → KORD → KDEN → KLAX")
    print("\n⚡ Features:")
    print("• Real-time weather data (METAR, TAF, PIREP)")
    print("• Weather categorization (Clear/Significant/Severe)")
    print("• Interactive visualizations and maps")
    print("• Flight route analysis")
    print("• Individual airport reports")
    print("\n🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Thank you for using Aviation Weather Briefing!")

if __name__ == '__main__':
    main()
