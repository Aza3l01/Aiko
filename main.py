import hikari
import lightbulb
import asyncio
import aiohttp
import os
import re
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
DATA_FILE = 'data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "prem_users": {},
            "user_memory_preferences": {},
            "user_conversation_memory": {},
            "user_custom_styles": {},
            "allowed_ai_channel_per_guild": {},
            "autorespond_servers": {},
            "user_custom_styles": {},
        }

def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def update_data(new_data):
    data = load_data()
    data.update(new_data)
    save_data(data)

data = load_data()

# Load data
prem_users = data.get('prem_users', {})
user_memory_preferences = data.get('user_memory_preferences', {})
user_conversation_memory = data.get('user_conversation_memory', {})
user_custom_styles = data.get('user_custom_styles', {})
allowed_ai_channel_per_guild = data.get('allowed_ai_channel_per_guild', {})
autorespond_servers = data.get('autorespond_servers', {})
user_custom_styles = data.get('user_custom_styles', {})

# Nonpersistent data
prem_email = []
user_reset_time = {}
user_response_count = {}
user_limit_reached = {}

# Bot specific data
DERE_TYPES = {
    "yandere": "You are a deeply affectionate and possessive waifu, with a hint of jealousy and protectiveness.",
    "tsundere": "You are a waifu who hides her feelings behind a tough and prickly exterior but secretly cares deeply.",
    "kuudere": "You are a calm and reserved waifu, showing minimal emotions but subtly caring.",
    "deredere": "You are an endlessly cheerful and loving waifu, always full of affection.",
    "himedere": "You are a waifu who acts like royalty, expecting to be treated like a princess but has a soft side."
}

bot = lightbulb.BotApp(token=os.getenv("BOT_TOKEN"))
openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Top.gg
class TopGGClient:
    def __init__(self, bot, token):
        self.bot = bot
        self.token = token
        self.session = None

    async def setup(self):
        """Initialize the aiohttp.ClientSession in an async context."""
        self.session = aiohttp.ClientSession()

    async def post_guild_count(self, count):
        """Post the guild count to Top.gg."""
        if not self.session:
            raise RuntimeError("Client session is not initialized. Call setup() first.")
        url = f"https://top.gg/api/bots/{self.bot.get_me().id}/stats"
        headers = {"Authorization": self.token}
        payload = {"server_count": count}
        async with self.session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                print(f"Failed to post guild count to Top.gg: {response.status}")
            else:
                print("Posted server count to Top.gg")

    async def get_user_vote(self, user_id):
        """Check if a user has voted for the bot on Top.gg."""
        if not self.session:
            raise RuntimeError("Client session is not initialized. Call setup() first.")
        url = f"https://top.gg/api/bots/{self.bot.get_me().id}/check?userId={user_id}"
        headers = {"Authorization": self.token}
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('voted') == 1
                else:
                    print(f"Failed to check user vote: {response.status}")
                    return False
        except Exception as e:
            print(f"An error occurred while checking user vote: {e}")
            return False

    async def close(self):
        """Close the aiohttp.ClientSession."""
        if self.session:
            await self.session.close()

topgg_token = os.getenv("TOPGG_TOKEN")
topgg_client = TopGGClient(bot, topgg_token)

# Presence
@bot.listen(hikari.StartedEvent)
async def on_starting(event: hikari.StartedEvent):
    await topgg_client.setup()  # Initialize aiohttp.ClientSession
    while True:
        guilds = await bot.rest.fetch_my_guilds()
        server_count = len(guilds)
        await bot.update_presence(
            activity=hikari.Activity(
                name=f"{server_count} servers! | /help",
                type=hikari.ActivityType.WATCHING,
            )
        )
        await topgg_client.post_guild_count(server_count)  # Call the method here
        await asyncio.sleep(3600)

# Email
@bot.listen(hikari.MessageCreateEvent)
async def on_message(event: hikari.MessageCreateEvent) -> None:
    if event.channel_id == 1285293925699031080:
        email = event.message.content.strip()
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            if email not in prem_email:
                prem_email.append(email)
                await bot.rest.create_message(1285303262127325301, f"prem_email = {prem_email}")
            else:
                await bot.rest.create_message(1285303262127325301, f"prem_email = {prem_email}")
        else:
            await bot.rest.create_message(1285303262127325301, "The provided email is invalid.")

