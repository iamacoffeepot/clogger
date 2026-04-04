package dev.ragger.plugin;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import dev.ragger.plugin.scripting.ScriptManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;

/**
 * Lightweight HTTP server bridging MCP tools to the RuneLite client thread.
 * Requests are queued and fulfilled on the game tick thread.
 */
public class BridgeServer {

    private static final Logger log = LoggerFactory.getLogger(BridgeServer.class);

    private final ScriptManager scriptManager;
    private final String token;
    private final ConcurrentLinkedQueue<PendingRequest> pendingRequests = new ConcurrentLinkedQueue<>();
    private final ConcurrentLinkedQueue<PendingRun> pendingRuns = new ConcurrentLinkedQueue<>();
    private HttpServer server;

    public BridgeServer(ScriptManager scriptManager) {
        this.scriptManager = scriptManager;
        this.token = java.util.UUID.randomUUID().toString();
    }

    public String getToken() {
        return token;
    }

    public void start(int port) throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);

        server.createContext("/eval", exchange -> {
            if (!authenticate(exchange)) {
                respond(exchange, 401, "{\"error\":\"unauthorized\"}");
                return;
            }
            handleEval(exchange);
        });
        server.createContext("/run", exchange -> {
            if (!authenticate(exchange)) {
                respond(exchange, 401, "{\"error\":\"unauthorized\"}");
                return;
            }
            handleRun(exchange);
        });
        server.createContext("/list", exchange -> {
            if (!authenticate(exchange)) {
                respond(exchange, 401, "{\"error\":\"unauthorized\"}");
                return;
            }
            handleList(exchange);
        });
        server.createContext("/source", exchange -> {
            if (!authenticate(exchange)) {
                respond(exchange, 401, "{\"error\":\"unauthorized\"}");
                return;
            }
            handleSource(exchange);
        });
        server.createContext("/templates", exchange -> {
            if (!authenticate(exchange)) {
                respond(exchange, 401, "{\"error\":\"unauthorized\"}");
                return;
            }
            handleTemplates(exchange);
        });
        server.createContext("/template-source", exchange -> {
            if (!authenticate(exchange)) {
                respond(exchange, 401, "{\"error\":\"unauthorized\"}");
                return;
            }
            handleTemplateSource(exchange);
        });
        server.createContext("/health", exchange -> {
            respond(exchange, 200, "{\"status\":\"ok\"}");
        });

        server.setExecutor(null);
        server.start();
        log.info("Bridge server started on port {}", port);
    }

    public void stop() {
        if (server != null) {
            server.stop(0);
            log.info("Bridge server stopped");
        }
    }

    /**
     * Called on the game tick thread. Processes all pending requests.
     */
    public void tick() {
        PendingRequest req;
        while ((req = pendingRequests.poll()) != null) {
            try {
                String result = scriptManager.eval(req.script);
                req.future.complete(result);
            } catch (Exception e) {
                req.future.complete("{\"error\":\"" + e.getMessage().replace("\"", "'") + "\"}");
            }
        }

        PendingRun run;
        while ((run = pendingRuns.poll()) != null) {
            try {
                scriptManager.load(run.name, run.script);
                run.future.complete("{\"status\":\"loaded\",\"name\":\"" + run.name + "\"}");
            } catch (Exception e) {
                run.future.complete("{\"error\":\"" + e.getMessage().replace("\"", "'") + "\"}");
            }
        }
    }

    private boolean authenticate(HttpExchange exchange) {
        String auth = exchange.getRequestHeaders().getFirst("Authorization");
        return auth != null && auth.equals("Bearer " + token);
    }

    private void handleEval(HttpExchange exchange) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            respond(exchange, 405, "{\"error\":\"POST required\"}");
            return;
        }

        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        try {
            JsonObject json = new JsonParser().parse(body).getAsJsonObject();
            String script = json.get("script").getAsString();

            CompletableFuture<String> future = new CompletableFuture<>();
            pendingRequests.add(new PendingRequest(script, future));

            // Wait for game tick to process it (max 5 seconds)
            String result = future.get(5, TimeUnit.SECONDS);
            respond(exchange, 200, result);
        } catch (Exception e) {
            respond(exchange, 500, "{\"error\":\"" + e.getMessage().replace("\"", "'") + "\"}");
        }
    }

    private void handleRun(HttpExchange exchange) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            respond(exchange, 405, "{\"error\":\"POST required\"}");
            return;
        }

        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        try {
            JsonObject json = new JsonParser().parse(body).getAsJsonObject();
            String name = json.get("name").getAsString();
            String script = json.get("script").getAsString();

            CompletableFuture<String> future = new CompletableFuture<>();
            pendingRuns.add(new PendingRun(name, script, future));

            String result = future.get(5, TimeUnit.SECONDS);
            respond(exchange, 200, result);
        } catch (Exception e) {
            respond(exchange, 500, "{\"error\":\"" + e.getMessage().replace("\"", "'") + "\"}");
        }
    }

    private void handleList(HttpExchange exchange) throws IOException {
        if (!"GET".equals(exchange.getRequestMethod())) {
            respond(exchange, 405, "{\"error\":\"GET required\"}");
            return;
        }

        var names = scriptManager.list();
        var arr = new com.google.gson.JsonArray();
        for (String name : names) {
            arr.add(name);
        }
        JsonObject result = new JsonObject();
        result.add("scripts", arr);
        respond(exchange, 200, result.toString());
    }

    private void handleSource(HttpExchange exchange) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            respond(exchange, 405, "{\"error\":\"POST required\"}");
            return;
        }

        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        try {
            JsonObject json = new JsonParser().parse(body).getAsJsonObject();
            String name = json.get("name").getAsString();
            String source = scriptManager.getSource(name);
            if (source == null) {
                respond(exchange, 404, "{\"error\":\"script not found\"}");
            } else {
                JsonObject result = new JsonObject();
                result.addProperty("name", name);
                result.addProperty("source", source);
                respond(exchange, 200, result.toString());
            }
        } catch (Exception e) {
            respond(exchange, 500, "{\"error\":\"" + e.getMessage().replace("\"", "'") + "\"}");
        }
    }

    private void handleTemplates(HttpExchange exchange) throws IOException {
        if (!"GET".equals(exchange.getRequestMethod())) {
            respond(exchange, 405, "{\"error\":\"GET required\"}");
            return;
        }

        var names = scriptManager.listTemplates();
        var arr = new com.google.gson.JsonArray();
        for (String name : names) {
            arr.add(name);
        }
        JsonObject result = new JsonObject();
        result.add("templates", arr);
        respond(exchange, 200, result.toString());
    }

    private void handleTemplateSource(HttpExchange exchange) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            respond(exchange, 405, "{\"error\":\"POST required\"}");
            return;
        }

        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        try {
            JsonObject json = new JsonParser().parse(body).getAsJsonObject();
            String name = json.get("name").getAsString();
            String source = scriptManager.getTemplate(name);
            if (source == null) {
                respond(exchange, 404, "{\"error\":\"template not found\"}");
            } else {
                JsonObject result = new JsonObject();
                result.addProperty("name", name);
                result.addProperty("source", source);
                respond(exchange, 200, result.toString());
            }
        } catch (Exception e) {
            respond(exchange, 500, "{\"error\":\"" + e.getMessage().replace("\"", "'") + "\"}");
        }
    }

    private void respond(HttpExchange exchange, int code, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(code, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private record PendingRequest(String script, CompletableFuture<String> future) {}
    private record PendingRun(String name, String script, CompletableFuture<String> future) {}
}
