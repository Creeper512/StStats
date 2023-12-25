import requests
from flask import Flask, request, jsonify, send_file, Blueprint
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache

applist = Blueprint('AppList', __name__)

STEAM_API_URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2"

@lru_cache(maxsize=1000)  # Set the maximum cache size as needed
def get_steam_app_list():
    response = requests.get(STEAM_API_URL)
    data = response.json()
    return data['applist']['apps']

def find_similar_apps(query, app_list):
    similar_apps = []
    for app in app_list:
        app_name = app['name'].lower()
        if query.lower() in app_name:
            similar_apps.append(app)
    return similar_apps

def generate_image(similar_apps):
    font_path = "C:\\Windows\\Fonts\\msyh.ttc"  # Replace with the actual path to your font file
    normal_font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed
    num_results = len(similar_apps)
    img_height = num_results * 50 + 20  # Calculate image height based on number of results
    img = Image.new('RGB', (400, img_height), color='white')
    img_draw = ImageDraw.Draw(img)
    y_offset = 10
    for app in similar_apps:
        app_name = app['name']
        app_id = app['appid']
        img_draw.text((10, y_offset), f"游戏名: {app_name}\nApp ID: {app_id}", fill='black', font=normal_font)
        y_offset += 50
    return img

@applist.route('/GetAppList')
def get_app_list():
    query = request.args.get('query', '')

    app_list = get_steam_app_list()
    similar_apps = find_similar_apps(query, app_list)

    if similar_apps:
        image = generate_image(similar_apps)
        image_buffer = BytesIO()
        image.save(image_buffer, format='PNG')
        image_data = image_buffer.getvalue()

        return send_file(BytesIO(image_data), mimetype='image/png')
    else:
        return jsonify({"message": "No similar apps found."}), 404

if __name__ == '__main__':
    applist.run(debug=True)