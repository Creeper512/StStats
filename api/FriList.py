import requests
from flask import Flask, request, Response, send_from_directory, Blueprint, send_file
from PIL import Image, ImageDraw, ImageFont
import logging
import os
import io
import time
from functools import lru_cache
import datetime
import json
from dotenv import load_dotenv, find_dotenv

'''
这个 API 正在考虑重写
'''

load_dotenv(find_dotenv(), verbose=True)
STEAM_API_KEY = os.environ.get("STEAM_WEB_API_KEY")
frilist = Blueprint('FriList', __name__)
font_path = 'C:\\Windows\\Fonts\\msyh.ttc'
font_size = 24
# Set up logging
logging.basicConfig(level=logging.DEBUG)  # This will enable debug-level logging


def get_friend_list_info(steam_id):
    friend_list_url = f'https://api.steampowered.com/ISteamUser/GetFriendList/v1/?key={STEAM_API_KEY}&steamid={steam_id}'
    response = requests.get(friend_list_url, verify=False)
    data = response.json()
    friends_info = data['friendslist']['friends']
    return friends_info

def get_player_info(steam_ids):
    steam_ids_str = ','.join(steam_ids)
    player_summaries_url = f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_ids_str}'
    response = requests.get(player_summaries_url, verify=False)
    data = response.json()
    player_info = {}

    for player in data['response']['players']:
        steam_id = player['steamid']
        player_info[steam_id] = {
            'name': player['personaname'],
            'avatar': player['avatar'],
            'status': get_player_status(player),
        }

    return player_info

def get_player_status(player_data):
    game = player_data.get('gameextrainfo')
    persona_state = player_data.get('personastate')

    if persona_state == 1:
        return (f"在玩 {game}", (81, 207, 102)) if game else ("在线", (0, 120, 121))
    elif persona_state == 3:
        return (f"在玩 {game}", (34, 184, 207)) if game else ("离开", (59, 201, 219))
    else:
        return ("离线", (128, 128, 128))


@lru_cache(maxsize=None)
def get_avatar_image(avatar_url):
    try:
        avatar_response = requests.get(avatar_url, stream=True)
        avatar_response.raise_for_status()

        avatar_img = Image.open(avatar_response.raw)
        avatar_img = avatar_img.resize((50, 50))
        return avatar_img

    except Exception as e:
        logging.error(f"Error downloading or processing avatar: {e}")
        return None

def generate_image(player_info, steam_username, friend_list_info):
    logging.debug("Generating image...")

    num_friends = len(player_info)
    img_height = max(600, 50 + (num_friends + 1) * 80)

    img = Image.new('RGB', (1000, img_height), color=(255, 255, 255))
    font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(img)

    y = 50

    steam_username_line = f"Steam 用户 {steam_username} 的好友列表 ({num_friends})"
    draw.text((50, y), steam_username_line, fill=(0, 0, 0), font=font, encoding="utf-8")
    y += 60

    for steam_id, player_data in player_info.items():
        name = player_data['name']
        status, color = player_data['status']
        avatar_url = player_data['avatar']

        line = f"{name} {status} ({steam_id})"
        logging.debug(f"Adding line: {line}")

        friend_info = next((info for info in friend_list_info if info['steamid'] == steam_id), None)
        if friend_info and 'friend_since' in friend_info:
            friend_since_timestamp = friend_info['friend_since']
            friend_since_datetime = datetime.datetime.fromtimestamp(friend_since_timestamp)
            friend_since_str = friend_since_datetime.strftime('%Y-%m-%d %H:%M:%S')
            draw.text((200, y + 30), f"成为好友时间: {friend_since_str}", fill=(0, 0, 0), font=font, encoding="utf-8")

        draw.text((200, y), line, fill=color, font=font, encoding="utf-8")

        avatar_img = get_avatar_image(avatar_url)
        if avatar_img is not None:
            avatar_position = (100, y + 10)
            img.paste(avatar_img, avatar_position)

        y += 80

    logging.debug("Image generation complete.")
    return img

def get_steam_username(steam_id):
    player_summaries_url = f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_id}'
    response = requests.get(player_summaries_url, verify=False)
    data = response.json()

    if 'response' in data and 'players' in data['response']:
        players = data['response']['players']
        if players:
            player = players[0]
            return player['personaname']

    return None

@frilist.route('/getGeneratedImage/<image_filename>', methods=['GET'])
@frilist.route('/getSteamFriends', methods=['GET'])
def get_steam_friends():
    steam_id = request.args.get('steamid')
    steam_username = get_steam_username(steam_id)

    if steam_username is None:
        response_data = {'code': 204, 'message': 'User not found'}
        return Response(json.dumps(response_data), content_type='frilistlication/json', status=204)

    friend_list_info = get_friend_list_info(steam_id)
    friend_ids = [friend['steamid'] for friend in friend_list_info][:50]

    player_info = get_player_info(friend_ids)

    img = generate_image(player_info, steam_username, friend_list_info)

    image_io = io.BytesIO()
    img.save(image_io, format='PNG')
    image_io.seek(0)
    return send_file(image_io, mimetype='image/png')