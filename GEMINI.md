# Gemini Project Context: Flight Manager Logger

This document provides architectural overview, development guidelines, and key technical context for the Flight Manager Logger project.

## 🚀 Project Overview

**Flight Manager Logger** is a Python desktop application designed for drone operators to log flight data, manage vehicle fleets, and perform parameter analysis.

### Core Technologies
- **Language:** Python 3.x
- **GUI Framework:** `tkinter` (with `ttk` widgets and `tkcalendar`)
- **Database:** SQLite (via `sqlite3`)
- **Image Processing:** `Pillow` (for icon handling)
- **Packaging:** `PyInstaller` (for Windows executables)

### Architecture
The project follows a loosely decoupled architecture:
- **Entry Point:** `main.py` initializes the Tkinter root and the main application class.
- **UI Layer (`flight_manager/ui/`):** Contains all GUI definitions. `main_window.py` is the primary controller.
- **Service Layer (`flight_manager/services.py`):** Encapsulates business logic, validation, and data preparation to keep UI code clean.
- **Data Layer (`flight_manager/database.py`):** Manages the SQLite connection, schema migrations, and CRUD operations.
- **File Management (`flight_manager/file_manager.py`):** Handles physical storage, naming, and automated cleanup of flight log files.
- **Utilities (`flight_manager/utils.py`):** Low-level logic for parsing parameter files and safely evaluating checklist validation rules using `ast`.

## 🛠️ Building and Running

### Development Environment
1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run Application:**
    ```bash
    python main.py
    ```

### Build Process
The project uses a custom build script to package the application into a standalone Windows executable.
- **Build Executable:**
    ```bash
    python build.py
    ```
    Or use the convenience batch file:
    ```cmd
    compile.bat
    ```
- **Build Artifacts:** Output is generated in the `dist/` directory. Temporary build files are stored in `build/`.

## 📂 Key Files & Directories

- `flight_manager/database.py`: **Critical.** Defines the SQLite schema and handles database migrations. Always check here when adding new data fields.
- `flight_manager/services.py`: Contains `LogService` for validating flight logs before they are saved.
- `flight_manager/utils.py`: Contains safe evaluation logic for checklist rules. Uses `ast` to avoid unsafe `eval()`.
- `flight_manager/ui/main_window.py`: The heart of the UI. Manages state for filtering, sorting, and the dynamic checklist.
- `captured_logs/`: (Generated at runtime) Default directory where attached flight log files are stored and managed.

## 📝 Development Conventions

- **Database Migrations:** The `DatabaseManager.create_tables()` method performs "safe" migrations by checking if columns exist before attempting `ALTER TABLE`.
- **Threading:** Long-running operations (file cleanup, database fetching, saving logs) should be performed in background threads (using `threading.Thread`) to keep the UI responsive.
- **Font Scaling:** The application implements a custom font scaling system in `main_window.py` that updates both standard Tkinter named fonts and TTK styles.
- **Error Handling:** Use `messagebox` for user-facing errors. Database and file operations should typically be wrapped in try-except blocks with UI callbacks on the main thread.
- **Versioning:** Versioning is dynamic based on git tags (`flight_manager/version.py`). The `build.py` script hardcodes the version into the package during the build process and reverts it afterward.

## 📋 Features to Note
- **Safe Rule Evaluation:** Checklist items can have validation rules (e.g., `value > 10`). These are parsed into an Abstract Syntax Tree (AST) in `utils.py` for secure evaluation.
- **Parameter Comparison:** Users can compare current parameter files against historical logs for the same vehicle.
- **Automated Cleanup:** The `FileManager` can prune the `captured_logs/` directory based on total size or file age, excluding "locked" logs.
