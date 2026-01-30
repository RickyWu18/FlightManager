@echo off
set ENV_DIR=build/build_env

echo Cleaning up previous build artifacts...
if exist %ENV_DIR% rmdir /s /q %ENV_DIR%
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

echo Creating virtual environment...
python -m venv %ENV_DIR%

echo Activating virtual environment...
call %ENV_DIR%\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo Building FlightManager...
python build.py

echo Deactivating virtual environment...
deactivate

echo Cleaning up virtual environment...
rmdir /s /q %ENV_DIR%

echo Build complete! Executable is in the 'dist' folder.
pause