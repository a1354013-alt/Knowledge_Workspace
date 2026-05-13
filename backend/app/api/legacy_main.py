# ruff: noqa: F403,I001
from __future__ import annotations

import sys
from types import ModuleType

from app.api.handlers import docs, items, knowledge, logbook, photos, prompts, qa, search, support, system, templates
from app.api.handlers.support import *  # noqa: F403
from app.api.handlers.search import *  # noqa: F403
from app.api.handlers.system import *  # noqa: F403
from app.api.handlers.docs import *  # noqa: F403
from app.api.handlers.knowledge import *  # noqa: F403
from app.api.handlers.logbook import *  # noqa: F403
from app.api.handlers.photos import *  # noqa: F403
from app.api.handlers.items import *  # noqa: F403
from app.api.handlers.qa import *  # noqa: F403
from app.api.handlers.prompts import *  # noqa: F403
from app.api.handlers.templates import *  # noqa: F403

_PATCH_TARGETS = (support, search, system, docs, knowledge, logbook, photos, items, qa, prompts, templates)


class _LegacyMainModule(ModuleType):
    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for module in _PATCH_TARGETS:
            if hasattr(module, name):
                setattr(module, name, value)


sys.modules[__name__].__class__ = _LegacyMainModule
