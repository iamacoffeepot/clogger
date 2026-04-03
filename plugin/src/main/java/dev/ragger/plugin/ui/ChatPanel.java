package dev.ragger.plugin.ui;

import net.runelite.client.ui.PluginPanel;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;

/**
 * Minimal sidebar panel. Chat is handled by the in-game console overlay.
 */
public class ChatPanel extends PluginPanel {

    public ChatPanel() {
        super(false);
        setLayout(new BorderLayout());
        setBorder(new EmptyBorder(10, 10, 10, 10));

        JLabel hint = new JLabel("Press ` to open console");
        hint.setForeground(new Color(0x88, 0x88, 0x88));
        hint.setHorizontalAlignment(SwingConstants.CENTER);
        add(hint, BorderLayout.CENTER);
    }
}
