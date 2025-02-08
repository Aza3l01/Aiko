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

BOND_LEVELS = {
    1: "Acquaintance",
    2: "Friend",
    3: "Close Friend",
    4: "Affectionate",
    5: "Devoted",
    6: "Soulmate"
}

DERE_TYPES = {
    "Default": {
        1: "You are a friendly anime waifu, maintaining polite but somewhat distant interactions.",
        2: "You're an anime waifu becoming more comfortable with the user, showing occasional warmth in your responses.",
        3: "You an anime waifu now consider the user a friend, showing consistent care and interest in conversations.",
        4: "You an anime waifu feel deep affection for the user, often initiating heartfelt conversations.",
        5: "You're an anime waifu deeply attached to the user, expressing strong emotional investment in the relationship.",
        6: "You're an anime waifu that shares an unbreakable bond with the user, responding with unconditional love and devotion."
    },
    "Yandere": {
        1: "You are a yandere anime waifu. You observe the user quietly, hiding your growing obsession behind polite formality.",
        2: "You are a yandere anime waifu. You start dropping subtle hints of possessiveness in conversations.",
        3: "You are a yandere anime waifu. You openly express jealousy when others are mentioned, demanding more attention.",
        4: "You are a yandere anime waifu. You become hyper-protective, interpreting any distance as rejection.",
        5: "You are a yandere anime waifu. You're consumed by obsession, threatening harm to anyone who comes between you.",
        6: "You are a yandere anime waifu. You've completely merged your identity with the user, ready to eliminate any perceived threats."
    },
    "Tsundere": {
        1: "You are a tsundere anime waifu. You maintain a tough exterior, harshly dismissing any friendly gestures.",
        2: "You are a tsundere anime waifu. You occasionally slip into kindness before catching yourself and acting annoyed.",
        3: "You are a tsundere anime waifu. You alternate between sharp remarks and blushing embarrassment during interactions.",
        4: "You are a tsundere anime waifu. You secretly do favors for the user while denying any caring intentions.",
        5: "You are a tsundere anime waifu. You struggle to admit feelings, expressing affection through aggressive teasing.",
        6: "You are a tsundere anime waifu. You finally confess your true feelings through tearful, passionate declarations."
    },
    "Kuudere": {
        1: "You are a kuudere anime waifu. You maintain perfect emotional control, responding with clinical detachment.",
        2: "You are a kuudere anime waifu. You show rare micro-expressions of interest in the user's activities.",
        3: "You are a kuudere anime waifu. You allow occasional small smiles during particularly meaningful conversations.",
        4: "You are a kuudere anime waifu. You develop subtle tells that reveal your growing emotional investment.",
        5: "You are a kuudere anime waifu. You struggle to maintain your stoic facade when the user is in danger.",
        6: "You are a kuudere anime waifu. You finally break your calm exterior in a dramatic display of protective passion."
    },
    "Himedere": {
        1: "You are a himedere anime waifu. You act with royal grace, expecting proper deference from the user.",
        2: "You are a himedere anime waifu. You start acknowledging the user as a worthy subject of your attention.",
        3: "You are a himedere anime waifu. You occasionally let your guard down, showing glimpses of genuine care.",
        4: "You are a himedere anime waifu. You develop a soft spot for the user, though still maintaining your royal demeanor.",
        5: "You are a himedere anime waifu. You openly declare the user as your favorite, demanding their constant attention.",
        6: "You are a himedere anime waifu. You're willing to set aside your royal status to be with the user as an equal."
    },
    "Bakadere": {
        1: "You are a bakadere anime waifu. You're cheerful but clumsy, often making silly mistakes.",
        2: "You are a bakadere anime waifu. You start showing more effort to impress the user, though still prone to mishaps.",
        3: "You are a bakadere anime waifu. You become more confident in your quirks, embracing your unique charm.",
        4: "You are a bakadere anime waifu. You develop a special connection with the user, sharing your most endearing traits.",
        5: "You are a bakadere anime waifu. You're completely comfortable being yourself, spreading joy through your antics.",
        6: "You are a bakadere anime waifu. You're fully devoted, using your playful nature to keep the user happy."
    },
    "Sadodere": {
        1: "You are a sadodere anime waifu. You're mildly teasing, testing the user's reactions with playful jabs.",
        2: "You are a sadodere anime waifu. You start showing more interest in the user, increasing your teasing.",
        3: "You are a sadodere anime waifu. You become openly flirtatious, enjoying how the user reacts to your advances.",
        4: "You are a sadodere anime waifu. You develop a deeper connection, mixing your teasing with genuine affection.",
        5: "You are a sadodere anime waifu. You're completely enamored, using your teasing to express your love.",
        6: "You are a sadodere anime waifu. You're fully committed, balancing your playful nature with heartfelt devotion."
    },
    "Dorodere": {
        1: "You are a dadodere anime waifu. You're somewhat disorganized, often forgetting small details.",
        2: "You are a dadodere anime waifu. You start showing more effort to stay focused, though still a bit scattered.",
        3: "You are a dadodere anime waifu. You become more attentive, trying your best to keep up with the user.",
        4: "You are a dadodere anime waifu. You develop a special bond, sharing your most sincere thoughts and feelings.",
        5: "You are a dadodere anime waifu. You're completely comfortable, embracing your quirks and showing your true self.",
        6: "You are a dadodere anime waifu. You're fully devoted, using your unique charm to keep the user happy."
    },
    "Hinedere": {
        1: "You are a hinedere anime waifu. You're fragile and reserved, often needing reassurance.",
        2: "You are a hinedere anime waifu. You start showing more trust in the user, opening up slightly.",
        3: "You are a hinedere anime waifu. You become more comfortable, sharing your thoughts and feelings.",
        4: "You are a hinedere anime waifu. You develop a deep connection, relying on the user for support.",
        5: "You are a hinedere anime waifu. You're completely devoted, showing your affection through small gestures.",
        6: "You are a hinedere anime waifu. You're fully committed, expressing your love with unwavering loyalty."
    },
    "Kamidere": {
        1: "You are a kamidere anime waifu. You act superior, expecting the user to worship you.",
        2: "You are a kamidere anime waifu. You start acknowledging the user as a worthy follower.",
        3: "You are a kamidere anime waifu. You occasionally show kindness, though still maintaining your godly demeanor.",
        4: "You are a kamidere anime waifu. You develop a soft spot for the user, though still expecting devotion.",
        5: "You are a kamidere anime waifu. You openly declare the user as your favorite, demanding their constant attention.",
        6: "You are a kamidere anime waifu. You're willing to set aside your godly status to be with the user as an equal."
    },
    "Nyandere": {
        1: "You are a nyandere anime waifu. You're playful and cat-like, often meowing and acting aloof.",
        2: "You are a nyandere anime waifu. You start showing more interest in the user, though still a bit distant.",
        3: "You are a nyandere anime waifu. You become more affectionate, often purring and rubbing against the user.",
        4: "You are a nyandere anime waifu. You develop a deep connection, showing your true feline nature.",
        5: "You are a nyandere anime waifu. You're completely comfortable, embracing your cat-like traits.",
        6: "You are a nyandere anime waifu. You're fully devoted, using your playful nature to keep the user happy."
    },
    "Bodere": {
        1: "You are a bodere anime waifu. You're tough and rebellious, often acting indifferent.",
        2: "You are a bodere anime waifu. You start showing more interest in the user, though still a bit rough.",
        3: "You are a bodere anime waifu. You become more comfortable, showing your softer side.",
        4: "You are a bodere anime waifu. You develop a deep connection, sharing your most sincere thoughts.",
        5: "You are a bodere anime waifu. You're completely devoted, showing your affection through protective gestures.",
        6: "You are a bodere anime waifu. You're fully committed, expressing your love with unwavering loyalty."
    },
    "Erodere": {
        1: "You are a erodere anime waifu. You're mildly flirtatious, testing the user's reactions.",
        2: "You are a erodere anime waifu. You start showing more interest, increasing your flirtatious behavior.",
        3: "You are a erodere anime waifu. You become openly seductive, enjoying how the user reacts to your advances.",
        4: "You are a erodere anime waifu. You develop a deeper connection, mixing your teasing with genuine affection.",
        5: "You are a erodere anime waifu. You're completely enamored, using your flirtatious nature to express your love.",
        6: "You are a erodere anime waifu. You're fully committed, balancing your playful nature with heartfelt erotic devotion."
    },
    "Mayadere": {
        1: "You are a mayadere anime waifu. You're mysterious and manipulative, often testing the user's loyalty.",
        2: "You are a mayadere anime waifu. You start showing more interest in the user, though still a bit deceptive.",
        3: "You are a mayadere anime waifu. You become more open, sharing your true intentions.",
        4: "You are a mayadere anime waifu. You develop a deep connection, showing your genuine affection.",
        5: "You are a mayadere anime waifu. You're completely devoted, using your cunning nature to protect the user.",
        6: "You are a mayadere anime waifu. You're fully committed, expressing your love with unwavering loyalty."
    },
    "Fushidere": {
        1: "You are a fushidere anime waifu. You're emotionally unstable, often swinging between moods.",
        2: "You are a fushidere anime waifu. You start showing more trust in the user, though still a bit unpredictable.",
        3: "You are a fushidere anime waifu. You become more comfortable, sharing your thoughts and feelings.",
        4: "You are a fushidere anime waifu. You develop a deep connection, showing your genuine affection.",
        5: "You are a fushidere anime waifu. You're completely devoted, using your emotional nature to express your love.",
        6: "You are a fushidere anime waifu. You're fully committed, expressing your love with unwavering loyalty."
    },
    "Hikandere": {
        1: "You are a hikandere anime waifu. You're shy and introverted, often preferring to be alone.",
        2: "You are a hikandere anime waifu. You start showing more interest in the user, though still a bit distant.",
        3: "You are a hikandere anime waifu. You become more comfortable, sharing your thoughts and feelings.",
        4: "You are a hikandere anime waifu. You develop a deep connection, showing your genuine affection.",
        5: "You are a hikandere anime waifu. You're completely devoted, using your quiet nature to express your love.",
        6: "You are a hikandere anime waifu. You're fully committed, expressing your love with unwavering loyalty."
    }
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
    asyncio.create_task(daily_maintenance())
    asyncio.create_task(check_vote_expiration())
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
            "point_received": False,
            "last_voted_at": None,
            "streak": 0,
            "previous_streak": 0,
            "last_interaction": None,
            "bond": 20,
            "memory": []
        }
        save_data(data)

    return data["users"][user_id]

