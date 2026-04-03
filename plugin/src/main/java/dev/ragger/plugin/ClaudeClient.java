package dev.ragger.plugin;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Manages communication with the Claude CLI.
 */
public class ClaudeClient {

    private static final Logger log = LoggerFactory.getLogger(ClaudeClient.class);

    private final String claudePath;
    private String sessionId;

    public ClaudeClient(String claudePath) {
        this.claudePath = claudePath;
    }

    /**
     * Send a message to Claude asynchronously with the given behavior profiles.
     */
    public CompletableFuture<String> send(String message, String... behaviors) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                return execute(message, behaviors);
            } catch (Exception e) {
                log.error("Claude CLI error", e);
                return "Error: " + e.getMessage();
            }
        });
    }

    private String execute(String message, String... behaviors) throws IOException, InterruptedException {
        List<String> command = new ArrayList<>();
        command.add(claudePath);
        command.add("--bare");
        command.add("-p");
        command.add(message);

        String systemPrompt = loadBehaviors(behaviors);
        if (!systemPrompt.isEmpty()) {
            command.add("--system-prompt");
            command.add(systemPrompt);
        }

        if (sessionId != null) {
            command.add("--resume");
            command.add(sessionId);
        }

        command.add("--output-format");
        command.add("text");

        ProcessBuilder pb = new ProcessBuilder(command);
        pb.redirectErrorStream(true);
        Process process = pb.start();

        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (!output.isEmpty()) {
                    output.append("\n");
                }
                output.append(line);
            }
        }

        int exitCode = process.waitFor();
        if (exitCode != 0) {
            log.warn("Claude CLI exited with code {}", exitCode);
        }

        return output.toString();
    }

    /**
     * Load behavior files from classpath resources and concatenate them.
     */
    private String loadBehaviors(String... behaviors) {
        StringBuilder sb = new StringBuilder();
        for (String behavior : behaviors) {
            String resource = behavior + ".md";
            try (InputStream is = getClass().getResourceAsStream(resource)) {
                if (is == null) {
                    log.warn("Behavior resource not found: {}", resource);
                    continue;
                }
                if (!sb.isEmpty()) {
                    sb.append("\n\n");
                }
                sb.append(new String(is.readAllBytes(), StandardCharsets.UTF_8));
            } catch (IOException e) {
                log.error("Failed to load behavior: {}", behavior, e);
            }
        }
        return sb.toString();
    }

    /**
     * Reset the session — next message starts a fresh conversation.
     */
    public void resetSession() {
        sessionId = null;
    }
}
