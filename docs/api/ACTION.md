### Action (`src/ragger/action.py`)

```python
from ragger.action import Action, ActionOutputExperience, ActionInputItem, ActionInputObject, ActionInputCurrency, ActionOutputItem, ActionOutputObject

# Core queries
Action.all(conn) -> list[Action]
Action.by_name(conn, name) -> list[Action]             # multiple methods for same output
Action.at_object(conn, at) -> list[Action]             # performed at world object
Action.search(conn, name) -> list[Action]              # partial name match
Action.by_trigger_type(conn, trigger_type) -> list[Action]  # bitmask match

# Producing queries
Action.producing_item(conn, item_name) -> list[Action]
Action.producing_object(conn, object_name) -> list[Action]
Action.producing_experience(conn, skill) -> list[Action]

# Consuming queries
Action.consuming_item(conn, item_name) -> list[Action]
Action.consuming_object(conn, object_name) -> list[Action]
Action.consuming_currency(conn, currency) -> list[Action]

# Output methods
action.output_experience(conn) -> list[ActionOutputExperience]
action.output_items(conn) -> list[ActionOutputItem]
action.output_objects(conn) -> list[ActionOutputObject]

# Input methods
action.input_items(conn) -> list[ActionInputItem]      # consumed items
action.input_objects(conn) -> list[ActionInputObject]   # consumed objects
action.input_currencies(conn) -> list[ActionInputCurrency]  # consumed currencies

# Requirements (skill levels and tools are stored as requirement groups)
action.requirement_groups(conn) -> list[RequirementGroup]
action.skill_requirements(conn) -> list[GroupSkillRequirement]
action.quest_requirements(conn) -> list[GroupQuestRequirement]

Action.delete_by_source(conn, source) -> list[int]     # delete all actions for a source and dependents

action.name -> str                                     # what the action creates
action.members -> bool
action.ticks -> int | None                             # game ticks per action (NULL for gathering)
action.notes -> str | None                             # quest/other requirements
action.trigger_types -> int                            # TriggerType bitmask (oploc, opnpc, opheld, etc.)
action.has_trigger_type(trigger_type) -> bool
action.trigger_type_list() -> list[TriggerType]
```
