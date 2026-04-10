from dataclasses import dataclass

from ragger.enums import Skill, SKILL_LABELS


@dataclass
class ExperienceReward:
    id: int
    eligible_skills: int
    amount: int

    def asdict(self) -> dict:
        skills = [SKILL_LABELS[s] for s in Skill if self.eligible_skills & s.mask]
        return {"skills": skills, "amount": self.amount}


@dataclass
class ItemReward:
    id: int
    item_id: int
    quantity: int

    def asdict(self) -> dict:
        return {"item_id": self.item_id, "quantity": self.quantity}
