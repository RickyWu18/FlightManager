# Flight Manager Logger

**Flight Manager Logger** is a desktop application designed to streamline flight data logging, vehicle management, and parameter tracking for drone operations.

## 🚀 Key Features

### Flight Logging
*   **Comprehensive Data Entry:** Log essential flight details including Flight ID, Date, Vehicle, Mission Title, and detailed Notes.
*   **File Attachments:** Easily attach external flight log files and parameter files to your records.
*   **Preflight Checklist:** Integrated, customizable preflight checklist to ensure operational safety before every flight.

### Vehicle Management
*   **Fleet Tracking:** Manage a fleet of vehicles with ease.
*   **Archiving:** Archive old or inactive vehicles to keep your active list clean.

### Parameter Analysis
*   **Comparison Tool:** Compare parameter files against previous logs or specific vehicles to track configuration changes over time.
*   **Ignore Patterns:** Configure specific patterns to ignore during parameter comparison to focus on relevant changes.

### Search & History
*   **Filtering:** Filter flight history by Flight ID, Date, and Vehicle to quickly find past records.
*   **Pagination:** Efficient pagination support for browsing through large log databases.

### Data Management
*   **Settings Portability:** Export and Import application settings (Checklists, Vehicles, Ignore Patterns) via JSON.
*   **Robust Storage:** Uses a local SQLite database (`flight_log.db`) for reliable and self-contained data storage.

## 🛠️ Build & Installation

### Running from Source
1.  Ensure you have Python 3.x installed.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```bash
    python main.py
    ```

### Building the Executable
To build a standalone Windows executable:

1.  Run the compile script:
    ```bat
    compile.bat
    ```
    *   This will create a virtual environment, install dependencies, and build the EXE.
    *   The output file will be located in the `dist/` folder, named `FlightManager-<version>.exe`.
