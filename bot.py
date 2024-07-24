import os
import json
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime, timedelta
import time

# Получаем токен из переменных окружения
TOKEN = os.environ.get('TOKEN')

# Файлы для хранения данных
PASSWORD_FILE = 'passwords.json'
SETTINGS_FILE = 'settings.json'

bot = Bot(token=TOKEN)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            return json.load(file)
    return {
        'CHANNEL_ID': None,
        'TARGET_SUBSCRIBERS': 100,
        'END_DATE': None
    }

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file)

def load_passwords():
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_passwords(passwords):
    with open(PASSWORD_FILE, 'w') as file:
        json.dump(passwords, file)

settings = load_settings()
passwords = load_passwords()

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Используйте команды /set_channel, /set_subscribers и /set_date для настройки параметров. '
        'Отправьте мне ваш пароль и дату окончания в формате ГГГГ-ММ-ДД. Например: "пароль 2023-08-30". '
        'Пароль будет отправлен вам только если количество подписчиков на канале достигнет целевого значения к указанной дате.'
    )

def set_channel(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text('Используйте: /set_channel <CHANNEL_ID>')
        return

    settings['CHANNEL_ID'] = context.args[0]
    save_settings(settings)
    update.message.reply_text(f'CHANNEL_ID установлен на {context.args[0]}')

def set_subscribers(update: Update, context: CallbackContext):
    if len(context.args) != 1 or not context.args[0].isdigit():
        update.message.reply_text('Используйте: /set_subscribers <TARGET_SUBSCRIBERS>')
        return

    settings['TARGET_SUBSCRIBERS'] = int(context.args[0])
    save_settings(settings)
    update.message.reply_text(f'TARGET_SUBSCRIBERS установлен на {context.args[0]}')

def set_date(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text('Используйте: /set_date <END_DATE>')
        return

    try:
        end_date = datetime.fromisoformat(context.args[0])
        settings['END_DATE'] = end_date.isoformat()
        save_settings(settings)
        update.message.reply_text(f'END_DATE установлен на {context.args[0]}')
    except ValueError:
        update.message.reply_text('Неправильный формат даты. Используйте: ГГГГ-ММ-ДД')

def handle_password(update: Update, context: CallbackContext):
    message_parts = update.message.text.split()
    if len(message_parts) != 2:
        update.message.reply_text('Неправильный формат. Используйте: "пароль 2023-08-30"')
        return

    password, end_date_str = message_parts
    chat_id = update.message.chat_id

    try:
        end_date = datetime.fromisoformat(end_date_str)
    except ValueError:
        update.message.reply_text('Неправильный формат даты. Используйте: "пароль 2023-08-30"')
        return

    passwords[chat_id] = password
    save_passwords(passwords)

    bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)

    update.message.reply_text('Ваш пароль сохранен и сообщение удалено. Дата окончания: ' + end_date_str)

def check_subscribers(context: CallbackContext):
    end_date = settings.get('END_DATE')
    if not end_date:
        return

    end_date = datetime.fromisoformat(end_date)
    channel_id = settings.get('CHANNEL_ID')
    target_subscribers = settings.get('TARGET_SUBSCRIBERS')

    if not channel_id or not target_subscribers:
        return

    while datetime.now() < end_date:
        chat = bot.get_chat(channel_id)
        subscribers_count = chat.get_member_count()

        if subscribers_count >= target_subscribers:
            for chat_id, password in passwords.items():
                context.bot.send_message(chat_id=chat_id, text=f'Ваш пароль: {password}')
            passwords.clear()
            save_passwords(passwords)
            break
        time.sleep(60)
    else:
        passwords.clear()
        save_passwords(passwords)
        context.bot.send_message(chat_id=admin_chat_id, text='Количество подписчиков не достигло целевого значения, пароли удалены.')

def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('set_channel', set_channel))
    dp.add_handler(CommandHandler('set_subscribers', set_subscribers))
    dp.add_handler(CommandHandler('set_date', set_date))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_password))

    updater.job_queue.run_repeating(check_subscribers, interval=60, first=0)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
