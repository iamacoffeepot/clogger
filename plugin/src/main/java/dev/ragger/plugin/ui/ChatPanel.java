package dev.ragger.plugin.ui;

import net.runelite.client.ui.PluginPanel;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.util.function.Consumer;

public class ChatPanel extends PluginPanel {

    private final JTextArea chatLog;
    private final JTextField inputField;

    public ChatPanel(Consumer<String> onMessage) {
        super(false);
        setLayout(new BorderLayout());
        setBorder(new EmptyBorder(10, 10, 10, 10));

        // Chat log
        chatLog = new JTextArea();
        chatLog.setEditable(false);
        chatLog.setLineWrap(true);
        chatLog.setWrapStyleWord(true);
        chatLog.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));

        JScrollPane scrollPane = new JScrollPane(chatLog);
        scrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
        add(scrollPane, BorderLayout.CENTER);

        // Input field
        inputField = new JTextField();
        inputField.addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                if (e.getKeyCode() == KeyEvent.VK_ENTER) {
                    String text = inputField.getText().trim();
                    if (!text.isEmpty()) {
                        inputField.setText("");
                        onMessage.accept(text);
                    }
                }
            }
        });
        add(inputField, BorderLayout.SOUTH);
    }

    public void addMessage(String sender, String message) {
        SwingUtilities.invokeLater(() -> {
            chatLog.append(sender + ": " + message + "\n\n");
            chatLog.setCaretPosition(chatLog.getDocument().getLength());
        });
    }
}
