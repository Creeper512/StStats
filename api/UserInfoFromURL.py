import requests
from flask import Flask, request, jsonify, send_file, Blueprint, redirect
from PIL import Image, ImageDraw, ImageFont
import io
import os
from io import BytesIO
import datetime
import re
from dotenv import load_dotenv, find_dotenv
import requests_cache

userinfofromurl = Blueprint('userinfofromurl', __name__)

load_dotenv(find_dotenv(), verbose=True)
verify=False
STEAM_WEB_API_KEY = os.environ.get("STEAM_WEB_API_KEY")
CACHE = requests_cache.CachedSession(cache_name='steam_cache', expire_after=900, verify=False)

def get_user_id(url):
    response = CACHE.get(f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1?key={STEAM_WEB_API_KEY}&vanityurl={url}", verify=False, timeout=10)
    data = response.json()
    steamid = data['response']['steamid']
    return steamid

@userinfofromurl.route('/GetUserInfoFromURL', methods=['GET'])
def get_app_list():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    print(f"正在获取 {url} 的 SteamID...")

    try:
        steamid = get_user_id(url)  # Retrieve both steam_name and game_list
        if steamid == None:
            image = gen_error_image(steamid)
        else:
            print(f"正在重定向到 ./GetUserInfo?steamid={steamid}")
            return redirect(f'./GetUserInfo?steamid={steamid}')
    except Exception as e:
        print("error: ", e)
        raise
        image = gen_exception_image(e)

    image_io = io.BytesIO()
    image.save(image_io, format='PNG')
    image_io.seek(0)
    print(f"[{steamid}] 图片已返回")
    return send_file(image_io, mimetype='image/png')

if __name__ == '__main__':
    userinfofromurl.run(debug=True)
