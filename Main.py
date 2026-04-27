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
                  subscribe_end DATE)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    today = datetime.now().date()
    
    if not user:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                 (user_id, "free", 0, 0, today, None))
        conn.commit()
        user = (user_id, "free", 0, 0, today, None)
    else:
        if user[5]:
            sub_end = datetime.strptime(str(user[5]), "%Y-%m-%d").date()
            if sub_end < today:
                c.execute("UPDATE users SET tier = 'free', subscribe_end = NULL WHERE user_id = ?", (user_id,))
                conn.commit()        if str(user[4]) != str(today):
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

init_db()

# --- 🌐 СЕРВЕР ---
app = Flask('')
@app.route('/')
def home():
    return "MangaGen Bot is running!"
def run():
    app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- 🎨 ГЕНЕРАЦИЯ (УЛУЧШЕННАЯ) ---
def generate_image(prompt, quality="normal"):
    style = "solo leveling style, manhwa, dark fantasy, detailed, anime art style, professional illustration"
    if quality == "hd":
        style += ", 8k resolution, ultra hd, masterpiece, best quality, highly detailed"
    
    full_prompt = f"{prompt}, {style}"
    size = 1024 if quality == "normal" else 2048
    
    # 🎲 МАКСИМАЛЬНАЯ случайность
    seed = random.randint(100000, 999999)
    timestamp = int(time.time() * 1000)
    
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(full_prompt)}"
    url += f"?width={size}&height={size}&nologo=true&seed={seed}&nonce={timestamp}"
    
    try:        headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}
        response = requests.get(url, headers=headers, timeout=180)
        if response.status_code == 200 and len(response.content) > 1000:
            return response.content
    except: pass
    return None

# --- 📱 КЛАВИАТУРЫ (ВСЕГДА ДОСТУПНЫ) ---
def main_keyboard(tier):
    """Основная клавиатура с кнопками"""
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if tier == "free":
        kb.add("🎨 Генерация SD")
        kb.add("⭐ Купить VIP", "💎 Купить PREMIUM")
        kb.add("💝 Поддержать", "📊 Статистика")
        kb.add("❓ Помощь")
    elif tier == "vip":
        kb.add("🎨 Генерация SD")
        kb.add("🖼️ Генерация HD")
        kb.add("💎 Купить PREMIUM")
        kb.add("💝 Поддержать", "📊 Статистика")
        kb.add("❓ Помощь")
    else:  # premium
        kb.add("🎨 Генерация SD")
        kb.add("🖼️ Генерация HD")
        kb.add("🔥 Ultra HD (Безлимит)")
        kb.add("💝 Поддержать", "📊 Статистика")
        kb.add("❓ Помощь")
    
    return kb

def help_text():
    return (
        "❓ **КАК ПОЛЬЗОВАТЬСЯ**\n\n"
        "📝 **Советы для лучших результатов:**\n\n"
        "✏️ **Пишите подробно:**\n"
        "❌ *Плохо:* 'Машина'\n"
        "✅ *Хорошо:* 'Чёрная спортивная машина, ночь, дождь, киберпанк стиль'\n\n"
        "🎨 **Примеры хороших запросов:**\n"
        "• 'Девушка с розовыми волосами, школьная форма, цветущая сакура'\n"
        "• 'Дракон летит над горами, огонь, эпичная битва'\n"
        "• 'Тёмный рыцарь с мечом, замок на заднем плане'\n"
        "• 'Кот в космосе, звёзды, скафандр'\n\n"
        "💡 **Чем подробнее опишете — тем лучше результат!**\n\n"
        "📊 **Ваши лимиты:**\n"
        "• Free: 10 генераций/день (SD)\n"
        "• VIP: 100 генераций/день (HD)\n"
        "• PREMIUM: безлимит (Ultra HD)\n\n"
        "👇 **Нажми на кнопку ниже чтобы начать!**"    )

