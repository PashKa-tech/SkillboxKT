from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from db import get_connection
import time

def register_handlers(bot: TeleBot):
    @bot.message_handler(commands=["start"])
    def start_command(message: Message):
        user_id = str(message.from_user.id)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE tgid = ?", (user_id,))
        if cursor.fetchone():
            conn.close()
        else:
            cursor.execute("SELECT groupid FROM allowgroups")
            allowed_groups = [row[0] for row in cursor.fetchall()]
            found_groups = []

            for group_id in allowed_groups:
                try:
                    member = bot.get_chat_member(group_id, message.from_user.id)
                    if member.status != 'left':
                        found_groups.append(group_id)
                except Exception as e:
                    print(f"Ошибка при проверке группы {group_id}: {e}")
                    continue

            if not found_groups:
                bot.reply_to(
                    message,
                    "Вы не можете использовать этого бота, либо я не имею доступа к участникам в группе вашего потока."
                )
                conn.close()
                return

            groups_str = ",".join(found_groups)
            cursor.execute(
                "INSERT INTO users (tgid, group_ids, settings) VALUES (?, ?, ?)",
                (user_id, groups_str, "Не установлено")
            )
            conn.commit()
            conn.close()

            bot.reply_to(message, "Вы успешно зарегестирировались в боте.")
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("📚Дисциплины"))
        markup.add(KeyboardButton("⚙Настройки"))

        bot.send_message(
            message.chat.id,
            "Вы верифицированы. Выберите одну из опций:",
            reply_markup=markup
        )