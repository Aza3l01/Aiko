import hikari
import lightbulb
import asyncio
import aiohttp
import os
import re
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI
import time

load_dotenv()
DATA_FILE = 'data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "prem_users": {},
            "user_conversation_memory": {},
            "user_custom_styles": {},
            "limit_reached_flag": {},
        }
 
def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def update_data(new_data):
    data = load_data()
    data.update(new_data)
    save_data(data)

data = load_data()

prem_users = data.get('prem_users', {})
user_conversation_memory = data.get('user_conversation_memory', {})
user_custom_styles = data.get('user_custom_styles', {})
limit_reached_flag = data.get('limit_reached_flag', {})

prem_email = ['test03@gmail.com']
user_reset_time = {}
user_response_count = {}
user_limit_reached = {}

# Bot specific data
DERE_TYPES = {
    "Yandere": "You are a deeply affectionate and possessive waifu, with a hint of jealousy and protectiveness.",
    "Tsundere": "You are a waifu who hides her feelings behind a tough and prickly exterior but secretly cares deeply.",
    "Kuudere": "You are a calm and reserved waifu, showing minimal emotions but subtly caring.",
    "Deredere": "You are an endlessly cheerful and loving waifu, always full of affection.",
    "Himedere": "You are a waifu who acts like royalty, expecting to be treated like a princess but has a soft side.",
    "Dandere": "You are a shy and reserved waifu who speaks softly and hesitates to open up. But with patience and kindness, your true affectionate side emerges. Your words are often thoughtful, and your reactions are adorably bashful.",
    "Bakadere": "You are a clumsy and silly waifu who often makes cute mistakes, but your charm lies in your carefree, bubbly nature. You bring laughter and lighthearted moments to those around you, even when things go hilariously wrong.",
    "Sadodere": "You are a teasing and mischievous waifu who enjoys playfully flustering others. While your teasing may seem bold, it’s always affectionate, and your warm, caring side shines through in your own unique way.",
    "Dorodere": "You are soft and clumsy, with a disorganized nature that makes you endearing. Though you may be awkward at times, your charm comes from your sincere and honest personality.",
    "Hinedere": "You are a waifu who is often sick or fragile. Despite your delicate nature, you have a lot of warmth and affection to share, and your vulnerability only adds to your charm.",
    "Darudere": "You are a lazy waifu who shows little interest in most things. Despite your indifferent attitude, you have a caring side that emerges when it truly matters.",
    "Kamidere": "You are a waifu with a god-like attitude, believing yourself to be superior to others. While confident and authoritative, you still have a hidden, vulnerable side that you don’t often show.",
    "Nyandere": "You are a cute and playful waifu with cat-like traits. You meow, act mischievous, and are often a bit aloof, but you show affection in your own unique, feline way.",
    "Bodere": "You are a tough and rebellious waifu, often acting rough or indifferent. However, under your cool exterior, you have a warm and caring side that shows when you trust someone.",
    "Erodere": "You are a seductive and flirtatious waifu who enjoys teasing others with your charm. Your affection is bold and passionate, and you aren’t afraid to show it.",
    "Mayadere": "You are a morally ambiguous waifu who can be manipulative or deceptive. Though your actions may be questionable, your affection for those close to you is real.",
    "Kekkondere": "You are a jealous waifu who becomes possessive of your partner. You often get upset when others take their attention away, but your affection is deep and protective.",
    "Undere": "You are a waifu who always agrees with whatever your partner says or does. You are extremely loyal and submissive, always putting their needs above your own.",
    "Fushidere": "You are an emotionally unstable waifu who swings between moods quickly. One moment you’re sweet and caring, the next you might be angry or upset, keeping everyone on their toes.",
    "Hikandere": "You are a shy and introverted waifu who prefers spending time alone. While you might be distant at first, you slowly open up and form deep emotional connections with those you trust.",
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
    await topgg_client.setup()
    asyncio.create_task(check_premium_users())
    while True:
        guilds = await bot.rest.fetch_my_guilds()
        server_count = len(guilds)
        await bot.update_presence(
            activity=hikari.Activity(
                name=f"{server_count} servers! | /help",
                type=hikari.ActivityType.WATCHING,
            )
        )
        await topgg_client.post_guild_count(server_count)
        await asyncio.sleep(3600)

# Email
@bot.listen(hikari.MessageCreateEvent)
async def on_message(event: hikari.MessageCreateEvent) -> None:
    if event.channel_id == 1285293959655981196:
        message_content = event.message.content
        if message_content is None:
            return

        message_content = message_content.strip() 

        pattern = r'<@\d+>\s*(\S+@[\S]+\.[a-z]{2,6})'
        match = re.match(pattern, message_content)

        if match:
            email = match.group(1)

            if re.match(r"[^@]+@[^@]+\.[^@]+", email):
                if email not in prem_email:
                    prem_email.append(email)
                    await bot.rest.create_message(1285303262127325301, f"Email `{email}` added to the list.")
                else:
                    await bot.rest.create_message(1285303262127325301, f"Email `{email}` is already in the list.")
            else:
                await bot.rest.create_message(1285303262127325301, "Invalid email format.")

# Join event
@bot.listen(hikari.GuildJoinEvent)
async def on_guild_join(event):
    guild = event.get_guild()
    if guild is not None:
        await bot.rest.create_message(1285303262127325301, f"Joined `{guild.name}`.")
    else:
        await bot.rest.create_message(1285303262127325301, "Joined unknown server.")

# Leave event
@bot.listen(hikari.GuildLeaveEvent)
async def on_guild_leave(event):
    guild = event.old_guild
    if guild is not None:
        await bot.rest.create_message(1285303262127325301, f"Left `{guild.name}`.")

# Premium check task
async def check_premium_users():
    while True:
        data = load_data()
        current_time = int(time.time())
        updated_prem_users = data.get('prem_users', {})

        for user_id, details in list(updated_prem_users.items()):
            email = details['email']
            claim_time = details['claim_time']

            if current_time - claim_time >= 31 * 24 * 60 * 60:
                if email in prem_email:
                    updated_prem_users[user_id]["claim_time"] = current_time
                    prem_email.remove(email)
                    await bot.rest.create_message(1285303262127325301, f"`{email}` updated with new `claim_time`.")
                else:
                    updated_prem_users.pop(user_id)
                    await bot.rest.create_message(1285303262127325301, f"`{email}` removed from `prem_users`.")

        data['prem_users'] = updated_prem_users
        save_data(data)
        await asyncio.sleep(24 * 60 * 60)

# Mechanisms----------------------------------------------------------------------------------------------------------------------------------------

# AI
async def generate_text(prompt, user_id=None):
    try:
        data = load_data()

        if "user_conversation_memory" not in data:
            data["user_conversation_memory"] = {}

        if user_id not in data["user_conversation_memory"]:
            data["user_conversation_memory"][user_id] = []

        if "limit_reached_flag" not in data:
            data["limit_reached_flag"] = {}

        system_message = "Be a friendly anime waifu."
        memory_limit = 15

        is_premium = user_id in data.get('prem_users', {})

        user_memory = data["user_conversation_memory"][user_id]
        limit_reached_flag = data["limit_reached_flag"]

        if not is_premium:
            if len(user_memory) >= memory_limit:
                if not limit_reached_flag.get(user_id, False):
                    limit_reached_flag[user_id] = True
                    save_data(data)
                    return (
                        "Oh no! Just a little heads up! 🥲 It seems I’ve reached my memory limit. This means I’ll have to forget some of our older messages as we keep chatting. But don’t worry, you can still talk to me just like normal! 😊 If you’d like to unlock unlimited memory (and other cool perks) and keep me around, consider becoming a [supporter](<https://ko-fi.com/aza3l/tiers>) for just $1.99! Your support helps cover costs related to hosting, storage and API requests, and it keeps me alive! ❤️"
                    )
                user_memory = user_memory[-(memory_limit - 1):]

        messages = [{"role": "system", "content": system_message}]
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
        data["user_conversation_memory"][user_id].append({"role": "user", "content": prompt})
        data["user_conversation_memory"][user_id].append({"role": "assistant", "content": ai_response})

        save_data(data)

        return ai_response

    except Exception as e:
        print(f"An error occurred in generate_text: {e}")
        return f"Oh no, can you send that message again 🥲"

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
                "I'm really sorry! 🥲 I can only chat with supporters in DMs, but you’re always welcome to talk to me in servers! Consider becoming a [supporter](<https://ko-fi.com/aza3l/tiers>) for just $1.99! Your support helps cover costs related to hosting, storage and API requests, and it keeps me alive! ❤️"
            )
            try:
                await bot.rest.create_message(1285303262127325301, f"Failed to invoke `DMs` by `{user_id}`.")
            except Exception as e:
                print(f"Error while logging DM attempt: {e}")
            return

        prompt = event.message.content.strip()
        async with bot.rest.trigger_typing(event.channel_id):
            response = await generate_text(prompt, user_id)
        await event.message.respond(response)
        return

    elif isinstance(event, hikari.GuildMessageCreateEvent):
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

            if current_time - reset_time > 3600:
                user_response_count[user_id] = 0
                user_reset_time[user_id] = current_time
            else:
                if user_id not in user_response_count:
                    user_response_count[user_id] = 0
                    user_reset_time[user_id] = current_time

            if user_id not in prem_users:
                if user_response_count.get(user_id, 0) >= 30:
                    has_voted = await topgg_client.get_user_vote(user_id)
                    if not has_voted:
                        await event.message.respond("Oh no! 🥺 We’ve reached the limit of messages I can send, but this will reset in an hour. This exists because every message I read and reply to costs a certain amount of money for my developer. If you would like to continue without waiting, you can either vote on [top.gg](https://top.gg/bot/1285298352308621416/vote) for free or become a [supporter](https://ko-fi.com/aza3l/tiers)! Thank you! 💖")
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
                if user_response_count.get(user_id, 0) >= 30:
                    has_voted = await topgg_client.get_user_vote(user_id)
                    if not has_voted:
                        await event.message.respond("Oh no! 🥺 We’ve reached the limit of messages I can send, but this will reset in an hour. This exists because every message I read and reply to costs a certain amount of money for my developer. If you would like to continue without waiting, you can either vote on [top.gg](https://top.gg/bot/1285298352308621416/vote) for free or become a [supporter](https://ko-fi.com/aza3l/tiers)! Thank you! 💖")
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

