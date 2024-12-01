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
import csv
import chromadb
from config import ADDRESSES_FILE
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создание экземпляра модели GigaChat
model = GigaChat(
    credentials=GigaChat_API,
    scope="GIGACHAT_API_PERS",
    model="GigaChat", # GigaChat (GigaChat Lite), GigaChat-Pro, GigaChat-Max
    temperature=0.7,
    max_tokens=1000,
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

# Функция получения JSON-контекста для конкретного вопроса

def get_building_id(address): 
    """Получить ID здания по адресу""" 
    url = "https://geo.hack-it.yazzh.ru/api/v2/geo/buildings/search/" 
    response = requests.get(url, params={"query": address}).json() 
    if response.get("success") and response["data"]: 
        return response["data"][0]["id"]  # Берем ID первого здания из ответа 
    return None 
 
def get_building_details(building_id): 
    """Получить детали здания по ID""" 
    url = f"https://geo.hack-it.yazzh.ru/api/v2/geo/buildings/{building_id}" 
    response = requests.get(url).json() 
    if response.get("data"): 
        return response["data"]  # Возвращаем все данные о здании 
    return None 
 
def get_vehicles_around(latitude, longitude): 
    """Получить транспорт вокруг здания по координатам""" 
    url = "https://hack-it.yazzh.ru/api/v2/external/dus/get-vehicles-around" 
    response = requests.get(url, params={"latitude": latitude, "longitude": longitude}).json() 
 
    if response.get("success") and response.get("data"): 
        return response["data"]  # Список транспорта 
    return [] 
 
def get_dispatcher_phones(building_id, dist): 
    """ 
    Получить все номера телефонов из категории 'Аварийно-диспетчерские службы' 
    по building_id. 
    """ 
    url = f"https://hack-it.yazzh.ru/districts-info/building-id/{building_id}" 
    response = requests.get(url, params={"query": dist}).json()[0] 
 
    ans = [] 
    for item in response['data']: 
        ans.append(item) 
    return ans 
 
 
def get_json(input_class: str, user_address) -> str: 
    try: 
        if input_class == 'Благоустройство, ЖКХ и уборка дорог': 
            # Первый запрос 
            building_id = get_building_id(user_address) 
            if not building_id: 
                print("Не удалось найти здание по адресу.") 
                return 
 
            # Получение телефонов аварийно-диспетчерских служб 
            dispatcher_phones = get_dispatcher_phones(building_id, user_address) 
            details = get_building_details(building_id) 
            latitude = details['latitude'] 
            longtitude = details['longitude'] 
            vechicle = get_vehicles_around(latitude, longtitude) 
            vechicle.extend(dispatcher_phones) 
            combined_json_str = json.dumps(vechicle, ensure_ascii=False, indent=4) 
            return combined_json_str 
 
        elif input_class == 'Поиск контактов, основанный на Базе Контактов Санкт-Петербурга': 
            # Первый запрос 
            response = requests.get("https://hack-it.yazzh.ru/districts-info/building-id/58490", params={"query": "Замшина улица, дом 70, литера А"}).json()[0] 
 
            contacts = [] 
            for item in response['data']: 
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
        elif input_class == 'Раздельный сбор мусора': 
            building_id = get_building_id(user_address) 
            if not building_id: 
                print("Не удалось найти здание по адресу.") 
                return 
            details = get_building_details(building_id) 
            latitude = details['latitude'] 
            longtitude = details['longitude'] 
            recycling_response = requests.get( 
                f"https://yazzh.gate.petersburg.ru/api/v2/recycling/map/?category=Все&location_latitude={latitude}&location_longitude={longtitude}&location_radius=3" 
            ).json() 
            data = [] 
            count = 0 # мы оставляем только первые 5 объектов из за ошибки в api на вашей стороне :(
            for item in recycling_response['data']:
                if count == 5:
                    break 
                data.append({ 
                    'title': item['title'], 
                    'location': item['location'] 
                })
                count += 1

        else: 
            return "[]"

        # Преобразуем в JSON-строку 
        return json.dumps(data, ensure_ascii=False) 
    except Exception as e: 
        logging.error(f"Ошибка при получении JSON: {e}") 
        return "[]"

class typeDefiner():
    def __init__(self):
        client = chromadb.Client()
        collection_themes = client.get_or_create_collection(name="collection_themes")
        
        embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
        self.vector_store_themes = Chroma(embedding_function=embeddings)
        self.vector_store_themes.add_documents([Document('Поиск контактов, основанный на Базе Контактов Санкт-Петербурга'), 
                                        Document('Раздельный сбор мусора'), 
                                        Document('Благоустройство, ЖКХ и уборка дорог'),
                                        ])
    def define_type(self, query: str):
        self.retriever_2 = self.vector_store_themes.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 1})
        
        return self.retriever_2.invoke(query)[0].page_content

def find_address_by_user_id(user_id: int) -> str:
    try:
        with open(ADDRESSES_FILE, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            # Пропускаем заголовок
            next(reader)
            for row in reader:
                if int(row[0]) == user_id:
                    return row[2]  # Адрес находится в третьей колонке
        return "Адрес не найден."
    except FileNotFoundError:
        return "CSV-файл не найден."
    except Exception as e:
        return f"Произошла ошибка: {e}"


# Функция генерации ответа
def generate_response(question: str, user_context: str, user_id) -> str:
    try:
        # Получение JSON-контекста для текущего вопроса
        definer = typeDefiner()
        class_question = definer.define_type(question)
        user_address = find_address_by_user_id(user_id)
        json_context = get_json(class_question, user_address=user_address)
        
        # Формирование запроса
        rag_chain = {"context": RunnablePassthrough(), "question": RunnablePassthrough()} | prompt | model
        response = rag_chain.invoke({
            "вопрос пользователя:": question,
            "json файл, по которому ты должен составить ответ пользователю:": json_context,
            "текущий контекст": user_context
        })
        
        # Возврат текста ответа
        return response.content
    except Exception as e:
        logging.error(f"Ошибка при обращении к GigaChat: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."
