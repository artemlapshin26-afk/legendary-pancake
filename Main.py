import telebot
import requests
from io import BytesIO
import urllib.parse
import sqlite3
from datetime import datetime, timedelta
from flask import Flask
import threading
import random
import time

# --- НАСТРОЙКИ ---
TOKEN = '8544559089:AAElVSZP62-MIKoyFhjdJPNTVtLDd_ABu0o'
DONATE_LINK = "https://www.donationalerts.com/r/temohagame"
ADMIN_ID = 760757633

bot = telebot.TeleBot(TOKEN)

# --- 🎨 СТИЛИ ---
STYLES = {
    "🗡️ Solo Leveling": "solo leveling style, manhwa, dark fantasy, detailed, action pose, shadows",
    "🌸 Аниме": "anime style, japanese animation, vibrant colors, detailed background",
    "🎭 Реализм": "photorealistic, realistic, 8k resolution, highly detailed, professional photography",
    "🏰 Фэнтези": "fantasy art, medieval, magical, epic, detailed illustration",
    "🌃 Киберпанк": "cyberpunk, neon, futuristic, sci-fi, blade runner style, dark atmosphere",
    "🎨 Масло": "oil painting, classical art, renaissance style, textured, artistic",
    "🔮 Магия": "magical girl, sparkles, fantasy, colorful, anime style, ethereal",
    "⚔️ Средневековье": "medieval, knights, castles, historical, detailed armor",
    "🚀 Космос": "space, sci-fi, stars, galaxies, futuristic, cosmic",
    "🐉 Драконы": "dragons, fantasy creatures, epic, detailed scales, mythical"
}

# --- 🗄️ БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY,
                  tier TEXT DEFAULT 'free',
                  generations_today INTEGER DEFAULT 0,
                  total_generations INTEGER DEFAULT 0,
                  last_use DATE,
                  subscribe_end DATE,
                  current_style TEXT DEFAULT '🗡️ Solo Leveling')''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    today = datetime.now().date()
    
    if not user:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                 (user_id, "free", 0, 0, today, None, "🗡️ Solo Leveling"))
        conn.commit()
        user = (user_id, "free", 0, 0, today, None, "🗡️ Solo Leveling")
    else:
        if user[5]:
            sub_end = datetime.strptime(str(user[5]), "%Y-%m-%d").date()
            if sub_end < today:
                c.execute("UPDATE users SET tier = 'free', subscribe_end = NULL WHERE user_id = ?", (user_id,))
                conn.commit()
        if str(user[4]) != str(today):
            c.execute("UPDATE users SET generations_today = 0, last_use = ? WHERE user_id = ?", (today, user_id))
            conn.commit()
    
    conn.close()
    return user

def use_generation(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET generations_today = generations_today + 1, total_generations = total_generations + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def upgrade_user(user_id, tier, days=30):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    end_date = datetime.now() + timedelta(days=days)
    c.execute("UPDATE users SET tier = ?, subscribe_end = ? WHERE user_id = ?", (tier, end_date.date(), user_id))
    conn.commit()
    conn.close()

def set_style(user_id, style_name):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET current_style = ? WHERE user_id = ?", (style_name, user_id))
    conn.commit()
    conn.close()

init_db()

# 🔥 АВТОМАТИЧЕСКАЯ АКТИВАЦИЯ PREMIUM ДЛЯ ТЕБЯ 🔥
upgrade_user(ADMIN_ID, 'premium', 9999) 

# --- 🌐 СЕРВЕР ---app = Flask('')
@app.route('/')
def home():
    return "MangaGen Bot Premium HD is running!"
def run():
    app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- 🎨 ГЕНЕРАЦИЯ ---
def generate_image(prompt, quality="normal", style_prompt=""):
    # Улучшаем качество в зависимости от уровня
    extra_quality = ""
    size = 1024
    
    if quality == "hd":
        size = 2048
        extra_quality = ", 8k resolution, ultra hd, masterpiece, best quality"
    elif quality == "premium_hd":
        size = 2048
        # Максимальные теги качества
        extra_quality = ", masterpiece, best quality, ultra detailed, 8k, raw photo, sharp focus, cinematic lighting"
    
    full_prompt = f"{prompt}, {style_prompt}{extra_quality}"
    
    seed = random.randint(100000, 999999)
    timestamp = int(time.time() * 1000)
    
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(full_prompt)}"
    url += f"?width={size}&height={size}&nologo=true&seed={seed}&nonce={timestamp}"
    
    try:
        headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}
        print(f"🎨 Генерация: {quality.upper()} | Seed: {seed}")
        response = requests.get(url, headers=headers, timeout=180)
        if response.status_code == 200 and len(response.content) > 1000:
            return response.content
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    return None

