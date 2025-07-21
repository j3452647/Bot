from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import InputStream, AudioPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio
from config import API_ID, API_HASH, BOT_TOKEN, SESSION, OWNER_ID
from youtube_dl import YoutubeDL
import asyncio

bot = Client("MusicBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client(session_name="assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION)
vc = PyTgCalls(assistant)

queue = {}

ydl_opts = {
    'format': 'bestaudio',
    'quiet': True,
    'extract_flat': 'in_playlist'
}


def yt_search(query):
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return info['url'], info['title']
        except Exception as e:
            print(e)
            return None, None


@bot.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply("🎵 **Welcome to the Music Bot!**\nUse /play to play a song.")


@bot.on_message(filters.command("alive"))
async def alive(_, message: Message):
    await message.reply("✅ Bot is **alive** and working!")


@bot.on_message(filters.command("play") & filters.private | filters.group)
async def play(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Give a song name to play.\nExample: `/play Alone`")

    query = message.text.split(None, 1)[1]
    url, title = yt_search(query)

    if not url:
        return await message.reply("❌ Failed to find the song.")

    chat_id = message.chat.id
    if chat_id in queue:
        queue[chat_id].append(url)
        return await message.reply(f"✅ Added to queue: **{title}**")

    await vc.join_group_call(
        chat_id,
        InputStream(
            AudioPiped(url),
            audio_parameters=HighQualityAudio()
        )
    )
    queue[chat_id] = []
    await message.reply(f"▶️ Playing: **{title}**")


@bot.on_message(filters.command("skip"))
async def skip(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in queue or not queue[chat_id]:
        return await message.reply("⚠️ Nothing to skip.")
    
    url = queue[chat_id].pop(0)
    await vc.change_stream(
        chat_id,
        InputStream(
            AudioPiped(url),
            audio_parameters=HighQualityAudio()
        )
    )
    await message.reply("⏭️ Skipped to next track.")


@bot.on_message(filters.command("end"))
async def end(_, message: Message):
    chat_id = message.chat.id
    await vc.leave_group_call(chat_id)
    queue.pop(chat_id, None)
    await message.reply("⏹️ Ended the music.")


@bot.on_message(filters.command("loop"))
async def loop(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in queue or not queue[chat_id]:
        return await message.reply("⚠️ Nothing to loop.")
    
    url = queue[chat_id][0]
    queue[chat_id].insert(0, url)
    await message.reply("🔁 Looping current track.")


@vc.on_stream_end()
async def stream_end(_, update):
    chat_id = update.chat_id
    if queue.get(chat_id):
        url = queue[chat_id].pop(0)
        await vc.change_stream(
            chat_id,
            InputStream(
                AudioPiped(url),
                audio_parameters=HighQualityAudio()
            )
        )
    else:
        await vc.leave_group_call(chat_id)
        queue.pop(chat_id, None)


async def start_all():
    await assistant.start()
    await bot.start()
    await vc.start()
    print("✅ Bot and Assistant started!")
    await idle()
    await bot.stop()
    await assistant.stop()

if __name__ == "__main__":
    asyncio.run(start_all())
