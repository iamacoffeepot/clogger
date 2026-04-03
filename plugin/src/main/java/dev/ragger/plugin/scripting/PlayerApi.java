package dev.ragger.plugin.scripting;

import net.runelite.api.Client;
import net.runelite.api.Player;
import net.runelite.api.Skill;
import net.runelite.api.coords.WorldPoint;

/**
 * Lua binding for local player information.
 * Exposed as the global "player" table in Lua scripts.
 */
public class PlayerApi {

    private final Client client;

    public PlayerApi(Client client) {
        this.client = client;
    }

    // Identity
    public String name() {
        Player p = client.getLocalPlayer();
        return p != null ? p.getName() : "";
    }

    public int combat_level() {
        Player p = client.getLocalPlayer();
        return p != null ? p.getCombatLevel() : 0;
    }

    // Position
    public int x() {
        Player p = client.getLocalPlayer();
        if (p == null) return 0;
        WorldPoint wp = p.getWorldLocation();
        return wp != null ? wp.getX() : 0;
    }

    public int y() {
        Player p = client.getLocalPlayer();
        if (p == null) return 0;
        WorldPoint wp = p.getWorldLocation();
        return wp != null ? wp.getY() : 0;
    }

    public int plane() {
        Player p = client.getLocalPlayer();
        if (p == null) return 0;
        WorldPoint wp = p.getWorldLocation();
        return wp != null ? wp.getPlane() : 0;
    }

    // Skills
    public int level(Skill skill) { return client.getRealSkillLevel(skill); }
    public int boosted_level(Skill skill) { return client.getBoostedSkillLevel(skill); }
    public int xp(Skill skill) { return client.getSkillExperience(skill); }
    public int total_level() { return client.getTotalLevel(); }

    // Health/prayer
    public int hp() { return client.getBoostedSkillLevel(Skill.HITPOINTS); }
    public int max_hp() { return client.getRealSkillLevel(Skill.HITPOINTS); }
    public int prayer() { return client.getBoostedSkillLevel(Skill.PRAYER); }
    public int max_prayer() { return client.getRealSkillLevel(Skill.PRAYER); }

    // State
    public int animation() {
        Player p = client.getLocalPlayer();
        return p != null ? p.getAnimation() : -1;
    }

    public boolean is_dead() {
        Player p = client.getLocalPlayer();
        return p != null && p.isDead();
    }

    public boolean is_interacting() {
        Player p = client.getLocalPlayer();
        return p != null && p.isInteracting();
    }

    public int orientation() {
        Player p = client.getLocalPlayer();
        return p != null ? p.getOrientation() : 0;
    }

    // Overhead text
    public String overhead_text() {
        Player p = client.getLocalPlayer();
        return p != null ? p.getOverheadText() : "";
    }

    public void set_overhead_text(String text) {
        Player p = client.getLocalPlayer();
        if (p != null) p.setOverheadText(text);
    }
}
