import random
import discord
from discord.ext import tasks, commands

# Your game channel ID (replace with your actual channel)
GAME_CHANNEL_ID = 1409097497112088627  

leaderstats = {}  # {user_id: {"correct": int, "tries": int}}
current_word = None
pinned_message = None


# --- WORD GENERATOR ---
def get_new_word():
    words = ["python", "discord", "banana", "gaming", "leaderboard", "ephemeral", "openai"]
    return random.choice(words)


# --- GUESS MODAL ---
class GuessModal(discord.ui.Modal, title="Guess the Word"):
    guess = discord.ui.TextInput(label="Enter your guess", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        global current_word
        user_id = interaction.user.id
        game_channel = interaction.client.get_channel(GAME_CHANNEL_ID)

        if user_id not in leaderstats:
            leaderstats[user_id] = {"correct": 0, "tries": 0}

        leaderstats[user_id]["tries"] += 1

        if self.guess.value.lower() == current_word.lower():
            leaderstats[user_id]["correct"] += 1

            # Private confirmation
            await interaction.response.send_message(
                f"✅ Correct! The word was **{current_word}** 🎉\n"
                f"Stats: {leaderstats[user_id]['correct']} correct / {leaderstats[user_id]['tries']} tries",
                ephemeral=True
            )

            # Public announcement
            await game_channel.send(
                f"🎉 <@{user_id}> guessed the word correctly! The word was **{current_word}** with {leaderstats[user_id]['tries'] tries."
            )
        else:
            await interaction.response.send_message(
                f"❌ Wrong guess. Try again!\n"
                f"Stats: {leaderstats[user_id]['correct']} correct / {leaderstats[user_id]['tries']} tries",
                ephemeral=True
            )


# --- GUESS BUTTON VIEW ---
class GuessView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Try to Guess", style=discord.ButtonStyle.primary)
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuessModal())


# --- DAILY RESET ---
@tasks.loop(hours=24)
async def reset_word(bot: commands.Bot):
    global current_word, pinned_message
    current_word = get_new_word()

    game_channel = bot.get_channel(GAME_CHANNEL_ID)

    # delete all messages except pinned
    await game_channel.purge(limit=100, check=lambda m: not m.pinned)

    # reset pinned message
    if pinned_message:
        try:
            await pinned_message.unpin()
        except:
            pass

    view = GuessView()
    pinned_message = await game_channel.send("📌 **[GUESS THE WORD]**\nClick below to try your guess!", view=view)
    await pinned_message.pin()

    print(f"[RESET] New word is: {current_word}")


@reset_word.before_loop
async def before_reset_word():
    await discord.Client.wait_until_ready


# --- LEADERBOARD COMMAND ---
async def leaderboard(interaction: discord.Interaction):
    if not leaderstats:
        await interaction.response.send_message("No guesses yet!", ephemeral=True)
        return

    sorted_stats = sorted(leaderstats.items(), key=lambda x: x[1]["correct"], reverse=True)
    leaderboard_text = "\n".join(
        [f"<@{user}> — {stats['correct']} correct / {stats['tries']} tries"
         for user, stats in sorted_stats[:10]]
    )

    embed = discord.Embed(
        title="🏆 Leaderboard",
        description=leaderboard_text,
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


# --- SETUP FUNCTION ---
def setup_game(bot: commands.Bot):
    # Register leaderboard command
    @bot.tree.command(name="leaderboard", description="Show top guessers")
    async def _leaderboard(interaction: discord.Interaction):
        await leaderboard(interaction)

    # Start reset loop
    @bot.event
    async def on_ready():
        global current_word, pinned_message
        if not reset_word.is_running():
            reset_word.start(bot)

        # initialize pinned message on first run
        if not current_word:
            current_word = get_new_word()
            game_channel = bot.get_channel(GAME_CHANNEL_ID)

            await game_channel.purge(limit=100, check=lambda m: not m.pinned)
            view = GuessView()
            pinned_message = await game_channel.send("📌 **[GUESS THE WORD]**\nClick below to try your guess!", view=view)
            await pinned_message.pin()

            print(f"✅ Game ready, word is: {current_word}")
