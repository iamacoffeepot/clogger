package dev.ragger.plugin.ui;

import net.runelite.client.ui.PluginPanel;
import org.commonmark.node.Node;
import org.commonmark.parser.Parser;
import org.commonmark.renderer.html.HtmlRenderer;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.util.function.Consumer;

public class ChatPanel extends PluginPanel {

    private static final Parser MARKDOWN_PARSER = Parser.builder().build();
    private static final HtmlRenderer HTML_RENDERER = HtmlRenderer.builder().build();

    private static final String STYLE =
        "<style>" +
        "body { font-family: monospace; font-size: 10px; margin: 4px; color: #ddd; }" +
        ".sender { font-weight: bold; color: #ffb347; }" +
        "pre { background: #2a2a2a; padding: 4px; overflow-x: auto; }" +
        "code { background: #2a2a2a; padding: 1px 3px; }" +
        "hr { border: 1px solid #444; }" +
        "</style>";

    private final JEditorPane chatLog;
    private final JTextField inputField;
    private final StringBuilder chatHtml = new StringBuilder();

    public ChatPanel(Consumer<String> onMessage) {
        super(false);
        setLayout(new BorderLayout());
        setBorder(new EmptyBorder(10, 10, 10, 10));

        // Chat log — HTML rendering
        chatLog = new JEditorPane();
        chatLog.setContentType("text/html");
        chatLog.setEditable(false);
        chatLog.putClientProperty(JEditorPane.HONOR_DISPLAY_PROPERTIES, Boolean.TRUE);
        chatLog.setBackground(new Color(0x2d, 0x2d, 0x2d));

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
            Node document = MARKDOWN_PARSER.parse(message);
            String html = HTML_RENDERER.render(document);

            chatHtml.append("<p><span class='sender'>").append(sender).append(":</span></p>");
            chatHtml.append(html);
            chatHtml.append("<hr>");

            chatLog.setText("<html><head>" + STYLE + "</head><body>" + chatHtml + "</body></html>");

            // Scroll to bottom
            chatLog.setCaretPosition(chatLog.getDocument().getLength());
        });
    }

    public void clear() {
        SwingUtilities.invokeLater(() -> {
            chatHtml.setLength(0);
            chatLog.setText("");
        });
    }
}
