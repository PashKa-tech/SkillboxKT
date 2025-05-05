import json
import re
from telebot import TeleBot
from telebot.types import Message
from db import get_connection

def register_handlers(bot: TeleBot):
    @bot.message_handler(commands=["курсы_редактировать"])
    def edit_courses(message: Message):
        user_id = str(message.from_user.id)
        
        if not is_admin(user_id):
            bot.reply_to(message, "❌ У вас нет прав для использования этой команды.")
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name, timekt FROM courses")
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            bot.send_message(message.chat.id, "База курсов пуста.")
            return

        response = "Список всех курсов:\n\n"
        for name, timekt in courses:
            response += f"\"{name}\" — {timekt}\n"

        bot.send_message(message.chat.id, response)

    @bot.message_handler(commands=["курс_кт"])
    def update_course_date(message: Message):
        user_id = str(message.from_user.id)

        if not is_admin(user_id):
            bot.reply_to(message, "❌ У вас нет прав для использования этой команды.")
            return
        m = re.search(r'\((.+?)\)\s+(\d{2}\.\d{2}\.\d{4})', message.text)
        if not m:
            bot.reply_to(message, "❗ Неверный формат команды.\nПример: /курс_кт (Русский язык) 20.05.2025")
            return

        course_name, new_date = m.groups()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE courses SET timekt = ? WHERE name = ?", (new_date, course_name))
        if cursor.rowcount == 0:
            bot.send_message(message.chat.id, f"❗ Курс \"{course_name}\" не найден.")
        else:
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Дата КТ для курса \"{course_name}\" обновлена на {new_date}.")

        conn.close()

def is_admin(user_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM admins WHERE id = ?", (user_id,))
    is_admin = cursor.fetchone() is not None

    conn.close()
    return is_admin
