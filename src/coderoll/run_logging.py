from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import traceback
from typing import Any


class RunStage(str, Enum):
    CREATING_SANDBOX = "creating_sandbox"
    EXECUTING_SANDBOX = "executing_sandbox"
    SANDBOX_EXECUTION_COMPLETE = "sandbox_execution_complete"
    RANKING_RESULTS = "ranking_results"
    EXPORTING_RESULTS = "exporting_results"
    DONE = "done"
    FAILED = "failed"


@dataclass
class RunEvent:
    ts: str
    level: str
    stage: str
    message: str
    run_id: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "level": self.level,
            "stage": self.stage,
            "message": self.message,
            "run_id": self.run_id,
            "data": self.data,
        }


class EventLogger:
    def __init__(self, run_dir: Path, run_id: str) -> None:
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.run_dir / "events.jsonl"

    def emit(self, stage: RunStage, message: str, level: str = "info", **data: Any) -> None:
        event = RunEvent(
            ts=datetime.now(timezone.utc).isoformat(),
            level=level,
            stage=stage.value,
            message=message,
            run_id=self.run_id,
            data=dict(data),
        )
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False, default=str))
            handle.write("\n")
            handle.flush()


class StageReporter:
    def __init__(self, logger: EventLogger, total_steps: int = 5) -> None:
        self.logger = logger
        self.total_steps = total_steps
        self._printed_step = False

    def step(self, index: int, stage: RunStage, message: str, **data: Any) -> None:
        rendered = message
        if stage != RunStage.SANDBOX_EXECUTION_COMPLETE and not rendered.endswith("..."):
            rendered = f"{rendered}..."
        print(f"[{index}/{self.total_steps}] {rendered}")
        self._printed_step = True
        self.logger.emit(stage=stage, message=message, level="info", **data)

    def done(self) -> None:
        if self._printed_step:
            print()
        print("DONE")
        self.logger.emit(stage=RunStage.DONE, message="Run complete", level="info")

    def failed(self, message: str, exc: BaseException | None = None) -> None:
        print(f"FAILED: {message}")
        data: dict[str, Any] = {}
        if exc is not None:
            data["error_type"] = type(exc).__name__
            data["error"] = str(exc)
            data["traceback"] = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self.logger.emit(stage=RunStage.FAILED, message=message, level="error", **data)
