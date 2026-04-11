Read and control the game camera.

```lua
-- Read position
camera:x()                    -- camera X position
camera:y()                    -- camera Y position
camera:z()                    -- camera Z position

-- Read angles
camera:yaw()                  -- camera yaw angle
camera:pitch()                -- camera pitch angle

-- Set targets
camera:set_yaw(1024)          -- set yaw target
camera:set_pitch(200)         -- set pitch target
camera:set_speed(2.0)         -- set camera speed

-- Camera mode
camera:mode()                 -- get current mode
camera:set_mode(1)            -- set camera mode

-- Focal point
camera:focal_x()              -- get focal X
camera:focal_y()              -- get focal Y
camera:focal_z()              -- get focal Z
camera:set_focal_x(3200.0)   -- set focal X
camera:set_focal_y(3200.0)   -- set focal Y
camera:set_focal_z(0.0)      -- set focal Z

-- Shake
camera:shake_disabled()       -- is shake disabled?
camera:set_shake_disabled(true)
```
