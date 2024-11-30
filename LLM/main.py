import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Инициализация модели для эмбеддингов
model = SentenceTransformer('all-MiniLM-L6-v2')

# Пример запроса пользователя и объектов из датасета
user_query = "Как получить справку о доходах?"

dataset = [
    {"id": 1, "text": "Как оформить налоговый вычет?"},
    {"id": 2, "text": "Где найти документы по государственной помощи?"},
    {"id": 3, "text": "Какие льготы для пенсионеров в Санкт-Петербурге?"},
    {"id": 4, "text": "Как получить справку о доходах?"}
]

# Получение эмбеддингов для запроса пользователя
user_query_embedding = model.encode([user_query])

# Получение эмбеддингов для объектов из датасета
dataset_texts = [item["text"] for item in dataset]
dataset_embeddings = model.encode(dataset_texts)

# Вычисление косинусного расстояния
cosine_similarities = cosine_similarity(user_query_embedding, dataset_embeddings).flatten()

# Пороговое значение для принятия решения о выполнении поиска
threshold = 0.7  # Можете настроить этот порог в зависимости от ситуации

# Поиск, если косинусное расстояние больше порога
results = []
for idx, similarity in enumerate(cosine_similarities):
    if similarity > threshold:
        results.append({
            "id": dataset[idx]["id"],
            "text": dataset[idx]["text"],
            "similarity": similarity
        })

# Функция для поиска информации на сайте
def search_on_government_site(query):
    search_url = f"https://www.gov.spb.ru/search/?query={query}"
    response = requests.get(search_url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        # Пример извлечения ссылок с сайта
        links = soup.find_all('a', {'class': 'search-result-title'})
        return [link.get_text() for link in links]
    else:
        return None

# Применяем логику выбора ответа
if results:
    print("Результаты поиска в базе данных:")
    for result in results:
        print(f"ID: {result['id']}, Text: {result['text']}, Similarity: {result['similarity']}")
else:
    print("Ни одного подходящего ответа в базе данных не найдено. Пытаемся найти информацию на сайте.")
    search_results = search_on_government_site(user_query)
    if search_results:
        print("Результаты поиска на сайте:")
        for result in search_results:
            print(result)
    else:
        print("Не удалось найти информацию на сайте. Используем fallback-ответ.")
        print("Для получения справки о доходах, пожалуйста, обратитесь в налоговую службу или на сайт Минфина Санкт-Петербурга.")
