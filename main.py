import hikari
import lightbulb

bot = lightbulb.BotApp(token="MTI4NTI5ODM1MjMwODYyMTQxNg.GaCLW5.mSnd-j0-mJTU7_CJO83N7Ie-pT_iXXtDLM3-5k")

# Presence
@bot.listen(hikari.StartedEvent)
async def on_starting(event: hikari.StartedEvent) -> None:
    while True:
        guilds = await bot.rest.fetch_my_guilds()
        server_count = len(guilds)
        await bot.update_presence(
            activity=hikari.Activity(
                name=f"{server_count} servers! | /help",
                type=hikari.ActivityType.WATCHING,
            )
        )

bot.run()