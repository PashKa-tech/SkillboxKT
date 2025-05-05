import telebot
from commands import start, courses, settings, notify, admin
from db import init_db

bot = telebot.TeleBot("ВАШ_ТОКЕН")

init_db()

start.register_handlers(bot)
courses.register_handlers(bot)
settings.register_handlers(bot)
notify.register_handlers(bot)
admin.register_handlers(bot)

if __name__ == "__main__":
    print("Бот запущен!")
    bot.infinity_polling()