# --- 📱 КЛАВИАТУРЫ ---
def main_keyboard(tier):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if tier == "free":
        kb.add("🎨 Генерация (SD)")
        kb.add("🎭 Выбрать стиль")
        kb.add("⭐ Купить VIP", "💎 Купить PREMIUM")
        kb.add("💝 Поддержать", "📊 Статистика")
        kb.add("❓ Помощь")    elif tier == "vip":
        kb.add("🎨 Генерация (SD)")
        kb.add("🖼️ Генерация (HD)")
        kb.add("🎭 Выбрать стиль")
        kb.add("💎 Купить PREMIUM")
        kb.add("💝 Поддержать", "📊 Статистика")
        kb.add("❓ Помощь")
    else: # premium
        kb.add("🎨 Генерация (SD)")
        kb.add("🖼️ Генерация (HD)")
        kb.add("💎 Premium HD (Max)") # Отдельная кнопка
        kb.add("🎭 Выбрать стиль")
        kb.add("💝 Поддержать", "📊 Статистика")
        kb.add("❓ Помощь")
    
    return kb

def style_keyboard():
    kb = telebot.types.InlineKeyboardMarkup(row_width=2)
    for style_name in STYLES.keys():
        kb.add(telebot.types.InlineKeyboardButton(style_name, callback_data=f"style_{style_name}"))
    kb.add(telebot.types.InlineKeyboardButton("◀️ Назад", callback_data="back_main"))
    return kb

def help_text():
    return (
        "❓ **КАК ПОЛЬЗОВАТЬСЯ**\n\n"
        "🎨 **Стили:** Выбери стиль кнопкой '🎭 Выбрать стиль'\n"
        "📝 **Описание:** Пиши подробно (кто, что делает, где)\n\n"
        "💎 **Premium HD:** Максимальное качество и детализация!"
    )

# --- 📱 КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    tier = user[1]
    style = user[6]
    emoji = "🆓" if tier == "free" else "⭐" if tier == "vip" else "💎"
    tier_name = "Free" if tier == "free" else "VIP" if tier == "vip" else "PREMIUM"
    
    text = (
        f"{emoji} **Генератор | {tier_name}**\n\n"
        "🎨 Рисую в разных стилях!\n\n"
        f"📊 **Статистика:**\n"
        f"• Сегодня: {user[2]}\n"
        f"• Всего: {user[3]}\n\n"
        f"🎭 **Стиль:** {style}\n\n"
        "👇 **Выбери действие:**"
    )    
    bot.reply_to(message, text, reply_markup=main_keyboard(tier))

# --- 🔘 КНОПКИ ---
@bot.message_handler(func=lambda message: message.text == "🎭 Выбрать стиль" or message.text == "🖼️ Выбрать стиль")
def select_style(message):
    bot.reply_to(message, "🎨 **ВЫБЕРИ СТИЛЬ:**", reply_markup=style_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("style_"))
