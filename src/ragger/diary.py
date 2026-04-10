from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ragger.enums import DiaryLocation, DiaryTier
from ragger.mcp_registry import mcp_tool
from ragger.requirements import RequirementGroup


@dataclass
class DiaryTask:
    id: int
    location: DiaryLocation
    tier: DiaryTier
    description: str

    def asdict(self) -> dict:
        return {
            "id": self.id,
            "location": self.location.value,
            "tier": self.tier.value,
            "description": self.description,
        }

    def requirement_groups(self, conn: sqlite3.Connection) -> list[RequirementGroup]:
        return RequirementGroup.for_diary_task(conn, self.id)

    @classmethod
    @mcp_tool(name="DiaryTaskAll", description="List achievement diary tasks, optionally filtered by location (ARDOUGNE, DESERT, FALADOR, FREMENNIK, KANDARIN, KARAMJA, KOUREND_AND_KEBOS, LUMBRIDGE_AND_DRAYNOR, MORYTANIA, VARROCK, WESTERN_PROVINCES, WILDERNESS) and tier (EASY, MEDIUM, HARD, ELITE).")
    def all(
        cls,
        conn: sqlite3.Connection,
        location: DiaryLocation | None = None,
        tier: DiaryTier | None = None,
    ) -> list[DiaryTask]:
        query = "SELECT id, location, tier, description FROM diary_tasks"
        params: list = []
        conditions: list[str] = []

        if location is not None:
            conditions.append("location = ?")
            params.append(location.value)
        if tier is not None:
            conditions.append("tier = ?")
            params.append(tier.value)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY location, tier, id"

        rows = conn.execute(query, params).fetchall()
        return [cls(row[0], DiaryLocation(row[1]), DiaryTier(row[2]), row[3]) for row in rows]
