import json
import os
import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# === Настройки ===
openai.api_key = os.getenv("OPENAI_API_KEY")  # Ключ из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен из переменной окружения

# === Хранение данных пользователей ===
def load_users():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f)

# === Промты для генерации ===
def generate_description_prompt(product_info, marketplace):
    if marketplace == "wildberries":
        return f"Напиши длинное SEO-оптимизированное описание для товара '{product_info}' с ключевыми словами в начале текста."
    elif marketplace == "ozon":
        return f"Напиши краткое и структурированное описание для товара '{product_info}' с выделением преимуществ."

def generate_review_prompt(review_text, product_info):
    return f"Сгенерируй вежливый и профессиональный ответ на отзыв: '{review_text}' для товара '{product_info}'."

def generate_keywords_prompt(topic):
    return f"Проанализируй популярные запросы для товара '{topic}'. Верни список ключевых слов с частотностью и примерами использования."

# === Логика бота ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Начать использование", callback_data='choose_marketplace')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я помощник для селлеров Wildberries и Ozon.\n"
        "У тебя есть 3 бесплатных генерации.\n"
        "Нажми 'Начать использование', чтобы выбрать маркетплейс и начать работать.",
        reply_markup=reply_markup
    )

async def choose_marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Wildberries", callback_data='wildberries')],
        [InlineKeyboardButton("Ozon", callback_data='ozon')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите маркетплейс:", reply_markup=reply_markup)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    users = load_users()
    marketplace = query.data
    users[user_id] = {"marketplace": marketplace, "tariff": "free", "requests_left": 3}
    save_users(users)
    
    keyboard = [
        [InlineKeyboardButton("Генерация описаний", callback_data='describe')],
        [InlineKeyboardButton("Анализ ключевых слов", callback_data='keywords')],
        [InlineKeyboardButton("Генерация ответов на отзывы и вопросы", callback_data='reviews_submenu')],
        [InlineKeyboardButton("Как пользоваться", callback_data='instructions')],
        [InlineKeyboardButton("Оплата и тарифы", callback_data='payment')],
        [InlineKeyboardButton("Профиль", callback_data='profile')],
        [InlineKeyboardButton("Назад", callback_data='choose_marketplace')]  # Кнопка "Назад"
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Вы в главном меню. Текущий маркетплейс: {marketplace}", reply_markup=reply_markup)

# === Функция 1: Генерация описаний ===
async def describe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("Назад", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Введите характеристики товара (например, 'платье красное, размеры S-XXL, материал — шифон')",
        reply_markup=reply_markup
    )

async def generate_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    if users[user_id]["requests_left"] <= 0:
        await update.message.reply_text("У вас закончились бесплатные запросы. Перейдите в 'Оплата и тарифы' для покупки подписки.")
        return
    
    product_info = update.message.text
    marketplace = users[user_id]["marketplace"]
    prompt = generate_description_prompt(product_info, marketplace)
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}]
        )
        description = response['choices'][0]['message']['content']
        users[user_id]["requests_left"] -= 1
        save_users(users)
        await update.message.reply_text(description)
    except Exception as e:
        await update.message.reply_text("Ошибка генерации. Попробуйте позже.")

# === Функция 2: Анализ ключевых слов ===
async def keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("Назад", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Введите тематику товара (например, 'спортивные футболки')",
        reply_markup=reply_markup
    )

async def analyze_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    if users[user_id]["requests_left"] <= 0:
        await update.message.reply_text("У вас закончились бесплатные запросы. Перейдите в 'Оплата и тарифы' для покупки подписки.")
        return
    
    topic = update.message.text
    prompt = generate_keywords_prompt(topic)
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}]
        )
        keywords = response['choices'][0]['message']['content']
        users[user_id]["requests_left"] -= 1
        save_users(users)
        await update.message.reply_text(keywords)
    except Exception as e:
        await update.message.reply_text("Ошибка генерации. Попробуйте позже.")

