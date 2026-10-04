# Техническое задание: локальный бот для идентификации растений

## 1. Цель проекта

Создать полностью локальную систему, которая по фотографии растения:

1. принимает изображение;
2. локально определяет вид растения с помощью PlantCLEF24 DINOv2 Core ML;
3. возвращает Top-N наиболее вероятных видов;
4. получает информацию о выбранном виде из локальной SQLite БД;
5. формирует краткую карточку растения;
6. при необходимости использует локальную Qwen3-0.6B для генерации расширенного человекочитаемого описания;
7. не использует внешние API во время работы приложения.

Главные требования:

- целевая платформа разработки/запуска: Apple MacBook с M1;
- inference должен использовать Apple Silicon / Core ML;
- классификатор должен работать полностью offline;
- покрытие: около 7 806 видов PlantCLEF24;
- текстовая LLM также должна работать локально;
- архитектура должна позволять позднее заменить отдельные компоненты без переписывания всего приложения.

---

# 2. Основной стек

## Computer Vision

Модель:

- PlantCLEF24 DINOv2 ViT-B/14
- готовый Core ML bundle
- INT8 вариант:
  `PlantCLEF24_DINOv2_int8.mlpackage`
- около 7 806 классов
- размер модели около 86 MB

Модель должна использоваться через Apple Core ML, без PyTorch runtime.

Ожидаемые файлы:

```text
models/
└── plantclef/
    ├── PlantCLEF24_DINOv2_int8.mlpackage
    ├── classes.json
    └── preprocessing.json
```

Источник модели:

Hugging Face:
https://huggingface.co/ianleelamb/yardie-plantid

## LLM

Модель:

```text
mlx-community/Qwen3-0.6B-4bit
```

Backend:

```text
MLX / mlx-lm
```

Модель используется для генерации текста, а не для идентификации растения.

Важно: LLM НЕ должна быть источником ботанической истины. Она должна получать структурированные данные из SQLite и превращать их в человекочитаемый текст.

Источник:

https://huggingface.co/mlx-community/Qwen3-0.6B-4bit

## Database

На первом этапе:

```text
SQLite
```

Файл:

```text
data/plants.db
```

PostgreSQL пока НЕ нужен.

## Python

Предпочтительно:

```text
Python 3.11 или 3.12
```

---

# 3. Архитектура

Общая схема:

```text
                    USER
                      |
                      v
                    PHOTO
                      |
                      v
          +-------------------------+
          | Image preprocessing    |
          +------------+------------+
                       |
                       v
          +-------------------------+
          | PlantCLEF24 DINOv2      |
          | Core ML INT8             |
          +------------+------------+
                       |
                       v
                Top-N predictions
                       |
                       v
          +-------------------------+
          | Plant service            |
          +------------+------------+
                       |
                       v
          +-------------------------+
          | SQLite                  |
          | 7 806 plant species     |
          +------------+------------+
                       |
                       v
              Plant information
                       |
             +---------+---------+
             |                   |
             v                   v
       Template response    Qwen3 0.6B
                            (optional)
                                 |
                                 v
                         Extended response
```

---

# 4. Важный принцип архитектуры

Не делать:

```text
photo -> LLM -> "это растение X"
```

Не делать:

```text
photo -> classifier -> LLM -> "расскажи всё о X"
```

без проверки данных.

Правильный pipeline:

```text
photo
  |
  v
PlantCLEF classifier
  |
  v
species_id
  |
  v
SQLite
  |
  +-- structured facts
  |
  v
template OR Qwen3
```

LLM является генератором/редактором текста, но не ботанической базой знаний.

---

# 5. Структура проекта

Создать следующую структуру:

```text
plant-bot/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   │
│   ├── classifier/
│   │   ├── __init__.py
│   │   ├── plant_classifier.py
│   │   └── preprocessing.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   └── generator.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── models.py
│   │   └── repository.py
│   │
│   └── services/
│       ├── __init__.py
│       └── plant_service.py
│
├── models/
│   ├── plantclef/
│   │   ├── PlantCLEF24_DINOv2_int8.mlpackage
│   │   ├── classes.json
│   │   └── preprocessing.json
│   │
│   └── qwen/
│
├── data/
│   └── plants.db
│
├── scripts/
│   ├── init_db.py
│   ├── test_classifier.py
│   ├── test_llm.py
│   └── benchmark.py
│
├── tests/
│   ├── test_classifier.py
│   ├── test_database.py
│   └── test_llm.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# 6. Установка окружения

Использовать обычный Python venv.

Команды:

```bash
mkdir plant-bot
cd plant-bot

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
```

Проверить архитектуру:

```bash
uname -m
```

Ожидаемый результат:

```text
arm64
```

Установить зависимости:

```bash
pip install mlx
pip install mlx-lm

