"""Database management for the Flight Manager application.

This module handles all SQLite database interactions, including table creation,
data insertion, querying, and schema migrations.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple


class DatabaseManager:
    """Manages the SQLite database connection and operations."""

    def __init__(self, db_name: str = "flight_log.db"):
        """Initializes the DatabaseManager.

        Args:
            db_name: The name of the database file.
        """
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def _column_exists(self, table: str, column: str) -> bool:
        """Checks if a column exists in a table using PRAGMA.
        
        Args:
            table: Table name.
            column: Column name.
            
        Returns:
            True if column exists, False otherwise.
        """
        cursor = self.conn.cursor()
        # PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns

    def create_tables(self):
        """Creates necessary tables and applies migrations safely."""
        cursor = self.conn.cursor()

        # 1. Main logs table (Base Schema)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_no TEXT NOT NULL,
                date TEXT NOT NULL,
                vehicle_name TEXT,
                mission_title TEXT,
                note TEXT,
                system_check TEXT,
                parameter_changes TEXT,
                log_file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 2. Migrations for 'logs' table
        # We check existence to avoid OperationalError or duplicate columns
        logs_cols = [
            ("vehicle_name", "TEXT"),
            ("log_file_path", "TEXT"),
            ("mission_title", "TEXT"),
            ("note", "TEXT")
        ]
        for col_name, col_type in logs_cols:
            if not self._column_exists("logs", col_name):
                cursor.execute(f"ALTER TABLE logs ADD COLUMN {col_name} {col_type}")

        # 3. Checklist configuration table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS checklist_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL UNIQUE,
                item_type TEXT DEFAULT 'checkbox',
                options TEXT,
                validation_rule TEXT,
                order_index INTEGER DEFAULT 0
            )
        """
        )
        
        # Migrations for 'checklist_config'
        checklist_cols = [
            ("order_index", "INTEGER DEFAULT 0"),
            ("validation_rule", "TEXT")
        ]
        for col_name, col_def in checklist_cols:
            if not self._column_exists("checklist_config", col_name):
                cursor.execute(f"ALTER TABLE checklist_config ADD COLUMN {col_name} {col_def}")

        # 4. Vehicles table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_archived INTEGER DEFAULT 0
            )
        """
        )
        
        # Migrations for 'vehicles'
        if not self._column_exists("vehicles", "is_archived"):
            cursor.execute("ALTER TABLE vehicles ADD COLUMN is_archived INTEGER DEFAULT 0")

        # 5. Ignore Patterns table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ignore_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL UNIQUE
            )
        """
        )

        # 6. Settings table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        self.conn.commit()
        self.seed_defaults()

    def seed_defaults(self):
        """Seeds the database with default values if tables are empty."""
        cursor = self.conn.cursor()

        # Default Font Size
        cursor.execute("SELECT COUNT(*) FROM settings WHERE key = 'font_size'")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)", ("font_size", "10")
            )
        
        # Default Feature Settings
        feature_defaults = [
            ("enable_edit_log", "1"),
            ("enable_delete_log", "1"),
            ("enable_update_params", "1"),
            ("enable_update_log_file", "1"),
            ("log_max_size_gb", "0"),
            ("log_retention_days", "0"),
        ]
        for key, val in feature_defaults:
            cursor.execute("SELECT COUNT(*) FROM settings WHERE key = ?", (key,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, val))

        # Default Vehicle
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO vehicles (name) VALUES (?)", ("Default Drone",)
            )

        # Default Checklist
        cursor.execute("SELECT COUNT(*) FROM checklist_config")
        if cursor.fetchone()[0] == 0:
            defaults = [
                ("Battery Charged", "checkbox", None, 0),
                ("Props Secure", "checkbox", None, 1),
                ("GPS Lock", "checkbox", None, 2),
                (
                    "Flight Mode",
                    "single_select",
                    "Stabilize,Loiter,Auto,RTL",
                    3,
                ),
                ("Voltage (V)", "text", None, 4),
            ]
            cursor.executemany(
                "INSERT INTO checklist_config "
                "(item_name, item_type, options, order_index) "
                "VALUES (?, ?, ?, ?)",
                defaults,
            )

        self.conn.commit()

    def close(self):
        """Closes the database connection."""
        self.conn.close()

    # --- Vehicles ---
    def get_vehicles(self, include_archived: bool = False) -> List[Any]:
        """Retrieves a list of vehicle names.

        Args:
            include_archived: Whether to include archived vehicles.

        Returns:
            A list of vehicle names or tuples (name, is_archived) if
            include_archived is True.
        """
        cursor = self.conn.cursor()
        if include_archived:
            cursor.execute(
                "SELECT name, is_archived FROM vehicles ORDER BY name"
            )
            return cursor.fetchall()
        else:
            cursor.execute(
                "SELECT name FROM vehicles WHERE is_archived = 0 ORDER BY name"
            )
            return [r[0] for r in cursor.fetchall()]

    def add_vehicle(self, name: str) -> bool:
        """Adds a new vehicle to the database.

        Args:
            name: The name of the vehicle.

        Returns:
            True if successful, False if the vehicle already exists.
        """
        try:
            self.conn.execute(
                "INSERT INTO vehicles (name, is_archived) VALUES (?, 0)",
                (name,),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def toggle_vehicle_archive(self, name: str) -> bool:
        """Toggles the archived status of a vehicle.

        Args:
            name: The name of the vehicle.

        Returns:
            True if the vehicle was found and updated, False otherwise.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT is_archived FROM vehicles WHERE name = ?", (name,)
        )
        res = cursor.fetchone()
        if res:
            new_state = 0 if res[0] else 1
            self.conn.execute(
                "UPDATE vehicles SET is_archived = ? WHERE name = ?",
                (new_state, name),
            )
            self.conn.commit()
            return True
        return False

    # --- Checklist ---
    def get_checklist_items(self) -> List[Tuple]:
        """Retrieves all checklist items.

        Returns:
            A list of tuples containing checklist item details.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT item_name, item_type, options, validation_rule, id, order_index "
            "FROM checklist_config ORDER BY order_index, id"
        )
        return cursor.fetchall()

    def add_checklist_item(
        self, name: str, item_type: str, options: Optional[str] = None, validation_rule: Optional[str] = None
    ) -> bool:
        """Adds a new item to the checklist configuration.

        Args:
            name: The name of the checklist item.
            item_type: The type of input (e.g., 'checkbox', 'text').
            options: Comma-separated options for 'single_select' types.
            validation_rule: Rule to validate the input (e.g., '>10', 'checked').

        Returns:
            True if successful, False if the item already exists.
        """
        try:
            c = self.conn.cursor()
            c.execute("SELECT MAX(order_index) FROM checklist_config")
            res = c.fetchone()[0]
            next_order = (res + 1) if res is not None else 0

            self.conn.execute(
                "INSERT INTO checklist_config "
                "(item_name, item_type, options, validation_rule, order_index) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, item_type, options, validation_rule, next_order),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_checklist_item(self, item_id: int):
        """Deletes a checklist item by ID.

        Args:
            item_id: The ID of the item to delete.
        """
        self.conn.execute(
            "DELETE FROM checklist_config WHERE id = ?", (item_id,)
        )
        self.conn.commit()

    def swap_checklist_order(self, id1: int, id2: int):
        """Swaps the order of two checklist items.

        Args:
            id1: The ID of the first item.
            id2: The ID of the second item.
        """
        c = self.conn.cursor()
        c.execute("SELECT order_index FROM checklist_config WHERE id=?", (id1,))
        o1 = c.fetchone()[0]
        c.execute("SELECT order_index FROM checklist_config WHERE id=?", (id2,))
        o2 = c.fetchone()[0]

        self.conn.execute(
            "UPDATE checklist_config SET order_index=? WHERE id=?", (o2, id1)
        )
        self.conn.execute(
            "UPDATE checklist_config SET order_index=? WHERE id=?", (o1, id2)
        )
        self.conn.commit()

    # --- Ignore Patterns ---
    def get_ignore_patterns(self) -> List[str]:
        """Retrieves all ignore patterns.

        Returns:
            A list of pattern strings.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT pattern FROM ignore_patterns ORDER BY pattern")
        return [r[0] for r in cursor.fetchall()]

    def add_ignore_pattern(self, pattern: str) -> bool:
        """Adds a new ignore pattern.

        Args:
            pattern: The pattern string to add.

        Returns:
            True if successful, False if the pattern already exists.
        """
        try:
            self.conn.execute(
                "INSERT INTO ignore_patterns (pattern) VALUES (?)", (pattern,)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_ignore_pattern(self, pattern: str):
        """Deletes an ignore pattern.

        Args:
            pattern: The pattern string to delete.
        """
        self.conn.execute(
            "DELETE FROM ignore_patterns WHERE pattern = ?", (pattern,)
        )
        self.conn.commit()

    # --- Settings ---
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves a setting value.

        Args:
            key: The setting key.
            default: The default value if the key is not found.

        Returns:
            The setting value.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        res = cursor.fetchone()
        return res[0] if res else default

    def set_setting(self, key: str, value: Any):
        """Sets a setting value.

        Args:
            key: The setting key.
            value: The setting value.
        """
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        self.conn.commit()

    # --- Logs ---
    def get_next_flight_id(self, date_str: str) -> int:
        """Calculates the next flight ID for a given date.

        Args:
            date_str: The date string (YYYY-MM-DD).

        Returns:
            The next available flight ID integer.
        """
        cursor = self.conn.cursor()
        # Use SQL aggregation to find the max flight_no.
        # We cast to INTEGER to handle cases where flight_no is stored as text.
        cursor.execute(
            "SELECT MAX(CAST(flight_no AS INTEGER)) FROM logs WHERE date = ?",
            (date_str,),
        )
        res = cursor.fetchone()[0]
        return (res if res is not None else 0) + 1

    def insert_log(self, data: Dict[str, Any]) -> bool:
        """Inserts a new flight log into the database.

        Args:
            data: A dictionary containing the log data. Keys must match column
              names.

        Returns:
            True if successful.

        Raises:
            Exception: If the insertion fails.
        """
        try:
            self.conn.execute(
                """
                INSERT INTO logs (
                    flight_no, date, vehicle_name, mission_title, note,
                    system_check, parameter_changes, log_file_path
                )
                VALUES (
                    :flight_no, :date, :vehicle_name, :mission_title, :note,
                    :system_check, :parameter_changes, :log_file_path
                )
                """,
                data,
            )
            self.conn.commit()
            return True
        except Exception as e:
            raise e

    def update_log(self, log_id: int, data: Dict[str, Any]) -> bool:
        """Updates an existing flight log in the database.

        Args:
            log_id: The ID of the log to update.
            data: A dictionary containing the updated log data.

        Returns:
            True if successful.

        Raises:
            Exception: If the update fails.
        """
        try:
            query = """
                UPDATE logs SET
                    flight_no = :flight_no,
                    date = :date,
                    vehicle_name = :vehicle_name,
                    mission_title = :mission_title,
                    note = :note,
                    system_check = :system_check,
                    parameter_changes = :parameter_changes,
                    log_file_path = :log_file_path
                WHERE id = :id
            """
            data["id"] = log_id
            self.conn.execute(query, data)
            self.conn.commit()
            return True
        except Exception as e:
            raise e

    def delete_log(self, log_id: int) -> bool:
        """Deletes a flight log from the database.

        Args:
            log_id: The ID of the log to delete.

        Returns:
            True if successful.
        """
        try:
            self.conn.execute("DELETE FROM logs WHERE id = ?", (log_id,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_logs(
        self,
        filter_id: Optional[str] = None,
        filter_date: Optional[str] = None,
        filter_vehicle: Optional[str] = None,
        sort_col: str = "id",
        sort_desc: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Tuple]:
        """Retrieves logs based on filters and pagination.

        Args:
            filter_id: Optional flight ID to filter by.
            filter_date: Optional date to filter by.
            filter_vehicle: Optional vehicle name to filter by.
            sort_col: Column to sort by.
            sort_desc: Whether to sort descending.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            A list of tuples representing the logs.
        """
        query = (
            "SELECT id, flight_no, date, vehicle_name, system_check, "
            "mission_title, parameter_changes, log_file_path, note "
            "FROM logs WHERE 1=1"
        )
        params = []

        if filter_id:
            query += " AND flight_no LIKE ?"
            params.append(f"%{filter_id}%")
        if filter_date:
            query += " AND date LIKE ?"
            params.append(f"%{filter_date}%")
        if filter_vehicle and filter_vehicle != "All":
            query += " AND vehicle_name = ?"
            params.append(filter_vehicle)

        order = "DESC" if sort_desc else "ASC"
        allowed_sort = [
            "id",
            "flight_no",
            "date",
            "vehicle_name",
            "system_check",
            "mission_title",
            "note",
        ]
        if sort_col not in allowed_sort:
            sort_col = "id"

        query += f" ORDER BY {sort_col} {order}"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def get_logs_count(
        self,
        filter_id: Optional[str] = None,
        filter_date: Optional[str] = None,
        filter_vehicle: Optional[str] = None,
    ) -> int:
        """Counts total logs matching the filters.

        Args:
            filter_id: Optional flight ID to filter by.
            filter_date: Optional date to filter by.
            filter_vehicle: Optional vehicle name to filter by.

        Returns:
            The total number of matching logs.
        """
        query = "SELECT COUNT(*) FROM logs WHERE 1=1"
        params = []

        if filter_id:
            query += " AND flight_no LIKE ?"
            params.append(f"%{filter_id}%")
        if filter_date:
            query += " AND date LIKE ?"
            params.append(f"%{filter_date}%")
        if filter_vehicle and filter_vehicle != "All":
            query += " AND vehicle_name = ?"
            params.append(filter_vehicle)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()[0]

    def get_log_by_id(self, log_id: int) -> Optional[Tuple]:
        """Retrieves a single log by its ID.

        Args:
            log_id: The ID of the log.

        Returns:
            A tuple containing the log details, or None if not found.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT flight_no, date, vehicle_name, system_check, "
            "parameter_changes, log_file_path, mission_title, note "
            "FROM logs WHERE id = ?",
            (log_id,),
        )
        return cursor.fetchone()

    def get_log_history_for_vehicle(self, vehicle_name: str) -> List[Tuple]:
        """Retrieves log history for a specific vehicle.

        Args:
            vehicle_name: The name of the vehicle.

        Returns:
            A list of tuples (id, date, flight_no, parameter_changes).
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, date, flight_no, parameter_changes "
            "FROM logs WHERE vehicle_name = ? ORDER BY id DESC",
            (vehicle_name,),
        )
        return cursor.fetchall()

    # --- Import / Export ---
    def get_all_settings(self) -> Dict[str, Any]:
        """Retrieves all application settings.

        Returns:
            A dictionary containing vehicles, checklist, and ignore_patterns.
        """
        cursor = self.conn.cursor()
        settings = {}

        # Vehicles
        cursor.execute("SELECT name, is_archived FROM vehicles")
        settings["vehicles"] = [
            {"name": r[0], "is_archived": r[1]} for r in cursor.fetchall()
        ]

        # Checklist
        cursor.execute(
            "SELECT item_name, item_type, options, validation_rule, order_index FROM checklist_config"
        )
        settings["checklist"] = [
            {
                "item_name": r[0],
                "item_type": r[1],
                "options": r[2],
                "validation_rule": r[3],
                "order_index": r[4],
            }
            for r in cursor.fetchall()
        ]

        # Ignore Patterns
        cursor.execute("SELECT pattern FROM ignore_patterns")
        settings["ignore_patterns"] = [r[0] for r in cursor.fetchall()]

        return settings

    def import_settings(self, settings: Dict[str, Any]) -> bool:
        """Imports settings from a dictionary.

        Args:
            settings: The dictionary containing settings to import.

        Returns:
            True if successful.

        Raises:
            Exception: If the import fails.
        """
        cursor = self.conn.cursor()
        try:
            # Vehicles
            if "vehicles" in settings:
                for v in settings["vehicles"]:
                    try:
                        cursor.execute(
                            "INSERT OR IGNORE INTO vehicles "
                            "(name, is_archived) VALUES (?, ?)",
                            (v["name"], v.get("is_archived", 0)),
                        )
                    except Exception:
                        pass

            # Checklist (Upsert)
            if "checklist" in settings:
                for c in settings["checklist"]:
                    try:
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO checklist_config
                            (item_name, item_type, options, validation_rule, order_index)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                c["item_name"],
                                c["item_type"],
                                c["options"],
                                c.get("validation_rule"),
                                c["order_index"],
                            ),
                        )
                    except Exception:
                        pass

            # Ignore Patterns
            if "ignore_patterns" in settings:
                for p in settings["ignore_patterns"]:
                    try:
                        cursor.execute(
                            "INSERT OR IGNORE INTO ignore_patterns "
                            "(pattern) VALUES (?)",
                            (p,),
                        )
                    except Exception:
                        pass

            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            raise e