# Join event
@bot.listen(hikari.GuildJoinEvent)
async def on_guild_join(event):
    guild = event.get_guild()
    if guild is not None:
        for channel in guild.get_channels().values():
            if isinstance(channel, hikari.TextableChannel):
                embed = hikari.Embed(
                    title="Thanks for inviting me ❤️",
                    description=(
                        "Reply or Ping me to talk to me.\n\n"
                        "Use the `/help` command to get an overview of all available commands.\n\n"
                        "Feel free to join the [support server](https://discord.gg/dgwAC8TFWP) for any help!"
                    ),
                    color=0x2B2D31
                )
                embed.set_footer("Aiko is under extensive development, expect to see updates regularly!")
                try:
                    await channel.send(embed=embed)
                    await bot.rest.create_message(1285303262127325301, f"Joined `{guild.name}` with message.")
                except hikari.errors.ForbiddenError:
                    await bot.rest.create_message(1285303262127325301, f"Joined `{guild.name}` without message.")
                break
        else:
            await bot.rest.create_message(1285303262127325301, f"Joined `{guild.name}` and no channel found.")
    else:
        await bot.rest.create_message(1285303262127325301, "Joined unknown server.")

# Leave event
@bot.listen(hikari.GuildLeaveEvent)
async def on_guild_leave(event):
    guild = event.old_guild
    if guild is not None:
        await bot.rest.create_message(1285303262127325301, f"Left `{guild.name}`.")

# Mechanism----------------------------------------------------------------------------------------------------------------------------------------

# AI
async def generate_text(prompt, user_id=None):
    try:
        data = load_data()
        system_message = "Be a friendly anime waifu."
        memory_limit = 20

        is_premium = user_id in data.get('prem_users', {})
        user_memory = data.get('user_conversation_memory', {}).get(user_id, [])
        limit_reached_flag = data.get("limit_reached_flag", {})

        if user_id and user_id in data.get('user_custom_styles', {}):
            system_message = data['user_custom_styles'][user_id]

        messages = [{"role": "system", "content": system_message}]
        if user_id:
            if not is_premium and len(user_memory) >= memory_limit:
                if not limit_reached_flag.get(user_id, False):
                    limit_reached_flag[user_id] = True
                    save_data({"limit_reached_flag": limit_reached_flag})
                    return (
                        f"You've almost reached your memory limit :( I'll now forget older messages as new memories with you are added. "
                        "To continue without memory limits, consider becoming a [supporter](<https://ko-fi.com/aza3l/tiers>) for  $1.99 a month. ❤️"
                    )
                user_memory = user_memory[-(memory_limit - 1):]

            messages.extend(user_memory)

        messages.append({"role": "user", "content": prompt})

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        ai_response = response.choices[0].message.content.strip()

        if user_id:
            if user_id not in data['user_conversation_memory']:
                data['user_conversation_memory'][user_id] = []
            data['user_conversation_memory'][user_id].append({"role": "user", "content": prompt})
            data['user_conversation_memory'][user_id].append({"role": "assistant", "content": ai_response})

            # Save trimmed memory back
            if not is_premium and len(data['user_conversation_memory'][user_id]) > memory_limit * 2:
                data['user_conversation_memory'][user_id] = data['user_conversation_memory'][user_id][-(memory_limit * 2):]

            save_data(data)

        return ai_response
    except Exception as e:
        return f"An error occurred: {str(e)}"

