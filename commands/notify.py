import time
import re
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from db import get_connection

def matches_period(days_left: int, period: str) -> bool:
    mapping = {
        "за 2 недели до дедлайна": 14,
        "за 1 неделю до дедлайна": 7,
        "за 1 день до дедлайна": 1,
        "в день дедлайна": 0
    }
    if period == "каждый день":
        return days_left >= 0
    return days_left == mapping.get(period, -999)

def parse_gmt_offset(chaspoy: str) -> int:
    m = re.match(r'GMT\s*([+-])\s*(\d{1,2})', chaspoy or "")
    if not m:
        return 0
    sign, hours = m.groups()
    return int(hours) * (1 if sign == '+' else -1)

def is_time_on_half_hour(dt: datetime) -> bool:
    return dt.minute % 30 == 0

def check_and_send_notifications(bot):
    now_utc = datetime.utcnow()
    print(f"[{now_utc.isoformat()} UTC] → Начинаю проверку уведомлений")

    if not is_time_on_half_hour(now_utc):
        print(f"[{now_utc.isoformat()} UTC] Время не кратно 30 минутам, пропуск")
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_notifications (
            tgid TEXT,
            course TEXT,
            period TEXT,
            date_sent TEXT
        )
    """)
    conn.commit()

    cursor.execute("SELECT name, timekt FROM courses")
    courses = cursor.fetchall()
    print(f"[{now_utc.isoformat()}] Курсов в БД: {len(courses)}")

    cursor.execute("SELECT tgid, settings FROM users")
    users = cursor.fetchall()
    print(f"[{now_utc.isoformat()}] Пользователей в БД: {len(users)}")

    for tgid, settings_str in users:
        try:
            settings = json.loads(settings_str) if settings_str not in (None, "", "Не установлено") else {}
        except json.JSONDecodeError:
            settings = {}
            print(f"  [!] Ошибка JSON в настройках пользователя {tgid}. Использую пустые настройки.")

        offset = parse_gmt_offset(settings.get("chaspoy", ""))
        now_local = now_utc + timedelta(hours=offset)
        local_time_str = now_local.strftime("%Y-%m-%d %H:%M:%S")
        print(f"  → Пользователь {tgid}: GMT offset {offset:+d}, локальное время {local_time_str}")

        target_time = settings.get("timenap")
        if target_time != now_local.strftime("%H:%M"):
            print(f"    — Пропускаем: время уведомлений {target_time}, сейчас {now_local.strftime('%H:%M')}")
            continue

        notifyon = set(settings.get("notifyon", []))
        periods = settings.get("notifysettingson", [])
        print(f"    — Подписки: курсы={notifyon}, периоды={periods}")

        for name, timekt in courses:
            if name not in notifyon:
                continue

            try:
                course_date = datetime.strptime(timekt, "%d.%m.%Y").date()
            except ValueError:
                print(f"    [!] Неверный формат даты KТ для курса «{name}»: {timekt}")
                continue

            days_left = (course_date - now_local.date()).days
            print(f"    — Курс «{name}»: осталось {days_left} дн. (дедлайн {course_date.isoformat()})")

            for period in periods:
                if not matches_period(days_left, period):
                    print(f"      • Период «{period}» не подходит (требуется {period}, осталось {days_left})")
                    continue

                date_sent = now_local.date().isoformat()
                cursor.execute(
                    "SELECT 1 FROM sent_notifications WHERE tgid=? AND course=? AND period=? AND date_sent=?",
                    (tgid, name, period, date_sent)
                )
                if cursor.fetchone():
                    print(f"      • Уже отправлено сегодня ({date_sent}) для периода «{period}»")
                    continue

                print(f"      • ОТПРАВЛЯЮ [{tgid}] «{name}», период «{period}»")
                try:
                    bot.send_message(
                        tgid,
                        f"🔔 Напоминание по «{name}»: до КТ осталось {days_left} дн. (период «{period}»)"
                    )
                except Exception as e:
                    print(f"      [!] Ошибка отправки сообщения пользователю {tgid}: {e}")
                else:
                    cursor.execute(
                        "INSERT INTO sent_notifications (tgid, course, period, date_sent) VALUES (?, ?, ?, ?)",
                        (tgid, name, period, date_sent)
                    )
                    conn.commit()

    cutoff = (now_utc.date() - timedelta(days=2)).isoformat()
    cursor.execute("DELETE FROM sent_notifications WHERE date_sent < ?", (cutoff,))
    conn.commit()
    print(f"[{now_utc.isoformat()}] Удалены все уведомления старше {cutoff}")

    conn.close()
    print(f"[{now_utc.isoformat()} UTC] ← Проверка завершена\n")

def start_notification_loop(bot):
    def _worker():
        print(f"[{datetime.utcnow().isoformat()} UTC] — Поток уведомлений начал работу")
        try:
            check_and_send_notifications(bot)
        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()} UTC] [ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            now = datetime.utcnow()
            next_minute = 30 if now.minute < 30 else 60
            next_time = now.replace(minute=next_minute % 60, second=0, microsecond=0)
            if next_minute == 60:
                next_time += timedelta(hours=1)
            sleep_seconds = (next_time - now).total_seconds()
            print(f"[{now.isoformat()} UTC] — Засыпаю до {next_time.isoformat()} UTC ({int(sleep_seconds)} сек)\n")
            time.sleep(sleep_seconds)
            _worker()

    print(f"[{datetime.utcnow().isoformat()} UTC] → Запуск потока уведомлений")
    threading.Thread(target=_worker, daemon=True).start()

def register_handlers(bot):
    start_notification_loop(bot)