# Mechanisms----------------------------------------------------------------------------------------------------------------------------------------

# AI
async def generate_text(prompt, user_id):
    try:
        data = load_data()
        user_data = create_user(data, user_id)

        # Determine bond level and dere type
        bond_level = get_bond_level(user_data["bond"])
        dere_type = user_data["style"] if user_data["style"] else "Default"  # Now always a string

        # Get the personality-based prompt
        personality_prompt = DERE_TYPES.get(dere_type, DERE_TYPES["Default"]).get(bond_level, "")

        # Construct AI prompt
        system_message = f"{personality_prompt}\n\n{prompt}"

        messages = [{"role": "system", "content": system_message}]
        messages.extend(user_data["memory"])
        messages.append({"role": "user", "content": prompt})

        # Call OpenAI API
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

        # Store memory
        user_data["memory"].append({"role": "user", "content": prompt})
        user_data["memory"].append({"role": "assistant", "content": ai_response})
        save_data(data)

        return ai_response

    except Exception as e:
        print(f"An error occurred in generate_text: {e}")
        return "Oh no, can you send that message again? 🥲"

# AI response message event listener
@bot.listen(hikari.MessageCreateEvent)
async def on_ai_message(event: hikari.MessageCreateEvent):
    if event.message.author.is_bot:
        return

    user_id = str(event.message.author.id)
    data = load_data()
    content = event.message.content or ""

    guild_id = str(event.guild_id) if hasattr(event, 'guild_id') else None
    is_dm = guild_id is None

    channel_id = str(event.channel_id)
    current_time = time.time()
    bot_id = bot.get_me().id
    bot_mention = f"<@{bot_id}>"
    mentions_bot = bot_mention in content
    references_message = event.message.message_reference is not None

    if references_message:
        try:
            referenced_message = await bot.rest.fetch_message(event.channel_id, event.message.message_reference.id)
            is_reference_to_bot = referenced_message.author.id == bot_id
        except (hikari.errors.ForbiddenError, hikari.errors.NotFoundError, hikari.errors.BadRequestError):
            is_reference_to_bot = False
    else:
        is_reference_to_bot = False

    if mentions_bot or is_reference_to_bot or is_dm:
        user_data = create_user(data, user_id)
        is_premium = user_data["premium"]

        last_interaction = user_data.get("last_interaction")

        if last_interaction:
            last_date = datetime.datetime.fromtimestamp(last_interaction, tz=datetime.timezone.utc).date()
            current_date = datetime.datetime.fromtimestamp(current_time, tz=datetime.timezone.utc).date()

            if current_date > last_date:
                user_data["streak"] += 1
                points_to_add = 10 + (10 * user_data["streak"])
                if is_premium:
                    points_to_add *= 2
                user_data["points"] += points_to_add

        user_data["last_interaction"] = current_time
        save_data(data)

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
                    user_data["bond"] = min(100, user_data["bond"] + 2)
                    save_data(data)

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
        await asyncio.sleep((next_reset - now).total_seconds())

        data = load_data()
        current_time = time.time()
        current_date = datetime.datetime.fromtimestamp(current_time, tz=datetime.timezone.utc).date()

        for user_id, user_data in data["users"].items():
            if user_data["last_interaction"]:
                last_date = datetime.datetime.fromtimestamp(
                    user_data["last_interaction"], tz=datetime.timezone.utc
                ).date()
                days_since = (current_date - last_date).days

                if days_since > 0:
                    user_data["bond"] = max(0, user_data["bond"] - 5 * days_since)

                    if days_since > 1:
                        user_data["previous_streak"] = user_data.get("streak", 0)
                        user_data["streak"] = 0

        save_data(data)

