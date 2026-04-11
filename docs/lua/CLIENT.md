Read client and game state information.

```lua
-- World info
client:world()                -- current world number
client:plane()                -- current plane/level
client:tick_count()           -- game tick count
client:fps()                  -- current FPS

-- Player state
client:energy()               -- run energy
client:weight()               -- carried weight

-- Game state
client:state()                -- GameState enum value
client:logged_in()            -- true if logged in

-- Canvas/viewport
client:canvas_width()         -- full canvas width
client:canvas_height()        -- full canvas height
client:viewport_width()       -- game viewport width
client:viewport_height()      -- game viewport height
client:viewport_x()           -- viewport X offset
client:viewport_y()           -- viewport Y offset

-- Idle tracking
client:mouse_idle_ticks()     -- ticks since last mouse input
client:keyboard_idle_ticks()  -- ticks since last keyboard input
```

#### GameState Constants

Access via `client.NAME`:

```
client.UNKNOWN                client.STARTING
client.LOGIN_SCREEN           client.LOGIN_SCREEN_AUTHENTICATOR
client.LOGGING_IN             client.LOADING
client.LOGGED_IN              client.CONNECTION_LOST
client.HOPPING
```
