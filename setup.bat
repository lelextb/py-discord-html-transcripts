@echo off
title Discord Transcript Bot Setup

echo 🔧 Setting up Discord Transcript Bot...

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

:: Create virtual environment
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate.bat

:: Upgrade pip
python -m pip install --upgrade pip

:: Install requirements
echo 📥 Installing dependencies...
pip install -r requirements.txt

:: Setup .env if not exists
if not exist ".env" (
    echo ⚙️ Creating .env file from example...
    copy .env.example .env
    echo ⚠️  Please edit .env with your DISCORD_TOKEN and SERVER_ID.
    echo    Press any key after editing...
    pause >nul
)

:: Create assets directory
if not exist "assets" mkdir assets

:: Create transcripts directory
if not exist "transcripts" mkdir transcripts

:: Run the bot
echo 🚀 Starting bot...
python main.py
pause