import requests
from flask import Flask, request, jsonify, send_file, Blueprint
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import io
import os
from io import BytesIO
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), verbose=True)
STEAM_WEB_API_KEY = os.environ.get("STEAM_WEB_API_KEY")

gamelist = Blueprint('GameList', __name__)
LINE_CHAR_COUNT = 12 * 8

def get_game_list(steamid):
    steam_api_url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1?steamid={steamid}&key={STEAM_WEB_API_KEY}&include_appinfo=true"
    response = requests.get(steam_api_url, verify=False)
    data = response.json()

    game_list = data["response"]["games"]
    game_count = data['response']['game_count']

    steam_api_url_player_name = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2?steamids={steamid}&key={STEAM_WEB_API_KEY}"
    response_name = requests.get(steam_api_url_player_name, verify=False)
    data_name = response_name.json()
    steam_name = data_name['response']['players'][0]['personaname']

    return steam_name, game_list, game_count

def generate_game_list_image(steam_name, game_list, game_count):
    image = Image.new("RGB", (800, 900), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    font_path = f"{parent_directory}\\font\\hmsc.ttf"  # Replace with the actual path to your font file
    normal_font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed
    title_font = ImageFont.truetype(font_path, 30)
    draw.text((8,10), f"{steam_name} 拥有的所有游戏 ({game_count})", font=title_font, fill=(52,58,64))
    draw.line([(8,55), (882,55)], fill=(52,58,64), width=2)

    sorted_game_list = sorted(game_list, key=lambda x: x['name'])

    game_names = [f"{game['name']} ({game['appid']})" for game in sorted_game_list]  # Use sorted_game_list here
    games_text = ", ".join(game_names)

    split_lines = line_break(games_text, LINE_CHAR_COUNT)  # Use the existing line_break function to handle text wrapping
    split_lines = split_lines.split('\n')
    y_position = 70
    for line in split_lines:
        draw.text(xy=(8, y_position), text=line, fill=(52,58,64), font=normal_font, spacing=4)
        y_position += normal_font.getsize(line)[1] + 4  # Adjust the next line's position based on font height and spacing

    return image

@gamelist.route('/GetGameList', methods=['GET'])
def get_app_list():
    steamid = request.args.get('steamid')
    if not steamid:
        return jsonify({"error": "Missing 'steamidid' parameter"}), 400

    steam_name, game_list, game_count = get_game_list(steamid)  # Retrieve both steam_name and game_list
    image = generate_game_list_image(steam_name, game_list, game_count)  # Pass both arguments

    image_io = io.BytesIO()
    image.save(image_io, format='PNG')
    image_io.seek(0)

    return send_file(image_io, mimetype='image/png')

def line_break(line, line_char_count):
    ret = ''
    width = 0
    for c in line:
        if len(c.encode('utf8')) == 3:  # 判断是否为中文字符
            if LINE_CHAR_COUNT == width + 1:  # 剩余位置不够一个汉字
                width = 2
                ret += '\n' + c
            else:  # 中文宽度加2，注意换行边界
                width += 2
                ret += c
        else:
            if c == '\t':
                space_c = TABLE_WIDTH - width % TABLE_WIDTH  # 已有长度对TABLE_WIDTH取余
                ret += ' ' * space_c
                width += space_c
            elif c == '\n':
                width = 0
                ret += c
            else:
                width += 1
                ret += c
        if width >= LINE_CHAR_COUNT:
            ret += '\n'
            width = 0
    if ret.endswith('\n'):
        return ret
    return ret + '\n'

if __name__ == '__main__':
    gamelist.run(debug=True)
