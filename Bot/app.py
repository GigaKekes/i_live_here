import sys
import os
# Добавить корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import logging
import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from config import BOT_API, RATINGS_FILE
from LLM.answer import generate_response

# Включить логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и роутера
bot = Bot(token=BOT_API)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Убедимся, что файл существует и имеет заголовки
if not os.path.exists(RATINGS_FILE):
    with open(RATINGS_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["user_id", "username", "rating"])

# Создание клавиатуры
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/start"), KeyboardButton(text="/info")],
        [KeyboardButton(text="/rate"), KeyboardButton(text="/question")]
    ],
    resize_keyboard=True
)

async def get_custom_llm_response(prompt: str, user_id: int) -> str:
    try:
        response = generate_response(prompt, user_id)  # Pass user_id here
        return response
    except Exception as e:
        logging.error(f"Ошибка при запросе к LLM: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."

@router.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer(
        "Привет! Я Ваш ai - помощник. Напишите мне сообщение, и я отвечу вам!\n"
        "Доступные команды:\n"
        "- /start: Начать работу с ботом\n"
        "- /rate: Оценить мою работу\n"
        '- /setaddress: Установить домашний адрес для наиболее релевантных ответов помощника (Адрес по умолчанию: "Санкт-Петербург, Невский проспект, 30")\n'
        "- /question: Задать вопрос\n",
        reply_markup=keyboard
    )

@router.message(Command("setaddress"))
async def set_address(message: Message):
    try:
        # Извлечение адреса из текста команды
        user_input = message.text[len("/setaddress "):].strip()
        
        if not user_input:
            await message.answer("Пожалуйста, укажите ваш адрес после команды /setaddress. Пример: /setaddress Невский проспект, д. 1")
            return
        
        # Сохранение адреса в CSV-файл
        address_file = "user_addresses.csv"
        if not os.path.exists(address_file):
            # Создание файла с заголовками, если он отсутствует
            with open(address_file, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["user_id", "username", "address"])
        
        # Запись адреса пользователя
        with open(address_file, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([message.from_user.id, message.from_user.username, user_input])
        
        await message.answer(f"Ваш адрес успешно сохранён: {user_input}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении адреса: {e}")
        await message.answer("Извините, произошла ошибка при сохранении вашего адреса.")

@router.message(Command("rate"))
async def rate_bot(message: Message):
    try:
        # Извлечение оценки из текста команды
        parts = message.text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Пожалуйста, укажите оценку от 1 до 5. Пример: /rate 5")
            return

        rating = int(parts[1])
        if rating < 1 or rating > 5:
            await message.answer("Оценка должна быть числом от 1 до 5.")
            return

        # Сохранение оценки в CSV-файл
        with open(RATINGS_FILE, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([message.from_user.id, message.from_user.username, rating])


        await message.answer(f"Спасибо за вашу оценку: {rating} ⭐️")
    except Exception as e:
        logging.error(f"Ошибка при обработке оценки: {e}")
        await message.answer("Извините, произошла ошибка при сохранении вашей оценки.")

@router.message(Command("question"))
async def ask_question(message: Message):
    try:
        # Получение текста команды
        user_input = message.text[len("/question "):].strip()
        
        if not user_input:
            await message.answer("Пожалуйста, напишите ваш вопрос после команды /question. Пример: /question Что такое искусственный интеллект?")
            return
        
        # Отображение "набирает сообщение"
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Запрос к LLM, передача user_id
        response = await get_custom_llm_response(user_input, message.from_user.id)
        
        # Отправка ответа пользователю
        await message.answer(response)
    except Exception as e:
        logging.error(f"Ошибка при обработке команды /question: {e}")
        await message.answer("Извините, произошла ошибка при обработке вашего запроса.")

@router.message()
async def handle_message(message: Message):
    user_input = message.text
    
    # Отображение "набирает сообщение"
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Получение ответа от вашей LLM с передачей user_id
    response = await get_custom_llm_response(user_input, message.from_user.id)
    
    # Отправка ответа пользователю
    await message.answer(response)

async def main():
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
