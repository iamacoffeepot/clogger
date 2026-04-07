### Npc (`src/ragger/npc.py`)

```python
from ragger.npc import Npc

Npc.all(conn, region?) -> list[Npc]
Npc.by_name(conn, name) -> list[Npc]              # multiple versions possible
Npc.search(conn, name) -> list[Npc]                # partial name match
Npc.with_option(conn, option, region?) -> list[Npc] # e.g. "Travel", "Teleport"
Npc.at_location(conn, location) -> list[Npc]
npc.has_option(option) -> bool
npc.option_list() -> list[str]
npc.game_vars(conn) -> list[GameVariable]               # associated game variables
```
