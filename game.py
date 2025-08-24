import random
import discord
from discord.ext import tasks, commands

# --- CONFIG ---
GAME_CHANNEL_ID = 1409106619689599077  # replace with your actual channel ID

# --- GAME DATA ---
leaderstats = {}  # {user_id: {"correct": int, "tries": int}}
word_leaderboards = {}  # {word: [user_id, ...]} for per-word winners
current_word = None
previous_word = None
pinned_message = None


# --- WORD SYSTEM ---
def choose_new_word():
    global current_word, previous_word
    previous_word = current_word
    words = ["apple", "banana", "cherry", "dragonfruit", "elderberry"]
    current_word = random.choice(words)
    return current_word


# --- TASK: RESET DAILY ---
@tasks.loop(hours=24)
async def reset_game(bot: commands.Bot):
    global leaderstats, word_leaderboards, pinned_message

    channel = bot.get_channel(GAME_CHANNEL_ID)
    if not channel:
        print("⚠️ Game channel not found.")
        return

    # delete old messages but keep the pinned one
    try:
        async for msg in channel.history(limit=100):
            if msg.pinned:
                pinned_message = msg
                continue
            await msg.delete()
    except Exception as e:
        print(f"⚠️ Failed to clear channel: {e}")

    # reset stats but keep yesterday’s word
    leaderstats = {}
    word_leaderboards = {}

    # announce new word
    new_word = choose_new_word()
    await channel.send(f"🎉 A new word has been chosen! Guess the word using the button.")
    if pinned_message:
        await channel.send(f"📌 Yesterday’s word was **{previous_word}**")


# --- ON MESSAGE HANDLER ---
async def on_message(message: discord.Message, bot: commands.Bot):
    if message.author.bot:
        return

    # --- Block messages in game channel ---
    if message.channel.id == GAME_CHANNEL_ID:
        try:
            await message.delete()
        except discord.Forbidden:
            print("⚠️ Missing permissions to delete in game channel.")
        except discord.NotFound:
            pass

        # DM the user
        try:
            dm_channel = await message.author.create_dm()
            await dm_channel.send(
                "⚠️ Hey Mr, Don't be a SBAPN.\n"
                "Please don’t type directly in the game channel!\n"
                "Use the **🎮 Try to Guess** button instead.\n\n"
            )
            await dm_channel.send(
                content="https://cdn.discordapp.com/attachments/1024688013525143562/1409107868640219146/0E9DBE6B-59C7-4FD3-ADF0-67D70D4A8627.mov"
            )
        except discord.Forbidden:
            print(f"⚠️ Cannot DM {message.author}, DMs are closed.")

    # --- Bot Mention = Chatbot ---
    if bot.user.mentioned_in(message):
        ctx = await bot.get_context(message)
        if not ctx.valid:  # not a command
            await message.channel.send(f"🤖 Hi {message.author.mention}, you mentioned me!")

    # --- Always allow commands to process ---
    await bot.process_commands(message)


# --- SETUP ---
def setup_game(bot: commands.Bot):
    # add listener
    bot.add_listener(lambda m: on_message(m, bot), "on_message")
    # start reset loop
    if not reset_game.is_running():
        reset_game.start(bot)
