package dev.ragger.plugin.scripting;

import net.runelite.api.Skill;

/**
 * Lua binding for skill enum constants.
 * Exposed as the global "skill" table in Lua scripts.
 *
 * Usage: player:level(skill.MINING)
 */
public class SkillApi {

    public final Skill ATTACK = Skill.ATTACK;
    public final Skill DEFENCE = Skill.DEFENCE;
    public final Skill STRENGTH = Skill.STRENGTH;
    public final Skill HITPOINTS = Skill.HITPOINTS;
    public final Skill RANGED = Skill.RANGED;
    public final Skill PRAYER = Skill.PRAYER;
    public final Skill MAGIC = Skill.MAGIC;
    public final Skill COOKING = Skill.COOKING;
    public final Skill WOODCUTTING = Skill.WOODCUTTING;
    public final Skill FLETCHING = Skill.FLETCHING;
    public final Skill FISHING = Skill.FISHING;
    public final Skill FIREMAKING = Skill.FIREMAKING;
    public final Skill CRAFTING = Skill.CRAFTING;
    public final Skill SMITHING = Skill.SMITHING;
    public final Skill MINING = Skill.MINING;
    public final Skill HERBLORE = Skill.HERBLORE;
    public final Skill AGILITY = Skill.AGILITY;
    public final Skill THIEVING = Skill.THIEVING;
    public final Skill SLAYER = Skill.SLAYER;
    public final Skill FARMING = Skill.FARMING;
    public final Skill RUNECRAFT = Skill.RUNECRAFT;
    public final Skill HUNTER = Skill.HUNTER;
    public final Skill CONSTRUCTION = Skill.CONSTRUCTION;
    public final Skill SAILING = Skill.SAILING;
}