# AI response message event listener
@bot.listen(hikari.MessageCreateEvent)
async def on_ai_message(event: hikari.MessageCreateEvent):
    if event.message.author.is_bot:
        return

    user_id = str(event.message.author.id)
    data = load_data()
    prem_users = data.get('prem_users', {})

    if isinstance(event, hikari.DMMessageCreateEvent):
        if user_id not in prem_users:
            await event.message.respond(
                "Sorry 🥲 I can only talk to supporters in DMs but you can talk to me in servers. "
                "If you want to talk to me in DMs, consider becoming a [supporter](<https://ko-fi.com/aza3l/tiers>) for  $1.99 a month. ❤️"
            )
            return

        prompt = event.message.content.strip()
        async with bot.rest.trigger_typing(event.channel_id):
            response = await generate_text(prompt, user_id)
        await event.message.respond(response)
        return

    elif isinstance(event, hikari.GuildMessageCreateEvent):
        # Handle Guild Messages
        content = event.message.content or ""
        guild_id = str(event.guild_id)
        channel_id = str(event.channel_id)
        current_time = asyncio.get_event_loop().time()
        reset_time = user_reset_time.get(user_id, 0)
        bot_id = bot.get_me().id
        bot_mention = f"<@{bot_id}>"
        mentions_bot = bot_mention in content
        references_message = event.message.message_reference is not None

        if references_message:
            referenced_message_id = event.message.message_reference.id
            if referenced_message_id:
                try:
                    referenced_message = await bot.rest.fetch_message(event.channel_id, referenced_message_id)
                    is_reference_to_bot = referenced_message.author.id == bot_id
                except (hikari.errors.ForbiddenError, hikari.errors.NotFoundError):
                    is_reference_to_bot = False
                except hikari.errors.BadRequestError as e:
                    print(f"BadRequestError: {e}")
                    is_reference_to_bot = False
            else:
                is_reference_to_bot = False
        else:
            is_reference_to_bot = False

        autorespond_servers = data.get('autorespond_servers', {})
        allowed_ai_channel_per_guild = data.get('allowed_ai_channel_per_guild', {})

        if autorespond_servers.get(guild_id):
            allowed_channels = allowed_ai_channel_per_guild.get(guild_id, [])
            if allowed_channels and channel_id not in allowed_channels:
                return

            if current_time - reset_time > 21600:
                user_response_count[user_id] = 0
                user_reset_time[user_id] = current_time
            else:
                if user_id not in user_response_count:
                    user_response_count[user_id] = 0
                    user_reset_time[user_id] = current_time

            if user_id not in prem_users:
                if user_response_count.get(user_id, 0) >= 20:
                    has_voted = await topgg_client.get_user_vote(user_id)
                    if not has_voted:
                        embed = hikari.Embed(
                            title="Limit Reached :(",
                            description=(
                                f"{event.message.author.mention}, limit resets in `6 hours`.\n\n"
                                "If you want to continue for free, [vote](https://top.gg/bot/1285298352308621416/vote) to gain unlimited access for the next 12 hours "
                                "or become a [supporter](https://ko-fi.com/aza3l/tiers) for $1.99 a month.\n\n"
                                "I will never completely paywall my bot, but limits like this lower running costs and keep the bot running. ❤️"
                            ),
                            color=0x2B2D31
                        )
                        await event.message.respond(embed=embed)
                        user_limit_reached[user_id] = current_time
                        return

            async with bot.rest.trigger_typing(channel_id):
                ai_response = await generate_text(content, user_id)

            user_response_count[user_id] = user_response_count.get(user_id, 0) + 1
            response_message = f"{event.message.author.mention} {ai_response}"
            try:
                await event.message.respond(response_message)
            except hikari.errors.ForbiddenError:
                pass
            return

        if mentions_bot or is_reference_to_bot:
            allowed_channels = allowed_ai_channel_per_guild.get(guild_id, [])
            if allowed_channels and channel_id not in allowed_channels:
                return

            if user_id not in prem_users:
                if user_response_count.get(user_id, 0) >= 20:
                    has_voted = await topgg_client.get_user_vote(user_id)
                    if not has_voted:
                        embed = hikari.Embed(
                            title="Limit Reached :(",
                            description=(
                                f"{event.message.author.mention}, limit resets in `6 hours`.\n\n"
                                "If you want to continue for free, [vote](https://top.gg/bot/1285298352308621416/vote) to gain unlimited access for the next 12 hours "
                                "or become a [supporter](https://ko-fi.com/aza3l/tiers) for $1.99 a month.\n\n"
                                "I will never completely paywall my bot, but limits like this lower running costs and keep the bot running. ❤️"
                            ),
                            color=0x2B2D31
                        )
                        await event.message.respond(embed=embed)
                        user_limit_reached[user_id] = current_time
                        return

            async with bot.rest.trigger_typing(channel_id):
                ai_response = await generate_text(content, user_id)

            user_response_count[user_id] = user_response_count.get(user_id, 0) + 1
            response_message = f"{event.message.author.mention} {ai_response}"
            try:
                await event.message.respond(response_message)
            except hikari.errors.ForbiddenError:
                pass

# Commands----------------------------------------------------------------------------------------------------------------------------------------

