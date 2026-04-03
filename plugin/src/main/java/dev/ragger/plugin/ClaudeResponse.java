package dev.ragger.plugin;

import java.util.List;

/**
 * Parsed response from Claude CLI containing chat text, tool usage log,
 * and any scripts submitted via the ragger_run tool.
 */
public class ClaudeResponse {

    private final String text;
    private final List<String> scripts;
    private final List<String> toolLog;

    public ClaudeResponse(String text, List<String> scripts, List<String> toolLog) {
        this.text = text;
        this.scripts = scripts;
        this.toolLog = toolLog;
    }

    public String getText() {
        return text;
    }

    public List<String> getScripts() {
        return scripts;
    }

    public boolean hasScripts() {
        return scripts != null && !scripts.isEmpty();
    }

    public List<String> getToolLog() {
        return toolLog;
    }
}