# === Функция 3: Ответы на отзывы и вопросы ===
async def reviews_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Ответы на отзывы", callback_data='generate_review_response')],
        [InlineKeyboardButton("Ответы на вопросы", callback_data='generate_question_response')],
        [InlineKeyboardButton("Назад", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите тип ответа:", reply_markup=reply_markup)

async def request_review_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['review_type'] = 'review'
    keyboard = [[InlineKeyboardButton("Назад", callback_data='reviews_submenu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Введите текст негативного отзыва:", reply_markup=reply_markup)

async def request_question_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['review_type'] = 'question'
    keyboard = [[InlineKeyboardButton("Назад", callback_data='reviews_submenu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Введите текст вопроса:", reply_markup=reply_markup)

async def request_product_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    context.user_data['user_input'] = user_input
    await update.message.reply_text("Введите информацию о товаре (например, 'платье красное, размеры S-XXL, материал — шифон'):")

async def generate_review_or_question_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    if users[user_id]["requests_left"] <= 0:
        await update.message.reply_text("У вас закончились бесплатные запросы. Перейдите в 'Оплата и тарифы' для покупки подписки.")
        return
    
    product_info = update.message.text
    user_input = context.user_data.get('user_input', '')
    review_type = context.user_data.get('review_type', 'review')
    
    prompt = generate_review_prompt(user_input, product_info)
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}]
        )
        ai_response = response['choices'][0]['message']['content']
        users[user_id]["requests_left"] -= 1
        save_users(users)
        await update.message.reply_text(ai_response)
    except Exception as e:
        await update.message.reply_text("Ошибка генерации. Попробуйте позже.")

# === Раздел "Оплата и тарифы" ===
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("Назад", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Тарифы:\n"
        "Бесплатный: 3 запроса (для знакомства с функционалом)\n"
        "Премиум: 500 руб/мес → 150 запросов, полный доступ ко всем функциям, приоритетная поддержка\n"
        "Кнопка 'Купить подписку' будет доступна после интеграции с платежной системой.",
        reply_markup=reply_markup
    )

# === Раздел "Профиль" ===
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    users = load_users()
    data = users.get(user_id, {"requests_left": 3, "tariff": "free", "subscription_until": "none"})
    keyboard = [[InlineKeyboardButton("Назад", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Ваш профиль:\n"
        f"Статус тарифа: {data['tariff']}\n"
        f"Остаток запросов: {data['requests_left']}/3\n"
        f"Подписка до: {data['subscription_until']}",
        reply_markup=reply_markup
    )

# === Раздел "Как пользоваться" ===
async def instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = """
    Как использовать функции:
    1. Генерация описаний: введите характеристики товара, и бот предложит 3 варианта.
    2. Анализ ключевых слов: введите тематику товара, и бот вернет популярные запросы.
    3. Ответы на отзывы: введите текст отзыва и информацию о товаре, и бот сгенерирует ответ.
    """
    keyboard = [[InlineKeyboardButton("Назад", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

# === Запуск бота ===
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    
    # Callback-обработчики
    application.add_handler(CallbackQueryHandler(choose_marketplace, pattern='choose_marketplace'))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='wildberries|ozon'))
    application.add_handler(CallbackQueryHandler(describe, pattern='describe'))
    application.add_handler(CallbackQueryHandler(keywords, pattern='keywords'))
    application.add_handler(CallbackQueryHandler(reviews_submenu, pattern='reviews_submenu'))
    application.add_handler(CallbackQueryHandler(request_review_input, pattern='generate_review_response'))
    application.add_handler(CallbackQueryHandler(request_question_input, pattern='generate_question_response'))
    application.add_handler(CallbackQueryHandler(payment, pattern='payment'))
    application.add_handler(CallbackQueryHandler(profile, pattern='profile'))
    application.add_handler(CallbackQueryHandler(instructions, pattern='instructions'))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='main_menu'))  # Обработчик для кнопки "Назад"
    
    # Сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_description))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_keywords))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, request_product_info))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_review_or_question_response))
    
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        url_path=os.getenv("BOT_TOKEN"),
        webhook_url=f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com/{os.getenv('BOT_TOKEN')}"
    )

if __name__ == '__main__':
    main()