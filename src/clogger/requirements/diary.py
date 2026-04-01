from dataclasses import dataclass

from clogger.enums import DiaryLocation, DiaryTier


@dataclass
class DiaryRequirement:
    id: int
    location: DiaryLocation
    tier: DiaryTier
