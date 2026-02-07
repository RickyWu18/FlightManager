"""Utility functions for parameter parsing and comparison."""

import ast
import fnmatch
import operator as op_lib
from typing import Any, Dict, List, Optional, Tuple

# Security-safe operators mapping for AST evaluation
SAFE_OPERATORS = {
    ast.Add: op_lib.add,
    ast.Sub: op_lib.sub,
    ast.Mult: op_lib.mul,
    ast.Div: op_lib.truediv,
    ast.Mod: op_lib.mod,
    ast.Pow: op_lib.pow,
    ast.USub: op_lib.neg,
    ast.UAdd: op_lib.pos,
    ast.Gt: op_lib.gt,
    ast.Lt: op_lib.lt,
    ast.GtE: op_lib.ge,
    ast.LtE: op_lib.le,
    ast.Eq: op_lib.eq,
    ast.NotEq: op_lib.ne,
}

def _safe_eval(node, variables):
    """Recursively evaluates an AST node safely."""
    if isinstance(node, ast.Constant): # Python 3.8+
        return node.value
    elif hasattr(ast, 'Num') and isinstance(node, ast.Constant): # Pre-3.8
        return node.n
    elif hasattr(ast, 'Str') and isinstance(node, ast.Constant): # Pre-3.8
        return node.s
    elif hasattr(ast, 'NameConstant') and isinstance(node, ast.Constant): # Pre-3.8
        return node.value
    elif isinstance(node, ast.BinOp):
        return SAFE_OPERATORS[type(node.op)](_safe_eval(node.left, variables), _safe_eval(node.right, variables))
    elif isinstance(node, ast.UnaryOp):
        return SAFE_OPERATORS[type(node.op)](_safe_eval(node.operand, variables))
    elif isinstance(node, ast.Compare):
        left = _safe_eval(node.left, variables)
        for op, right_node in zip(node.ops, node.comparators):
            right = _safe_eval(right_node, variables)
            if not SAFE_OPERATORS[type(op)](left, right):
                return False
            left = right
        return True
    elif isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        raise ValueError(f"Unknown variable: {node.id}")
    elif isinstance(node, ast.Expression):
        return _safe_eval(node.body, variables)
    else:
        raise TypeError(f"Unsupported operation: {type(node).__name__}")

def validate_checklist_rule(value: Any, rule_str: str) -> Tuple[bool, str]:
    """Validates a value against a rule string expression securely.

    Supports mathematical expressions (e.g., 'value/2 > 3.9') and keywords.
    Uses AST-based safe evaluation instead of unsafe eval().

    Args:
        value: The value to validate (string, float, bool).
        rule_str: The rule string (e.g., "value > 10, required").

    Returns:
        A tuple (is_valid, error_message).
    """
    if not rule_str:
        return True, ""

    # Normalize value for comparison
    val_str = str(value).strip() if value is not None else ""
    eval_value = value
    if not isinstance(value, bool):
        try:
            eval_value = float(val_str)
        except ValueError:
            eval_value = val_str

    val_bool = value if isinstance(value, bool) else (val_str.lower() == "true")
    context = {"value": eval_value, "True": True, "False": False, "None": None}

    rules = [r.strip() for r in rule_str.split(",")]

    for rule in rules:
        if not rule:
            continue

        rule_lower = rule.lower()

        # 1. Keywords (Shorthand)
        if rule_lower == "required":
            if not val_str:
                return False, "Required"
            continue
        if rule_lower == "checked":
            if not val_bool:
                return False, "Must be checked"
            continue
        if rule_lower == "unchecked":
            if val_bool:
                return False, "Must be unchecked"
            continue

        # 2. Expression Evaluation
        expr = rule
        # Support shorthand like "> 10" by prepending "value"
        if expr.strip().startswith((">","<","=","!")):
            expr = "value " + expr

        try:
            tree = ast.parse(expr, mode='eval')
            result = _safe_eval(tree, context)
            if not result:
                return False, f"Condition failed: {rule}"
        except Exception as e:
            return False, f"Error processing rule '{rule}': {e}"

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