from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from clogger.enums import Region, TaskDifficulty


@dataclass
class LeagueTask:
    id: int
    name: str
    description: str
    difficulty: TaskDifficulty
    region: Region | None

    @property
    def points(self) -> int:
        return self.difficulty.points