pip install pyobjc-framework-CoreML
pip install pyobjc-framework-Vision
```

Опционально, только если понадобится работа с Core ML model inspection/conversion:

```bash
pip install coremltools
```

Не устанавливать без необходимости:

- PyTorch
- TensorFlow
- CUDA
- Docker
- Ollama
- LangChain
- LlamaIndex

---

# 7. Qwen3

Проверить MLX:

```bash
python -c "import mlx; print('MLX:', mlx.__version__)"
```

Первый запуск:

```bash
python -m mlx_lm.chat \
  --model mlx-community/Qwen3-0.6B-4bit
```

Модель должна быть скачана локально в cache.

LLM должна использоваться только для генерации/переформатирования информации.

---

# 8. PlantCLEF classifier

Сначала реализовать classifier как самостоятельный компонент.

До создания бота, БД и LLM должен существовать работающий CLI-тест:

```bash
python scripts/test_classifier.py path/to/plant.jpg
```

Ожидаемый результат:

```text
Top 5 predictions:

1. Rosa canina              0.913
2. Rosa rubiginosa          0.041
3. Rosa arvensis            0.018
4. Rosa gallica             0.011
5. Rosa dumalis             0.008
```

Названия и значения должны соответствовать реальному выводу модели.

---

# 9. Core ML inference

Не использовать PyTorch для inference PlantCLEF.

Использовать:

```text
Python
  |
  v
PyObjC
  |
  v
Apple Core ML
  |
  v
Apple Silicon GPU / Neural Engine
```

Нужно определить точный input/output интерфейс модели автоматически через Core ML.

Не предполагать имена input/output features.

Сначала написать диагностический скрипт, который выводит:

- model inputs;
- input shape;
- input type;
- model outputs;
- output shape;
- количество классов.

Например:

```bash
python scripts/inspect_model.py
```

Если такого файла нет, его необходимо добавить.

---

# 10. Preprocessing

Использовать preprocessing, соответствующий `preprocessing.json` из model bundle.

Не придумывать собственные normalization values.

Нужно проверить:

- размер входного изображения;
- RGB/BGR;
- resize;
- crop;
- normalization;
- значения mean/std;
- expected pixel range.

Все параметры должны быть взяты из model metadata / preprocessing.json.

---

# 11. Top-N результат

Classifier должен возвращать не одну строку, а структурированный результат.

Пример Python-объекта:

```python
Prediction(
    class_index=1234,
    scientific_name="Rosa canina",
    confidence=0.913
)
```

Метод:

```python
classifier.predict(image, top_k=5)
```

должен возвращать:

```python
list[Prediction]
```

Сортировка по confidence — по убыванию.

---

# 12. Confidence

Не считать softmax score автоматически абсолютной вероятностью правильности.

В UI на первом этапе можно называть это:

```text
Уверенность модели
```

Но сохранить возможность в будущем провести calibration.

Нужны режимы:

```text
high confidence
medium confidence
low confidence
```

Пороговые значения не фиксировать до тестирования на реальных изображениях.

---

# 13. SQLite schema

Создать таблицу:

```sql
CREATE TABLE plants (
    id INTEGER PRIMARY KEY,
    scientific_name TEXT NOT NULL UNIQUE,
    common_name_ru TEXT,
    common_name_en TEXT,
    family TEXT,
    genus TEXT,

    description TEXT,
    characteristics TEXT,
    habitat TEXT,
    distribution TEXT,
    flowering_period TEXT,

    toxicity TEXT,
    edibility TEXT,

    interesting_facts TEXT,

    llm_description TEXT,
    llm_features TEXT,
    llm_interesting_fact TEXT,

    created_at TEXT,
    updated_at TEXT
);
```

Отдельно:

```sql
CREATE TABLE classification_aliases (
    id INTEGER PRIMARY KEY,
    plant_id INTEGER NOT NULL,
    alias TEXT NOT NULL,

    FOREIGN KEY (plant_id)
        REFERENCES plants(id)
);
```

В будущем можно добавить:

```sql
plant_images
taxonomic_synonyms
sources
licenses
```

---

# 14. Сопоставление class index -> species

Критически важно:

```text
model output index
       |
       v
classes.json
       |
       v
scientific name
       |
       v
