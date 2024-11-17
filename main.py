import random
import asyncio
import os
import json
import uuid
from typing import Any
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram import F

# Установите токен вашего бота
API_TOKEN = 'YOUR TG BOT TOKEN'

# Путь к файлу с данными пользователей
current_directory = os.path.dirname(os.path.abspath(__file__))
USER_DATA_FILE = os.path.join(current_directory, 'user_data.json')


SYMBOLS = {
    "Пиво": "🍺",
    "Вино": "🍷",
    "Серфер": "🏄",
    "Тунец": "🐟",
    "Осьминог": "🐙",
    "Флаг Португалии": "🇵🇹",
    "ВНЖ": "🪪",
    "Чемодан": "🧳",
    "Океан": "🌊"
}

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Глобальная переменная для хранения данных пользователей
user_data = {}

# Функция для загрузки данных пользователей
def load_user_data():
    """Загружает данные пользователей из файла, если файл существует."""
    if not os.path.exists(USER_DATA_FILE):
        # Файл не существует, создаем его с пустым содержимым
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        return {}  # Возвращаем пустой словарь, как если бы файл был пустым

    with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}  # Если файл поврежден, возвращаем пустой словарь

# Функция для записи данных пользователей в файл
def save_user_data(data):
    """Сохраняет данные пользователей в файл."""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Функция для очистки базы данных
def clear_user_data():
    """Очищает данные пользователей в базе данных."""
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)  # Записываем пустой словарь

# Функция для разбанивания пользователей при старте
async def unban_users_on_start():
    """Пытается разбанить пользователей, которые были заблокированы ранее."""
    global user_data  # Убедимся, что мы работаем с глобальной переменной
    user_data = load_user_data()  # Загружаем данные пользователей
    for user_id in list(user_data.keys()):
        try:
            # Получаем chat_id из данных пользователя
            chat_id = user_data[user_id]["chat_id"]
            await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            print(f"Пользователь {user_id} разбанен.")
            del user_data[user_id]  # Удаляем из данных после разбанивания
        except Exception as e:
            print(f"Не удалось разбанить пользователя {user_id}: {e}")
    save_user_data(user_data)  # Сохраняем обновленные данные

