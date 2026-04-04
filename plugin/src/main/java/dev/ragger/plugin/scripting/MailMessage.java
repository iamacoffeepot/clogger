package dev.ragger.plugin.scripting;

import java.util.Map;

/**
 * A message in transit between two Lua scripts.
 */
public record MailMessage(String from, String to, Map<String, Object> data) {}
