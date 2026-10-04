import os
import asyncio
import json
import math
import wikipediaapi
import requests
from PIL import Image
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class PlantariumState(StatesGroup):
    waiting_for_photo = State()

import sys
import onnxruntime as ort
import numpy as np
def transform_image(img):
    w, h = img.size
    if w < h:
        new_w = 518
        new_h = int(518 * h / w)
    else:
        new_h = 518
        new_w = int(518 * w / h)
    img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
    
    w, h = img.size
    left = (w - 518) / 2
    top = (h - 518) / 2
    right = left + 518
    bottom = top + 518
    img = img.crop((left, top, right, bottom))
    
    img_np = np.array(img).astype(np.float32) / 255.0
    img_np = np.transpose(img_np, (2, 0, 1))
    
    mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)
    img_np = (img_np - mean) / std
    
    return img_np

class PlantClassifier:
    def __init__(self, model_path="models/plantclef/plantclef24_dinov2_fp16.onnx", labels_path="models/plantclef/classes.json"):
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opts.enable_cpu_mem_arena = False
        
        self.session = ort.InferenceSession(model_path, sess_options=opts)
        with open(labels_path, 'r', encoding='utf-8') as f:
            self.classes = json.load(f)
        
    def predict(self, image_path, top_k=5):
        try:
            img = Image.open(image_path).convert('RGB')
            img_t = np.expand_dims(transform_image(img), axis=0).astype(np.float16)
            
            input_name = self.session.get_inputs()[0].name
            output_name = self.session.get_outputs()[0].name
            
            out = self.session.run([output_name], {input_name: img_t})[0]
            
            exp_out = np.exp(out - np.max(out, axis=1, keepdims=True))
            probs = exp_out / np.sum(exp_out, axis=1, keepdims=True)
            probs = probs[0]
            
            top_indices = np.argsort(probs)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                results.append({
                    "scientific_name": self.classes[idx],
                    "confidence": float(probs[idx])
                })
                
            return results
        except Exception as e:
            print(f"Prediction error: {e}")
            return []

from app.database.db import get_connection, init_db

from aiogram.client.session.aiohttp import AiohttpSession
import aiohttp

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8740390083:AAEzIo90a7WyLZE0yAktpBmyP8NiIXQv8Xs")

session = AiohttpSession(
    connector=aiohttp.TCPConnector(force_close=True)
)
bot = Bot(token=TELEGRAM_TOKEN, session=session)
dp = Dispatcher()

def has_camera_metadata(image_path: str) -> bool:
    try:
        img = Image.open(image_path)
        exif = img.getexif()
        if not exif:
            return False
            
        # 271: Make (Производитель), 272: Model (Модель), 306: DateTime, 36867: DateTimeOriginal
        for tag_id in [271, 272, 306, 36867]:
            if tag_id in exif:
                return True
        return False
    except Exception:
        return False

def get_keyboard(game_mode: bool):
    if game_mode:
        return types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🌿 Добавить растение")],
                [types.KeyboardButton(text="📗 Мой Плантариум"), types.KeyboardButton(text="👤 Профиль")]
            ],
            resize_keyboard=True
        )
    else:
        return types.ReplyKeyboardRemove()

classifier = None
wiki = wikipediaapi.Wikipedia('PlantBot/1.0 (plant@example.com)', 'ru')

def generate_plant_text(sci_name: str) -> str:
    page = wiki.page(sci_name)
    if not page.exists():
        parts = sci_name.split()
        if len(parts) >= 2:
            short_name = f"{parts[0]} {parts[1]}"
            page = wiki.page(short_name)
            
    if page.exists():
        summary = page.summary
        cut_idx = 200
        if len(summary) > 150:
            dot_idx = summary.find('. ', 100)
            if dot_idx != -1 and dot_idx < 300:
                cut_idx = dot_idx + 1
        
        short_summary = summary[:cut_idx].strip()
        if len(summary) > cut_idx and not short_summary.endswith('.'):
            short_summary += "..."
            
        title = page.title
        
        text = f"🌱 **{title}**\n"
        text += f"*{sci_name}*\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📖 {short_summary}\n\n"
        text += f"🔗 [Читать в Википедии]({page.fullurl})"
        return text
    else:
        text = f"🌱 **Неизвестное название**\n"
        text += f"*{sci_name}*\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📖 _К сожалению, описания в русской Википедии пока нет._"
        return text

