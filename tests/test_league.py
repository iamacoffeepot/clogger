import sqlite3

from ragger.enums import DiaryLocation, DiaryTier, League, Region, Skill, TaskDifficulty
from ragger.league import LeagueTask
from ragger.requirements import (
    GroupDiaryRequirement,
    GroupItemRequirement,
    GroupQuestRequirement,
    GroupSkillRequirement,
)
from ragger.wiki import link_group_requirement


def _seed_tasks(conn: sqlite3.Connection, league: League = League.DEMONIC_PACTS) -> None:
    conn.executemany(
        "INSERT INTO league_tasks (name, description, difficulty, region, league) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("Kill a Goblin", "Kill a goblin", TaskDifficulty.EASY.value,
             Region.MISTHALIN.value, league.value),
            ("50 Wintertodt Kills", "Kill Wintertodt 50 times", TaskDifficulty.HARD.value,
             Region.KOUREND.value, league.value),
            ("Achieve Level 99", "Get 99 in any skill", TaskDifficulty.ELITE.value,
             Region.GENERAL.value, league.value),
        ],
    )
    conn.commit()


def test_all(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    tasks = LeagueTask.all(conn)
    assert len(tasks) == 3
    assert all(isinstance(t, LeagueTask) for t in tasks)


def test_all_filter_difficulty(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    tasks = LeagueTask.all(conn, difficulty=TaskDifficulty.HARD)
    assert len(tasks) == 1
    assert tasks[0].name == "50 Wintertodt Kills"


def test_all_filter_region(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    tasks = LeagueTask.all(conn, region=Region.KOUREND)
    assert len(tasks) == 1
    assert tasks[0].region == Region.KOUREND


def test_by_name(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    task = LeagueTask.by_name(conn, "Kill a Goblin")
    assert task is not None
    assert task.difficulty == TaskDifficulty.EASY
    assert task.region == Region.MISTHALIN
    assert task.points == 10


def test_by_name_not_found(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    assert LeagueTask.by_name(conn, "Nonexistent") is None


def test_points(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    tasks = LeagueTask.all(conn)
    points = {t.name: t.points for t in tasks}
    assert points["Kill a Goblin"] == 10
    assert points["50 Wintertodt Kills"] == 80
    assert points["Achieve Level 99"] == 200


def test_general_region(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    task = LeagueTask.by_name(conn, "Achieve Level 99")
    assert task.region == Region.GENERAL


def test_by_skill(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    task = LeagueTask.by_name(conn, "50 Wintertodt Kills")
    link_group_requirement(
        conn, "group_skill_requirements", {"skill": Skill.FIREMAKING.value, "level": 50},
        "league_task_requirement_groups", "league_task_id", task.id,
    )
    conn.commit()

    tasks = LeagueTask.by_skill(conn, Skill.FIREMAKING)
    assert len(tasks) == 1
    assert tasks[0].name == "50 Wintertodt Kills"


def test_by_skill_with_filters(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    for task_name in ("Kill a Goblin", "50 Wintertodt Kills"):
        task = LeagueTask.by_name(conn, task_name)
        link_group_requirement(
            conn, "group_skill_requirements", {"skill": Skill.ATTACK.value, "level": 10},
            "league_task_requirement_groups", "league_task_id", task.id,
        )
    conn.commit()

    # Filter by region
    tasks = LeagueTask.by_skill(conn, Skill.ATTACK, region=Region.KOUREND)
    assert len(tasks) == 1
    assert tasks[0].name == "50 Wintertodt Kills"

    # Filter by difficulty
    tasks = LeagueTask.by_skill(conn, Skill.ATTACK, difficulty=TaskDifficulty.EASY)
    assert len(tasks) == 1
    assert tasks[0].name == "Kill a Goblin"


def test_skill_requirements(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    task = LeagueTask.by_name(conn, "50 Wintertodt Kills")
    link_group_requirement(
        conn, "group_skill_requirements", {"skill": Skill.FIREMAKING.value, "level": 50},
        "league_task_requirement_groups", "league_task_id", task.id,
    )
    conn.commit()

    reqs = task.skill_requirements(conn)
    assert len(reqs) == 1
    assert isinstance(reqs[0], GroupSkillRequirement)
    assert reqs[0].skill == Skill.FIREMAKING
    assert reqs[0].level == 50


def test_quest_requirements(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    task = LeagueTask.by_name(conn, "Kill a Goblin")
    conn.execute("INSERT INTO quests (name, points) VALUES (?, ?)", ("Goblin Diplomacy", 5))
    quest_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    link_group_requirement(
        conn, "group_quest_requirements", {"required_quest_id": quest_id},
        "league_task_requirement_groups", "league_task_id", task.id,
    )
    conn.commit()

    reqs = task.quest_requirements(conn)
    assert len(reqs) == 1
    assert isinstance(reqs[0], GroupQuestRequirement)
    assert reqs[0].required_quest_id == quest_id


def test_item_requirements(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    task = LeagueTask.by_name(conn, "Kill a Goblin")
    conn.execute("INSERT INTO items (name) VALUES (?)", ("Bronze sword",))
    item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    link_group_requirement(
        conn, "group_item_requirements", {"item_id": item_id, "quantity": 1},
        "league_task_requirement_groups", "league_task_id", task.id,
    )
    conn.commit()

    reqs = task.item_requirements(conn)
    assert len(reqs) == 1
    assert isinstance(reqs[0], GroupItemRequirement)
    assert reqs[0].item_id == item_id


def test_diary_requirements(conn: sqlite3.Connection) -> None:
    _seed_tasks(conn)
    task = LeagueTask.by_name(conn, "50 Wintertodt Kills")
    link_group_requirement(
        conn, "group_diary_requirements",
        {"location": DiaryLocation.KOUREND_KEBOS.value, "tier": DiaryTier.EASY.value},
        "league_task_requirement_groups", "league_task_id", task.id,
    )
    conn.commit()

    reqs = task.diary_requirements(conn)
    assert len(reqs) == 1
    assert isinstance(reqs[0], GroupDiaryRequirement)
    assert reqs[0].location == DiaryLocation.KOUREND_KEBOS
    assert reqs[0].tier == DiaryTier.EASY


def test_league_filter_isolates_catalogs(conn: sqlite3.Connection) -> None:
    # Raging Echoes catalog
    _seed_tasks(conn, League.RAGING_ECHOES)
    # Demonic Pacts catalog (same task names — must coexist under UNIQUE(name, league))
    _seed_tasks(conn, League.DEMONIC_PACTS)

    assert len(LeagueTask.all(conn)) == 6
    assert len(LeagueTask.all(conn, league=League.RAGING_ECHOES)) == 3
    assert len(LeagueTask.all(conn, league=League.DEMONIC_PACTS)) == 3

    dpl_task = LeagueTask.by_name(conn, "Kill a Goblin", league=League.DEMONIC_PACTS)
    rel_task = LeagueTask.by_name(conn, "Kill a Goblin", league=League.RAGING_ECHOES)
    assert dpl_task.id != rel_task.id
    assert dpl_task.league == League.DEMONIC_PACTS
    assert rel_task.league == League.RAGING_ECHOES
