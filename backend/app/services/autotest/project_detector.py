from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.services.autotest.archive import sanitize_path_for_report
from app.services.autotest.detector import find_project_root_on_disk


@dataclass(frozen=True)
class DetectedProject:
    project_type_detected: str
    working_dir: Path
    working_dir_rel: str
    project_name: str


def detect_project(
    *,
    extracted_dir: Path,
    fallback_project_name: str,
    root_finder: Callable[[Path], tuple[str, Path]] = find_project_root_on_disk,
) -> DetectedProject:
    project_type_detected, working_dir = root_finder(extracted_dir)
    return DetectedProject(
        project_type_detected=project_type_detected,
        working_dir=working_dir,
        working_dir_rel=sanitize_path_for_report(working_dir, base_dir=extracted_dir),
        project_name=working_dir.name or fallback_project_name,
    )
