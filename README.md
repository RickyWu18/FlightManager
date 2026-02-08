# Flight Manager Logger

**Flight Manager Logger** is a professional desktop application designed to streamline flight data logging, vehicle management, and parameter tracking for drone operations. It provides a robust, self-contained environment for maintaining operational history and ensuring pre-flight safety.

## 🚀 Key Features

### Flight Logging & Security
*   **Comprehensive Data Entry:** Log essential flight details including Flight ID, Date, Vehicle, Mission Title, and detailed Notes.
*   **Log Locking:** Secure important records by "locking" them. Locked logs are protected from accidental deletion and automated cleanup processes.
*   **File Attachments:** Easily attach external flight log files and parameter files. The system automatically organizes these files into a managed directory structure.

### Preflight Checklist
*   **Dynamic & Customizable:** Create and manage a custom preflight checklist via the settings menu.
*   **Smart Validation:** Supports advanced validation rules (e.g., `value > 10` or `required`) using a secure AST-based evaluation engine to ensure operational safety.

### Vehicle Management
*   **Fleet Tracking:** Manage an unlimited fleet of vehicles.
*   **Archiving:** Archive retired vehicles to keep your active selection list clean while preserving historical flight data.

### Parameter Analysis
*   **Comparison Tool:** Compare current parameter files against historical records to track configuration changes over time.
*   **Ignore Patterns:** Define glob patterns (e.g., `STAT_*`, `BARO_*`) to filter out telemetry noise and focus on critical parameter shifts.

### Search & History
*   **Multi-Column Filtering:** Quickly find records by Date or Vehicle with real-time, debounced searching.
*   **Advanced Sorting:** Sort your flight history by any column (ID, Vehicle, Date, etc.) to organize your data effectively.

### Data Management & Portability
*   **Automated Cleanup:** Configure automatic log file pruning based on total storage size (GB) or file age (days) to manage disk space.
*   **Settings Portability:** Export and Import your entire configuration (Checklists, Vehicles, Ignore Patterns) via JSON for easy backup or synchronization across machines.
*   **Robust Storage:** Powered by a local SQLite database for reliability and high performance.

## 🛠️ Technical Stack
*   **Language:** Python 3.x
*   **UI Framework:** Tkinter (with High-DPI support and dynamic font scaling)
*   **Database:** SQLite 3
*   **Packaging:** PyInstaller

## ⚙️ Installation & Build

### Running from Source
1.  **Ensure Python 3.x is installed.**
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application:**
    ```bash
    python main.py
    ```

### Building the Executable
The project includes a comprehensive build pipeline that handles icon conversion and dependency packaging.

1.  **Run the build script:**
    ```bash
    python build.py
    ```
    *Or use the batch wrapper on Windows:*
    ```cmd
    compile.bat
    ```
2.  The standalone EXE will be located in the `dist/` folder.