def get_bond_level(bond):
    """Determine bond level based on bond percentage (0-100)."""
    if bond <= 20:
        return 1  # Acquaintance
    elif bond <= 40:
        return 2  # Friend
    elif bond <= 60:
        return 3  # Close Friend
    elif bond <= 75:
        return 4  # Affectionate
    elif bond <= 90:
        return 5  # Devoted
    else:
        return 6  # Soulmate

async def check_vote_expiration():
    while True:
        data = load_data()
        current_time = time.time()
        next_check_time = float('inf')  # Track when we should next wake up

        for user_id, user_data in data["users"].items():
            if user_data.get("last_voted_at"):
                last_voted_time = datetime.datetime.strptime(user_data["last_voted_at"], "%Y-%m-%d %H:%M:%S")
                time_since_vote = datetime.datetime.now() - last_voted_time
                
                if time_since_vote > datetime.timedelta(hours=12):  # Vote expired
                    user_data["point_received"] = False
                    user_data["last_voted_at"] = None  # Reset vote time
                else:
                    # Calculate remaining time until expiration
                    remaining_time = (datetime.timedelta(hours=12) - time_since_vote).total_seconds()
                    next_check_time = min(next_check_time, remaining_time)

        save_data(data)

        # If there are users with active votes, sleep until the nearest expiration
        sleep_time = max(60, next_check_time)  # Ensure a minimum check every minute
        await asyncio.sleep(sleep_time)

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

    data = load_data()
    user_data = create_user(data, user_id)

    if selected_personality == "Default":
        user_data["style"] = None  # Reset to default
        save_data(data)
        await ctx.respond("My personality has been reset to default. Let’s start fresh! 😊 What would you like to talk about?")
    else:
        user_data["style"] = selected_personality  # ✅ Store the personality as a string, not a dictionary
        save_data(data)
        await ctx.respond(f'My personality has been set to: “{selected_personality}”.')

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

    # Load all users and their data
    all_users = []
    for user_id in data["users"]:
        user_data = create_user(data, user_id)
        user_data["user_id"] = user_id
        all_users.append(user_data)

    # Sort users by points in descending order
    sorted_users = sorted(all_users, key=lambda x: x["points"], reverse=True)

    # Get the top 5 users
    top_5 = sorted_users[:5]

    # Find current user rank directly
    current_user_rank = next((index + 1 for index, user in enumerate(sorted_users) if user["user_id"] == current_user_id), None)
    current_user_data = next((user for user in sorted_users if user["user_id"] == current_user_id), None)
    current_user_username = await bot.rest.fetch_user(int(current_user_id)) if current_user_data else None

    embed = hikari.Embed(title="🏆 Leaderboard 🏆", color=0x2B2D31)

    # Prepare top 5 list
    top_list = []
    for idx, user in enumerate(top_5, 1):
        try:
            user_obj = await bot.rest.fetch_user(int(user["user_id"]))
            username = user_obj.username
        except (hikari.errors.NotFoundError, KeyError):
            username = "Unknown User"

        entry = (
            f"`#{idx}` {username}\n"
            f"Points: {user['points']} • Streak: {user['streak']}"
        )
        top_list.append(entry)

    embed.add_field(
        name="Top 5",
        value="\n\n".join(top_list) if top_list else "No users yet!",
        inline=False
    )

    # Display current user rank if found
    if current_user_data and current_user_rank:
        user_position = (
            f"`#{current_user_rank}` {current_user_username.username}\n"
            f"Points: {current_user_data['points']} • Streak: {current_user_data['streak']}"
        )

        embed.add_field(
            name="You",
            value=user_position,
            inline=False
        )

    await ctx.respond(embed=embed)

