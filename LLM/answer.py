import sys
import os
# Добавить корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import json
from langchain_gigachat.chat_models import GigaChat
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from config import GigaChat_API
import requests 
from pprint3x import pprint

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создание экземпляра модели GigaChat
model = GigaChat(
    credentials=GigaChat_API,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-Pro",
    temperature=0.7,          # Контроль "творчества" ответа
    max_tokens=1000,           # Максимальная длина ответа
    verify_ssl_certs=False
)

# Шаблон промпта
message = """
Вопрос пользователя:
{question}

Учитывая все важные аспекты, сгенерируй ответ пользователю, основываясь на следующем контексте:
(ОБЯЗАТЕЛЬНО ИСПОЛЬЗУЙ НОМЕРА ИЗ КОНТЕКСТА И ПРОЧУЮ ДРУГУЮ ИНФОРМАЦИЮ ИЗ КОНТЕКСТА ЕСЛИ ЕСТЬ)
КОНТЕКСТ:
{context}
КОНЕЦ КОНТЕКСТА

Пример структуры ответа:
Здравствуйте!
(тут подробно ответ на вопрос, избегая упоминания источников данных)

Ты — AI помощник, будь внимателен и обеспечь полезный и качественный ответ.
Ответ должен быть вежливым, подробным и профессиональным, с ясными рекомендациями или информацией.
"""

prompt = ChatPromptTemplate.from_messages([("human", message)])

# Контейнер для хранения контекста
context_store = {}

# Функция получения JSON-контекста для конкретного вопроса
def get_json(input_class: str) -> str: 
    try: 
        if input_class == 'Благоустройство, ЖКХ и уборка дорог': 
            # Первый запрос 
            response = requests.get("https://geo.hack-it.yazzh.ru/api/v2/geo/buildings/search/", params={"query": "Замшина улица, дом 70, литера А"}).json() 
            pprint(response) 
 
            # Второй запрос 
            response = requests.get("https://hack-it.yazzh.ru/districts-info/building-id/58490", params={"query": "Замшина улица, дом 70, литера А"}).json()[0] 
 
            contacts = [] 
            for item in response['data']: 
                if item['category'] == 'Аварийно-диспетчерские службы': 
                    contacts.append({ 
                        'name': item['name'], 
                        'phones': item['phones'] 
                    }) 
 
            message = "" 
            for contact in contacts: 
                message += f"Название службы: {contact['name']} \n" 
                message += f"Телефоны: {', '.join(contact['phones'])} \n" 
 
            item_to_message = contacts.copy() 
 
            # Создаем словарь с ключом "message" 
            data = { 
                "message": message, 
                "contacts": item_to_message 
            } 
        else: 
            data = []  # Если данных нет 
 
        # Преобразуем в JSON-строку 
        return json.dumps(data, ensure_ascii=False) 
    except Exception as e: 
        logging.error(f"Ошибка при получении JSON: {e}") 
        return "[]"

import chromadb
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document


class typeDefiner():
    def __init__(self):
        client = chromadb.Client()
        collection_themes = client.get_or_create_collection(name="collection_themes")
        
        embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
        self.vector_store_themes = Chroma(embedding_function=embeddings)
        self.vector_store_themes.add_documents([Document('Поиск контактов, основанный на Базе Контактов Санкт-Петербурга'), 
                                        Document('Образование, Детские сады и Школы'), 
                                        Document('Благоустройство, ЖКХ и уборка дорог'),
                                        Document('Афиша и Красивые места')])
    def define_type(self, query: str):
        self.retriever_2 = self.vector_store_themes.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 1})
        
        return self.retriever_2.invoke(query)[0].page_content


# Функция генерации ответа
def generate_response(question: str, user_id: str) -> str:
    try:
        # Получение контекста для пользователя из хранилища
        context = context_store.get(user_id, "")
        
        # Получение JSON-контекста для текущего вопроса
        definer = typeDefiner()
        class_question = definer.define_type(question)
        json_context = get_json(class_question)

        # Обновляем контекст, добавляя текущую информацию
        context += f"\n\nТекущий вопрос: {question}\nКонтекст: {json_context}"
        
        # Сохраняем обновленный контекст в хранилище
        context_store[user_id] = context
        
        # Формирование запроса
        rag_chain = {"context": RunnablePassthrough(), "question": RunnablePassthrough()} | prompt | model
        response = rag_chain.invoke({
            "вопрос пользователя:": question,
            "json файл, по которому ты должен составить ответ пользователю:": json_context,
            "текущий контекст": context
        })
        
        # Возврат текста ответа
        return response.content
    except Exception as e:
        logging.error(f"Ошибка при обращении к GigaChat: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."

# # Пример использования
# if __name__ == "__main__":
#     user_id = "user123"  # Идентификатор пользователя, например, сессия или IP
#     question = "Что делать при протекшей крыше?" 
#     response = generate_response(question, user_id)
#     print(response)