SQLite
```

Не хранить зависимость только по позиции массива внутри Python-кода.

`classes.json` является источником mapping между classifier output и scientific name.

---

# 15. PlantService

Создать сервис:

```python
PlantService
```

Он должен объединять classifier и database.

Пример:

```python
result = plant_service.identify(image)
```

Результат:

```python
IdentificationResult(
    predictions=[
        Prediction(...),
        Prediction(...),
        ...
    ],
    plant=Plant(...)
)
```

Сервис не должен знать детали Core ML.

---

# 16. LLM service

Создать:

```text
app/llm/generator.py
```

Класс:

```python
PlantDescriptionGenerator
```

Основной метод:

```python
generate_card(plant: Plant) -> str
```

Вход LLM должен быть структурированным.

Например:

```json
{
  "scientific_name": "Rosa canina",
  "common_name": "Шиповник собачий",
  "family": "Rosaceae",
  "height": "1–3 м",
  "flowering": "май–июнь",
  "features": [
    "колючие побеги",
    "белые или розовые цветки",
    "красные плоды"
  ]
}
```

System prompt:

```text
Ты составляешь краткие ботанические карточки растений.

Используй только информацию, переданную во входных данных.
Не придумывай отсутствующие факты.
Не добавляй медицинские, токсикологические или иные утверждения,
если они отсутствуют во входных данных.

Сформируй:
1. краткое описание;
2. 3 отличительных признака;
3. интересный факт, только если он указан во входных данных.

Пиши на русском языке.
Будь кратким.
```

Ограничить генерацию:

```text
max_tokens ~= 150
```

Точное значение подобрать экспериментально.

---

# 17. Не запускать LLM для каждого запроса

Обязательный кэш.

Логика:

```text
species
   |
   v
SQLite
   |
   +-- llm_description exists?
          |
       +--+--+
       |     |
      yes    no
       |     |
       v     v
    return  Qwen
             |
             v
          SQLite
             |
             v
           return
```

Таким образом один и тот же вид не будет генерироваться повторно.

---

# 18. Ещё лучше: предварительная генерация

В будущем сделать:

```bash
python scripts/generate_descriptions.py
```

Скрипт:

1. читает все растения из SQLite;
2. проверяет наличие `llm_description`;
3. вызывает Qwen только для отсутствующих;
4. сохраняет результат;
5. показывает progress bar;
6. позволяет продолжить после остановки.

После заполнения базы runtime-путь:

```text
PHOTO
 ↓
PlantCLEF
 ↓
species
 ↓
SQLite
 ↓
готовый текст
```

Qwen при обычном запросе вообще не нужен.

---

# 19. Два режима ответа

## Быстрый режим

Не использовать LLM.

Шаблон:

```text
🌿 {common_name}

{scientific_name}

Уверенность модели: {confidence}

🔎 Отличительные признаки:
• ...
• ...
• ...

🌸 Цветение: ...
📏 Высота: ...
🌍 Распространение: ...
```

Это самый быстрый вариант.

## Подробный режим

Использовать Qwen:

```text
SQLite
 ↓
Qwen3
 ↓
расширенная карточка
```

Например кнопка:

```text
[Подробнее]
```

---

# 20. Benchmark

Создать:

```bash
python scripts/benchmark.py
```

Замерять отдельно:

1. загрузку модели;
2. preprocessing;
3. Core ML inference;
4. postprocessing;
5. SQLite lookup;
6. Qwen generation;
7. полный pipeline.

Особенно важно измерить:

```text
cold start
warm inference
```

Не считать загрузку модели частью времени каждого запроса.

Модель должна загружаться один раз при старте приложения и оставаться в памяти.

---

# 21. Требования к runtime

После старта приложения:

```text
PlantCLEF model -> loaded once
Qwen -> loaded lazily
SQLite -> persistent connection / lightweight access
```

Qwen желательно загружать lazy:

```text
startup
  |
  +-- PlantCLEF loaded
  |
  +-- SQLite opened
  |
  +-- Qwen NOT loaded
```

Qwen загружается только при необходимости.

---

# 22. Обработка ошибок

Обязательно обработать:

### Невалидное изображение

```text
Не удалось открыть изображение.
```

### Очень маленькое изображение

Вернуть понятную ошибку.

### Низкая уверенность

Не утверждать, что растение определено точно.

Например:

```text
Модель не смогла уверенно определить растение.

Наиболее вероятные варианты:
1. ...
2. ...
3. ...
```

### Нет данных в SQLite

Classifier всё равно должен вернуть scientific name.

Например:

```text
Вид распознан как:
Rosa canina

