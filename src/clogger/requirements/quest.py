from dataclasses import dataclass


@dataclass
class QuestRequirement:
    id: int
    task_id: int
    quest_id: int
    partial: bool
