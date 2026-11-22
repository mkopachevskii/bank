# Banking Backend API (`banking_app`)
Учебный pet-проект банковского бэкенда на Django и Django REST Framework. Писал его для практики в backend-разработке, проектировании REST API, работе с PostgreSQL и применении принципов ООП.
В проекте реализовано управление клиентами, банковскими счетами (дебетовыми и кредитными) и переводы средств между счетами с проверкой прав доступа, атомарными транзакциями и автотестами.

## Стек технологи
* Python 3.13
* Django 6.1 & Django REST Framework 3.18
* PostgreSQL ('psycopg2-binary')
* Django TestCase & DRF APIClient — для модульного и интеграционного тестирования

## Что реализовано в проекте
* Денежные расчёты без потери точности: все балансы, кредитные лимиты и суммы переводов хранятся и считаются через `Decimal`, чтобы избежать проблем с округлением `float`.
* Безопасные транзакции: списание, зачисление денег и создание записи в истории (`Transaction`) обёрнуты в `transaction.atomic()` — если на любом этапе произойдёт ошибка, база откатится в исходное состояние.
* Вынесенная бизнес-логика (сервисный слой): чтобы не перегружать `views.py`, логику переводов вынес в отдельный класс `TransferService` (`core/services.py`) со своим исключением `TransferError`.
* Авторизация и проверка владельца счёта:
  * API закрыто от анонимных запросов (`IsAuthenticated`, `SessionAuthentication`, `BasicAuthentication`).
  * Модель `Client` связана с `User`, поэтому при попытке перевести деньги с чужого счёта сервер вернёт `403 Forbidden`.
* Автотесты: написал 11 тестов (`core/tests.py`), которые проверяют логику счетов, валидацию переводов, права доступа и коды ответов API (`200`, `400`, `403`, `404`).

## Структура проекта
```text
banking_app/
├── config/
├── core/
│   ├── migrations/
│   ├── admin.py
│   ├── models.py
│   ├── serializers.py
│   ├── services.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```
## Основные эндпоинты API
Все запросы требуют авторизации (SessionAuthentication или BasicAuthentication):
```text
   GET, POST /api/clients/ — список клиентов или создание нового клиента
   GET, POST /api/accounts/ — список счетов или открытие нового счёта
   POST /api/accounts/{id}/transfer/ — перевод средств со счёта {id} на другой счёт
   GET /api/transactions/ — история транзакций (только чтение)
```

## Пример перевода средств
Запрос: `POST /api/accounts/1/transfer/`
{
  "target_account_id": 2,
  "amount": "250.00"
}

Ответ (`200 OK`):

{
  "message": "Перевод успешно выполнен!",
  "new_balance": "750.00"
}

Какие ошибки обрабатываются:
* `400 Bad Request` — не хватает средств, перевод самому себе, отрицательная/нулевая или некорректная сумма.
* `403 Forbidden` — пользователь не авторизован или пытается перевести деньги с чужого счёта.
* `404 Not Found` — указан несуществующий счёт отправителя или получателя.

## Как запустить проект локально
1. Клонируйте репозиторий и перейдите в папку проекта:
   git clone <url-репозитория>
   cd banking_app
2. Создайте и активируйте виртуальное окружение:
   python -m venv venv
   .\venv\Scripts\activate
3. Установите зависимости:
   pip install -r requirements.txt
4. Настройте PostgreSQL и переменные окружения:
   Создайте базу данных `banking_db` в PostgreSQL. При необходимости задайте переменные окружения (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`), после чего примените миграции:
   python manage.py migrate
5. Создайте суперпользователя и запустите сервер:
   python manage.py createsuperuser
   python manage.py runserver

## Быстрый запуск с помощью Docker (рекомендуемый способ)
1. Склонируйте репозиторий и перейдите в папку проекта:
   git clone https://github.com/mkopachevskii/bank.git
   cd banking_app
2. Запустите сборку и контейнеры (Django + PostgreSQL):
   docker compose up --build
3. После запуска миграций и старта сервера приложение будет доступно по адресу http://127.0.0.1:8000/

## Запуск тестов
python manage.py test