import discord

async def handle_chatbot_message(message: discord.Message, bot, client_ai) -> bool:
    """Return True if this handled the message (bot mention), else False."""
    if not bot.user:
        return False

    if not bot.user.mentioned_in(message):
        return False

    # Remove both <@id> and <@!id> from the content
    prompt = message.content
    prompt = prompt.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

    if not prompt:
        await message.reply("Hi! Mention me like: `@Dr. Ron what is photosynthesis?`")
        return True

    thinking_msg = await message.reply("Doc Ron is thinking...")

    try:
        response = client_ai.chat.completions.create(
            model="openai/gpt-oss-120b:fireworks-ai",
            messages=[
                {
                    "role": "system",
                    "content": "Your name is Doc Ron. You are a helpful tutor. "
                               "Respond in casual Filipino style. Limit responses to 1 sentence only."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )

        if response.choices and response.choices[0].message.content:
            answer = response.choices[0].message.content
            await thinking_msg.edit(content=f"{message.author.mention} {answer}")
        else:
            await thinking_msg.edit(content=f"{message.author.mention} ❌ No response from model.")
    except Exception as e:
        if "402" in str(e):
            await thinking_msg.edit(content=f"{message.author.mention} ❌ Monthly credit limit reached.")
        else:
            await thinking_msg.edit(content=f"{message.author.mention} ❌ Error: {str(e)}")

    return True
