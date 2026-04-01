from dataclasses import dataclass


@dataclass
class ItemRequirement:
    id: int
    item_id: int
    quantity: int