Подробная информация для этого вида пока отсутствует.
```

### Ошибка LLM

Бот должен продолжать работать без LLM.

LLM является optional dependency runtime.

---

# 23. Безопасность данных

Не отправлять фотографии или данные о растении во внешние сервисы.

Не использовать:

- внешние AI API;
- облачные LLM API;
- PlantNet API;
- OpenAI API;
- Google Vision API.

Вся runtime-обработка должна быть локальной.

---

# 24. Что НЕ нужно делать на первом этапе

Не делать сразу:

- Telegram integration;
- web frontend;
- PostgreSQL;
- Redis;
- Docker;
- vector database;
- DINOv2 embeddings;
- RAG;
- обучение собственной модели;
- fine-tuning Qwen;
- автоматический web scraping.

Сначала получить стабильный pipeline:

```text
image -> PlantCLEF -> Top-5
```

Затем:

```text
image -> PlantCLEF -> SQLite
```

Затем:

```text
image -> PlantCLEF -> SQLite -> Qwen
```

---

# 25. Этапы разработки

## Phase 1 — Classifier

Цель:

```text
image -> Top-5 PlantCLEF predictions
```

Done criteria:

- модель загружается;
- изображение принимается;
- preprocessing соответствует модели;
- Core ML работает;
- Top-5 выводятся;
- benchmark работает.

---

## Phase 2 — SQLite

Цель:

```text
prediction -> plant record
```

Done criteria:

- SQLite создан;
- class index mapping работает;
- species lookup работает;
- отсутствующие записи обрабатываются.

---

## Phase 3 — PlantService

Цель:

```text
image -> IdentificationResult
```

Done criteria:

- classifier скрыт за service interface;
- database скрыта за repository;
- компоненты тестируются независимо.

---

## Phase 4 — Qwen

Цель:

```text
Plant -> generated description
```

Done criteria:

- Qwen запускается через MLX;
- prompt ограничивает галлюцинации;
- max token ограничен;
- результат сохраняется в SQLite;
- повторная генерация не происходит без необходимости.

---

## Phase 5 — Full local pipeline

```text
image
 ↓
PlantCLEF
 ↓
Top-5
 ↓
SQLite
 ↓
fast card
 ↓
optional Qwen detailed response
```

---

# 26. Целевая производительность

Не фиксировать заранее конкретные миллисекунды.

На первом запуске выполнить benchmark на конкретном MacBook M1.

Цель:

- модель загружается один раз;
- inference работает локально;
- повторные классификации выполняются без cold start;
- SQLite lookup практически не влияет на latency;
- Qwen вызывается только по необходимости;
- обычный ответ без Qwen должен быть максимально быстрым.

Результаты benchmark записывать в:

```text
benchmark-results.md
```

---

# 27. Что coding agent должен сделать первым

НЕ реализовывать весь проект сразу.

Сначала:

### Step 1

Создать структуру проекта.

### Step 2

Создать venv/requirements.

### Step 3

Добавить диагностику Core ML model:

```bash
python scripts/inspect_model.py
```

### Step 4

Реализовать:

```bash
python scripts/test_classifier.py image.jpg
```

### Step 5

Проверить реальный inference на MacBook M1.

### Step 6

Сделать benchmark.

Только после успешного Step 6 переходить к SQLite.

---

# 28. Критически важное требование для агента

Не выдумывать API, имена input/output, preprocessing или структуру model outputs.

Перед реализацией classifier необходимо прочитать metadata реального `.mlpackage`.

Если обнаружится, что готовый Core ML bundle требует другой способ вызова, изменить implementation под фактическую модель.

Также не предполагать, что `confidence` является calibrated probability.

---

# 29. Источники моделей

PlantCLEF24 Core ML:

https://huggingface.co/ianleelamb/yardie-plantid

Qwen3 0.6B MLX:

https://huggingface.co/mlx-community/Qwen3-0.6B-4bit

Оригинальный PlantCLEF 2024 dataset/model:

https://zenodo.org/records/10848263

---

# 30. Итоговая архитектура

```text
                    ┌──────────────────────┐
                    │       IMAGE          │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Image preprocessing  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ PlantCLEF24 DINOv2   │
                    │ Core ML INT8          │
                    │ 7,806 classes         │
                    └──────────┬───────────┘
                               │
                               ▼
                         Top-5 predictions
                               │
                               ▼
                    ┌──────────────────────┐
                    │     PlantService     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       SQLite         │
                    │  plant information   │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┴──────────────┐
                 │                            │
                 ▼                            ▼
        Fast template response        Qwen3-0.6B MLX
                                      optional / cached
                                             │
                                             ▼
                                     detailed response
```

Главный принцип:

> **PlantCLEF определяет растение. SQLite хранит факты. Qwen делает текст красивым.**

Это позволяет сохранить полностью локальную работу, высокую скорость и возможность независимо менять classifier, БД или LLM.