def style_selected(call):
    style_name = call.data.replace("style_", "")
    set_style(call.from_user.id, style_name)
    bot.answer_callback_query(call.id, f"✅ Стиль: {style_name}")
    bot.edit_message_text(f"✅ Стиль изменён на: **{style_name}**", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    start(call.message)

# Кнопка SD
@bot.message_handler(func=lambda message: message.text == "🎨 Генерация (SD)")
def gen_sd(message):
    user = get_user(message.chat.id)
    if user[2] >= 10 and user[1] == "free":
        bot.reply_to(message, "❌ **Лимит SD исчерпан!**", reply_markup=main_keyboard("free"))
        return
    msg = bot.reply_to(message, "✏️ **Напиши что нарисовать (SD):**\n\n💡 *Стиль: {}*".format(user[6]), reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_image, "normal")

# Кнопка HD
@bot.message_handler(func=lambda message: message.text == "🖼️ Генерация (HD)")
def gen_hd(message):
    user = get_user(message.chat.id)
    if user[1] == "free":
        bot.reply_to(message, "❌ **HD только для VIP!**", reply_markup=main_keyboard("free"))
        return
    if user[2] >= 100 and user[1] == "vip":
        bot.reply_to(message, "❌ **Лимит HD исчерпан!**", reply_markup=main_keyboard("vip"))
        return
    msg = bot.reply_to(message, "✏️ **Напиши что нарисовать (HD):**\n\n💡 *Стиль: {}*".format(user[6]), reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_image, "hd")

# Кнопка PREMIUM HD
@bot.message_handler(func=lambda message: message.text == "💎 Premium HD (Max)")
def gen_premium_hd(message):
    user = get_user(message.chat.id)
    if user[1] != "premium":
        bot.reply_to(message, "❌ **Premium HD только для PREMIUM!**\n💎 /premium", reply_markup=main_keyboard("premium"))
        return
        msg = bot.reply_to(message, "🔥 **PREMIUM HD (MAX)**\n\n✏️ Напиши что нарисовать:\n\n*Будет максимальная детализация!*", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_image, "premium_hd")

# Остальные кнопки меню
@bot.message_handler(func=lambda message: message.text == "⭐ Купить VIP")
def buy_vip(message):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
    bot.reply_to(message, f"⭐ **VIP (300₽)**\n\nID: `{message.chat.id}`", reply_markup=kb)

@bot.message_handler(func=lambda message: message.text == "💎 Купить PREMIUM")
def buy_prem(message):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
    bot.reply_to(message, f"💎 **PREMIUM (500₽)**\n\nID: `{message.chat.id}`", reply_markup=kb)

@bot.message_handler(func=lambda message: message.text == "💝 Поддержать")
def donate_btn(message):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
    bot.reply_to(message, "💝 **Поддержать проект**", reply_markup=kb)

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def stats_btn(message):
    user = get_user(message.chat.id)
    text = f"📊 **Статистика**\n\nСегодня: {user[2]}\nВсего: {user[3]}\nТариф: {user[1].upper()}\n🎭 Стиль: {user[6]}"
    bot.reply_to(message, text, reply_markup=main_keyboard(user[1]))

@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_btn(message):
    bot.reply_to(message, help_text(), reply_markup=main_keyboard("free"))

# --- 🖼️ ПРОЦЕСС ---
def process_image(message, quality):
    if not message.text:
        bot.reply_to(message, "❌ Пустой запрос", reply_markup=main_keyboard("free"))
        return
    
    user = get_user(message.chat.id)
    
    # Проверка лимитов
    if user[1] == "free" and user[2] >= 10:
        bot.reply_to(message, "❌ Лимит!", reply_markup=main_keyboard("free"))
        return
    if user[1] == "vip" and user[2] >= 100:
        bot.reply_to(message, "❌ Лимит!", reply_markup=main_keyboard("vip"))
        return
    
    style_prompt = STYLES.get(user[6], STYLES["🗡️ Solo Leveling"])
        status = bot.reply_to(message, "⏳ **Генерирую...**\n🎭 Стиль: {}".format(user[6]), reply_markup=telebot.types.ReplyKeyboardRemove())
    
    img = generate_image(message.text, quality, style_prompt)
    
    if img:
        use_generation(message.chat.id)
        new_user = get_user(message.chat.id)
        
        tier_emoji = "🆓" if user[1] == "free" else "⭐" if user[1] == "vip" else "💎"
        # Premium безлимит
        if user[1] == "premium": left = "♾️"
        elif user[1] == "vip": left = 100 - new_user[2]
        else: left = 10 - new_user[2]
        
        cap = (
            f"{tier_emoji} **ГОТОВО!**\n\n"
            f"📝 {message.text}\n"
            f"🎭 Стиль: {user[6]}\n"
            f"🎨 Качество: {quality.upper()}\n"
            f"📊 Осталось: {left}"
        )
        
        bot.send_photo(message.chat.id, BytesIO(img), caption=cap, reply_markup=main_keyboard(user[1]))
        try:
            bot.delete_message(message.chat.id, status.message_id)
        except: pass
    else:
        bot.reply_to(message, "❌ **Ошибка**\nПопробуй другой запрос!", reply_markup=main_keyboard(user[1]))

# --- 💳 И АДМИН ---
@bot.message_handler(commands=['payment'])
def payment_confirm(message):
    bot.reply_to(message, "✅ **Заявка принята!**", reply_markup=main_keyboard("free"))
    bot.send_message(ADMIN_ID, f"💰 **Оплата!**\n👤 `{message.chat.id}`")

@bot.message_handler(commands=['upgrade'])
def admin_upgrade(message):
    if message.chat.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        uid = int(parts[1])
        tier = parts[2].lower()
        upgrade_user(uid, tier)
        bot.send_message(uid, f"✅ Аккаунт улучшен до **{tier.upper()}**!", reply_markup=main_keyboard(tier))
        bot.reply_to(message, f"✅ {uid} → {tier.upper()}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

print("🚀 Бот запущен! Ты ADMIN и PREMIUM!")
bot.polling(none_stop=True)