# --- 📱 КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    tier = user[1]
    emoji = "🆓" if tier == "free" else "⭐" if tier == "vip" else "💎"
    tier_name = "Free" if tier == "free" else "VIP" if tier == "vip" else "PREMIUM"
    
    text = (
        f"{emoji} **Генератор Манхвы | {tier_name}**\n\n"
        "🎨 Рисую в стиле Solo Leveling!\n\n"
        f"📊 **Твои лимиты:**\n"
        f"• Сегодня: {user[2]}\n"
        f"• Всего: {user[3]}\n\n"
        "👇 **Выбери действие из меню внизу!**"
    )
    
    bot.reply_to(message, text, reply_markup=main_keyboard(tier))

@bot.message_handler(commands=['vip'])
def vip_info(message):
    text = "⭐ **VIP подписка**\n\n💰 300₽/мес\n✅ 100 генераций/день\n✅ HD качество (2048x2048)\n✅ Быстрая генерация"
    bot.reply_to(message, text, reply_markup=main_keyboard("vip"))

@bot.message_handler(commands=['premium'])
def prem_info(message):
    text = "💎 **PREMIUM подписка**\n\n💰 500₽/мес\n✅ БЕЗЛИМИТ генераций\n✅ Ultra HD качество\n✅ Максимальная скорость"
    bot.reply_to(message, text, reply_markup=main_keyboard("premium"))

@bot.message_handler(commands=['donate'])
def donate_menu(message):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
    bot.reply_to(message, "💝 **Поддержать проект**\n\nЛюбой донат помогает развитию!", reply_markup=kb)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, help_text(), reply_markup=main_keyboard("free"))

# --- 🔘 ОБРАБОТКА КНОПОК ---
@bot.message_handler(func=lambda message: message.text == "🎨 Генерация SD")
def gen_sd(message):
    user = get_user(message.chat.id)
    if user[2] >= 10 and user[1] == "free":
        bot.reply_to(message, "❌ **Лимит Free исчерпан!**\n\nЗавтра обновится или купи VIP: /vip", reply_markup=main_keyboard("free"))
        return
    msg = bot.reply_to(message, "✏️ **Напиши что нарисовать:**\n\n💡 *Совет: пиши подробно для лучшего результата!*", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_image, "normal")
@bot.message_handler(func=lambda message: message.text == "🖼️ Генерация HD")
def gen_hd(message):
    user = get_user(message.chat.id)
    if user[1] == "free":
        bot.reply_to(message, "❌ **HD доступно только для VIP!**\n\n⭐ Купи VIP: /vip", reply_markup=main_keyboard("free"))
        return
    if user[2] >= 100 and user[1] == "vip":
        bot.reply_to(message, "❌ **Лимит VIP исчерпан!**", reply_markup=main_keyboard("vip"))
        return
    msg = bot.reply_to(message, "✏️ **Напиши что нарисовать (HD качество):**\n\n💡 *Пример: 'Девушка с розовыми волосами, школьная форма'*", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_image, "hd")

@bot.message_handler(func=lambda message: message.text == "🔥 Ultra HD (Безлимит)")
def gen_uhd(message):
    user = get_user(message.chat.id)
    if user[1] != "premium":
        bot.reply_to(message, "❌ **Ultra HD доступно только для PREMIUM!**\n\n💎 Купи PREMIUM: /premium", reply_markup=main_keyboard("premium"))
        return
    msg = bot.reply_to(message, "✏️ **Напиши что нарисовать (Ultra HD качество):**", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_image, "hd")  # Используем hd как ultra

@bot.message_handler(func=lambda message: message.text == "⭐ Купить VIP")
def buy_vip(message):
    msg = f"⭐ **VIP (300₽/мес)**\n\n1. Перейди по ссылке\n2. Укажи сумму 300₽\n3. В комментарии напиши: `{message.chat.id}`\n4. После оплаты напиши /payment"
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
    bot.reply_to(message, msg, reply_markup=kb)

