"""Service layer for Flight Manager business logic.

This module handles data validation, processing, and preparation, decoupling
logic from the UI code.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from flight_manager.utils import validate_checklist_rule

class LogService:
    """Service for handling flight log operations."""

    @staticmethod
    def validate_log_entry(
        flight_no: str,
        date: str,
        vehicle: str,
        checklist_items: Dict[str, Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """Validates log entry data.

        Args:
            flight_no: The flight ID.
            date: The flight date.
            vehicle: The vehicle name.
            checklist_items: Dictionary of checklist widget data.

        Returns:
            A tuple (is_valid, error_messages_list).
        """
        errors = []
        if not flight_no:
            errors.append("Flight ID is required.")
        if not vehicle:
            errors.append("Vehicle selection is required.")
        if not date:
            errors.append("Date is required.")

        # Validate Checklist Rules
        for name, data in checklist_items.items():
            rule = data.get("rule")
            val = data.get("value")
            
            if rule:
                is_valid, err_msg = validate_checklist_rule(val, rule)
                if not is_valid:
                    errors.append(f"Checklist '{name}': {err_msg}")

        return len(errors) == 0, errors

    @staticmethod
    def prepare_log_payload(
        flight_no: str,
        date: str,
        vehicle: str,
        mission: str,
        note: str,
        checklist_items: Dict[str, Dict[str, Any]],
        param_content: str,
        log_file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Constructs the dictionary payload for database insertion.

        Args:
            flight_no: Flight ID.
            date: Date string.
            vehicle: Vehicle name.
            mission: Mission title.
            note: Note text.
            checklist_items: Dictionary of checklist data from UI.
            param_content: Content of the parameter file.
            log_file_path: Path to the saved log file (optional).

        Returns:
            A dictionary ready for DB insertion.
        """
        # Serialize Checklist
        checklist_data = []
        for name, data in checklist_items.items():
            checklist_data.append({
                "name": name,
                "type": data["type"],
                "value": data["value"]
            })
        
        system_check_json = json.dumps(checklist_data)

        return {
            "flight_no": flight_no,
            "date": date,
            "vehicle_name": vehicle,
            "mission_title": mission,
            "note": note,
            "system_check": system_check_json,
            "parameter_changes": param_content,
            "log_file_path": log_file_path,
        }
