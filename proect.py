from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.utils.i18n import gettext as _
import sqlite3
import asyncio
from datetime import datetime, timedelta
    from config import DATABASE_PATH

load_dotenv(dotenv_path="BOT_TOKEN.env")
TOKEN = os.getenv("BOT_TOKEN")
if TOKEN is None:
    raise ValueError("❌ ТОКЕН НЕ НАЙДЕН")

bot = Bot(token=TOKEN)
dispetcher = Dispatcher(storage=MemoryStorage())

ADMIN_ID = 540311740

connect = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
cursor = connect.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    name TEXT,
    date TEXT,  -- Формат: YYYY-MM-DD HH:MM
    description TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS registrations (
    user_id INTEGER,
    event_id INTEGER,
    FOREIGN KEY(event_id) REFERENCES events(id),
    UNIQUE(user_id, event_id)
)
''')
connect.commit()


class SostoyaniyaSobytiy(StatesGroup):
    zhdem_nazvanie = State()
    zhdem_datu = State()
    zhdem_vremya = State()
    zhdem_opisanie = State()
    zhdem_sobytie_dlya_udaleniya = State()
    zhdem_podderzhku = State()

# ====================== КЛАВИАТУРЫ ======================

def glavnoe_menu(is_admin: bool):
    knopki = ReplyKeyboardBuilder()
    knopki.button(text="📅 Предстоящие события")
    knopki.button(text="🆘 Поддержка")
    if is_admin:
        knopki.button(text="⚙️ Админ-панель")
    knopki.adjust(1)
    return knopki.as_markup(resize_keyboard=True)


def admin_panel_kb():
    knopki = ReplyKeyboardBuilder()
    knopki.button(text="➕ Добавить событие")
    knopki.button(text="🗑️ Удалить событие")
    knopki.button(text="📋 Список событий")
    knopki.button(text="🔙 Главное меню")
    knopki.adjust(1)
    return knopki.as_markup(resize_keyboard=True)


def knopka_otmena():
    knopki = ReplyKeyboardBuilder()
    knopki.button(text="❌ Отмена")
    return knopki.as_markup(resize_keyboard=True)


def dati():
    knopki = ReplyKeyboardBuilder()
    today = datetime.now().date()
    for i in range(7):
        date = today + timedelta(days=i)
        knopki.button(text=date.strftime("%d.%m.%Y"))
    knopki.button(text="❌ Отмена")
    knopki.adjust(3)
    return knopki.as_markup(resize_keyboard=True)


def chasi():
    knopki = ReplyKeyboardBuilder()
    for hour in range(9, 19):
        for minute in ['00', '30']:
            knopki.button(text=f"{hour}:{minute}")
    knopki.button(text="❌ Отмена")
    knopki.adjust(4)
    return knopki.as_markup(resize_keyboard=True)


# ====================== ОБРАБОТЧИКИ КОМАНД ======================

@dispetcher.message(Command("start"))
async def start(message: types.Message):
    is_admin = message.from_user.id == ADMIN_ID
    await message.answer(
        "Добро пожаловать в ботика-напоминалку",
        reply_markup=glavnoe_menu(is_admin)
    )


# ====================== ОСНОВНОЙ ИНТЕРФЕЙС ======================
@dispetcher.message(lambda message: message.text == "🆘 Поддержка")
async def support_start(message: types.Message, state: FSMContext):
    await state.set_state(SostoyaniyaSobytiy.zhdem_podderzhku)
    await message.answer(
        "✉️ Напишите, что у вас не работает или вызывает затруднение.\n\n"
        "❌ Чтобы отменить, нажмите кнопку ниже.",
        reply_markup=knopka_otmena()
    )

@dispetcher.message(SostoyaniyaSobytiy.zhdem_podderzhku)
async def support(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отправка сообщения отменена.", reply_markup=glavnoe_menu(message.from_user.id == ADMIN_ID))
        return

    text = message.text
    user = message.from_user

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "📨 <b>Новое сообщение поддержки</b>\n\n"
            f"👤 От: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"💬 Сообщение:\n{text}"
        ),
        parse_mode="HTML"
    )

    await message.answer("✅ Ваше сообщение отправлено. Администратор свяжется с вами при необходимости.", reply_markup=glavnoe_menu(message.from_user.id == ADMIN_ID))
    await state.clear()

@dispetcher.message(Command("support"))
async def support_command(message: types.Message, state: FSMContext):
    await state.set_state(SostoyaniyaSobytiy.zhdem_podderzhku)
    await message.answer(
        "Пожалуйста, опишите вашу проблему или вопрос, и мы постараемся помочь:",
        reply_markup=knopka_otmena()
    )

@dispetcher.message(lambda message: message.text == "📅 Предстоящие события")
async def show_events(message: types.Message):
    try:
        cursor.execute("SELECT * FROM events WHERE date >= datetime('now') ORDER BY date LIMIT 10")
        events = cursor.fetchall()

        if not events:
            await message.answer("Нет предстоящих событий.")
            return

        for event in events:
            builder = InlineKeyboardBuilder()
            builder.button(
                text="✅ Зарегистрироваться",
                callback_data=f"register_{event[0]}"
            )

            if message.from_user.id == ADMIN_ID:
                builder.button(
                    text="❌ Удалить",
                    callback_data=f"delete_{event[0]}"
                )
                builder.adjust(2)

            await message.answer(
                f"<b>{event[1]}</b>\n"
                f"📅 {datetime.strptime(event[2], '%Y-%m-%d %H:%M').strftime('%d.%m.%Y в %H:%M')}\n"
                f"ℹ️ {event[3]}",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@dispetcher.callback_query(lambda c: c.data.startswith('delete_') and c.from_user.id == ADMIN_ID)
async def delete_event_prompt(callback: types.CallbackQuery):
    event_id = callback.data.split('_')[1]

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"final_delete_{event_id}")
    builder.button(text="❌ Нет, отменить", callback_data="cancel_deletion")
    builder.adjust(2)

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer("Уверен, что хочешь удалить?")


# ====================== АДМИН-ПАНЕЛЬ ======================

@dispetcher.message(lambda message: message.text == "⚙️ Админ-панель" and message.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    await message.answer(
        "Выберите действие:",
        reply_markup=admin_panel_kb()
    )


@dispetcher.message(lambda message: message.text == "🔙 Главное меню")
async def vozvrat_nazad(message: types.Message):
    is_admin = message.from_user.id == ADMIN_ID
    await message.answer(
        "Главное меню:",
        reply_markup=glavnoe_menu(is_admin)
    )


# Добавление события
@dispetcher.message(lambda message: message.text == "➕ Добавить событие" and message.from_user.id == ADMIN_ID)
async def dobavlenie_eventa(message: types.Message, state: FSMContext):
    await state.set_state(SostoyaniyaSobytiy.zhdem_nazvanie)
    await message.answer(
        "Введите название события:",
        reply_markup=knopka_otmena()
    )


@dispetcher.message(SostoyaniyaSobytiy.zhdem_nazvanie)
async def vibor_datbl(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=admin_panel_kb())
        return

    await state.update_data(name=message.text)
    await state.set_state(SostoyaniyaSobytiy.zhdem_datu)
    await message.answer(
        "Выберите дату:",
        reply_markup=dati()
    )


@dispetcher.message(SostoyaniyaSobytiy.zhdem_datu)
async def event_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=admin_panel_kb())
        return

    try:
        date = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(date=date.strftime("%Y-%m-%d"))
        await state.set_state(SostoyaniyaSobytiy.zhdem_vremya)
        await message.answer(
            "Выберите время:",
            reply_markup=chasi()
        )
    except ValueError:
        await message.answer("Неверный формат даты! Выберите дату из списка:")


@dispetcher.message(SostoyaniyaSobytiy.zhdem_vremya)
async def event_time(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=admin_panel_kb())
        return

    try:
        time = datetime.strptime(message.text, "%H:%M").time()
        data = await state.get_data()
        full_date = f"{data['date']} {time.strftime('%H:%M')}"

        await state.update_data(date=full_date)
        await state.set_state(SostoyaniyaSobytiy.zhdem_opisanie)
        await message.answer(
            "Введите описание события:",
            reply_markup=knopka_otmena()
        )
    except ValueError:
        await message.answer("Неверный формат времени! Выберите время из списка:")


@dispetcher.message(SostoyaniyaSobytiy.zhdem_opisanie)
async def event_opisanie(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=admin_panel_kb())
        return

    data = await state.get_data()
    try:
        cursor.execute(
            "INSERT INTO events (name, date, description) VALUES (?, ?, ?)",
            (data['name'], data['date'], message.text)
        )
        connect.commit()
        await message.answer(
            "✅ Событие успешно добавлено!",
            reply_markup=admin_panel_kb()
        )
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
    finally:
        await state.clear()


@dispetcher.message(lambda message: message.text == "🗑️ Удалить событие" and message.from_user.id == ADMIN_ID)
async def delete_event(message: types.Message, state: FSMContext):
    await state.set_state(SostoyaniyaSobytiy.zhdem_sobytie_dlya_udaleniya)
    await show_events_for_deletion(message)


async def show_events_for_deletion(message: types.Message):
    try:
        cursor.execute("SELECT id, name, date FROM events ORDER BY date")
        events = cursor.fetchall()

        if not events:
            await message.answer("Нет событий для удаления.")
            return

        builder = InlineKeyboardBuilder()
        for event in events:
            builder.button(
                text=f"{event[1]} ({event[2][:10]})",
                callback_data=f"confirm_delete_{event[0]}"
            )
        builder.button(text="❌ Отмена", callback_data="cancel_deletion")
        builder.adjust(1)

        await message.answer(
            "Выберите событие для удаления:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@dispetcher.callback_query(lambda c: c.data.startswith('confirm_delete_') and c.from_user.id == ADMIN_ID)
async def confirm_delete(callback: types.CallbackQuery):
    event_id = callback.data.split('_')[2]

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"final_delete_{event_id}")
    builder.button(text="❌ Нет, отменить", callback_data="cancel_deletion")
    builder.adjust(2)

    await callback.message.edit_text(
        "Вы уверены, что хотите удалить это событие?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dispetcher.callback_query(lambda c: c.data.startswith('final_delete_') and c.from_user.id == ADMIN_ID)
async def final_delete(callback: types.CallbackQuery):
    event_id = callback.data.split('_')[2]

    try:
        # Удаляем регистрации
        cursor.execute("DELETE FROM registrations WHERE event_id = ?", (event_id,))
        # Удаляем событие
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        connect.commit()

        await callback.message.edit_text("✅ Событие успешно удалено!")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {str(e)}")
    finally:
        await callback.answer()


@dispetcher.callback_query(lambda c: c.data == "cancel_deletion" and c.from_user.id == ADMIN_ID)
async def cancel_deletion(callback: types.CallbackQuery):
    await callback.message.edit_text("Удаление отменено.")
    await callback.answer()


@dispetcher.message(lambda message: message.text == "📋 Список событий" and message.from_user.id == ADMIN_ID)
async def show_all_events(message: types.Message):
    try:
        cursor.execute("SELECT * FROM events ORDER BY date")
        events = cursor.fetchall()

        if not events:
            await message.answer("Нет доступных событий.")
            return

        otvet = "📋 Все события:\n\n"
        for event in events:
            otvet += (
                f"<b>{event[1]}</b>\n"
                f"ID: {event[0]}\n"
                f"Дата: {datetime.strptime(event[2], '%Y-%m-%d %H:%M').strftime('%d.%m.%Y в %H:%M')}\n"
                f"Описание: {event[3]}\n\n"
            )

        await message.answer(otvet, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


# ====================== РЕГИСТРАЦИЯ НА СОБЫТИЯ ======================

@dispetcher.callback_query(lambda c: c.data.startswith('register_'))
async def register_for_event(callback: types.CallbackQuery):
    event_id = callback.data.split('_')[1]
    user_id = callback.from_user.id

    try:
        cursor.execute("INSERT INTO registrations VALUES (?, ?)", (user_id, event_id))
        connect.commit()
        await callback.answer("✅ Вы успешно зарегистрировались!")
    except sqlite3.IntegrityError:
        await callback.answer("⚠️ Вы уже зарегистрированы на это событие!")
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


# ====================== НАПОМИНАНИЯ ======================

async def check_events():
    while True:
        try:
            cursor.execute('''
            SELECT * FROM events 
            WHERE datetime(date) BETWEEN datetime('now', '+59 minutes') AND datetime('now', '+60 minutes')
            ''')
            events = cursor.fetchall()

            for event in events:
                cursor.execute("SELECT user_id FROM registrations WHERE event_id = ?", (event[0],))
                users = cursor.fetchall()
                for user in users:
                    try:
                        await bot.send_message(
                            user[0],
                            f"⏰ Напоминание: мероприятие <b>{event[1]}</b> "
                            f"начнётся через 1 час ({datetime.strptime(event[2], '%Y-%m-%d %H:%M').strftime('%d.%m.%Y в %H:%M')})!",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Ошибка отправки уведомления: {str(e)}")

        except Exception as e:
            print(f"Ошибка проверки событий: {str(e)}")

        await asyncio.sleep(60)


# ====================== ЗАПУСК БОТА ======================

async def on_startup():
    asyncio.create_task(check_events())


# async def main():
#     await on_startup()
#     await dispetcher.start_polling(bot)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(check_events())
    await dispetcher.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())