@bot.message_handler(func=lambda message: message.text == "💎 Купить PREMIUM")
def buy_prem(message):
    msg = f"💎 **PREMIUM (500₽/мес)**\n\n1. Перейди по ссылке\n2. Укажи сумму 500₽\n3. В комментарии напиши: `{message.chat.id}`\n4. После оплаты напиши /payment"
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
    bot.reply_to(message, msg, reply_markup=kb)

@bot.message_handler(func=lambda message: message.text == "💝 Поддержать")
def donate_btn(message):
    donate_menu(message)

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def stats_btn(message):
    user = get_user(message.chat.id)
    tier = user[1]
    text = f"📊 **Твоя статистика**\n\nСегодня: {user[2]}\nВсего: {user[3]}\nТариф: {tier.upper()}"
    bot.reply_to(message, text, reply_markup=main_keyboard(tier))

@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_btn(message):
    bot.reply_to(message, help_text(), reply_markup=main_keyboard("free"))
# --- 🖼️ ОБРАБОТКА ИЗОБРАЖЕНИЙ ---
def process_image(message, quality):
    if not message.text:
        bot.reply_to(message, "❌ Ошибка: пустой запрос", reply_markup=main_keyboard("free"))
        return
    
    user = get_user(message.chat.id)
    
    # Проверка лимитов
    if user[1] == "free" and user[2] >= 10:
        bot.reply_to(message, "❌ Лимит исчерпан!", reply_markup=main_keyboard("free"))
        return
    if user[1] == "vip" and user[2] >= 100:
        bot.reply_to(message, "❌ Лимит исчерпан!", reply_markup=main_keyboard("vip"))
        return
    
    status = bot.reply_to(message, "⏳ **Генерирую...**\n\nПодожди немного...", reply_markup=telebot.types.ReplyKeyboardRemove())
    
    img = generate_image(message.text, quality)
    
    if img:
        use_generation(message.chat.id)
        new_user = get_user(message.chat.id)
        
        tier_emoji = "🆓" if user[1] == "free" else "⭐" if user[1] == "vip" else "💎"
        left = "♾️" if user[1] == "premium" else (100 - new_user[2]) if user[1] == "vip" else (10 - new_user[2])
        
        cap = (
            f"{tier_emoji} **ГОТОВО!**\n\n"
            f"📝 {message.text}\n"
            f"🎨 Качество: {quality.upper()}\n"
            f"📊 Осталось сегодня: {left}\n\n"
            f"💝 Поддержать: /donate"
        )
        
        bot.send_photo(message.chat.id, BytesIO(img), caption=cap, reply_markup=main_keyboard(user[1]))
        try:
            bot.delete_message(message.chat.id, status.message_id)
        except: pass
    else:
        bot.reply_to(message, "❌ **Ошибка генерации**\n\nПопробуй другой запрос или напиши подробнее!", reply_markup=main_keyboard(user[1]))

# --- 💳 ОПЛАТА ---
@bot.message_handler(commands=['payment'])
def payment_confirm(message):
    bot.reply_to(message, "✅ **Заявка принята!**\n\nАдминистратор проверит и активирует подписку в течение часа.\n\nСпасибо! 🙏", reply_markup=main_keyboard("free"))
    bot.send_message(ADMIN_ID, f"💰 **Новая оплата!**\n👤 Пользователь: `{message.chat.id}`\n📝 Ждёт проверки")

# --- 🛠 АДМИН ---@bot.message_handler(commands=['upgrade'])
def admin_upgrade(message):
    if message.chat.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        uid = int(parts[1])
        tier = parts[2].lower()
        upgrade_user(uid, tier)
        bot.send_message(uid, f"✅ Аккаунт улучшен до **{tier.upper()}**! Наслаждайся!", reply_markup=main_keyboard(tier))
        bot.reply_to(message, f"✅ {uid} получил {tier.upper()}", reply_markup=main_keyboard("free"))
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

print("🚀 Бот запущен! Кнопки всегда доступны!")
bot.polling(none_stop=True)
