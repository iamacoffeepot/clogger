package dev.ragger.plugin.ui;

import net.runelite.client.ui.PluginPanel;
import org.commonmark.Extension;
import org.commonmark.ext.gfm.tables.TablesExtension;
import org.commonmark.ext.gfm.strikethrough.StrikethroughExtension;
import org.commonmark.node.Node;
import org.commonmark.parser.Parser;
import org.commonmark.renderer.html.HtmlRenderer;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.util.List;
import java.util.function.Consumer;

public class ChatPanel extends PluginPanel {

    private static final List<Extension> MD_EXTENSIONS = List.of(
        TablesExtension.create(),
        StrikethroughExtension.create()
    );
    private static final Parser MARKDOWN_PARSER = Parser.builder().extensions(MD_EXTENSIONS).build();
    private static final HtmlRenderer HTML_RENDERER = HtmlRenderer.builder().extensions(MD_EXTENSIONS).build();

    private static final String STYLE =
        "<style>" +
        "body { font-family: monospace; font-size: 10px; margin: 4px; color: #ddd; }" +
        ".sender { font-weight: bold; color: #ffb347; margin: 0 0 4px 0; padding: 0; }" +
        ".message { margin-top: 2px; margin-bottom: 4px; }" +
        ".message p { margin: 2px 0; }" +
        // JEditorPane uses HTML 3.2 — <pre> works but needs explicit font
        "pre { background: #2a2a2a; padding: 4px; margin: 2px 0; }" +
        "code { background: #2a2a2a; padding: 1px 3px; }" +
        // JEditorPane draws its own bright line for <hr>, so we zero it out
        "hr { border: none; margin: 0; padding: 0; height: 0; }" +
        ".divider { border-top: 1px solid #444; padding-top: 8px; }" +
        // JEditorPane doesn't support <del>, only <strike>
        "strike { text-decoration: line-through; color: #888; }" +
        "table { border-collapse: collapse; width: 100%; margin: 4px 0; }" +
        "th, td { border: 1px solid #555; padding: 3px 6px; }" +
        "th { background: #383838; }" +
        ".thinking { color: #888; font-style: italic; }" +
        ".tool { color: #666; font-style: italic; font-size: 9px; padding: 2px 0; }" +
        // JEditorPane ignores margin on most elements, use padding instead
        "ul, ol { padding-left: 20px; margin: 2px 0; }" +
        "li { margin: 1px 0; }" +
        "blockquote { border-left: 2px solid #555; padding-left: 6px; margin: 2px 0; color: #aaa; }" +
        "</style>";

    private final JEditorPane chatLog;
    private final JTextField inputField;
    private final StringBuilder chatHtml = new StringBuilder();
    private final Consumer<String> onMessage;
    private JFrame detachedFrame;
    private JEditorPane detachedLog;
    private JTextField detachedInput;
    private Timer thinkingTimer;
    private int thinkingDots = 0;