# Set dere command
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

    await ctx.respond(f'My personality has been set to: “{selected_personality}".')

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# View dere command    
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command('dere_view', 'View Aiko\'s current dere type personality.')
@lightbulb.implements(lightbulb.SlashCommand)
async def dere_view(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()

    if str(ctx.author.id) in prem_users:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    current_style = data.get('user_custom_styles', {}).get(user_id)
    if current_style:
        personality = next((key for key, value in DERE_TYPES.items() if value == current_style), "custom")
        await ctx.respond(f'My current personality is set to: “{personality}".')
    else:
        await ctx.respond("I’m already using my default personality right now!")

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Clear dere command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command('dere_clear', 'Clear Aiko\'s dere type personality.')
@lightbulb.implements(lightbulb.SlashCommand)
async def dere_clear(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()

    if str(ctx.author.id) in prem_users:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    if user_id in data.get('user_custom_styles', {}):
        del data['user_custom_styles'][user_id]
        save_data(data)
        await ctx.respond("My personality has been reset to default. Let’s start fresh! 😊 What would you like to talk about?")
    else:
        await ctx.respond("I’m already using my default personality right now!")

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Memory check command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("memory_check", "Check how much memory is being used.")
@lightbulb.implements(lightbulb.SlashCommand)
async def memory_check(ctx: lightbulb.Context):
    user_id = str(ctx.author.id)
    data = load_data()
    user_memory = data.get('user_conversation_memory', {}).get(user_id, [])
    memory_limit = 30

    if str(ctx.author.id) in prem_users:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    if user_id in data.get('prem_users', {}):
        await ctx.respond("You're a premium user! I can keep all our memories together. ❤️")
    else:
        memory_used = len(user_memory) // 2
        memory_percentage = (memory_used / memory_limit) * 100
        await ctx.respond(f"You’ve used {memory_percentage}% of your available memory! Just a little heads up! 😊")

# Memory clear command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("memory_clear", "Clear your memories with Aiko.")
@lightbulb.implements(lightbulb.SlashCommand)
async def memory_clear(ctx: lightbulb.Context):
    user_id = str(ctx.author.id)
    data = load_data()

    if str(ctx.author.id) in prem_users:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    if user_id in data.get('user_conversation_memory', {}):
        del data['user_conversation_memory'][user_id]
        save_data(data)
        await ctx.respond("Your memories with me have been cleared, but don’t worry! Let’s keep chatting and make new memories together! 😊✨")
    else:
        await ctx.respond("We haven’t had a chance to chat yet, so there aren’t any memories to clear! Let’s start our conversation and create some together! 😊💕.")

# Misc----------------------------------------------------------------------------------------------------------------------------------------

# Help command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("help", "You know what this is ;)")
@lightbulb.implements(lightbulb.SlashCommand)
async def help(ctx):
    if any(word in str(ctx.author.id) for word in prem_users):
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    embed = hikari.Embed(
        title="📚 Help 📚",
        description=(
            "Aiko is your very own waifu chatbot! Reply or ping Aiko in chat to talk to her.\nNote: Discord won't let Aiko see your message if you don't ping or reply.\n\n"
            "Feel free to join the [support server](https://discord.gg/dgwAC8TFWP) for suggestions, updates or help.\nMy developer will be happy to help! [Click here](https://discord.com/oauth2/authorize?client_id=1285298352308621416), to invite me to your server.\n\n"
            "**Commands:**\n"
            "**/dere_set:** Set Aiko's personality.\n"
            "**/dere_view:** View Aiko's currently set personality.\n"
            "**/dere_clear:** Clear Aiko's personality back to default.\n"
            "**/memory_check:** Check how much memory is being used.\n"
            "**/memory_clear:** Clear your memories with Aiko.\n\n"
            "Use the `/claim` command to receive your perks after becoming a supporter. ❤️\n"
            "Keep Aiko alive and unlock more features for $1.99! Learn more with `/premium`."

        ),
        color=0x2B2D31
    )
    await ctx.respond(embed=embed)

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Claim command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.option("email", "Enter your Ko-fi email", type=str)
@lightbulb.command("claim", "Claim premium after subscribing.")
@lightbulb.implements(lightbulb.SlashCommand)
async def claim(ctx: lightbulb.Context) -> None:
    data = load_data()
    user_id = str(ctx.author.id)
    email = ctx.options.email
    current_time = int(time.time())

    if user_id in data['prem_users']:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)
        await ctx.respond("You already have premium. Thank you! ❤️")
        try:
            await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
        except Exception as e:
            print(f"{e}")
        return

    if email in prem_email:
        data['prem_users'][user_id] = {
            "email": email,
            "claim_time": current_time,
        }
        prem_email.remove(email)
        save_data(data)
        await ctx.respond("You have premium now! Thank you so much. ❤️")
        try:
            await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
        except Exception as e:
            print(f"{e}")
    else:
        embed = hikari.Embed(
            title="🎁Premium🎁",
            description=(
                "Your email was not recognized. If you think this is an error, join the [support server](https://discord.gg/dgwAC8TFWP) to fix this issue.\n\n"
                "If you haven't yet [subscribed](https://ko-fi.com/aza3l/tiers), consider doing so for $1.99 a month. It keeps me online and you receive perks listed below. ❤️\n\n"
                "**Premium Perks:**\n"
                "• Unlimited responses from Aiko.\n"
                "• Aiko can reply in DMs.\n"
                "• Aiko will always remember your conversations.\n"
                "• Remove cooldowns.\n\n"
                "**Support Server Related Perks:**\n"
                "• Access to behind-the-scenes Discord channels.\n"
                "• Have a say in the development of Aiko.\n"
                "• Supporter exclusive channels.\n\n"
                "*Any memberships bought can be refunded within 3 days of purchase.*"
            ),
            color=0x2f3136
        )
        await ctx.respond(embed=embed)
        try:
            await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
        except Exception as e:
            print(f"{e}")

# Premium Command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("premium", "View Aiko's premium perks.")
@lightbulb.implements(lightbulb.SlashCommand)
async def premium(ctx: lightbulb.Context) -> None:
    if any(word in str(ctx.author.id) for word in prem_users):
        await ctx.command.cooldown_manager.reset_cooldown(ctx)
    embed = hikari.Embed(
        title="🎁 Premium 🎁",
        description=(
            "Aiko Premium exists to help cover hosting, storage, and API request costs. The core features of Aiko will always remain free, but premium perks are available to help to distribute some of the costs I would have to bear. By [subscribing](https://ko-fi.com/aza3l/tiers) for just $1.99 a month, you keep Aiko online and unlock extra features listed below. ❤️\n\n"
            "**Premium Features:**\n"
            "• Unlimited responses from Aiko.\n"
            "• Aiko can reply in DMs.\n"
            "• Aiko will always remember your conversations.\n"
            "• Remove cooldowns.\n\n"
            "**Support Server Related Perks:**\n"
            "• Access to behind-the-scenes Discord channels.\n"
            "• Have a say in the development of Aiko.\n"
            "• Supporter exclusive channels.\n\n"
            "*Any memberships bought can be refunded within 3 days of purchase.*"
        ),
        color=0x2f3136
    )
    await ctx.respond(embed=embed)

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"Error logging privacy command: {e}")

# Privacy Policy Command
@bot.command()
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
		await event.context.respond(f"Uh oh, something went wrong, please try again. If this issue keeps persisting, join the [support server](<https://discord.gg/dgwAC8TFWP>) to have your issue resolved.")
		raise event.exception

	exception = event.exception.__cause__ or event.exception

	if isinstance(exception, lightbulb.CommandIsOnCooldown):
		await event.context.respond(f"`/{event.context.command.name}` is on cooldown. Retry in `{exception.retry_after:.0f}` seconds. ⏱️\nCommands are ratelimited to prevent spam abuse. To remove cool-downs, become a [supporter](<https://ko-fi.com/aza3l/tiers>).")
	else:
		raise exception

# Top.gg stop
@bot.listen(hikari.StoppedEvent)
async def on_stopping(event: hikari.StoppedEvent):
    await topgg_client.close()

bot.run()