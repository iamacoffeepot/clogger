package dev.ragger.plugin.scripting;

import net.runelite.api.ChatMessageType;
import net.runelite.client.chat.ChatMessageManager;
import net.runelite.client.chat.QueuedMessage;

/**
 * Lua binding for sending messages to the RuneLite chat box.
 * Exposed as the global "chat" table in Lua scripts.
 */
public class ChatApi {

    private final ChatMessageManager chatMessageManager;

    public ChatApi(ChatMessageManager chatMessageManager) {
        this.chatMessageManager = chatMessageManager;
    }

    public void game(String message) {
        chatMessageManager.queue(QueuedMessage.builder()
            .type(ChatMessageType.GAMEMESSAGE)
            .value(message)
            .build());
    }

    public void console(String message) {
        chatMessageManager.queue(QueuedMessage.builder()
            .type(ChatMessageType.CONSOLE)
            .value(message)
            .build());
    }
}
