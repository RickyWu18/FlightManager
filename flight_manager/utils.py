"""Utility functions for parameter parsing and comparison.

This module provides functions to parse parameter files, filter them based on
ignore patterns, and compare two sets of parameters to identify additions,
removals, and changes.
"""

import fnmatch
import math
from typing import Any, Dict, List, Optional, Tuple


def validate_checklist_rule(value: Any, rule_str: str) -> Tuple[bool, str]:
    """Validates a value against a rule string expression.

    Supports simple Python expressions where 'value' is the variable.
    Multiple rules can be separated by commas.

    Args:
        value: The value to validate (string, float, bool).
        rule_str: The rule string (e.g., "value > 10, value < 20").

    Returns:
        A tuple (is_valid, error_message).
    """
    if not rule_str:
        return True, ""

    # Prepare Context
    # Try to convert string input to float if possible for numeric comparisons
    eval_value = value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            # Empty string handling depends on rule logic, but usually fails numeric rules
            eval_value = "" 
        else:
            try:
                eval_value = float(value)
            except ValueError:
                eval_value = value
    
    # Context for eval
    context = {
        "value": eval_value,
        "math": math,
        "true": True,
        "false": False,
        "len": len,
        "str": str,
        "int": int,
        "float": float,
    }

    # Split by comma to support multiple rules
    # Basic split, assumes no commas in string literals within rules
    rules = [r.strip() for r in rule_str.split(",")]

    for rule in rules:
        if not rule:
            continue
        
        # Backward Compatibility / Short-hand syntax
        expr = rule
        if rule.lower() == "checked":
            expr = "value == True"
        elif rule.lower() == "unchecked":
            expr = "value == False"
        elif rule.lower() == "required":
            expr = "bool(str(value))" # Check for non-empty string
        elif rule.startswith(">") and rule[1:].strip().replace('.', '', 1).isdigit():
            # Support ">10" style
            expr = f"value > {rule[1:]}"
        elif rule.startswith("<") and rule[1:].strip().replace('.', '', 1).isdigit():
            expr = f"value < {rule[1:]}"
            
        try:
            # Restricted eval
            result = eval(expr, {"__builtins__": None}, context)
            if not result:
                return False, f"Rule failed: {rule}"
        except Exception as e:
            # If evaluation crashes (e.g. comparing str > int), it's a fail
            return False, f"Error evaluating rule '{rule}': {e}"

    return True, ""


def parse_params(content: str) -> Dict[str, str]:
    """Parses a string content into a dictionary of parameters.

    Supports '=' and ',' delimiters. Ignores lines starting with # or //.

    Args:
        content: The string content of the parameter file.

    Returns:
        A dictionary where keys are parameter names and values are their values.
    """
    params = {}
    if not content:
        return params

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        parts = []
        if "=" in line:
            parts = line.split("=", 1)
        elif "," in line:
            parts = line.split(",", 1)
        else:
            parts = line.split(None, 1)

        if len(parts) == 2:
            key = parts[0].strip()
            val = parts[1].strip()
            params[key] = val
    return params


def filter_params(
    params: Dict[str, str], ignore_patterns: Optional[List[str]]
) -> Dict[str, str]:
    """Filters a dictionary of parameters based on a list of glob patterns.

    Args:
        params: The dictionary of parameters to filter.
        ignore_patterns: A list of glob patterns to ignore (e.g., "PID_*").

    Returns:
        A new dictionary containing only the parameters that do not match any
        ignore pattern.
    """
    if not ignore_patterns:
        return params

    filtered = {}
    for key, value in params.items():
        ignored = False
        for pat in ignore_patterns:
            if fnmatch.fnmatch(key, pat):
                ignored = True
                break
        if not ignored:
            filtered[key] = value
    return filtered


def compare_params(
    current_content: str,
    ref_content: str,
    ignore_patterns: Optional[List[str]] = None,
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, Tuple[str, str]]]:
    """Compares two parameter strings and returns differences.

    Args:
        current_content: The content of the current parameter set.
        ref_content: The content of the reference parameter set.
        ignore_patterns: A list of patterns to ignore during comparison.

    Returns:
        A tuple containing three dictionaries:
        - added: Parameters present in current but not reference.
        - removed: Parameters present in reference but not current.
        - changed: Parameters present in both but with different values,
          mapping key to (old_value, new_value).
    """
    curr_dict = parse_params(current_content)
    ref_dict = parse_params(ref_content)

    curr_dict = filter_params(curr_dict, ignore_patterns or [])
    ref_dict = filter_params(ref_dict, ignore_patterns or [])

    added = {k: curr_dict[k] for k in curr_dict if k not in ref_dict}
    removed = {k: ref_dict[k] for k in ref_dict if k not in curr_dict}
    changed = {
        k: (ref_dict[k], curr_dict[k])
        for k in curr_dict
        if k in ref_dict and curr_dict[k] != ref_dict[k]
    }

    return added, removed, changed
