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
import datetime

load_dotenv()
DATA_FILE = 'data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            data = json.load(file)
            # Ensure the "users" key exists
            if "users" not in data:
                data["users"] = {}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # New default structure
        return {
            "users": {}  # Ensure "users" key exists
        }

def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def update_data(new_data):
    data = load_data()
    # Update only the "users" key if new_data contains user updates
    if "users" in new_data:
        data["users"].update(new_data["users"])
    save_data(data)

data = load_data()

prem_email = []
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
        """Check if a user has voted for the bot on Top.gg and automatically reward them."""
        if not self.session:
            raise RuntimeError("Client session is not initialized. Call setup() first.")

        url = f"https://top.gg/api/bots/{self.bot.get_me().id}/check?userId={user_id}"
        headers = {"Authorization": self.token}

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('voted') == 1:  # User has voted
                        # Load data properly
                        all_data = load_data()
                        user_id_str = str(user_id)
                        
                        # Ensure user exists
                        user_data = create_user(all_data, user_id_str)
                        
                        # Add 50 points
                        user_data["points"] += 50  

                        # Save the updated data back
                        all_data["users"][user_id_str] = user_data  
                        save_data(all_data)  

                        print(f"✅ User {user_id_str} voted and received 50 points! New balance: {user_data['points']}")
                        return True
                else:
                    print(f"❌ Failed to check user vote: {response.status}")
                    return False
        except Exception as e:
            print(f"⚠️ Error while checking user vote: {e}")
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
    asyncio.create_task(daily_maintenance())
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
        now = datetime.datetime.now(datetime.timezone.utc)  # Use timezone-aware UTC time
        next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        time_until_reset = (next_reset - now).total_seconds()

        # Sleep until the next midnight UTC
        await asyncio.sleep(time_until_reset)

        # Perform premium check
        data = load_data()
        current_time = int(time.time())

        AVERAGE_MONTH_SECONDS = 2629000  # ~30.44 days

        for user_id, user_data in list(data["users"].items()):
            if user_data["premium"] and user_data["email"] and user_data["claim_time"]:
                if current_time - user_data["claim_time"] >= AVERAGE_MONTH_SECONDS:
                    if user_data["email"] in prem_email:
                        user_data["claim_time"] = current_time
                        prem_email.remove(user_data["email"])
                        await bot.rest.create_message(1285303262127325301, f"`{user_data['email']}` renewed premium.")
                    else:
                        user_data["premium"] = False
                        user_data["email"] = None
                        user_data["claim_time"] = None
                        await bot.rest.create_message(1285303262127325301, f"`{user_data['email']}` premium expired.")

        save_data(data)

# Create user
def create_user(data, user_id):
    """Create a new user entry in the data if it doesn't exist."""
    if "users" not in data:
        data["users"] = {}
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "premium": False,
            "email": None,
            "claim_time": None,
            "style": None,
            "limit_reached": False,
            "points": 0,
            "streak": 0,
            "last_interaction": None,
            "mood": 20,
            "memory": []
        }
        save_data(data)
    return data["users"][user_id]

# Mechanisms----------------------------------------------------------------------------------------------------------------------------------------

# AI
async def generate_text(prompt, user_id=None):
    try:
        data = load_data()
        user_data = create_user(data, user_id)

        system_message = "Be a friendly anime waifu."
        memory_limit = 50

        is_premium = user_data["premium"]
        user_memory = user_data["memory"]
        limit_reached = user_data["limit_reached"]

        if not is_premium:
            if len(user_memory) >= memory_limit:
                if not limit_reached:
                    user_data["limit_reached"] = True
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

        user_data["memory"].append({"role": "user", "content": prompt})
        user_data["memory"].append({"role": "assistant", "content": ai_response})
        save_data(data)

        return ai_response

    except Exception as e:
        print(f"An error occurred in generate_text: {e}")
        return "Oh no, can you send that message again 🥲"