def identify_plant(image_path: str):
    predictions = classifier.predict(image_path, top_k=5)
    if not predictions: return None
        
    best_pred = predictions[0]
    scientific_name = best_pred['scientific_name']
    confidence = best_pred['confidence']
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM plants WHERE scientific_name = %s", (scientific_name,))
    plant_data = cursor.fetchone()
    
    if plant_data:
        plant_dict = dict(plant_data)
        llm_desc = plant_dict.get('llm_description')
        if not llm_desc:
            llm_desc = generate_plant_text(scientific_name)
            cursor.execute("UPDATE plants SET llm_description = %s WHERE scientific_name = %s", (llm_desc, scientific_name))
            conn.commit()
            plant_dict['llm_description'] = llm_desc
    else:
        llm_desc = generate_plant_text(scientific_name)
        cursor.execute("INSERT INTO plants (scientific_name, llm_description) VALUES (%s, %s)", (scientific_name, llm_desc))
        conn.commit()
        plant_dict = {'llm_description': llm_desc}
        
    conn.close()
    return {"scientific_name": scientific_name, "confidence": confidence, "plant_data": plant_dict}

def get_or_create_user(user_id: int, username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    game_mode = 0
    if not user:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (%s, %s)", (user_id, username))
        conn.commit()
    else:
        try:
            game_mode = user['game_mode']
        except IndexError:
            game_mode = 0
    conn.close()
    return game_mode

def unlock_plant(user_id: int, sci_name: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user_pokedex WHERE user_id = %s AND scientific_name = %s", (user_id, sci_name))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("INSERT INTO user_pokedex (user_id, scientific_name) VALUES (%s, %s)", (user_id, sci_name))
    conn.commit()
    conn.close()
    return True

@dp.message(F.text == "🌿 Добавить растение")
async def cmd_add_plant(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    game_mode = get_or_create_user(user_id, message.from_user.username)
    if not game_mode:
        return await message.answer("Сначала включите режим игры командой `/game`.")
        
    await state.set_state(PlantariumState.waiting_for_photo)
    await message.answer(
        "📸 **Добавление в Плантариум**\n\n"
        "Отправьте фото растения **КАК ФАЙЛ/ДОКУМЕНТ** (без сжатия), "
        "чтобы я мог проверить данные камеры (EXIF) и убедиться, что фото сделано вами на телефон!\n\n"
        "_(Для отмены отправьте любой текст)_",
        parse_mode="Markdown"
    )

@dp.message(PlantariumState.waiting_for_photo, F.text)
async def cancel_add_plant(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Добавление растения отменено.")

@dp.message(Command("game"))
async def cmd_toggle_game(message: types.Message):
    user_id = message.from_user.id
    current_mode = get_or_create_user(user_id, message.from_user.username)
    new_mode = 0 if current_mode else 1
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET game_mode = %s WHERE user_id = %s", (new_mode, user_id))
    conn.commit()
    conn.close()
    
    if new_mode:
        await message.answer(
            "🎮 Режим Плантариума включен! Теперь вы можете собирать коллекцию растений.\n"
            "Используйте команду `/region [Город]`, чтобы выбрать зону поиска.", 
            reply_markup=get_keyboard(True),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "📸 Режим игры выключен. Бот вернулся в режим чистого классификатора.", 
            reply_markup=get_keyboard(False)
        )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    game_mode = get_or_create_user(user_id, message.from_user.username)
    await message.answer(
        "Привет! Я бот Plant Discovery (PlantCLEF DINOv2).\n"
        "Отправь мне фото растения, и я моментально определю его из 7806 видов дикой природы!\n\n"
        "*(Секретная функция: введи `/game`, чтобы включить игровой режим и собирать свою коллекцию растений!)*", 
        parse_mode="Markdown",
        reply_markup=get_keyboard(game_mode)
    )

@dp.message(Command("region"))
async def cmd_region(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Пожалуйста, укажите город. Например: `/region Москва`\nБот возьмет большую зону вокруг этого города.", parse_mode="Markdown")
        
    region_query = args[1]
    wait_msg = await message.answer("🔍 Ищу крупный регион в базе iNaturalist...")
    
    try:
        headers = {'User-Agent': 'PlantBot/1.0'}
        place_resp = await asyncio.to_thread(requests.get, "https://api.inaturalist.org/v1/places/autocomplete", params={"q": region_query}, headers=headers)
        place_data = place_resp.json()
        
        if not place_data.get('results'):
            try:
                # Используем открытую базу OpenStreetMap для точного гео-перевода!
                osm_url = "https://nominatim.openstreetmap.org/search"
                osm_resp = await asyncio.to_thread(requests.get, osm_url, params={"q": region_query, "format": "json", "accept-language": "en"}, headers=headers)
                osm_data = osm_resp.json()
                
                if osm_data:
                    en_query = osm_data[0].get('name', region_query)
                    place_resp = await asyncio.to_thread(requests.get, "https://api.inaturalist.org/v1/places/autocomplete", params={"q": en_query}, headers=headers)
                    place_data = place_resp.json()
            except Exception as e:
                return await wait_msg.edit_text(f"❌ Ошибка гео-поиска ({e}).\nПожалуйста, введите название региона на английском языке (например: `/region Syktyvkar`).", parse_mode="Markdown")
            
        if not place_data.get('results'):
            return await wait_msg.edit_text("❌ Регион не найден даже на английском.")
            
        place = place_data['results'][0]
        place_id = place['id']
        place_name = place['display_name']
        
        await wait_msg.edit_text(f"🌍 Найден регион: **{place_name}**\nЗагружаю топ-50 растений для Плантариума...", parse_mode="Markdown")
        
        counts_resp = await asyncio.to_thread(requests.get, f"https://api.inaturalist.org/v1/observations/species_counts?place_id={place_id}&iconic_taxa=Plantae&per_page=50&locale=ru", headers=headers)
        counts_data = counts_resp.json()
        
        top_plants = []
        for idx, res in enumerate(counts_data.get('results', [])):
            taxon = res['taxon']
            rarity = '🟤 Бронза' if idx < 15 else ('⚪ Серебро' if idx < 30 else ('🟡 Золото' if idx < 45 else '💎 Алмаз'))
            top_plants.append({
                'scientific_name': taxon.get('name'),
                'common_name': taxon.get('preferred_common_name') or taxon.get('name'),
                'rarity': rarity
            })
            
        user_id = message.from_user.id
        get_or_create_user(user_id, message.from_user.username)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO region_cache (place_id, region_name, top_plants_json) VALUES (%s, %s, %s) ON CONFLICT (place_id) DO UPDATE SET region_name = EXCLUDED.region_name, top_plants_json = EXCLUDED.top_plants_json", 
                       (place_id, place_name, json.dumps(top_plants)))
                       
        cursor.execute("UPDATE users SET region_name = %s, region_place_id = %s WHERE user_id = %s", 
                       (place_name, place_id, user_id))
        conn.commit()
        conn.close()
        
        await wait_msg.edit_text(f"✅ Регион установлен: **{place_name}**!\nТеперь используйте `/plantarium` для просмотра растений и `/profile` для статистики.", parse_mode="Markdown")
        
    except Exception as e:
        await wait_msg.edit_text(f"❌ Ошибка: {e}")

def get_plantarium_text_and_kb(region_name, top_plants, unlocked_set, page=0, page_size=10):
    start = page * page_size
    end = start + page_size
    page_plants = top_plants[start:end]
    
    text = f"📗 **Плантариум: {region_name}**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, plant in enumerate(page_plants, start + 1):
        sci = plant['scientific_name']
        com = plant['common_name']
        rarity = plant['rarity']
        
        if sci in unlocked_set:
            text += f"{rarity.split()[0]} **{i}. {com}**\n"
            text += f"└ 🔬 *{sci}* [{rarity}]\n\n"
        else:
            text += f"🔒 **{i}. {com}**\n"
            text += f"└ 🔬 *{sci}* [{rarity}]\n\n"
            
    total_unlocked = len([p for p in top_plants if p['scientific_name'] in unlocked_set])
    total_pages = math.ceil(len(top_plants) / page_size)
    
    text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🏆 Собрано всего: **{total_unlocked} из {len(top_plants)}**\n"
    text += f"📄 Страница: {page + 1} из {total_pages}"
    
    buttons = []
    if page > 0:
        buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{page-1}"))
    if page < total_pages - 1:
        buttons.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page:{page+1}"))
        
    kb = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
    return text, kb

@dp.message(Command("plantarium"))
@dp.message(F.text == "📗 Мой Плантариум")
async def cmd_plantarium(message: types.Message):
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT region_name, region_place_id FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user or not user['region_place_id']:
        conn.close()
        return await message.answer("Сначала выберите регион командой `/region [Ваш город]`", parse_mode="Markdown")
        
    place_id = user['region_place_id']
    region_name = user['region_name']
    
    cursor.execute("SELECT top_plants_json FROM region_cache WHERE place_id = %s", (place_id,))
    cache = cursor.fetchone()
    if not cache:
        conn.close()
        return await message.answer("Ошибка кэша. Установите регион заново.")
        
    top_plants = json.loads(cache['top_plants_json'])
    
    cursor.execute("SELECT scientific_name FROM user_pokedex WHERE user_id = %s", (user_id,))
    unlocked_set = {row['scientific_name'] for row in cursor.fetchall()}
    conn.close()
    
    text, kb = get_plantarium_text_and_kb(region_name, top_plants, unlocked_set, page=0)
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data.startswith("page:"))
async def plantarium_page_callback(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT region_name, region_place_id FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return await callback.answer("Ошибка")
        
    cursor.execute("SELECT top_plants_json FROM region_cache WHERE place_id = %s", (user['region_place_id'],))
    cache = cursor.fetchone()
    cursor.execute("SELECT scientific_name FROM user_pokedex WHERE user_id = %s", (user_id,))
    unlocked_set = {row['scientific_name'] for row in cursor.fetchall()}
    conn.close()
    
    top_plants = json.loads(cache['top_plants_json'])
    text, kb = get_plantarium_text_and_kb(user['region_name'], top_plants, unlocked_set, page=page)
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@dp.message(Command("profile"))
@dp.message(F.text == "👤 Профиль")
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT username, region_name, region_place_id FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return await message.answer("Вы еще не зарегистрированы. Напишите `/start` или отправьте фото растения.", parse_mode="Markdown")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM user_pokedex WHERE user_id = %s", (user_id,))
    total_unlocked = cursor.fetchone()['cnt']
    
    region_info = "Не выбран"
    medal = "🌱 Новичок"
    
    if user['region_place_id']:
        region_info = user['region_name']
        cursor.execute("SELECT top_plants_json FROM region_cache WHERE place_id = %s", (user['region_place_id'],))
        cache = cursor.fetchone()
        if cache:
            top_plants = json.loads(cache['top_plants_json'])
            
            cursor.execute("SELECT scientific_name FROM user_pokedex WHERE user_id = %s", (user_id,))
            unlocked_set = {row['scientific_name'] for row in cursor.fetchall()}
            
            bronze, silver, gold, diamond = 0, 0, 0, 0
            for p in top_plants:
                if p['scientific_name'] in unlocked_set:
                    if 'Бронза' in p['rarity']: bronze += 1
                    elif 'Серебро' in p['rarity']: silver += 1
                    elif 'Золото' in p['rarity']: gold += 1
                    elif 'Алмаз' in p['rarity']: diamond += 1
                    
            if diamond >= 5:
                medal = "💎 Алмазный Мастер"
            elif gold >= 10:
                medal = "🟡 Золотой Искатель"
            elif silver >= 10:
                medal = "⚪ Серебряный Следопыт"
            elif bronze >= 10:
                medal = "🟤 Бронзовый Любитель"
                
            text = f"👤 **Профиль: {user['username'] or 'Аноним'}**\n\n"
            text += f"🌍 **Регион:** {region_info}\n"
            text += f"🏆 **Ранг:** {medal}\n"
            text += f"🌿 **Собрано растений всего:** {total_unlocked}\n\n"
            text += f"**В вашем регионе собрано по редкости:**\n"
            text += f"🟤 Бронза: {bronze}/15\n"
            text += f"⚪ Серебро: {silver}/15\n"
            text += f"🟡 Золото: {gold}/15\n"
            text += f"💎 Алмаз: {diamond}/5\n"
            
            conn.close()
            return await message.answer(text, parse_mode="Markdown")
            
    conn.close()
    await message.answer(f"👤 **Профиль: {user['username'] or 'Аноним'}**\n🌍 Регион: {region_info}\n🌿 Всего собрано: {total_unlocked}", parse_mode="Markdown")



@dp.message(F.photo | F.document)
async def handle_photo(message: types.Message, state: FSMContext):
    if not message.photo and not message.document: return
    
    current_state = await state.get_state()
    is_adding = (current_state == PlantariumState.waiting_for_photo.state)
    if is_adding:
        await state.clear()
    
    user_id = message.from_user.id
    game_mode = get_or_create_user(user_id, message.from_user.username)
        
    processing_msg = await message.answer("🔍 Анализирую фото...")
    
    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id
        if not message.document.mime_type or not message.document.mime_type.startswith('image/'):
            await processing_msg.delete()
            return await message.answer("Пожалуйста, отправьте изображение.")

    file = await bot.get_file(file_id)
    file_path = f"{file_id}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    try:
        result = await asyncio.to_thread(identify_plant, file_path)
        
        if not result:
            await processing_msg.delete()
            await message.answer("❌ Не удалось определить растение.")
            return
            
        sci_name = result["scientific_name"]
        conf = result["confidence"] * 100
        plant_data = result["plant_data"]
        
        llm_desc = plant_data.get('llm_description', '')
        
        text = f"{llm_desc}\n\n"
        
        if is_adding:
            is_document = bool(message.document)
            if not is_document:
                text += f"⚠️ **Античит:** Фото сжато! Чтобы растение зачлось, отправляйте его **как Файл/Документ**.\n\n"
            else:
                valid_exif = has_camera_metadata(temp_path)
                if not valid_exif:
                    text += f"❌ **Античит:** На фото нет данных камеры (EXIF). Похоже, оно скачано из интернета. Не добавлено!\n\n"
                else:
                    is_new = unlock_plant(user_id, sci_name)
                    if is_new:
                        text += f"🎉 **НОВОЕ РАСТЕНИЕ В ПЛАНТАРИУМЕ!** (Метаданные камеры подтверждены ✅)\n\n"
                    else:
                        text += f"ℹ️ Вы уже находили это растение ранее!\n\n"
            
        text += f"📊 **Точность:** {conf:.1f}% | ⚙️ _Plant Discovery_"
        
        await processing_msg.delete()
        await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

from aiohttp import web

async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server running on port {port}")

async def main():
    await start_web_server()
    print("Web server started, initializing DB...")
    init_db()
    
    print("Loading neural network...")
    global classifier
    classifier = PlantClassifier()
    
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
