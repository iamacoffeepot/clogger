Drawing context passed as an argument to `on_render`. Not a global — only available during rendering.

```lua
on_render = function(g)
    -- Text
    g:text(x, y, "message", 0xFFFFFF)       -- draw text (color optional, default white)
    g:text(x, y, "message")

    -- Rectangles
    g:rect(x, y, w, h, 0xFF0000)            -- rectangle outline
    g:fill_rect(x, y, w, h, 0x00FF00)       -- filled rectangle
    g:round_rect(x, y, w, h, 8, 8, 0xFF0000)       -- rounded rect outline
    g:fill_round_rect(x, y, w, h, 8, 8, 0x00FF00)  -- filled rounded rect

    -- Lines
    g:line(x1, y1, x2, y2, 0xFFFF00)        -- draw line

    -- Circles
    g:circle(x, y, radius, 0x00FFFF)        -- circle outline
    g:fill_circle(x, y, radius, 0xFF00FF)   -- filled circle

    -- Arcs (angles in degrees, counter-clockwise from 3 o'clock)
    g:arc(x, y, radius, 0, 90, 0x00FFFF)       -- arc outline
    g:fill_arc(x, y, radius, 0, 90, 0xFF00FF)  -- filled arc (pie wedge)

    -- Polygons (points from coords:world_tile_poly)
    local poly = coords:world_tile_poly(3200, 3400)
    if poly then
        g:polygon(poly, 0xFF0000)            -- polygon outline
        g:fill_polygon(poly, 0x00FF00)       -- filled polygon
    end

    -- Font
    g:font("Arial", "bold", 14)             -- set font (family, style, size)
    g:font("Monospaced", 12)                -- style defaults to "plain"
    -- Styles: "plain", "bold", "italic", "bold_italic"

    -- Text measurement
    local w = g:text_width("Hello")         -- pixel width of string
    local h = g:text_height()               -- line height (ascent + descent)
    local a = g:text_ascent()               -- pixels above baseline

    -- Stroke
    g:stroke_width(2)                        -- set line thickness
    g:stroke(2, "round", "round")            -- width + cap + join
    -- cap: "butt", "round", "square"
    -- join: "miter", "round", "bevel"
    g:stroke_dash(1, 5, 3)                   -- dashed line (width, dash, gap)

    -- Alpha & opacity
    g:opacity(0.5)                           -- global opacity (0.0-1.0)
    g:color(0x80FF0000)                      -- set color with alpha (0xAARRGGBB)

    -- Gradient (replaces solid color for fills)
    g:gradient(0, 0, 0xFF0000, 100, 0, 0x0000FF)  -- linear gradient
    g:gradient_cyclic(0, 0, 0xFF0000, 50, 0, 0x0000FF)  -- repeating gradient
    g:fill_rect(0, 0, 200, 50, 0xFFFFFF)    -- filled with the gradient

    -- Anti-aliasing
    g:anti_alias(true)                       -- smooth edges

    -- Transforms
    g:translate(100, 100)                    -- shift origin
    g:rotate(math.pi / 4, 50, 50)           -- rotate around point (radians)
    g:rotate(math.pi / 4)                   -- rotate around origin
    g:scale(2.0, 2.0)                        -- scale drawing

    -- Save/restore graphics state
    g:save()                                 -- push state (transform, clip, color, etc.)
    g:translate(50, 50)
    g:opacity(0.5)
    g:fill_rect(0, 0, 20, 20, 0xFF0000)
    g:restore()                              -- pop back to saved state

    -- Clipping (restrict drawing to a region)
    g:save()
    g:clip(10, 10, 200, 100)                 -- only draw inside this rect
    g:fill_rect(0, 0, 500, 500, 0x00FF00)   -- clipped to 200x100
    g:restore()

    -- Path API (arbitrary shapes, bezier curves)
    g:begin_path()                           -- start a new path
    g:move_to(10, 10)                        -- move cursor
    g:line_to(100, 10)                       -- straight line
    g:quad_to(150, 50, 100, 90)              -- quadratic bezier
    g:curve_to(80, 120, 20, 120, 10, 90)    -- cubic bezier
    g:close_path()                           -- line back to start
    g:stroke_path(0xFF0000)                  -- draw outline
    g:fill_path(0x8000FF00)                  -- fill interior
end
```

Colors are RGB integers (e.g. `0xFF0000` for red) or ARGB with alpha (e.g. `0x80FF0000` for 50% transparent red). If the top byte is `0x00` the color is fully opaque.
