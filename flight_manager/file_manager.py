"""File management utilities for the Flight Manager application.

This module handles file system operations such as copying log files
and managing directory structures.
"""

import os
import shutil
import re
import datetime
import time
from typing import List


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

    def cleanup_logs(self, max_size_gb: float = 0, retention_days: int = 0, excluded_paths: List[str] = None) -> int:
        """Cleans up old log files based on size and age constraints.

        Args:
            max_size_gb: Maximum total size of logs in GB (0 for unlimited).
            retention_days: Maximum age of logs in days (0 for unlimited).
            excluded_paths: List of file paths to never delete (e.g. locked logs).

        Returns:
            The number of files deleted.
        """
        if not os.path.exists(self.base_dir):
            return 0

        excluded_paths = {os.path.abspath(p) for p in (excluded_paths or [])}
        deleted_count = 0
        files = []

        # 1. Gather file info with error handling
        try:
            dir_list = os.listdir(self.base_dir)
        except OSError:
            return 0

        for f in dir_list:
            full_path = os.path.abspath(os.path.join(self.base_dir, f))
            if os.path.isfile(full_path):
                if full_path in excluded_paths:
                    continue
                try:
                    stats = os.stat(full_path)
                    files.append({
                        "path": full_path,
                        "name": f,
                        "size": stats.st_size,
                        "mtime": stats.st_mtime
                    })
                except OSError:
                    # Skip files that are inaccessible or locked during stat
                    continue

        def try_remove(file_info):
            nonlocal deleted_count
            try:
                # On Windows, this will fail if the file is opened by another process
                os.remove(file_info["path"])
                deleted_count += 1
                return True
            except (PermissionError, OSError):
                # File might be locked or permission denied
                return False

        # 2. Date-based Cleanup
        if retention_days > 0:
            cutoff_date = datetime.date.today() - datetime.timedelta(days=retention_days)
            remaining_files = []
            
            for file_info in files:
                should_delete = False
                
                try:
                    date_part = file_info["name"].split("_")[0]
                    file_date = datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
                    if file_date < cutoff_date:
                        should_delete = True
                except (ValueError, IndexError):
                    file_date = datetime.date.fromtimestamp(file_info["mtime"])
                    if file_date < cutoff_date:
                        should_delete = True

                if should_delete:
                    if not try_remove(file_info):
                        remaining_files.append(file_info)
                else:
                    remaining_files.append(file_info)
            
            files = remaining_files

        # 3. Size-based Cleanup
        if max_size_gb > 0:
            max_size_bytes = max_size_gb * 1024 * 1024 * 1024
            total_size = sum(f["size"] for f in files)

            if total_size > max_size_bytes:
                # Sort by mtime (oldest first)
                files.sort(key=lambda x: x["mtime"])

                for file_info in files:
                    if total_size <= max_size_bytes:
                        break
                    
                    if try_remove(file_info):
                        total_size -= file_info["size"]

        return deleted_count