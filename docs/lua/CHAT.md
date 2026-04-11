Send messages to the RuneLite chat box. Methods use colon syntax (`:`).

```lua
chat:game("message")              -- send a game message (system message)
chat:console("message")           -- send a console message (plugin console)
chat:send(chat.TYPE, "message")   -- send with a specific message type
```

#### Message Type Constants

Access via `chat.NAME`:

```
chat.GAMEMESSAGE              chat.PUBLICCHAT
chat.CONSOLE                  chat.PRIVATECHAT
chat.BROADCAST                chat.PRIVATECHATOUT
chat.FRIENDSCHAT              chat.FRIENDSCHATNOTIFICATION
chat.CLAN_CHAT                chat.CLAN_MESSAGE
chat.CLAN_GUEST_CHAT          chat.CLAN_GUEST_MESSAGE
chat.TRADE                    chat.TRADE_SENT
chat.DIALOG                   chat.MESBOX
chat.NPC_SAY                  chat.ITEM_EXAMINE
chat.NPC_EXAMINE              chat.OBJECT_EXAMINE
chat.WELCOME                  chat.LEVELUPMESSAGE
chat.SPAM                     chat.AUTOTYPER
```
