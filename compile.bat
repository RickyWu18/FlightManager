@echo off
setlocal
set ENV_DIR=build\build_env

for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)"') do set PYTHON_EXE=%%i

echo Cleaning up previous build artifacts...
if exist "%ENV_DIR%" rmdir /s /q "%ENV_DIR%"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

echo Creating virtual environment...
"%PYTHON_EXE%" -m venv "%ENV_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment. Error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo Activating virtual environment...
if not exist "%ENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] Activation script not found at "%ENV_DIR%\Scripts\activate.bat"
    pause
    exit /b 1
)

call "%ENV_DIR%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b %errorlevel%
)

echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b %errorlevel%
)

pip install pyinstaller
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install pyinstaller.
    pause
    exit /b %errorlevel%
)

echo Building FlightManager...
"%PYTHON_EXE%" build.py
if %errorlevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b %errorlevel%
)

echo Deactivating virtual environment...
call deactivate

echo Cleaning up virtual environment...
rmdir /s /q "%ENV_DIR%"

echo Build complete! Executable is in the 'dist' folder.
rem pause
endlocal