    public ChatPanel(Consumer<String> onMessage) {
        super(false);
        this.onMessage = onMessage;
        setLayout(new BorderLayout());
        setBorder(new EmptyBorder(10, 10, 10, 10));

        // Detach button
        JButton detachButton = new JButton("Detach");
        detachButton.addActionListener(e -> toggleDetach());
        JPanel topBar = new JPanel(new FlowLayout(FlowLayout.RIGHT, 0, 0));
        topBar.add(detachButton);
        add(topBar, BorderLayout.NORTH);

        // Chat log
        chatLog = createChatLog();

        JScrollPane scrollPane = new JScrollPane(chatLog);
        scrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
        add(scrollPane, BorderLayout.CENTER);

        // Input field
        inputField = new JTextField();
        inputField.addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                if (e.getKeyCode() == KeyEvent.VK_ENTER) {
                    submitInput(inputField);
                }
            }
        });
        add(inputField, BorderLayout.SOUTH);
    }

    private JEditorPane createChatLog() {
        JEditorPane pane = new JEditorPane();
        pane.setContentType("text/html");
        pane.setEditable(false);
        pane.putClientProperty(JEditorPane.HONOR_DISPLAY_PROPERTIES, Boolean.TRUE);
        pane.setBackground(new Color(0x2d, 0x2d, 0x2d));
        return pane;
    }

    private void submitInput(JTextField field) {
        String text = field.getText().trim();
        if (!text.isEmpty()) {
            field.setText("");
            onMessage.accept(text);
        }
    }

    private void toggleDetach() {
        SwingUtilities.invokeLater(() -> {
            if (detachedFrame != null) {
                String text = detachedInput != null ? detachedInput.getText() : "";
                if (!text.isEmpty()) {
                    inputField.setText(text);
                }
                detachedFrame.dispose();
                detachedFrame = null;
                detachedLog = null;
                detachedInput = null;
                return;
            }

            String pendingText = inputField.getText();
            inputField.setText("");

            detachedFrame = new JFrame("Ragger");
            detachedFrame.setSize(500, 600);
            detachedFrame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
            detachedFrame.addWindowListener(new java.awt.event.WindowAdapter() {
                @Override
                public void windowClosed(java.awt.event.WindowEvent e) {
                    if (detachedInput != null) {
                        String text = detachedInput.getText();
                        if (!text.isEmpty()) {
                            inputField.setText(text);
                        }
                    }
                    detachedFrame = null;
                    detachedLog = null;
                    detachedInput = null;
                }
            });

            detachedLog = createChatLog();
            detachedLog.setText(buildFullHtml(""));

            JScrollPane scrollPane = new JScrollPane(detachedLog);
            scrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);

            detachedInput = new JTextField(pendingText);
            detachedInput.addKeyListener(new KeyAdapter() {
                @Override
                public void keyPressed(KeyEvent e) {
                    if (e.getKeyCode() == KeyEvent.VK_ENTER) {
                        submitInput(detachedInput);
                    }
                }
            });

            JPanel content = new JPanel(new BorderLayout());
            content.setBorder(new EmptyBorder(10, 10, 10, 10));
            content.add(scrollPane, BorderLayout.CENTER);
            content.add(detachedInput, BorderLayout.SOUTH);

            detachedFrame.setContentPane(content);
            detachedFrame.setVisible(true);
        });
    }

    public void addMessage(String sender, String message) {
        SwingUtilities.invokeLater(() -> {
            stopThinking();

            String html = renderMarkdown(message);

            chatHtml.append("<div class='sender'>")
                .append(escapeHtml(sender))
                .append("</div>");
            chatHtml.append("<div class='message'>").append(html).append("</div>");
            chatHtml.append("<p class='divider'></p>");

            refreshDisplay();
        });
    }

    public void addToolMessage(String message) {
        SwingUtilities.invokeLater(() -> {
            chatHtml.append("<div class='tool'>")
                .append(escapeHtml(message))
                .append("</div>");
            refreshDisplay();
        });
    }

    public void showThinking() {
        SwingUtilities.invokeLater(() -> {
            thinkingDots = 0;
            thinkingTimer = new Timer(400, e -> {
                thinkingDots = (thinkingDots % 3) + 1;
                String dots = ".".repeat(thinkingDots);
                refreshDisplay("<p class='thinking'>Thinking" + dots + "</p>");
            });
            thinkingTimer.start();
        });
    }

    public void stopThinking() {
        if (thinkingTimer != null) {
            thinkingTimer.stop();
            thinkingTimer = null;
        }
    }

    public void clear() {
        SwingUtilities.invokeLater(() -> {
            stopThinking();
            chatHtml.setLength(0);
            chatLog.setText("");
            if (detachedLog != null) {
                detachedLog.setText("");
            }
        });
    }

    /**
     * Render markdown to HTML with post-processing for JEditorPane compatibility.
     *
     * JEditorPane uses an ancient HTML 3.2 renderer. Known workarounds:
     * - <del> is unsupported, must use <strike>
     * - <hr> draws its own bright line ignoring CSS, zeroed out in styles
     * - margin is unreliable on most elements, use padding instead
     * - <blockquote> works but needs explicit styling
     */
    private String renderMarkdown(String markdown) {
        Node document = MARKDOWN_PARSER.parse(markdown);
        String html = HTML_RENDERER.render(document);

        // JEditorPane only supports <strike>, not <del>
        html = html.replace("<del>", "<strike>").replace("</del>", "</strike>");

        return html;
    }

    private static String escapeHtml(String text) {
        return text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;");
    }

    private void refreshDisplay() {
        refreshDisplay("");
    }

    private void refreshDisplay(String suffix) {
        String fullHtml = buildFullHtml(suffix);
        chatLog.setText(fullHtml);
        chatLog.setCaretPosition(chatLog.getDocument().getLength());

        if (detachedLog != null) {
            detachedLog.setText(fullHtml);
            detachedLog.setCaretPosition(detachedLog.getDocument().getLength());
        }
    }

    private String buildFullHtml(String suffix) {
        return "<html><head>" + STYLE + "</head><body>" + chatHtml + suffix + "</body></html>";
    }
}
