ROLE_PERMISSIONS = {
    "candidate": [
        "view_combined_results",
        "view_practice_plans",
        "view_practice_tasks",
        "view_qna_results"
    ],
    "coach": [
        "all_view_combined_results",
        "all_view_practice_plans",
        "all_view_practice_tasks",
        "all_view_qna_results",
        "approve_practice_plans"
    ],
    "admin": ["all"]
}


def user_can(role: str, permission: str) -> bool:
    if "all" in ROLE_PERMISSIONS.get(role, []):
        return True
    return permission in ROLE_PERMISSIONS.get(role, [])