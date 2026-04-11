Send messages between actors. Mail is asynchronous — messages sent during one tick are delivered at the start of the next tick.

```lua
-- Send a message to another actor
mail:send("target-actor-name", { key = "value", count = 42 })
```

Receive messages via the `on_mail` lifecycle hook:

```lua
return {
    on_mail = function(from, data)
        -- from: sender's actor name (string)
        -- data: the table that was sent
        chat:game("Got mail from " .. from .. ": " .. tostring(data.key))
    end,

    on_tick = function()
        mail:send("other-actor", { ping = true })
    end
}
```

**Delivery rules:**
- FIFO order — messages delivered in the order they were sent
- Mail sent during tick N is delivered at the start of tick N+1
- `on_mail` can call `mail:send()` safely — those messages queue for the next tick
- If the target actor doesn't exist or has no `on_mail` hook, the message is silently dropped
- Self-send is allowed (delivered next tick)
- Data tables support string, number, boolean values and nested tables (maps and arrays up to 8 levels deep).

#### Sending prompts to the background agent

Actors can send questions to the background Claude agent at `claude:agent`. The agent automatically replies to the sender using the `from` field set by the mail system — no need to specify a reply address.

```lua
mail:send("claude:agent", { question = "What level do I need for Cook's Assistant?" })
```

The agent processes the message and replies via mail. Handle the response in `on_mail`:

```lua
return {
    on_start = function()
        mail:send("claude:agent", { question = "What items do I need for Cook's Assistant?" })
    end,

    on_mail = function(from, data)
        if from == "claude:agent" then
            chat:game(tostring(data.text or data.result))
        end
    end
}
```

The agent runs an async loop — responses are not instant. Design actors to continue operating while waiting for a reply.
