Measure and manipulate text using the game's actual bitmap fonts. Unlike `g:text_width()` on the overlay context (which uses Java AWT fonts), this API uses the real OSRS `FontTypeFace` for pixel-perfect measurements matching widget rendering.

```lua
-- Measure text width in pixels using a game font
text:width("Hello world", 495)        -- width using PLAIN_12 (default)
text:width("Hello world")             -- same (495 is default)
text:width("Hello world", 494)        -- width using PLAIN_11

-- Get font baseline (line height)
text:height(495)                       -- baseline of PLAIN_12
text:height()                          -- same (495 is default)

-- Fit text to a pixel width, truncating with suffix if needed
text:fit("Very long text here", 495, 100)         -- "Very long te..."
text:fit("Very long text here", 495, 100, "~")    -- "Very long tex~"
text:fit("Short", 495, 200)                        -- "Short" (no truncation)

-- Preserves <col=hex> and <br> tags during truncation
text:fit("<col=ff0000>Long red text", 495, 80)     -- "<col=ff0000>Long r..."

-- Transliterate Unicode to ASCII (strips diacritics)
text:ascii("Résumé café")              -- "Resume cafe"
text:ascii("naïve François")           -- "naive Francois"
```

Common font IDs (see `FontID` constants):
- `494` — PLAIN_11 (small)
- `495` — PLAIN_12 (standard, default)
- `496` — BOLD_12
- `497` — QUILL_8
