import requests
from flask import Flask, request, jsonify, send_file, Blueprint
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import io
import os
import re
import sys
from io import BytesIO
import time
import datetime
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), verbose=True)
STEAM_WEB_API_KEY = os.environ.get("STEAM_WEB_API_KEY")

appinfo = Blueprint('AppInfo', __name__)
LINE_CHAR_COUNT = 12 * 8.5
max_length = 320

def get_game_info(appid):
    print(f"[{appid}] 开始请求 API 以查询游戏数据")
    start_time_api = time.time()
    steam_api_url = f"https://store.steampowered.com/api/appdetails/?appids={appid}&cc=cn&l=schinese"
    xhh_api_url = f"https://api.xiaoheihe.cn/game/get_game_detail/?os_type=web&version=999.0.0&appid={appid}"
    augmented_price_api_url = f"https://api.augmentedsteam.com/v2/prices/?appids={appid}&cc=cn"
    augmented_info_api_url = f"https://api.augmentedsteam.com/v2/app/{appid}/"
    response = requests.get(steam_api_url, verify=False)
    if not response.text.strip():
        print(f"[{appid}] 通过 Steam Web API l=schinese 参数请求失败，尝试使用 l=english")
        steam_api_url = f"https://store.steampowered.com/api/appdetails/?appids={appid}&cc=cn&l=english"
        response = requests.get(steam_api_url, verify=False)
        if not response.text.strip():
            print(f"[{appid}] l=english 依然失败。已返回 None")
            return None
    data = response.json()

    if not data[str(appid)]['success']:
        print(f"[{appid}] 通过 Steam Web API l=schinese 参数请求失败 (success=false)，尝试使用 l=english")
        steam_api_url = f"https://store.steampowered.com/api/appdetails/?appids={appid}&cc=cn&l=english"
        response = requests.get(steam_api_url, verify=False)
        data = response.json()
        if not data[str(appid)]['success']:
            print(f"[{appid}] l=english 依然失败。已返回 None")
            return None

    response_xhh = requests.get(xhh_api_url)
    data_xhh = response_xhh.json()

    response_augsteam_info = requests.get(augmented_info_api_url)
    data_augsteam_info = response_augsteam_info.json()

    game_data = data[str(appid)]
    name = game_data['data']['name']
    app_type = game_data['data']['type']
    description = game_data['data']['short_description']
    is_free = game_data['data']['is_free']

    if "achievements" in game_data['data']:
        achievements_num = game_data['data']['achievements']['total']
    else:
        achievements_num = 0

    response_augsteam = requests.get(augmented_price_api_url)
    data_augsteam = response_augsteam.json()
    coming_soon = game_data['data']['release_date']['coming_soon']

    if "developers" in game_data['data']:
        developers = ", ".join(game_data['data']['developers'])
    else:
        developers = "无开发者"
    if "publishers" in game_data['data']:
        publishers = ", ".join(game_data['data']['publishers'])
    else:
        publishers = "无发行商"

    release_date = game_data['data']['release_date']['date']
    support_win = game_data['data']['platforms']['windows']
    support_mac = game_data['data']['platforms']['mac']
    support_linux = game_data['data']['platforms']['linux']
    all_descriptions = ""

    if not data_augsteam_info['data']['metacritic']:
        mscore_user = 'NA'
    else:
        if "userscore" in data_augsteam_info['data']['metacritic']:
            mscore_user = data_augsteam_info['data']['metacritic']['userscore']
        else:
            mscore_user = 'NA'

    if "family_sharing" in data_augsteam_info['data']:
        family_sharing = data_augsteam_info['data']['family_sharing']
    else:
        family_sharing = 'NA'

    if "categories" in game_data['data']:
        categories = game_data['data']["categories"]
        all_descriptions = ", ".join([category["description"] for category in categories])
    else:
        categories = []
        all_descriptions = "未知"

    website = game_data['data']['website']

    if "genres" in game_data['data']:
        genres = game_data['data']['genres']
        all_genres = ", ".join([category["description"] for category in genres])
    else:
        all_genres = f'Unknown'

    if app_type == 'game':
        display_type = '游戏 / 软件'
    elif app_type == 'dlc':
        display_type = 'DLC'
    elif app_type == 'music':
        display_type = '原声音轨'
    elif app_type == 'hardware':
        display_type = '硬件'
    elif app_type == 'video':
        display_type = '影片'
    elif app_type == 'mod':
        display_type = 'MOD'
    else:
        display_type = '未知类型'

    if is_free:
        free = '免费开玩'
    else:
        free = '收费'

    if coming_soon:
        other_info = f"即将推出于 {release_date}"

    if not coming_soon:
        response_webapi = requests.get(f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1?appid={appid}&key={STEAM_WEB_API_KEY}", verify=False)
        webapi_data = response_webapi.json()
        online_players = webapi_data['response']['player_count']
        if 'recommendations' not in game_data['data']:
            other_info = f"发布于 {release_date} | {online_players} 位玩家游戏中"
            recommendations = 'Unknown'
        else:
            recommendations = game_data['data']['recommendations']['total']
            other_info = f"发布于 {release_date} | {online_players} 位玩家游戏中 | {recommendations} 个好评"
    else:
        other_info = f"即将发布于 {release_date}"

    if support_win:
        display_support_win = '支持 Windows'
    else:
        display_support_win = '不支持 Windows'

    if support_mac:
        display_support_mac = '支持 Mac OS X'
    else:
        display_support_mac = '不支持 Mac OS X'

    if support_linux:
        display_support_linux = '支持 Linux'
    else:
        display_support_linux = '不支持 Linux'

    if not is_free and not coming_soon:
        if data_augsteam['data'][f'app/{appid}']['lowest'] is not None:
            lowest_price_record = data_augsteam['data'][f'app/{appid}']['lowest']['recorded']
        else:
            lowest_price_record = '100'
    else:
        lowest_price_record = '100'

    # 小黑盒部分
    if "steam_appid" in data_xhh['result']:
        xhh_available = 'true'
        if not is_free and not coming_soon:
            lowest_price = data_xhh['result']['user_num']['game_data'][1]['value']
            if 'is_lowest' in data_xhh['result']['price']:
                price_lowest = data_xhh['result']['price']['is_lowest']
            else:
                price_lowest = '0'
            if 'new_lowest' in data_xhh['result']['price']:
                price_new_lowest = data_xhh['result']['price']['new_lowest']
            else:
                price_new_lowest = '0'
            if "deadline_date" in data_xhh['result']['price']:
                deaddate = data_xhh['result']['price']['deadline_date']
            else:
                deaddate = '未知'
        else:
            lowest_price = '0'
            price_lowest = '0'
            price_new_lowest = '0'
            deaddate = '未知'
        support_chinese = data_xhh['result']['support_chinese']
        xhh_name = data_xhh['result']['name']
        if app_type == 'game' or app_type == 'mod':
            recommended_rate = data_xhh['result']['user_num']['game_data'][3]['value']
            high_online_yesterday = data_xhh['result']['user_num']['game_data'][4]['value']
            per_online = data_xhh['result']['user_num']['game_data'][5]['value']
            per_hour = data_xhh['result']['user_num']['game_data'][7]['value']
            review_summary = data_xhh['result']['game_review_summary']
            if 'mscore' in data_xhh['result']['menu_v2'][-1]['type']:
                mscore_value = data_xhh['result']['menu_v2'][-1]['value']
            else:
                print('No mscore found')
                mscore_value = '0'
            if 'dlc' in data_xhh['result']['menu_v2'][-2]['type']:
                xhh_dlcs = data_xhh['result']['menu_v2'][-2]['value']
                dlcs_info = re.search(r'\d+', xhh_dlcs)
                if dlcs_info:
                    dlc_count = int(dlcs_info.group())
                else:
                    dlc_count = '0'
            else:
                dlc_count = '0'
            xhh_players = data_xhh['result']['user_num']['game_data'][-2]['value']
        else:
            mscore_value = '0'
            recommendations = '0'
            recommended_rate = '0'
            high_online_yesterday = '0'
            per_online = '0'
            per_hour = '0'
            review_summary = '未知'
            xhh_players = '0'
        if "appicon" in data_xhh['result']:
            appicon = data_xhh['result']['appicon']
        else:
            appicon = 'unknown'
        if 'game_award' in data_xhh['result']:
            award = data_xhh['result']["game_award"]
            all_award = ", ".join([category["desc"] for category in award])
        else:
            award = []
            all_award = '未知'
    else:
        price_lowest = '0'
        price_new_lowest = '0'
        xhh_players = '0'
        xhh_name = '未知'
        mscore_value = '0'
        recommended_rate = 'false'
        xhh_available = "0"
        lowest_price = '0'
        recommendations = '0'
        high_online_yesterday = '0'
        per_online = '0'
        per_hour = '0'
        appicon = 'unknown'
        support_chinese = '-1'
        review_summary = '未知'
        deaddate = '未知'

    end_time_api = time.time()
    execution_time_api = end_time_api - start_time_api
    print(f"[{appid}] 已完成 API 请求")
    return name, app_type, description, display_type, free, is_free, developers, publishers, release_date, display_support_win, display_support_mac, display_support_linux, all_descriptions, game_data, all_genres, coming_soon, other_info, execution_time_api, website, xhh_available, lowest_price, recommended_rate, high_online_yesterday, per_online, per_hour, appicon, review_summary, mscore_value, support_chinese, xhh_name, xhh_players, price_new_lowest, deaddate, price_lowest, lowest_price_record, mscore_user, family_sharing, achievements_num, all_award, dlc_count

def clean_html_tags(text):
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text()
    clean_text = clean_text.replace("\r", "").replace("\n", "").replace("\t", "")
    return clean_text

def generate_game_info_image(appid, name, app_type, description, display_type, free, is_free, developers, publishers, release_date, display_support_win, display_support_mac, display_support_linux, all_descriptions, game_data, all_genres, coming_soon, other_info, execution_time_api, website, xhh_available, lowest_price, recommended_rate, high_online_yesterday, per_online, per_hour, appicon, review_summary, mscore_value, support_chinese, xhh_name, xhh_players, price_new_lowest, deaddate, price_lowest, lowest_price_record, mscore_user, family_sharing, achievements_num, all_award, dlc_count):
    print(f"[{appid}] 开始图片生成任务")
    start_time = time.time()
    image_width = 840
    image_height = 640

    background_url = f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/page_bg_generated_v6b.jpg"
    response = requests.get(background_url, verify=False)
    background_data = response.content
    background = Image.open(BytesIO(background_data))
    print(f"[{appid}] 背景图片下载完毕")

    # Resize the background image to the specified height
    background_resized = background.resize((image_width, image_height), Image.ANTIALIAS)
    background_rgba = background_resized.convert("RGBA")
    image = background_resized.copy()

    draw = ImageDraw.Draw(image)
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    font_path = f"{parent_directory}\\font\\STImgFonts-HEF.otf"
    font_bold_path = f"{parent_directory}\\font\\STImgFonts.otf"
    normal_font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed
    title_font = ImageFont.truetype(font_bold_path, 30)
    small_font = ImageFont.truetype(font_path, 12)
    lsmall_font = ImageFont.truetype(font_path, 14)
    mscore_font = ImageFont.truetype(font_bold_path, 28)

    try:
        if appicon != 'unknown':
            print(appicon)
            icon_response = requests.get(appicon, verify=False)
            app_icon_1 = Image.open(BytesIO(icon_response.content))
            app_icon_2 = app_icon_1.convert("RGBA")
            app_icon_3 = app_icon_2.resize((32,32), Image.ANTIALIAS)
            image.paste(app_icon_3, (8, 15), app_icon_3)
            draw.text((50,10), f"{name}", font=title_font, fill=(222,226,230))
        else:
            draw.text((8,10), f"{name}", font=title_font, fill=(222,226,230))
    except Exception as e:
        print("error when get game icon")
        draw.text((8,10), f"{name}", font=title_font, fill=(222,226,230))

    draw.line([(8,55), (832,55)], fill=(233,236,239), width=2)
    draw.text((8,60), f"{free} | {display_type} | {other_info}", font=normal_font, fill=(222,226,230))

    truncated_desc = truncate_text(description, max_length)

    split_lines = line_break(truncated_desc, LINE_CHAR_COUNT)  # 使用自动换行函数处理文本
    split_lines = split_lines.split('\n')
    y_position = 90
    for line in split_lines:
        draw.text(xy=(8, y_position), text=line, fill=(222,226,230), font=normal_font, spacing=3)
        y_position += normal_font.getsize(line)[1] + 3  # 根据字体高度和间距调整下一行的位置

    if coming_soon:
        draw.text((8,240), f"此游戏还尚未正式发布\n预计推出时间: {release_date}", fill=(222,226,230), font=normal_font)
    elif is_free:
        draw.text((8,240), f"该游戏国区免费开玩", fill=(222,226,230), font=normal_font)
    else:
        cn_price_rep = requests.get(f"https://store.steampowered.com/api/appdetails/?appids={appid}&cc=cn&filters=price_overview", verify=False)
        hk_price_rep = requests.get(f"https://store.steampowered.com/api/appdetails/?appids={appid}&cc=hk&filters=price_overview", verify=False)
        ar_price_rep = requests.get(f"https://store.steampowered.com/api/appdetails/?appids={appid}&cc=ar&filters=price_overview", verify=False)
        tr_price_rep = requests.get(f"https://store.steampowered.com/api/appdetails/?appids={appid}&cc=tr&filters=price_overview", verify=False)
        data_cn = cn_price_rep.json()
        data_hk = hk_price_rep.json()
        data_ar = ar_price_rep.json()
        data_tr = tr_price_rep.json()
        if "price_overview" in data_cn[str(appid)]['data']:
            data_cn_json = data_cn[str(appid)]
            price_cn = data_cn_json['data']['price_overview']['final_formatted']
            price_cn_discount = data_cn_json['data']['price_overview']['discount_percent']
            draw.text((8,240), f"国区售价: {price_cn}", font=normal_font, fill=(222,226,230))
            draw.text((208,240), f"-{price_cn_discount}%", font=normal_font, fill=(81,207,102))
            original_price = data_cn_json['data']['price_overview']['initial_formatted']
        else:
            print(data_cn)
            draw.text((8,240), f"国区无售价", font=normal_font, fill=(222,226,230))

        if "price_overview" in data_hk[str(appid)]['data']:
            data_hk_json = data_hk[str(appid)]
            price_hk = data_hk_json['data']['price_overview']['final_formatted']
            price_hk_discount = data_hk_json['data']['price_overview']['discount_percent']
            draw.text((278,240), f"港区售价: {price_hk}", font=normal_font, fill=(222,226,230))
            draw.text((478,240), f"-{price_hk_discount}%", font=normal_font, fill=(81,207,102))
        else:
            draw.text((278,240), f"港区无售价", font=normal_font, fill=(222,226,230))

        if "price_overview" in data_ar[str(appid)]['data']:
            data_ar_json = data_ar[str(appid)]
            price_ar = data_ar_json['data']['price_overview']['final_formatted']
            price_ar_discount = data_ar_json['data']['price_overview']['discount_percent']
            draw.text((8,260), f"阿区售价: {price_ar}", font=normal_font, fill=(222,226,230))
            draw.text((208,260), f"-{price_ar_discount}%", font=normal_font, fill=(81,207,102))
        else:
            draw.text((8,260), f"阿区无售价", font=normal_font, fill=(222,226,230))

        if "price_overview" in data_tr[str(appid)]['data']:
            data_tr_json = data_tr[str(appid)]
            price_tr = data_tr_json['data']['price_overview']['final_formatted']
            price_tr_discount = data_tr_json['data']['price_overview']['discount_percent']
            draw.text((278,260), f"土区售价: {price_tr}", font=normal_font, fill=(222,226,230))
            draw.text((478,260), f"-{price_tr_discount}%", font=normal_font, fill=(81,207,102))
        else:
            draw.text((278,260), f"土区无售价", font=normal_font, fill=(222,226,230))

    draw.text((8,300), f"开发商: {developers} | 发行商: {publishers}", font=normal_font, fill=(222,226,230))
    draw.text((8,320), f"{display_support_win} | {display_support_mac} | {display_support_linux}", font=normal_font, fill=(222,226,230))

    print(f"[{appid}] 小黑盒数据可用性:{xhh_available}")

    if xhh_available != '0':
        if mscore_value != '0':
            if mscore_value > 90:
                mscore_color = 47,158,68
            elif mscore_value < 70:
                mscore_color = 250,176,5
            elif mscore_value < 50:
                mscore_color = 255,107,107
            elif mscore_value < 30:
                mscore_color = 224,49,49
            elif mscore_value < 10:
                mscore_color = 201,42,42
            else:
                mscore_color = 47,158,68
            if mscore_user == 'NA':
                draw.text((670,480), f"Metacritic 评分", font=normal_font, fill=(222,226,230))
                draw.text((715,500), f"{mscore_value}", font=mscore_font, fill=mscore_color)
            else:
                draw.text((670,480), f"Metacritic 评分", font=normal_font, fill=(222,226,230))
                draw.text((675,500), f"{mscore_value}", font=mscore_font, fill=mscore_color)
                draw.text((670,535), f"媒体均分", font=small_font, fill=(173,181,189), align='center')
                draw.line([(725,510), (725,530)], fill=(173,181,189), width=1)
                draw.text((745,500), f"{mscore_user}", font=mscore_font, fill=mscore_color)
                draw.text((740,535), f"玩家评分", font=small_font, fill=(173,181,189), align='center')
        if support_chinese:
            draw.text((765,60), f"支持中文", font=normal_font, fill=(222,226,230))
        if not is_free and not coming_soon:
            if lowest_price_record != '100':
                lowest_datetime = datetime.datetime.fromtimestamp(lowest_price_record)
                lowest_price_date = lowest_datetime.strftime('%y-%m-%d')
                draw.text((548,240), f"国区史低: {lowest_price} (首次记录于 {lowest_price_date})", font=normal_font, fill=(222,226,230))
            else:
                draw.text((548,240), f"国区史低: {lowest_price}", font=normal_font, fill=(222,226,230))
            if price_new_lowest == 1:
                draw.text((548,260), f"当前价格为新历史最低", font=normal_font, fill=(81,207,102))
            else:
                if price_lowest == 1:
                    draw.text((548,260), f"当前价格为历史最低", font=normal_font, fill=(222,226,230))
        if deaddate != '未知':
            draw.text((8,280), f"优惠还{deaddate}结束，结束后将恢复至原价 {original_price}", font=normal_font, fill=(81,207,102))
        if not coming_soon:
            if review_summary == '好评如潮':
                review_summary_color = 55,178,77
            elif review_summary == '特别好评':
                review_summary_color = 81,207,102
            elif review_summary == '多半好评':
                review_summary_color = 116,184,22
            elif review_summary == '褒贬不一':
                review_summary_color = 252,196,25
            elif review_summary == '多半差评':
                review_summary_color = 253,126,20
            elif review_summary == '差评如潮':
                review_summary_color = 240,62,62
            else:
                review_summary_color = 255,255,255
        if all_award != '未知':
            draw.text((8,580), f"被提名: {all_award}", font=normal_font, fill=(222,226,230))
        if app_type == 'game' or app_type == 'mod':
            draw.text((8,460), f"昨日峰值在线: {high_online_yesterday} 玩家", font=normal_font, fill=(222,226,230))
            draw.text((238,460), f"本月平均在线: {per_online} 玩家", font=normal_font, fill=(222,226,230))
            draw.text((8,480), f"平均游戏时长: {per_hour}", font=normal_font, fill=(222,226,230))
            draw.text((238,480), f"小黑盒玩家数: {xhh_players}", font=normal_font, fill=(222,226,230))
            if not coming_soon:
                draw.text((8,500), f"Steam 好评率: {recommended_rate} ({review_summary})", font=normal_font, fill=review_summary_color)
        draw.text((8,600), f"小黑盒上该游戏的名称: {xhh_name}", font=lsmall_font, fill=(173,181,189))
    else:
        if price_cn_discount != '0':
            draw.text((8,280), f"游戏原价 {original_price}", font=normal_font, fill=(81,207,102))
        draw.text((8,600), f"无法从小黑盒 API (api.xiaoheihe.cn) 获取数据! 峰值在线人数、国区史低和评分等数据将无法显示。该游戏可能已被小黑盒屏蔽。", font=small_font, fill=(173,181,189))

    if dlc_count != 0:
        dlc_info = f'| {dlc_count} 个 DLC'
    else:
        dlc_info = ' '

    if achievements_num == 0:
        if dlc_count != 0:
            draw.text((8,520), f"没有任何成就 | {dlc_count} 个 DLC", font=normal_font, fill=(222,226,230))
        else:
            draw.text((8,520), f"该游戏没有任何成就", font=normal_font, fill=(222,226,230))
    else:
        draw.text((8,520), f"该游戏共有 {achievements_num} 个成就 {dlc_info}", font=normal_font, fill=(222,226,230))

    if not family_sharing and not is_free:
        draw.text((8,540), f"注意: 该游戏不支持家庭共享", font=normal_font, fill=(252,196,25))

    draw.text((8,340), f"特性:", font=normal_font, fill=(222,226,230))

    max_text_width = 720
    description_lines = []
    words = all_descriptions.split()
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if normal_font.getsize(test_line)[0] <= max_text_width:
            current_line = test_line
        else:
            description_lines.append(current_line)
            current_line = word
    description_lines.append(current_line)

    current_y = 360
    for line in description_lines:
        draw.text((8, current_y), line, fill=(222,226,230), font=normal_font)
        current_y += 20

    if app_type != 'music':
        draw.text((8,420), f"类别: {all_genres}", font=normal_font, fill=(222,226,230))

    if app_type == 'dlc':
        dlc_need_game = game_data['data']['fullgame']['name']
        dlc_need_game_appid = game_data['data']['fullgame']['appid']
        draw.text((8,580), f"此 DLC 需要拥有 {dlc_need_game} ({dlc_need_game_appid}) 才能畅玩。", font=normal_font, fill=(248,249,250))

    draw.text((8,440), f"官网: {website}", font=normal_font, fill=(222,226,230))

    end_time = time.time()
    execution_time = end_time - start_time
    draw.text((8,620), f"由 StStats 生成 | API 请求用了 {execution_time_api:.2f} 秒 | 图像生成大约用了 {execution_time:.2f} 秒 | 数据来源于 Steam Web API 以及小黑盒 | Python {sys.version.split()[0]}", font=small_font, fill=(173,181,189))
    print(f"[{appid}] 已完成图片生成")
    return image

def gen_error_info_image(appid):
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    font_path = f"{parent_directory}//font//hmsc.ttf"
    font_bold_path = f"{parent_directory}//font//STImgFonts.otf"
    normal_font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed
    title_font = ImageFont.truetype(font_bold_path, 30)
    image = Image.new("RGBA", (600, 260), (255,255,255))

    draw = ImageDraw.Draw(image)
    draw.line([(8,55), (792,55)], fill=(52,58,64), width=2)
    draw.text((8,60), f"在 Steam 商店 API 上找不到 App ID 为 {appid} 的游戏，可能是因为:\n- Steam API 返回内容为空。(即使游戏是存在的)\n- 服务器网络问题。\n- 该游戏已锁国区。\n- 这个游戏可能真的不存在。", font=normal_font, fill=(52,58,64))
    draw.text((8,230), f"Powered by StStats & Python", font=normal_font, fill=(134,142,150))
    draw.text((8,10), f":( 遇到了个错误", font=title_font, fill=(52,58,64))

    return image

@appinfo.route('/GetAppInfo', methods=['GET'])
def get_app_info():
    appid = request.args.get('appid')
    if not appid:
        return jsonify({"error": "Missing 'appid' parameter"}), 400

    print(f"正准备查询 AppID {appid} 的信息")

    game_info = get_game_info(appid)
    if game_info is None:
        print(f"查询 {appid} 出错")
        image = gen_error_info_image(appid)
    else:
        name, app_type, description, display_type, free, is_free, developers, publishers, release_date, display_support_win, display_support_mac, display_support_linux, all_descriptions, game_data, all_genres, coming_soon, other_info, execution_time_api, website, xhh_available, lowest_price, recommended_rate, high_online_yesterday, per_online, per_hour, appicon, review_summary, mscore_value, support_chinese, xhh_name, xhh_players, price_new_lowest, deaddate, price_lowest, lowest_price_record, mscore_user, family_sharing, achievements_num, all_award, dlc_count = game_info
        description = clean_html_tags(description)
        image = generate_game_info_image(appid, name, app_type, description, display_type, free, is_free, developers, publishers, release_date, display_support_win, display_support_mac, display_support_linux, all_descriptions, game_data, all_genres, coming_soon, other_info, execution_time_api, website, xhh_available, lowest_price, recommended_rate, high_online_yesterday, per_online, per_hour, appicon, review_summary, mscore_value, support_chinese, xhh_name, xhh_players, price_new_lowest, deaddate, price_lowest, lowest_price_record, mscore_user, family_sharing, achievements_num, all_award, dlc_count)  # 传递 appid 参数

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

def truncate_text(text, max_length):
    if len(text) > max_length:
        truncated_text = text[:max_length-3] + "..."
        return truncated_text
    else:
        return text

if __name__ == '__main__':
    appinfo.run(debug=True)
