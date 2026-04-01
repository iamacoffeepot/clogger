from enum import Enum


class Skill(int, Enum):
    ATTACK = 0
    STRENGTH = 1
    DEFENCE = 2
    RANGED = 3
    PRAYER = 4
    MAGIC = 5
    RUNECRAFT = 6
    CONSTRUCTION = 7
    HITPOINTS = 8
    AGILITY = 9
    HERBLORE = 10
    THIEVING = 11
    CRAFTING = 12
    FLETCHING = 13
    SLAYER = 14
    HUNTER = 15
    MINING = 16
    SMITHING = 17
    FISHING = 18
    COOKING = 19
    FIREMAKING = 20
    WOODCUTTING = 21
    FARMING = 22

    @property
    def label(self) -> str:
        return SKILL_LABELS[self]

    @property
    def mask(self) -> int:
        return 1 << self.value


SKILL_LABELS: dict["Skill", str] = {
    Skill.ATTACK: "Attack",
    Skill.STRENGTH: "Strength",
    Skill.DEFENCE: "Defence",
    Skill.RANGED: "Ranged",
    Skill.PRAYER: "Prayer",
    Skill.MAGIC: "Magic",
    Skill.RUNECRAFT: "Runecraft",
    Skill.CONSTRUCTION: "Construction",
    Skill.HITPOINTS: "Hitpoints",
    Skill.AGILITY: "Agility",
    Skill.HERBLORE: "Herblore",
    Skill.THIEVING: "Thieving",
    Skill.CRAFTING: "Crafting",
    Skill.FLETCHING: "Fletching",
    Skill.SLAYER: "Slayer",
    Skill.HUNTER: "Hunter",
    Skill.MINING: "Mining",
    Skill.SMITHING: "Smithing",
    Skill.FISHING: "Fishing",
    Skill.COOKING: "Cooking",
    Skill.FIREMAKING: "Firemaking",
    Skill.WOODCUTTING: "Woodcutting",
    Skill.FARMING: "Farming",
}

ALL_SKILLS_MASK = (1 << len(Skill)) - 1


class Region(int, Enum):
    ASGARNIA = 0
    DESERT = 1
    FREMENNIK = 2
    KANDARIN = 3
    KARAMJA = 4
    KOUREND = 5
    MISTHALIN = 6
    MORYTANIA = 7
    TIRANNWN = 8
    VARLAMORE = 9
    WILDERNESS = 10

    @property
    def label(self) -> str:
        return REGION_LABELS[self]

    @property
    def mask(self) -> int:
        return 1 << self.value


REGION_LABELS: dict["Region", str] = {
    Region.ASGARNIA: "Asgarnia",
    Region.DESERT: "Desert",
    Region.FREMENNIK: "Fremennik",
    Region.KANDARIN: "Kandarin",
    Region.KARAMJA: "Karamja",
    Region.KOUREND: "Kourend",
    Region.MISTHALIN: "Misthalin",
    Region.MORYTANIA: "Morytania",
    Region.TIRANNWN: "Tirannwn",
    Region.VARLAMORE: "Varlamore",
    Region.WILDERNESS: "Wilderness",
}

ALL_REGIONS_MASK = (1 << len(Region)) - 1


class DiaryLocation(str, Enum):
    ARDOUGNE = "Ardougne"
    DESERT = "Desert"
    FALADOR = "Falador"
    FREMENNIK = "Fremennik"
    KANDARIN = "Kandarin"
    KARAMJA = "Karamja"
    KOUREND_KEBOS = "Kourend & Kebos"
    LUMBRIDGE_DRAYNOR = "Lumbridge & Draynor"
    MORYTANIA = "Morytania"
    VARROCK = "Varrock"
    WESTERN_PROVINCES = "Western Provinces"
    WILDERNESS = "Wilderness"

    def xp_reward(self, tier: "DiaryTier") -> int:
        if self == DiaryLocation.KARAMJA:
            return _KARAMJA_DIARY_XP[tier]
        return _STANDARD_DIARY_XP[tier]

    def min_level(self, tier: "DiaryTier") -> int:
        if self == DiaryLocation.KARAMJA:
            return _KARAMJA_DIARY_MIN_LEVEL[tier]
        return _STANDARD_DIARY_MIN_LEVEL[tier]


class DiaryTier(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    ELITE = "Elite"


_STANDARD_DIARY_XP: dict[DiaryTier, int] = {
    DiaryTier.EASY: 2_500,
    DiaryTier.MEDIUM: 7_500,
    DiaryTier.HARD: 15_000,
    DiaryTier.ELITE: 50_000,
}

_KARAMJA_DIARY_XP: dict[DiaryTier, int] = {
    DiaryTier.EASY: 1_000,
    DiaryTier.MEDIUM: 5_000,
    DiaryTier.HARD: 10_000,
    DiaryTier.ELITE: 50_000,
}

_STANDARD_DIARY_MIN_LEVEL: dict[DiaryTier, int] = {
    DiaryTier.EASY: 30,
    DiaryTier.MEDIUM: 40,
    DiaryTier.HARD: 50,
    DiaryTier.ELITE: 70,
}

_KARAMJA_DIARY_MIN_LEVEL: dict[DiaryTier, int] = {
    DiaryTier.EASY: 1,
    DiaryTier.MEDIUM: 30,
    DiaryTier.HARD: 40,
    DiaryTier.ELITE: 70,
}
