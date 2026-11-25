# 🔥 Fire Emergency Response System

A rapid emergency reporting, live status tracking, and fire dispatch management system built with Flask, SQLite, and modern UI.

## Features
- **🚨 Instant Incident Reporting:** Quick emergency report submission with location, severity levels, and dispatcher preparation notes.
- **🔍 Real-Time Tracking:** Live 4-step progress pipeline (`Reported` ➔ `Dispatched` ➔ `In Progress` ➔ `Resolved`) with 30s auto-refresh.
- **✨ Sign Up & Auth:** Registration with interactive 8+ character password validation and character checklist.
- **🏠 Responder Portal:** Welcome dashboard and quick action navigation.
- **🚒 Fleet & Dispatch Console:** Centralized station unit monitoring and emergency response assignment.

## Getting Started

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python app.py
   ```

3. **Access the application:**
   - Open [http://127.0.0.1:5000](http://127.0.0.1:5000)
   - **Default Dispatcher Account:** `admin` / `admin123`
