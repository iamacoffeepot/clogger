from dataclasses import dataclass

from clogger.enums import Region


@dataclass
class RegionRequirement:
    id: int
    regions: int
    any_region: bool

    def region_list(self) -> list[Region]:
        return [r for r in Region if self.regions & r.mask]