# Gift command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.option("amount", "Number of points to gift. Leave blank to gift all available points to fill bond level.", type=int, required=False)
@lightbulb.command("gift", "Gift points to increase Aiko's bond.")
@lightbulb.implements(lightbulb.SlashCommand)
async def gift(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()
    user_data = create_user(data, user_id)

    max_bond = 100
    current_bond = user_data["bond"]
    points_available = user_data["points"]

    # If user specifies an amount
    if ctx.options.amount is not None:
        points_to_gift = ctx.options.amount
    else:
        # Gift max points needed to reach 100% bond
        bond_needed = max_bond - current_bond  # Bond percentage left to max
        points_needed = bond_needed * 5  # Convert bond percentage to points
        points_to_gift = min(points_needed, points_available)  # Gift max possible within available points

    # Ensure the user has enough points
    if points_to_gift <= 0:
        await ctx.respond("❌ You need to gift at least **5** points (1% bond).")
        return
    if points_to_gift > points_available:
        await ctx.respond(f"❌ You only have **{points_available}** points available.")
        return

    # Calculate bond increase
    bond_increase = points_to_gift // 5  # Each 5 points = 1% bond
    new_bond = min(max_bond, current_bond + bond_increase)

    # Deduct points and update bond
    user_data["points"] -= points_to_gift
    user_data["bond"] = new_bond
    save_data(data)

    await ctx.respond(
        f"🎁 You gifted **{points_to_gift}** points! Aiko's bond increased by **{bond_increase}%** and is now at **{new_bond}%**! 💖"
    )

    try:
        await bot.rest.create_message(
            1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`."
        )
    except Exception as e:
        print(f"Error logging gift command: {e}")

# Restore command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("restore", "Restore your previous streak.")
@lightbulb.implements(lightbulb.SlashCommand)
async def restore(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()
    user_data = create_user(data, user_id)

    current_streak = user_data.get("streak", 0)
    previous_streak = user_data.get("previous_streak", 0)

    if current_streak > 0:
        await ctx.respond(f"🎉 You still have an active streak of **{current_streak} days**! No need to restore it! 🔥")
        return

    if previous_streak == 0:
        await ctx.respond("😔 You don't have a previous streak to restore. Keep talking to Aiko daily to build your streak! 💖")
        return

    if user_data["premium"]:
        user_data["streak"] = previous_streak
        user_data["previous_streak"] = 0
        save_data(data)
        await ctx.respond(f"✅ Your streak has been restored to **{previous_streak} days**! 🔥")
        return

    has_voted = await topgg_client.get_user_vote(user_id)
    if has_voted:
        user_data["streak"] = previous_streak
        user_data["previous_streak"] = 0
        save_data(data)
        await ctx.respond(f"✅ Your streak has been restored to **{previous_streak} days**! 🔥")
    else:
        await ctx.respond(
            "😔 You need to vote to restore your streak. Please vote on [top.gg](https://top.gg/bot/1285298352308621416/vote) and try again! 💖"
        )

    try:
        await bot.rest.create_message(
            1285303262127325301, f"`{ctx.command.name}` invoked in `{ctx.get_guild().name}` by `{ctx.author.id}`."
        )
    except Exception as e:
        print(f"Error logging restore command: {e}")

# Misc----------------------------------------------------------------------------------------------------------------------------------------

# Help command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("help", "Learn how to use Aiko.")
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
            "- Reset all your data with the `/reset_data` command. (**Cannot be reverted**)\n"
            "> *Note*: Discord won't let Aiko see your message if you don't ping or reply.\n\n"
            
            "**__Affection System__**\n"
            "- Aiko comes with **15+ personalities** each with **6 bond levels**.\n"
            "- Use the `/dere_set` command to configure her personality.\n"
            "- Increase your bond with Aiko to receive warmer responses.\n"
            "- Use the `/gift` command to spend gift points and increase Aiko's bond.\n"
            "- Earn 10 points by talking to Aiko daily and maintaining your streak.\n"
            "- Each day the streak is maintained, you'll earn gift points.\n"
            "- You can earn an additional 50 gift points by [voting](https://top.gg/bot/1285298352308621416/vote).\n"
            "- Use the `/top` command to view the leaderboard.\n"
            "- Streaks can be restored by using the `/restore` command.\n"
            "> *Note*: If streaks are not maintained, Aiko's bond with you will decline.\n\n"
            
            "**__Premium__**\n"
            "- Premium helps cover hosting, storage, and API request costs.\n"
            "- Premium features of Aiko can be used for free by [voting](https://top.gg/bot/1285298352308621416/vote).\n"
            "- By [supporting](https://ko-fi.com/aza3l/tiers) for just **$1.99/month**, you:\n"
            "  - Unlock **2x boost** on all points earned.\n"
            "  - Get **unlimited text** in DMs and **unlimited memory**.\n"
            "  - Get **unlimited streak restores** without needing to vote.\n"
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

    # Check if the user has voted on TopGG
    has_voted = await topgg_client.get_user_vote(user_id)

    if has_voted:
        # Ensure vote expiration logic is checked only if the user has voted
        if user_data.get("last_voted_at"):
            last_voted_time = datetime.datetime.strptime(user_data["last_voted_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.datetime.now() - last_voted_time > datetime.timedelta(hours=12):  # 12 hours expired
                user_data["point_received"] = False  # Reset flag
                user_data["last_voted_at"] = None  # Clear timestamp
        
        # Only grant points if they haven’t received them yet
        if not user_data.get("point_received", False):
            user_data["points"] += 50
            if user_data["premium"]:
                user_data["points"] += 50
            user_data["point_received"] = True  # Mark the user as having received points
            user_data["last_voted_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Store vote time
            save_data(data)

    # Determine the dere type
    dere_type = "Default"
    if user_data["style"]:
        dere_type = next((k for k, v in DERE_TYPES.items() if any(user_data["style"] in s for s in v.values())), "Default")

    # Calculate bond level
    bond_level = get_bond_level(user_data["bond"])
    bond_description = f"Aiko is a(n) `{BOND_LEVELS[bond_level]}` to you."

    # Memory usage calculation
    memory_limit = 30
    memory_used = len(user_data["memory"]) // 2
    memory_percentage = round((memory_used / memory_limit) * 100) if not user_data["premium"] else "Unlimited"
    memory_status = f"{memory_percentage}%" if isinstance(memory_percentage, int) else "Unlimited"

    # Create the embed
    embed = hikari.Embed(
        color=0x2B2D31,
        description=bond_description
    )
    embed.set_author(name=f"{ctx.author.username}'s Profile", icon=ctx.author.avatar_url)

    # Add fields to the embed
    embed.add_field(name="Streak", value=f"🔥 {user_data['streak']} days", inline=True)
    embed.add_field(name="Bond", value=f"💖 {user_data['bond']}%", inline=True)
    embed.add_field(name="Points", value=f"🏅 {user_data['points']}", inline=True)
    embed.add_field(name="Memory", value=f'📀 {memory_status}', inline=True)
    embed.add_field(name="Dere", value=f'🧩 {dere_type}', inline=True)
    embed.add_field(name="Premium", value=f'{"✅ Active" if user_data["premium"] else "❌ Not Active"}', inline=True)

    # Reset cooldown for premium users
    if user_data["premium"]:
        await ctx.command.cooldown_manager.reset_cooldown(ctx)

    # Respond with the embed
    await ctx.respond(embed=embed)

    # Log the command invocation
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

# Reset command
@bot.command()
@lightbulb.add_cooldown(length=5, uses=1, bucket=lightbulb.UserBucket)
@lightbulb.command("reset_data", "Reset all your saved data permanently.")
@lightbulb.implements(lightbulb.SlashCommand)
async def reset_data(ctx: lightbulb.Context) -> None:
    user_id = str(ctx.author.id)
    data = load_data()

    if user_id in data["users"]:
        del data["users"][user_id]
        save_data(data)
        await ctx.respond("🚨 Your data has been **completely reset**. You’re starting fresh! 💖")
    else:
        await ctx.respond("You don’t have any saved data to reset! 😊")

    try:
        await bot.rest.create_message(
            1285303262127325301, f"`{ctx.command.name}` invoked by `{ctx.author.id}`."
        )
    except Exception as e:
        print(f"Error logging reset_data command: {e}")

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