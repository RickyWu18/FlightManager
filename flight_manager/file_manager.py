"""File management utilities for the Flight Manager application.

This module handles file system operations such as copying log files
and managing directory structures.
"""

import os
import shutil
import re


class FileManager:
    """Manages file operations for flight logs."""

    def __init__(self, base_dir: str = "captured_logs"):
        """Initializes the FileManager.

        Args:
            base_dir: The directory where logs will be saved.
        """
        self.base_dir = base_dir

    def save_log_file(
        self, source_path: str, date_str: str, vehicle_name: str, flight_id: str
    ) -> str:
        """Copies a log file to the captured_logs directory with a standard name.

        Args:
            source_path: Path to the source log file.
            date_str: Date of the flight (YYYY-MM-DD).
            vehicle_name: Name of the vehicle.
            flight_id: ID of the flight.

        Returns:
            The absolute path to the saved file.

        Raises:
            IOError: If the file copy fails.
        """
        if not source_path or not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")

        os.makedirs(self.base_dir, exist_ok=True)

        # Sanitize filename components (Robust)
        # Replace Windows/Unix reserved chars: < > : " / \ | ? *
        # Also handle control characters if any
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        
        safe_vehicle = re.sub(invalid_chars, "_", vehicle_name).strip()
        safe_date = re.sub(invalid_chars, "_", date_str).strip()
        safe_id = re.sub(invalid_chars, "_", str(flight_id)).strip()
        
        orig_filename = os.path.basename(source_path)
        safe_orig = re.sub(invalid_chars, "_", orig_filename)
        
        new_filename = f"{safe_date}_{safe_vehicle}_{safe_id}_{safe_orig}"

        dest_path = os.path.join(self.base_dir, new_filename)
        shutil.copy2(source_path, dest_path)

        return dest_path