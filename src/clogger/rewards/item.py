from dataclasses import dataclass


@dataclass
class ItemReward:
    id: int
    item_id: int
    quantity: int
