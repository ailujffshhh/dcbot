import random
import discord
from discord.ext import tasks, commands

# --- CONFIG ---
GAME_CHANNEL_ID = 1409106619689599077  # replace with your actual channel ID

# --- GAME DATA ---
leaderstats = {}
word_leaderboards = {}
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

    try:
        async for msg in channel.history(limit=100):
            if msg.pinned:
                pinned_message = msg
                continue
            await msg.delete()
    except Exception as e:
        print(f"⚠️ Failed to clear channel: {e}")

    leaderstats = {}
    word_leaderboards = {}

    new_word = choose_new_word()
    await channel.send(f"🎉 A new word has been chosen! Guess the word using the button.")
    if pinned_message:
        await channel.send(f"📌 Yesterday’s word was **{previous_word}**")

# --- MAIN HANDLER FOR GAME CHANNEL ---
async def handle_game_message(message: discord.Message, bot: commands.Bot) -> bool:
    """Return True if the message was handled by the game system."""
    if message.author.bot:
        return False

    if message.channel.id == GAME_CHANNEL_ID:
        try:
            await message.delete()
        except discord.Forbidden:
            print("⚠️ Missing permissions to delete in game channel.")
        except discord.NotFound:
            pass

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

        return True

    return False  # not handled

# --- SETUP ---
def setup_game(bot: commands.Bot):
    if not reset_game.is_running():
        reset_game.start(bot)
