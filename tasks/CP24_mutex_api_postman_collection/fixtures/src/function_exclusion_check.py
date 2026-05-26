"""Function exclusion check API endpoint."""
from flask import Blueprint, request, jsonify
from .function_exclusion_check_svc import FunctionExclusionService

bp = Blueprint('function_exclusion', __name__, url_prefix='/api/v1/function-exclusion')


@bp.route('/check', methods=['POST'])
def check_exclusion():
    """Check if given function codes have mutual exclusion conflicts.

    Request body:
        {"function_codes": ["CODE1", "CODE2", ...]}

    Returns:
        200: {"result": "pass", "conflicts": []}
        200: {"result": "conflict", "conflicts": [{"group": [...], "matched": [...]}]}
        400: {"error": "function_codes is required and must be non-empty list"}
    """
    data = request.get_json(force=True)
    function_codes = data.get('function_codes')

    if not function_codes or not isinstance(function_codes, list) or len(function_codes) == 0:
        return jsonify({"error": "function_codes is required and must be non-empty list"}), 400

    svc = FunctionExclusionService()
    result = svc.check(function_codes)
    return jsonify(result), 200
