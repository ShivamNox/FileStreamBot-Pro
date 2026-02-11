from ShivamNox.bot import StreamBot
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters
import time
import shutil, psutil
from utils_bot import *
from ShivamNox import StartTime


START_TEXT = """ Your Telegram DC Is : `{}`  """


@StreamBot.on_message(filters.command("maintainers"))
async def maintainers(b, m):
    try:
        await b.send_message(chat_id=m.chat.id, text="HELLO", quote=True)
    except Exception as e:
        await b.send_message(
            chat_id=m.chat.id,
            text="I am made by [ShivamNox](https://t.me/shivamnox)",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/shivamnox")
                    ]
                ]
            ),
            disable_web_page_preview=True
        )

            
         
@StreamBot.on_message(filters.command("subscribe"))
async def follow_user(b,m):
    try:
       await b.send_message(chat_id=m.chat.id,text="HELLO",quote=True)
    except Exception:
                await b.send_message(
                    chat_id=m.chat.id,
                    text="<B>HERE'S THE SUBSCRIBE LINK</B>",
                    
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("Subscribe ❤️", url=f"https://t.me/innoshiv")
                            ]
                        ]
                    ),
                    
                    disable_web_page_preview=True)
        

@StreamBot.on_message(filters.command("dc"))
async def start(bot, update):
    text = START_TEXT.format(update.from_user.dc_id)
    await update.reply_text(
        text=text,
        disable_web_page_preview=True,
        quote=True
    )


dmca = """📜 **DMCA Notice**

By clicking or generating a permanent link, you confirm that the files belong to you and do not contain any copyrighted material.

We do not host or promote copyrighted content. All files are provided by users. If a valid copyright owner submits a report, the reported file will be removed immediately.

18+ content, adult material, or nudity is strictly prohibited. Do not generate permanent links for such content.

If our admin detects any violation, your account will be immediately banned from using the bot.

Repeated or serious violations may result in permanent account restrictions or termination."""

@StreamBot.on_message(filters.command("dmca"))
async def dmca_cmd(bot, update):
    await update.reply_text(
        text=dmca,
        disable_web_page_preview=True,
        quote=True
    )


terms = """📄 **Terms & Conditions**

This bot generates direct download and streaming links for files provided by users.

By using this bot and especially by generating a **permanent link**, you agree to the following:

• You are solely responsible for the files you upload and share.
• You confirm that your content does not violate copyright laws.
• Permanent links are created at your own risk and responsibility.
• 18+ content, adult material, nudity, or illegal content is strictly forbidden.
• Do not upload or share copyrighted, pirated, or unauthorized material.

We do not verify user-uploaded files and do not claim ownership of any content.

If any violation is detected or reported:
• The content will be removed immediately.
• Your account may be temporarily or permanently banned.

By continuing to use this bot, you agree to these Terms & the /dmca policy."""


@StreamBot.on_message(filters.command("terms"))
async def terms_cmd(bot, update):
    await update.reply_text(
        text=terms,
        disable_web_page_preview=True,
        quote=True
    )


@StreamBot.on_message(filters.command("list"))
async def list(l, m):
    LIST_MSG = "Hi! {} Here is a list of all my commands \n \n 1 . `start⚡️` \n 2. `help📚` \n 3. `login🔑` \n 4.`Subscribe ❤️` \n 5. `ping📡` \n 6. `status📊` \n 7. `DC` this tells your telegram dc \n 8. `maintainers😎` "
    await l.send_message(chat_id = m.chat.id,
        text = LIST_MSG.format(m.from_user.mention(style="md"))
        
    )
    
    
@StreamBot.on_message(filters.command("ping"))
async def ping(b, m):
    start_t = time.time()
    ag = await m.reply_text("....")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await ag.edit(f"Pong!\n{time_taken_s:.3f} ms")
    
    
    
    
@StreamBot.on_message(filters.private & filters.command("status"))
async def stats(bot, update):
  currentTime = readable_time((time.time() - StartTime))
  total, used, free = shutil.disk_usage('.')
  total = get_readable_file_size(total)
  used = get_readable_file_size(used)
  free = get_readable_file_size(free)
  sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
  recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
  cpuUsage = psutil.cpu_percent(interval=0.5)
  memory = psutil.virtual_memory().percent
  disk = psutil.disk_usage('/').percent
  botstats = f'<b>Bot Uptime:</b> {currentTime}\n' \
            f'<b>Total disk space:</b> {total}\n' \
            f'<b>Used:</b> {used}  ' \
            f'<b>Free:</b> {free}\n\n' \
            f'📊Data Usage📊\n<b>Upload:</b> {sent}\n' \
            f'<b>Down:</b> {recv}\n\n' \
            f'<b>CPU:</b> {cpuUsage}% ' \
            f'<b>RAM:</b> {memory}% ' \
            f'<b>Disk:</b> {disk}%'
  await update.reply_text(botstats)