# AI response message event listener
@bot.listen(hikari.MessageCreateEvent)
async def on_ai_message(event: hikari.MessageCreateEvent):
    if event.message.author.is_bot:
        return

    user_id = str(event.message.author.id)
    data = load_data()
    content = event.message.content or ""

    guild_id = str(event.guild_id) if hasattr(event, 'guild_id') else None  # Fix: Handle DMs
    is_dm = guild_id is None  # Fix: Check if it's a DM

    channel_id = str(event.channel_id)
    current_time = time.time()
    bot_id = bot.get_me().id
    bot_mention = f"<@{bot_id}>"
    mentions_bot = bot_mention in content
    references_message = event.message.message_reference is not None

    # Check if message references bot
    if references_message:
        try:
            referenced_message = await bot.rest.fetch_message(event.channel_id, event.message.message_reference.id)
            is_reference_to_bot = referenced_message.author.id == bot_id
        except (hikari.errors.ForbiddenError, hikari.errors.NotFoundError, hikari.errors.BadRequestError):
            is_reference_to_bot = False
    else:
        is_reference_to_bot = False

    if mentions_bot or is_reference_to_bot or is_dm:  # Fix: Allow DMs to trigger AI response
        user_data = create_user(data, user_id)
        is_premium = user_data["premium"]

        # Update interaction and streaks
        last_interaction = user_data.get("last_interaction")
        
        if last_interaction:
            time_diff = current_time - last_interaction
            if 86400 <= time_diff < 172800:
                if user_data["streak"] > 0:  # Only award points if streak is maintained
                    user_data["streak"] += 1
                    points_to_add = 10 + (10 * user_data["streak"])
                    if is_premium:
                        points_to_add *= 2
                    user_data["points"] += points_to_add

        user_data["last_interaction"] = current_time
        save_data(data)

        # DM rate limiting check for non-premium users
        if is_dm and not is_premium:
            reset_time = user_reset_time.get(user_id, 0)

            if current_time - reset_time > 3600:
                user_response_count[user_id] = 0
                user_reset_time[user_id] = current_time
            else:
                if user_id not in user_response_count:
                    user_response_count[user_id] = 0
                    user_reset_time[user_id] = current_time

            if user_response_count.get(user_id, 0) >= 30:
                has_voted = await topgg_client.get_user_vote(user_id)
                if not has_voted:
                    await event.message.respond("Oh no! 🥺 We’ve reached the limit of messages I can send in DMs, but this will reset in an hour. If you would like to continue without waiting, you can either vote on [top.gg](https://top.gg/bot/1285298352308621416/vote) for free or become a [supporter](https://ko-fi.com/aza3l/tiers)! Thank you! 💖")
                    user_limit_reached[user_id] = current_time
                    return
                else:
                    user_data["points"] += 50
                    if is_premium:
                        user_data["points"] += 50
                    user_data["mood"] = min(100, user_data["mood"] + 2)
                    save_data(data)

        # Generate AI response
        async with bot.rest.trigger_typing(channel_id):
            ai_response = await generate_text(content, user_id)

        user_response_count[user_id] = user_response_count.get(user_id, 0) + 1
        response_message = f"{event.message.author.mention} {ai_response}"
        
        try:
            await event.message.respond(response_message)
        except hikari.errors.ForbiddenError:
            pass

# Daily checks
async def daily_maintenance():
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        time_until_reset = (next_reset - now).total_seconds()

        # Sleep until the next midnight UTC
        await asyncio.sleep(time_until_reset)

        # Perform daily reset
        data = load_data()
        current_time = time.time()

        for user_id, user_data in data["users"].items():
            if user_data["last_interaction"]:
                days_since = (current_time - user_data["last_interaction"]) // 86400
                if days_since > 0:
                    user_data["mood"] = max(0, user_data["mood"] - 5 * days_since)
                    if days_since > 1:
                        user_data["streak"] = 0

        save_data(data)

# Commands----------------------------------------------------------------------------------------------------------------------------------------

