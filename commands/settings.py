from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import re
from db import get_connection

def register_handlers(bot):
    period_options = [
        "за 2 недели до дедлайна",
        "за 1 неделю до дедлайна",
        "за 1 день до дедлайна",
        "в день дедлайна",
        "каждый день"
    ]

    def is_valid_timezone_input(text):
        match = re.match(r'^GMT\s*([+-])\s*(\d{1,2})$', text.strip())
        if not match:
            return False
        sign, hours = match.groups()
        offset = int(hours) * (1 if sign == '+' else -1)
        return -14 <= offset <= 14

    def get_user_settings(user_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT settings FROM users WHERE tgid = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0] and result[0] != "Не установлено":
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                return {}
        return {}

    def update_user_settings(user_id, new_settings):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET settings = ? WHERE tgid = ?",
            (json.dumps(new_settings, ensure_ascii=False), user_id)
        )
        conn.commit()
        conn.close()

    def create_periodicity_markup(settings):
        enabled = set(settings.get("notifysettingson", period_options))
        markup = InlineKeyboardMarkup()
        for option in period_options:
            symbol = "✅" if option in enabled else "❌"
            markup.add(InlineKeyboardButton(
                f"{symbol} {option}",
                callback_data=f"settings_toggle_period_{option}"
            ))
        return markup

    @bot.message_handler(func=lambda message: message.text == "⚙Настройки")
    def settings_menu(message):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Настроить периодичность", callback_data="settings_set_period"))
        markup.add(InlineKeyboardButton("Настроить часовой пояс", callback_data="settings_set_timezone"))
        markup.add(InlineKeyboardButton("Выбрать время напоминаний", callback_data="settings_set_notify_time"))
        bot.send_message(message.chat.id, "⚙️ Управление настройками", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "settings_set_timezone")
    def set_timezone_settings(call):
        bot.answer_callback_query(call.id)
        user_id = str(call.from_user.id)
        settings = get_user_settings(user_id)
        current = settings.get("chaspoy")
        if current:
            msg = (
                f"Ваш текущий часовой пояс — {current}, вы можете его изменить.\n\n"
                "Введите свой часовой пояс в формате: `GMT +3`\n"
                "[Узнать свой пояс](https://www.timeanddate.com/)"
            )
        else:
            msg = (
                "Введите свой часовой пояс в формате: `GMT +3`\n"
                "[Узнать свой пояс](https://www.timeanddate.com/)"
            )
        bot.send_message(call.message.chat.id, msg,
                         parse_mode="Markdown", disable_web_page_preview=True)
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_timezone_settings)

    def save_timezone_settings(message):
        user_id = str(message.from_user.id)
        tz = message.text.strip()
        if not is_valid_timezone_input(tz):
            bot.send_message(
                message.chat.id,
                "❌ Неверный формат или несуществующий часовой пояс. Введите в формате: `GMT +3`",
                parse_mode="Markdown"
            )
            return
        settings = get_user_settings(user_id)
        settings["chaspoy"] = tz
        update_user_settings(user_id, settings)
        bot.send_message(message.chat.id, f"✅ Часовой пояс установлен: {tz}")

    @bot.callback_query_handler(func=lambda call: call.data == "settings_set_period")
    def set_notification_periodicity(call):
        bot.answer_callback_query(call.id)
        user_id = str(call.from_user.id)
        settings = get_user_settings(user_id)
        if "notifysettingson" not in settings and "notifysettingoff" not in settings:
            settings["notifysettingson"] = period_options[:]
            settings["notifysettingoff"] = []
            update_user_settings(user_id, settings)
        markup = create_periodicity_markup(settings)
        bot.send_message(call.message.chat.id, "Выберите периодичность получения уведомлений:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("settings_toggle_period_"))
    def toggle_periodicity_option(call):
        bot.answer_callback_query(call.id)
        user_id = str(call.from_user.id)
        option = call.data.replace("settings_toggle_period_", "")
        settings = get_user_settings(user_id)
        on = set(settings.get("notifysettingson", period_options))
        off = set(settings.get("notifysettingoff", []))
        if option in on:
            on.remove(option)
            off.add(option)
        else:
            on.add(option)
            off.discard(option)
        settings["notifysettingson"] = list(on)
        settings["notifysettingoff"] = list(off)
        update_user_settings(user_id, settings)
        markup = create_periodicity_markup(settings)
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "settings_set_notify_time")
    def set_notify_time(call):
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "Введите время напоминаний в формате `ЧЧ:ММ`, кратное 30 минутам (например, 08:00, 13:30)",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_notify_time)

    def save_notify_time(message):
        user_id = str(message.from_user.id)
        text = message.text.strip()
        if not re.match(r'^\d{2}:\d{2}$', text):
            bot.send_message(message.chat.id, "❌ Неверный формат. Введите в формате `ЧЧ:ММ`", parse_mode="Markdown")
            return
        h, m = map(int, text.split(":"))
        if not (0 <= h < 24 and m in (0, 30)):
            bot.send_message(
                message.chat.id,
                "❌ Время должно быть кратным 30 минутам и в пределах суток (например, 08:00, 14:30)",
                parse_mode="Markdown"
            )
            return
        settings = get_user_settings(user_id)
        settings["timenap"] = text
        update_user_settings(user_id, settings)
        bot.send_message(message.chat.id, f"✅ Время напоминаний установлено: {text}")