# Функция для удаления сообщения, если оно существует
async def delete_message_if_exists(chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
        print(f"Сообщение с ID {message_id} удалено.")
    except TelegramForbiddenError:
        print(f"Боту не хватает прав для удаления сообщения с ID {message_id}.")
    except Exception as e:
        print(f"Сообщение с ID {message_id} уже удалено или возникла другая ошибка: {e}")


# Обработчик сообщений
@dp.message(F.text)
async def getmessage(message: types.Message):
    user_id = message.from_user.id
    print(f'Сообщение от {user_id}')

    if user_id in user_data:
        print(f'{user_id} ЕСТЬ в базе')
        try:
            # Проверка на совпадение идентификатора сообщения капчи
            if user_data[user_id]["question_message_id"] == message.message_id:
                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                print(f"Удалено сообщение от пользователя {user_id}.")
        except TelegramForbiddenError:
            print("Боту не хватает прав для удаления сообщений.")
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")
    else:
        print(f'{user_id} нет в базе')

# Обработчик присоединений новых участников
@dp.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def new_chat_member(event: types.ChatMemberUpdated):
    new_member = event.new_chat_member.user
    user_id = new_member.id
    chat_id = event.chat.id  # Сохраняем chat_id

    if user_id == bot.id:
        print("Бот не будет блокировать себя.")
        return

    if user_id in user_data and user_data[user_id]["status"] == "blocked":
        return  # Игнорируем если пользователь заблокирован

    # Сохраняем данные пользователя, включая chat_id
    user_data[user_id] = {
        "status": "pending",
        "correct_answer": None,
        "question_message_id": None,
        "captcha_id": str(uuid.uuid4()),  # Генерация уникального идентификатора для капчи
        "chat_id": chat_id  # Сохраняем ID чата
    }
    save_user_data(user_data)

    correct_item = random.choice(list(SYMBOLS.keys()))
    other_items = random.sample([item for item in SYMBOLS.keys() if item != correct_item], 2)
    options = [correct_item] + other_items
    random.shuffle(options)

    keyboard = InlineKeyboardBuilder()
    for item in options:
        keyboard.button(text=SYMBOLS[item], callback_data=item)
    keyboard.adjust(3)

    if new_member.username:
        mention = f"@{new_member.username}"
    else:
        mention = f'<a href="tg://user?id={user_id}">{new_member.first_name}</a>'

    question_message = await bot.send_message(
        chat_id,
        f"{mention}, знаете ли, что:\n{get_random_fact_from_file('portugal.json')}\n\nА сейчас выберите '{correct_item}'. У вас есть 2 минуты!",
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )

    user_data[user_id]["correct_answer"] = correct_item
    user_data[user_id]["question_message_id"] = question_message.message_id
    save_user_data(user_data)

    await asyncio.sleep(120)

    if user_data[user_id]["status"] == "pending":
        await ban_user(chat_id, user_id, question_message)
        user_data[user_id]["status"] = "blocked"
        save_user_data(user_data)

# Функция для блокировки пользователя и удаления сообщения капчи
async def ban_user(chat_id: int, user_id: int, question_message: types.Message):
    try:
        await bot.ban_chat_member(chat_id, user_id)

        # Удаляем сообщение капчи
        if question_message:
            await delete_message_if_exists(chat_id, question_message.message_id)

        print(f"Пользователь {user_id} был забанен и удалён из группы.")
        await asyncio.sleep(3 * 60 * 60)  # 3 часа
        await bot.unban_chat_member(chat_id, user_id)
        print(f"Пользователь {user_id} был разбанен и может снова присоединиться.")
    except Exception as e:
        print(f"Ошибка при блокировке пользователя: {e}")


# Обработчик правильного ответа на капчу
@dp.callback_query(F.data)
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if user_id not in user_data:
        await callback.answer("Это не ваша капча! И не вам ее проходить!", show_alert=True)
        return

    if user_data[user_id]["status"] == "blocked":
        await callback.answer("Вы заблокированы и не можете отвечать на этот вопрос.", show_alert=True)
        return

    # Проверка, что это тот же вопрос (по идентификатору сообщения)
    if callback.message.message_id != user_data[user_id]["question_message_id"]:
        await callback.answer("Вы не можете отвечать на этот вопрос.", show_alert=True)
        return

    if callback.data != user_data[user_id]["correct_answer"]:
        await callback.answer("Неправильно! Вы были заблокированы на 3 часа.")
        await ban_user(chat_id, user_id, callback.message)  # Передаем сообщение капчи в `ban_user`
        user_data[user_id]["status"] = "blocked"
        save_user_data(user_data)

        # Удаляем пользователя из данных только после выполнения блокировки
        del user_data[user_id]
        save_user_data(user_data)
    else:
        user_data[user_id]["status"] = "approved"
        await callback.answer("Правильный ответ! Добро пожаловать.")

        # Удаляем сообщение капчи после успешного ответа
        await delete_message_if_exists(chat_id, user_data[user_id]["question_message_id"])

        # Удаляем пользователя из данных только после выполнения всех действий
        del user_data[user_id]
        save_user_data(user_data)


# Функция для получения случайного факта из файла
def get_random_fact_from_file(file_name):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_directory, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            facts = json.load(file)
            if facts:
                return random.choice(facts)
            else:
                print("Список фактов пустой.")
                return None
    except FileNotFoundError:
        print(f"Файл {file_name} не найден.")
        return None

# Запуск бота
async def main():
    await unban_users_on_start()  # Запускаем разбанивание пользователей
    await dp.start_polling(bot)  # Запускаем polling для бота, используя await

if __name__ == "__main__":
    asyncio.run(main())  # Запуск основного кода через asyncio.run()
