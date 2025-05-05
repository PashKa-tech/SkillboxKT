import json
from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_connection

subjects = [
    "Математика",
    "Информатика",
    "Физика",
    "История",
    "Обществознание",
    "География",
    "Физическая культура",
    "Русский язык"
]

def register_handlers(bot: TeleBot):
    @bot.message_handler(func=lambda message: message.text == "📚Дисциплины")
    def disciplines_message(message: Message):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Список всех дисциплин", callback_data="list_disciplines"))
        markup.add(InlineKeyboardButton("Выбрать по каким предметам получать напоминания", callback_data="select_subjects"))

        bot.send_message(
            message.chat.id,
            "Выберите одну из опций:",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "list_disciplines")
    def list_disciplines(call):
        bot.answer_callback_query(call.id)
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name, timekt FROM courses")
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            bot.send_message(call.message.chat.id, "Данные отсутствуют.")
        else:
            response = "Вот информация о контрольных точках:\n"
            for course in courses:
                response += f"{course[0]}, {course[1]}\n"
            bot.send_message(call.message.chat.id, response)

    @bot.callback_query_handler(func=lambda call: call.data == "select_subjects")
    def select_subjects(call):
        bot.answer_callback_query(call.id)
        user_id = str(call.from_user.id)
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT settings FROM users WHERE tgid = ?", (user_id,))
        user_data = cursor.fetchone()

        if user_data:
            settings_str = user_data[0]
            if settings_str == "Не установлено" or not settings_str:
                settings = {}
            else:
                try:
                    settings = json.loads(settings_str)
                except json.JSONDecodeError:
                    settings = {}
        else:
            settings = {}

        notifyon = settings.get("notifyon", subjects[:])
        notifyoff = settings.get("notifyoff", [])

        markup = InlineKeyboardMarkup(row_width=2)
        for subject in subjects:
            status = "✅" if subject in notifyon else "❌"
            markup.add(InlineKeyboardButton(f"{status} {subject}", callback_data=f"toggle_{subject}"))

        bot.send_message(
            call.message.chat.id,
            "Выберите, что хотите получать:",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
    def toggle_subject(call):
        bot.answer_callback_query(call.id)
        subject = call.data[len("toggle_"):]

        user_id = str(call.from_user.id)
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT settings FROM users WHERE tgid = ?", (user_id,))
        user_data = cursor.fetchone()

        if user_data:
            settings_str = user_data[0]
            if settings_str == "Не установлено" or not settings_str:
                settings = {}
            else:
                try:
                    settings = json.loads(settings_str)
                except json.JSONDecodeError:
                    settings = {}
        else:
            settings = {}

        notifyon = settings.get("notifyon", [])
        notifyoff = settings.get("notifyoff", [])

        if subject in notifyon:
            notifyon.remove(subject)
        else:
            notifyon.append(subject)

        settings["notifyon"] = notifyon
        settings["notifyoff"] = notifyoff

        cursor.execute(
            "UPDATE users SET settings = ? WHERE tgid = ?",
            (json.dumps(settings), user_id)
        )
        conn.commit()
        conn.close()

        markup = InlineKeyboardMarkup(row_width=2)
        for subj in subjects:
            status = "✅" if subj in notifyon else "❌"
            markup.add(InlineKeyboardButton(f"{status} {subj}", callback_data=f"toggle_{subj}"))

        bot.edit_message_text(
            "Выберите, что хотите получать:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