# Set dere command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.option('personality', 'Choose a dere type for Aiko.', choices=["Default"] + list(DERE_TYPES.keys()), type=str)
@lightbulb.command('dere_set', 'Set Aiko\'s dere type personality.')
@lightbulb.implements(lightbulb.SlashCommand)
async def dere_set(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    selected_personality = ctx.options.personality

    data = load_data()
    user_data = create_user(data, user_id)

    if selected_personality == "Default":
        user_data["style"] = None
        save_data(data)
        await ctx.respond("My personality has been reset to default. Let’s start fresh! 😊 What would you like to talk about?")
    else:
        user_data["style"] = DERE_TYPES[selected_personality]
        save_data(data)
        await ctx.respond(f'My personality has been set to: “{selected_personality}".')

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Memory clear command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("memory_clear", "Clear your memories with Aiko.")
@lightbulb.implements(lightbulb.SlashCommand)
async def memory_clear(ctx: lightbulb.Context):
    user_id = str(ctx.author.id)
    data = load_data()
    user_data = create_user(data, user_id)

    if user_data["memory"]:
        user_data["memory"] = []
        save_data(data)
        await ctx.respond("Your memories with me have been cleared, but don’t worry! Let’s keep chatting and make new memories together! 😊✨")
    else:
        await ctx.respond("We haven’t had a chance to chat yet, so there aren’t any memories to clear! Let’s start our conversation and create some together! 😊💕.")

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Leaderboard
@bot.command()
@lightbulb.command("top", "View the leaderboard", auto_defer=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def leaderboard(ctx):
    data = load_data()
    current_user_id = str(ctx.author.id)
    
    # Ensure all users are properly initialized and get sorted list
    all_users = []
    for user_id in data["users"]:
        user_data = create_user(data, user_id)
        user_data["user_id"] = user_id  # Ensure user_id exists in data
        all_users.append(user_data)
    
    # Sort by points descending
    sorted_users = sorted(all_users, key=lambda x: x["points"], reverse=True)
    
    # Prepare top 10 entries
    top_10 = sorted_users[:10]
    
    # Find current user's rank and data
    current_user_rank = None
    current_user_data = None
    for index, user in enumerate(sorted_users):
        if user["user_id"] == current_user_id:
            current_user_rank = index + 1
            current_user_data = user
            break

    # Create embed
    embed = hikari.Embed(title="🏆 Leaderboard 🏆", color=0x2B2D31)
    
    # Build top 10 list
    top_list = []
    for idx, user in enumerate(top_10, 1):
        try:
            user_obj = await bot.rest.fetch_user(int(user["user_id"]))
            username = user_obj.username
        except (hikari.errors.NotFoundError, KeyError):
            username = "Unknown User"
        
        entry = (
            f"`#{idx}` {username}\n"
            f"Points: {user['points']} • "
            f"Streak: {user['streak']}"
        )
        top_list.append(entry)

    # Add top 10 to embed
    embed.add_field(
        name="Top 10 Users",
        value="\n\n".join(top_list) if top_list else "No users yet!",
        inline=False
    )

    # Add current user's position
    if current_user_data and current_user_rank:
        user_position = (
            f"`#{current_user_rank}` You\n"
            f"Points: {current_user_data['points']} • "
            f"Streak: {current_user_data['streak']}"
        )
        
        embed.add_field(
            name="\u200b",
            value=user_position,
            inline=False
        )

    embed.set_footer("Aiko is new and under extensive development.\nFeel free to visit the support server to learn more.")
    await ctx.respond(embed=embed)

# Gift command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("gift", "Spend 10 points to gift Aiko and increase her mood.")
@lightbulb.implements(lightbulb.SlashCommand)
async def gift(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()
    user_data = create_user(data, user_id)

    cost = 10
    mood_increase = 2

    # Reset cooldown for premium users
    if user_data["premium"]:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    # Check if user has enough points
    if user_data["points"] < cost:
        await ctx.respond(f"You need at least {cost} points to use this command. You currently have {user_data['points']} points. ❌")
        return

    # Deduct points and increase mood
    user_data["points"] -= cost
    user_data["mood"] = min(100, user_data["mood"] + mood_increase)
    save_data(data)

    # Send confirmation
    await ctx.respond(f"🎁 You spent {cost} points to increase Aiko's mood by {mood_increase}%! Her mood is now {user_data['mood']}%! 💖")

    # Log command usage
    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"Error logging gift command: {e}")

# Misc----------------------------------------------------------------------------------------------------------------------------------------

# Help command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("help", "You know what this is ;)")
@lightbulb.implements(lightbulb.SlashCommand)
async def help(ctx):
    user_id = str(ctx.author.id)
    data = load_data()
    user_data = create_user(data, user_id)

    if user_data["premium"]:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    embed = hikari.Embed(
        title="📚 Help 📚",
        description=(
            "**__Talking to Aiko__**\n"
            "- **Reply** or **ping** Aiko in chat to talk to her.\n"
            "- Use the `/profile` command to view all your stats.\n"
            "- Use the `/memory_clear` command to reset Aiko's memory.\n"
            "> *Note*: Discord won't let Aiko see your message if you don't ping or reply.\n\n"
            
            "**__Affection System__**\n"
            "- Earn points by talking to Aiko daily and maintaining your streak.\n"
            "- Each day the streak is maintained, you'll earn gift points.\n"
            "- You can earn additional gift points by [voting](https://top.gg/bot/1285298352308621416/vote).\n"
            "- Use the `/gift` command to spend gift points and increase Aiko's mood.\n"
            "> *Note*: If streaks are not maintained, Aiko's mood will slowly decline.\n\n"
            
            "**__Dere Types__**\n"
            "- Aiko comes with **20+ personalities**.\n"
            "- Use the `/dere_set` command to configure her personality.\n\n"
            
            "**__Premium__**\n"
            "- Premium helps cover hosting, storage, and API request costs.\n"
            "- Premium features of Aiko can be used for free by [voting](https://top.gg/bot/1285298352308621416/vote).\n"
            "- By [supporting](https://ko-fi.com/aza3l/tiers) for just **$1.99/month**, you:\n"
            "  - Unlock **2x boost** on points earned.\n"
            "  - Get **unlimited text** (in DMs) and **unlimited memory**.\n"
            "  - Access exclusive **support server perks** like behind-the-scenes channels.\n"
            "- Use the `/claim` command to receive your perks after becoming a supporter.\n\n"
            
            "**__Troubleshooting and Suggestions__**\n"
            "Join the [support server](https://discord.gg/dgwAC8TFWP) for help, suggestions, or updates. My developer will be happy to assist you! [Click here](https://discord.com/oauth2/authorize?client_id=1285298352308621416) to invite Aiko to your server.\n\n"
        ),
        color=0x2B2D31
    )
    await ctx.respond(embed=embed)

    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"{e}")

# Profile command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("profile", "View your profile.")
@lightbulb.implements(lightbulb.SlashCommand)
async def profile(ctx: lightbulb.Context):
    user_id = str(ctx.author.id)
    data = load_data()
    user_data = create_user(data, user_id)

    # Get dere type
    dere_type = "Default"
    if user_data["style"]:
        dere_type = next((k for k, v in DERE_TYPES.items() if v == user_data["style"]), "Custom")

    # Calculate memory usage
    memory_limit = 30
    memory_used = len(user_data["memory"]) // 2
    memory_percentage = round((memory_used / memory_limit) * 100) if not user_data["premium"] else "Unlimited"
    memory_status = f"{memory_percentage}%" if isinstance(memory_percentage, int) else "Unlimited"

    # Calculate mood status
    mood = user_data["mood"]
    if mood < 10:
        mood_status = "Feeling lonely 😔"
    elif mood < 30:
        mood_status = "Tired 😟"
    elif mood < 50:
        mood_status = "Neutral 😐"
    elif mood < 70:
        mood_status = "Content 😊"
    elif mood < 90:
        mood_status = "Loved 😍"
    else:
        mood_status = "Ecstatic 💖"

    # Create embed
    embed = hikari.Embed(
        color=0x2B2D31,
        description = f"Aiko is feeling `{mood_status}`"
    )
    embed.set_author(name=f"{ctx.author.username}'s Profile", icon=ctx.author.avatar_url)
    embed.add_field(name="Streak", value=f"🔥 {user_data['streak']} days", inline=True)
    embed.add_field(name="Mood", value=f"💖 {user_data['mood']}%", inline=True)
    embed.add_field(name="Points", value=f"🏅 {user_data['points']}", inline=True)
    embed.add_field(name="Memory", value=f'📀 {memory_status}', inline=True)
    embed.add_field(name="Dere", value=f'🧩 {dere_type}', inline=True)
    embed.add_field(name="Premium", value=f'{"✅ Active" if user_data["premium"] else "❌ Not Active"}', inline=True)
    embed.set_footer("Aiko is new and under extensive development.\nFeel free to visit the support server to learn more.")

    # Cooldown reset for premium
    if user_data["premium"]:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    await ctx.respond(embed=embed)

    # Log command usage
    try:
        await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
    except Exception as e:
        print(f"Error logging profile command: {e}")

# Claim command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.option("email", "Enter your Ko-fi email", type=str)
@lightbulb.command("claim", "Claim premium after subscribing.")
@lightbulb.implements(lightbulb.SlashCommand)
async def claim(ctx: lightbulb.Context) -> None:
    data = load_data()
    user_id = str(ctx.author.id)
    user_data = create_user(data, user_id)

    email = ctx.options.email
    current_time = int(time.time())

    if user_data["premium"]:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)
        await ctx.respond("You already have premium. Thank you! ❤️")
        try:
            await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
        except Exception as e:
            print(f"{e}")
        return

    if email in prem_email:
        user_data["premium"] = True
        user_data["email"] = email
        user_data["claim_time"] = current_time
        prem_email.remove(email)
        save_data(data)
        await ctx.respond("You have premium now! Thank you so much. ❤️")
        try:
            await bot.rest.create_message(1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`.")
        except Exception as e:
            print(f"{e}")
    else:
        embed = hikari.Embed(
            title="🎁 Premium 🎁",
            description=(
                "Your email was not recognized. If you think this is an error, join the [support server](https://discord.gg/dgwAC8TFWP) to fix this issue.\n\n"
                "If you haven't yet [subscribed](https://ko-fi.com/aza3l/tiers), consider doing so for $1.99 a month. It keeps me online and you receive perks listed below. ❤️\n\n"
                "**Premium Perks:**\n"
                "• 2x Daily Gift Points boost.\n"
                "• Unlimited responses from Aiko.\n"
                "• Unlimited responses in DMs.\n"
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

# Privacy Policy Command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("privacy", "View Aiko's Privacy Policy.")
@lightbulb.implements(lightbulb.SlashCommand)
async def privacy(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()
    user_data = create_user(data, user_id)

    if user_data["premium"]:
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