import re

with open('telegram_bot.py', 'r') as f:
    code = f.read()

code = code.replace('WHERE scientific_name = ?', 'WHERE scientific_name = %s')
code = code.replace('SET llm_description = ?', 'SET llm_description = %s')
code = code.replace('VALUES (?, ?)', 'VALUES (%s, %s)')
code = code.replace('WHERE user_id = ?', 'WHERE user_id = %s')
code = code.replace('AND scientific_name = ?', 'AND scientific_name = %s')
code = code.replace('SET game_mode = ?', 'SET game_mode = %s')
code = code.replace('REPLACE INTO region_cache (place_id, region_name, top_plants_json) VALUES (?, ?, ?)',
                    'INSERT INTO region_cache (place_id, region_name, top_plants_json) VALUES (%s, %s, %s) ON CONFLICT (place_id) DO UPDATE SET region_name = EXCLUDED.region_name, top_plants_json = EXCLUDED.top_plants_json')
code = code.replace('region_name = ?, region_place_id = ?', 'region_name = %s, region_place_id = %s')
code = code.replace('WHERE place_id = ?', 'WHERE place_id = %s')

with open('telegram_bot.py', 'w') as f:
    f.write(code)