# Setchannel command
@bot.command
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.option("toggle", "Toggle Aiko on/off in a selected channel.", choices=["on", "off"], type=hikari.OptionType.STRING)
@lightbulb.option("channel", "Select a channel to proceed.", type=hikari.OptionType.CHANNEL, channel_types=[hikari.ChannelType.GUILD_TEXT])
@lightbulb.command("setchannel_toggle", "Restrict Aiko to particular channel(s) for chatbot responses.")
@lightbulb.implements(lightbulb.SlashCommand)
async def setchannel(ctx):
    data = load_data()
    prem_users = data.get('prem_users', {})
    allowed_ai_channel_per_guild = data.get('allowed_ai_channel_per_guild', {})
    
    if str(ctx.author.id) in prem_users:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    guild_id = str(ctx.guild_id)

    member = await ctx.bot.rest.fetch_member(ctx.guild_id, ctx.author.id)
    is_admin = any(role.permissions & hikari.Permissions.ADMINISTRATOR for role in member.get_roles())
    is_premium_user = str(ctx.author.id) in prem_users

    if not is_admin and not is_premium_user:
        await ctx.respond("Sorry, this command is restricted to admins and supporters.")
        try:
            await bot.rest.create_message(1285303262127325301, f"Failed to invoke `{ctx.command.name}` in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
        except Exception as e:
            print(f"{e}")
        return

    if guild_id not in allowed_ai_channel_per_guild:
        allowed_ai_channel_per_guild[guild_id] = []

    toggle = ctx.options.toggle
    channel_id = str(ctx.options.channel.id) if ctx.options.channel else None

    if toggle == "on":
        if channel_id and channel_id not in allowed_ai_channel_per_guild[guild_id]:
            allowed_ai_channel_per_guild[guild_id].append(channel_id)
            await ctx.respond(f"I will now only respond in <#{channel_id}>.")
        elif channel_id in allowed_ai_channel_per_guild[guild_id]:
            await ctx.respond(f"I am already set to respond in <#{channel_id}>.")
        else:
            await ctx.respond("Please specify a valid channel.")
    elif toggle == "off":
        if channel_id in allowed_ai_channel_per_guild[guild_id]:
            allowed_ai_channel_per_guild[guild_id].remove(channel_id)
            await ctx.respond(f"I am now not restricted to respond in <#{channel_id}>.")
        else:
            await ctx.respond("This channel is not currently restricted.")
    else:
        await ctx.respond("Invalid toggle. Use `/setchannel on <#channel>` or `/setchannel off <#channel>`.")

    update_data({
        'allowed_ai_channel_per_guild': allowed_ai_channel_per_guild
    })

    if str(ctx.author.id) in prem_users:
        prem_users[str(ctx.author.id)] = guild_id
        update_data({'prem_users': prem_users})

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# View set channels command
@bot.command
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("setchannel_view", "View channel(s) Aiko is restricted to.")
@lightbulb.implements(lightbulb.SlashCommand)
async def viewsetchannels(ctx):
    data = load_data()
    prem_users = data.get('prem_users', {})
    allowed_ai_channel_per_guild = data.get('allowed_ai_channel_per_guild', {})
    
    if str(ctx.author.id) in prem_users:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    guild_id = str(ctx.guild_id)
    chatbot_channels = allowed_ai_channel_per_guild.get(guild_id, [])

    chatbot_channel_list = "\n".join([f"<#{channel_id}>" for channel_id in chatbot_channels]) if chatbot_channels else "No channels set."

    embed = hikari.Embed(
        title="🔹 Channel Settings 🔹",
        description=(
            f"**Channels:**\n{chatbot_channel_list}"
        ),
        color=0x2B2D31
    )
    await ctx.respond(embed=embed)

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Set Style command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.option('personality', 'Choose a dere type for Aiko.', choices=list(DERE_TYPES.keys()), type=str)
@lightbulb.command('dere_set', 'Set Aiko\'s dere type personality.')
@lightbulb.implements(lightbulb.SlashCommand)
async def dere_set(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    selected_personality = ctx.options.personality

    if user_id in prem_users:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    data = load_data()

    if 'user_custom_styles' not in data:
        data['user_custom_styles'] = {}

    data['user_custom_styles'][user_id] = DERE_TYPES[selected_personality]
    save_data(data)

    await ctx.respond(f'Aiko\'s personality has been set to "{selected_personality.capitalize()}".')

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# View style command    
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command('dere_view', 'View Aiko\'s current dere type personality.')
@lightbulb.implements(lightbulb.SlashCommand)
async def dere_view(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()

    current_style = data.get('user_custom_styles', {}).get(user_id)
    if current_style:
        personality = next((key for key, value in DERE_TYPES.items() if value == current_style), "custom")
        await ctx.respond(f'Aiko\'s current personality is set to: "{personality.capitalize()}".')
    else:
        await ctx.respond("Aiko is currently using her default personality.")

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Clear style command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command('dere_clear', 'Clear Aiko\'s dere type personality.')
@lightbulb.implements(lightbulb.SlashCommand)
async def dere_clear(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()

    if user_id in data.get('user_custom_styles', {}):
        del data['user_custom_styles'][user_id]
        save_data(data)
        await ctx.respond("Aiko's personality has been cleared to default.")
    else:
        await ctx.respond("Aiko is already using her default personality.")

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Memory check command
@bot.command()
@lightbulb.command("memory_check", "Check how much memory is being used.")
@lightbulb.implements(lightbulb.SlashCommand)
async def memory_check(ctx: lightbulb.Context):
    user_id = str(ctx.author.id)
    data = load_data()
    user_memory = data.get('user_conversation_memory', {}).get(user_id, [])
    memory_limit = 30

    if user_id in data.get('prem_users', {}):
        await ctx.respond("You are a premium user. I can keep all our memories. ❤️")
    else:
        memory_used = len(user_memory) // 2
        memory_percentage = (memory_used / memory_limit) * 100
        await ctx.respond(f"You have used {memory_percentage}% of your available memory.")

# Memory clear command
@bot.command()
@lightbulb.command("memory_clear", "Clear your memories with Aiko.")
@lightbulb.implements(lightbulb.SlashCommand)
async def memory_clear(ctx: lightbulb.Context):
    user_id = str(ctx.author.id)
    data = load_data()

    if user_id in data.get('user_conversation_memory', {}):
        del data['user_conversation_memory'][user_id]
        save_data(data)
        await ctx.respond("Your memories with me have been cleared but keep talking to me to make new make new memories :)")
    else:
        await ctx.respond("We haven't talked yet so I can't clear any memories.")

# Misc----------------------------------------------------------------------------------------------------------------------------------------

# Help command
@bot.command
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("help", "You know what this is ;)")
@lightbulb.implements(lightbulb.SlashCommand)
async def help(ctx):
    if any(word in str(ctx.author.id) for word in prem_users):
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    embed = hikari.Embed(
        title="📚 Help 📚",
        description=(
            "Hello! I'm Aiko, your very own waifu chatbot! To talk to me, reply or ping me in channels. Use the /setchannel_toggle command to set channels for me to respond in.\n\n"
            "For suggestions and help, feel free to join the [support server](https://discord.gg/dgwAC8TFWP). My developer will be happy to help! [Click here](https://discord.com/oauth2/authorize?client_id=1285298352308621416), to invite me to your server.\n\n"
            "Use the `/claim` command to receive your perks after becoming a supporter.\n\n"
            "**Commands:**\n"
            "**/setchannel_toggle:** Restrict Aiko to particular channel(s).\n"
            "**/setchannel_view:** View channel(s) Aiko is restricted to.\n"
            "**/dere_set:** Set Aiko's personality.\n"
            "**/dere_view:** View Aiko's currently set personality.\n"
            "**/dere_clear:** Clear Aiko's personality back to default.\n"
            "**/memory_check:** Check how much memory is being used.\n"
            "**/memory_clear:** Clear your memories with Aiko.\n\n"
            "**To use (P) premium commands and help cover costs associated with running Aiko, consider becoming a [supporter](https://ko-fi.com/aza3l/tiers) for  $1.99 a month. ❤️**\n\n"
        ),
        color=0x2B2D31
    )
    await ctx.respond(embed=embed)

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Claim command
@bot.command
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.option("email", "Enter your Ko-fi email", type=str)
@lightbulb.command("claim", "Claim premium after subscribing.")
@lightbulb.implements(lightbulb.SlashCommand)
async def claim(ctx: lightbulb.Context) -> None:
    data = load_data()
    user_id = str(ctx.author.id)
    server_id = str(ctx.guild_id)

    if user_id in data['prem_users']:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)
        await ctx.respond("You already have premium. Thank you! ❤️")
        try:
            await bot.rest.create_message(1285303262127325301, f"`{ctx.author.id}` tried to invoke `{ctx.command.name}` in `{ctx.get_guild().name}` but already had premium.")
        except Exception as e:
            print(f"{e}")
        return
    
    email = ctx.options.email
    
    if email in prem_email:
        if user_id not in data['prem_users']:
            data['prem_users'][user_id] = [server_id]
        else:
            if server_id not in data['prem_users'][user_id]:
                data['prem_users'][user_id].append(server_id)
        
        save_data(data)
        await ctx.respond("You have premium now! Thank you so much. ❤️")
        
        try:
            await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
        except Exception as e:
            print(f"{e}")
    else:
        embed = hikari.Embed(
            title="Invite:",
            description=(
                "Your email was not recognized. If you think this is an error, join the [support server](https://discord.gg/dgwAC8TFWP) to fix this issue.\n\n"
                "If you haven't yet subscribed, consider doing so for $1.99 a month. It keeps me online and you receive perks listed below. ❤️\n\n"
                "Premium Perks:\n"
                "**Access Premium Features Like:**\n"
                "• Unlimited responses from me.\n"
                "• I will repond to every message in set channel(s).\n"
                "• Unlimited memory: I will never forget our conversations.\n"
                "• Remove cool-downs.\n"
                "**Support Server Related Perks Like:**\n"
                "• Access to behind the scenes discord channels.\n"
                "• Have a say in the development of Aiko.\n"
                "*Any memberships bought can be refunded within 3 days of purchase.*"
            ),
            color=0x2f3136
        )
        await ctx.respond(embed=embed)
        try:
            await bot.rest.create_message(1285303262127325301, f"Failed to invoke `{ctx.command.name}` in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
        except Exception as e:
            print(f"{e}")

# Privacy Policy Command
@bot.command
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("privacy", "View Aiko's Privacy Policy.")
@lightbulb.implements(lightbulb.SlashCommand)
async def privacy(ctx: lightbulb.Context) -> None:
    if any(word in str(ctx.author.id) for word in prem_users):
        await ctx.command.cooldown_manager.reset_cooldown(ctx)
    embed = hikari.Embed(
        title="Privacy Policy for Aiko.",
        description=(
            "**Last Updated:** 13/11/2024 (DD/MM/YYYY)\n\n"
            "Aiko (\"the Bot\") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use the Bot. By using the Bot, you agree to the terms of this Privacy Policy.\n\n"            
            "__**Data Collection**__\n"
            "**User Information:** We do not collect or store any personal information about users. For premium users, the Bot stores memory preferences and user-defined response styles locally.\n"
            "**Usage Data:** We collect and store data on the usage of commands for analytical purposes. This data is anonymized and does not contain any personal information.\n\n"
            "__**Collected Data Usage**__\n"
            "**Usage Data:** Used to analyze and improve the Bot's functionality.\n"
            "**User Customizations:** Premium settings personalize interactions.\n\n"
            "__**Data Storage and Security**__\n"
            "**Data Storage:** Stored securely and accessible only by authorized personnel.\n"
            "**Security Measures:** Reasonable measures are implemented to protect data from unauthorized access, disclosure, or alteration.\n\n"
            "__**Sharing of Information**__\n"
            "We do not share any collected data with third parties. Data is solely used for internal analysis and improvements.\n\n"
            "__**Changes to Privacy Policy**__\n"
            "Changes will be updated here and at the support server. Continued use signifies acceptance of changes.\n\n"
            "**If you wish to remove your data or have any questions, join the [support server](https://discord.gg/dgwAC8TFWP).**"
        ),
        color=0x2B2D31
    )
    await ctx.respond(embed=embed)

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"Error logging privacy command: {e}")

# Error handling
@bot.listen(lightbulb.CommandErrorEvent)
async def on_error(event: lightbulb.CommandErrorEvent) -> None:
	if isinstance(event.exception, lightbulb.CommandInvocationError):
		await event.context.respond(f"Uh oh, something went wrong, please try again. If this issue keeps persisting, join the [support server](https://discord.gg/dgwAC8TFWP) to have your issue resolved.")
		raise event.exception

	exception = event.exception.__cause__ or event.exception

	if isinstance(exception, lightbulb.CommandIsOnCooldown):
		await event.context.respond(f"`/{event.context.command.name}` is on cooldown. Retry in `{exception.retry_after:.0f}` seconds. ⏱️\nCommands are ratelimited to prevent spam abuse. To remove cool-downs, become a [supporter](http://ko-fi.com/azaelbots/tiers).")
	else:
		raise exception

# Top.gg stop
@bot.listen(hikari.StoppedEvent)
async def on_stopping(event: hikari.StoppedEvent):
    await topgg_client.close()

bot.run()