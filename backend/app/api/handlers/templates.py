# ruff: noqa: F401,F403,F405
from app.api.handlers.support import *  # noqa: F403


async def list_templates(current_user: dict = Depends(get_current_user)) -> dict[str, list[dict[str, object]]]:
    _ = current_user
    return {
        "templates": [
            {"value": key, "label": key.replace("_", " ").title(), "fields": value["fields"]}
            for key, value in FORM_TEMPLATES.items()
        ]
    }
