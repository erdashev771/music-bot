import logging
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import os 
BOT_TOKEN = os.environ.get ("BOT_TOKEN", "8651166761:AAHeBDZL03i9K8Zae-Je0GZLJeWY3_2MxeE")
DB_PATH = "music_bot.db"
 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
 
 
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS musics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            file_unique_id TEXT NOT NULL UNIQUE,
            title TEXT,
            artist TEXT,
            duration INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
 
 
def save_music(user_id, file_id, file_unique_id, title, artist, duration):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR IGNORE INTO musics (user_id, file_id, file_unique_id, title, artist, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, file_id, file_unique_id, title or "Nomsiz", artist or "Noma'lum", duration or 0))
        conn.commit()
        return c.lastrowid if c.lastrowid else None
    finally:
        conn.close()
 
 
def get_user_musics(user_id, search=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if search:
        c.execute("""
            SELECT id, file_id, title, artist, duration
            FROM musics
            WHERE user_id = ? AND (LOWER(title) LIKE ? OR LOWER(artist) LIKE ?)
            ORDER BY added_at DESC
        """, (user_id, f"%{search.lower()}%", f"%{search.lower()}%"))
    else:
        c.execute("""
            SELECT id, file_id, title, artist, duration
            FROM musics
            WHERE user_id = ?
            ORDER BY added_at DESC
        """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows
 
 
def delete_music(music_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM musics WHERE id = ? AND user_id = ?", (music_id, user_id))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted > 0
 
 
def get_music_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM musics WHERE user_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count
 
 
def format_duration(seconds):
    if not seconds:
        return "?"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"
 
 
def music_list_keyboard(musics, page=0, search=None):
    per_page = 8
    start = page * per_page
    end = start + per_page
    page_musics = musics[start:end]
 
    keyboard = []
    for music in page_musics:
        mid, file_id, title, artist, duration = music
        label = f"🎵 {title[:20]} — {artist[:15]} ({format_duration(duration)})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"play:{mid}")])
 
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"page:{page-1}:{search or ''}"))
    if end < len(musics):
        nav.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"page:{page+1}:{search or ''}"))
    if nav:
        keyboard.append(nav)
 
    return InlineKeyboardMarkup(keyboard)
 
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Salom, {user.first_name}!\n\n"
        "🎵 *Musiqa Kutubxonangizga xush kelibsiz!*\n\n"
        "Bu bot orqali siz:\n"
        "• Musiqalaringizni saqlashingiz\n"
        "• Istalgan vaqt topib tinglashingiz\n"
        "• Nomi yoki ijrochi bo'yicha qidirishingiz mumkin\n\n"
        "📌 *Asosiy buyruqlar:*\n"
        "/list — Barcha musiqalarim\n"
        "/search — Musiqa qidirish\n"
        "/stats — Statistika\n"
        "/help — Yordam\n\n"
        "▶️ Boshlash uchun menga audio fayl yuboring!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
 
 
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🆘 *Yordam*\n\n"
        "🎵 *Musiqa saqlash:*\n"
        "Faqat audio (mp3, m4a va boshqa) yuboring — avtomatik saqlanadi.\n\n"
        "📋 *Ro'yxat ko'rish:*\n"
        "/list — barcha musiqalaringiz\n\n"
        "🔍 *Qidirish:*\n"
        "/search <nom> — masalan: /search Dildora\n\n"
        "🗑️ *O'chirish:*\n"
        "Musiqa ustiga bosib, O'chirish tugmasini tanlang.\n\n"
        "📊 *Statistika:*\n"
        "/stats — nechta musiqa saqlangani"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
 
 
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = get_music_count(user_id)
    await update.message.reply_text(
        f"📊 *Statistika*\n\n"
        f"🎵 Saqlangan musiqalar: *{count} ta*",
        parse_mode="Markdown"
    )
 
 
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    musics = get_user_musics(user_id)
 
    if not musics:
        await update.message.reply_text(
            "📭 Sizda hali musiqa yo'q.\n\nMenga audio fayl yuboring — saqlashni boshlaymiz! 🎵"
        )
        return
 
    keyboard = music_list_keyboard(musics, page=0)
    await update.message.reply_text(
        f"🎵 *Musiqa kutubxonangiz* ({len(musics)} ta)\n\nTinglash uchun tanlang:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
 
 
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
 
    if not context.args:
        await update.message.reply_text(
            "🔍 Qidiruv uchun:\n/search <musiqa nomi>\n\nMasalan: /search Shahlo"
        )
        return
 
    query = " ".join(context.args)
    musics = get_user_musics(user_id, search=query)
 
    if not musics:
        await update.message.reply_text(
            f"❌ *\"{query}\"* bo'yicha hech narsa topilmadi.\n\n"
            "Boshqa kalit so'z bilan urinib ko'ring.",
            parse_mode="Markdown"
        )
        return
 
    keyboard = music_list_keyboard(musics, page=0, search=query)
    await update.message.reply_text(
        f"🔍 *\"{query}\"* bo'yicha {len(musics)} ta natija:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
 
 
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    audio = update.message.audio
 
    if not audio:
        await update.message.reply_text("⚠️ Iltimos, audio fayl yuboring.")
        return
 
    file_id = audio.file_id
    file_unique_id = audio.file_unique_id
    title = audio.title or (audio.file_name or "").replace(".mp3", "").replace(".m4a", "") or "Nomsiz"
    artist = audio.performer or "Noma'lum"
    duration = audio.duration
 
    result = save_music(user_id, file_id, file_unique_id, title, artist, duration)
 
    if result:
        await update.message.reply_text(
            f"✅ *Saqlandi!*\n\n"
            f"🎵 {title}\n"
            f"🎤 {artist}\n"
            f"⏱ {format_duration(duration)}\n\n"
            f"📋 Barcha musiqalar: /list",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "ℹ️ Bu musiqa allaqachon saqlangan!\n\n📋 /list"
        )
 
 
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
 
    if data.startswith("play:"):
        music_id = int(data.split(":")[1])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT file_id, title, artist, duration FROM musics WHERE id = ? AND user_id = ?",
                  (music_id, user_id))
        row = c.fetchone()
        conn.close()
 
        if not row:
            await query.message.reply_text("❌ Musiqa topilmadi.")
            return
 
        file_id, title, artist, duration = row
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ O'chirish", callback_data=f"delete:{music_id}"),
             InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_list")]
        ])
        await query.message.reply_audio(
            audio=file_id,
            caption=f"🎵 *{title}*\n🎤 {artist}\n⏱ {format_duration(duration)}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
 
    elif data.startswith("page:"):
        parts = data.split(":", 2)
        page = int(parts[1])
        search = parts[2] if len(parts) > 2 and parts[2] else None
 
        musics = get_user_musics(user_id, search=search)
        keyboard = music_list_keyboard(musics, page=page, search=search)
 
        title_text = f"🔍 \"{search}\" — {len(musics)} ta" if search else f"🎵 Musiqa kutubxonangiz ({len(musics)} ta)"
        await query.edit_message_text(
            f"{title_text}\n\nTinglash uchun tanlang:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
 
    elif data.startswith("delete:"):
        music_id = int(data.split(":")[1])
        success = delete_music(music_id, user_id)
        if success:
            await query.message.reply_text("🗑️ Musiqa o'chirildi!")
        else:
            await query.message.reply_text("❌ O'chirishda xatolik.")
 
    elif data == "back_to_list":
        musics = get_user_musics(user_id)
        if not musics:
            await query.message.reply_text("📭 Kutubxona bo'sh.")
            return
        keyboard = music_list_keyboard(musics, page=0)
        await query.message.reply_text(
            f"🎵 *Musiqa kutubxonangiz* ({len(musics)} ta)\n\nTinglash uchun tanlang:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
 
 
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Musiqa saqlash uchun audio fayl yuboring.\n\n"
        "📋 Musiqalarni ko'rish: /list\n"
        "🔍 Qidirish: /search <nom>\n"
        "🆘 Yordam: /help"
    )
 
 
async def main():
    init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")
 
    app = Application.builder().token(BOT_TOKEN).build()
 
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
 
    logger.info("Bot ishga tushdi...")
 
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
 
    await asyncio.Event().wait()
 
 
if __name__ == "__main__":
    asyncio.run(main())
