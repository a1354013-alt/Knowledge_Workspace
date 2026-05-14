from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.autotest.detector import autotest_commands, autotest_step_should_run


@dataclass(frozen=True)
class PlannedStep:
    name: str
    argv: list[str]
    command: str
    should_run: bool
    skip_reason: str
    uses_real_execution: bool


def build_execution_plan(
    *,
    project_type_detected: str,
    working_dir: Path,
    execution_mode: str,
) -> list[PlannedStep]:
    uses_real_execution = execution_mode == "real" and project_type_detected in {"node", "python"}
    planned_steps: list[PlannedStep] = []
    for name, argv in autotest_commands(project_type_detected).items():
        should_run = True
        skip_reason = ""
        if uses_real_execution:
            should_run, skip_reason = autotest_step_should_run(
                project_type=project_type_detected,
                working_dir=working_dir,
                step_name=name,
            )
        planned_steps.append(
            PlannedStep(
                name=name,
                argv=list(argv),
                command=" ".join(argv),
                should_run=should_run,
                skip_reason=skip_reason,
                uses_real_execution=uses_real_execution,
            )
        )
    return planned_steps
