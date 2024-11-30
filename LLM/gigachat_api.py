from langchain_gigachat.chat_models import GigaChat
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
import logging
import json
import pandas as pd

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создание экземпляра модели GigaChat
model = GigaChat(
    credentials="ZTU3MmZjYjYtYzM0MS00NGEwLWJjOTEtYzhjYjAwNmVmODA3OjQ0MWQyNWU4LWM0NGQtNDlhMy1iMzZmLTBhNTIxMzFkZjQ0OQ==",
    scope="GIGACHAT_API_PERS",
    model="GigaChat-Pro",
    temperature=0.7,          # Контроль "творчества" ответа
    max_tokens=300,           # Максимальная длина ответа
    verify_ssl_certs=False
)

# Шаблон промпта
message = """
Отвечай на вопросы только с помощью полученного контекста.

{prompt}

Контекст:
{context}
"""

prompt = ChatPromptTemplate.from_messages([("human", message)])

# Функция получения JSON-контекста
def get_json(prompt: str) -> str:
    """
    Получает JSON-контекст на основе вопроса.
    Здесь можно реализовать запросы к базе данных, API, или обработку файла.
    """
    try:
        # Пример данных
        if "детские сады" in prompt.lower():
            data = [
                {"name": "Детский сад №1", "address": "ул. Ленина, д. 1", "available_slots": 5},
                {"name": "Детский сад №2", "address": "ул. Пушкина, д. 10", "available_slots": 3}
            ]
        else:
            data = []  # Если данных нет

        # Преобразуем в JSON-строку
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Ошибка при получении JSON: {e}")
        return "[]"

# Функция генерации ответа
def generate_response(prompt: str) -> str:
    # try:
        # Получение JSON-контекста
        # context = get_json(prompt)
        context = """
        [
            {"name": "Детский сад №1", "address": "ул. Ленина, д. 1", "available_slots": 5},
            {"name": "Детский сад №2", "address": "ул. Пушкина, д. 10", "available_slots": 3}
        ]
        """
        
        # Создание цепочки
        rag_chain = {"context": RunnablePassthrough(), "prompt": RunnablePassthrough()} | prompt | model
        
        # Формирование запроса
        data = pd.read_csv("../DataSet/questions.csv")

        # Преобразование данных в список словарей
        examples = data.to_dict(orient='records')

        # Использование примеров в rag_chain.invoke
        response = rag_chain.invoke({
            "вопрос пользователя:": prompt,
            "json файл, по которому ты должен составить ответ пользователю:": context,
            "примеры и шаблоны, по которым ты должен сгенерировать ответ на вопрос пользователя опираясь на данные в json файле": examples
        })        
        # Возврат текста ответа
        return response.content
    # except Exception as e:
    #     logging.error(f"Ошибка при обращении к GigaChat: {e}")
    #     return "Извините, произошла ошибка при обработке вашего запроса."

# Пример использования
if __name__ == "__main__":
    prompt = "Какие детские сады есть в Санкт-Петербурге?"
    response = generate_response(prompt)
    print(response)