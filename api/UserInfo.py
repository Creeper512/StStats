import requests
import flask
from flask import Flask, request, jsonify, send_file, Blueprint
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import os
import time
import sys
import re
from io import BytesIO
import datetime
from dotenv import load_dotenv, find_dotenv
import html2text
import requests_cache
import concurrent.futures

'''
警告! 在这段代码里，你可能会看到:
1. 谜之代码
2. if 套娃
3. 摆烂 (指 try...except...)
4. ChatGPT
5. 此代码依靠 Bug 运行
如有不适，请尽快执行 rm -rf /* !
'''
import warnings
warnings.filterwarnings("ignore")
load_dotenv(find_dotenv(), verbose=True)
verify=False
STEAM_WEB_API_KEY = os.environ.get("STEAM_WEB_API_KEY")
STEAM_COOKIE = os.environ.get("STEAM_COOKIE")
CACHE = requests_cache.CachedSession(cache_name='steam_cache', expire_after=900, verify=False)
LONGTIME_CACHE = requests_cache.CachedSession(cache_name='longtime_cache', expire_after=3600)

userinfo = Blueprint('userinfo', __name__)

LINE_CHAR_COUNT = 12 * 5.4
max_length = 22
headers = {
    'Cookie': f'{STEAM_COOKIE}',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.62',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6'
}

def get_user_info(steamid):
    def fetch_url(url, use_cache=True):
        response = None
        if use_cache:
            response = CACHE.get(url, verify=False, headers=headers, timeout=10)

        if response is None:
            # 如果缓存中没有结果，或者不使用缓存，发送HTTP请求
            response = requests.get(url, verify=False, headers=headers, timeout=10)

            if use_cache:
                # 如果需要缓存，将响应数据缓存起来
                CACHE.set(url, response)

        # 根据需要解析响应
        if "application/json" in response.headers.get("content-type", ""):
            return response.json(), response.status_code
        elif "text/html" in response.headers.get("content-type", ""):
            return response.text, response.status_code
        elif "text/xml" in response.headers.get("content-type", ""):
            return response.text, response.status_code

        # 如果不属于以上任何一种类型，可以返回原始文本
        return response.text, response.status_code

    # 定义需要缓存的URL和不需要缓存的URL
    urls_to_cache = [
        f"https://api.steampowered.com/ISteamUser/GetPlayerBans/v1?steamids={steamid}&key={STEAM_WEB_API_KEY}",
        f"https://api.steampowered.com/ISteamUser/GetUserGroupList/v1/?steamid={steamid}&key={STEAM_WEB_API_KEY}",
        f"https://api.steampowered.com/ISteamUser/GetFriendList/v1?steamid={steamid}&key={STEAM_WEB_API_KEY}",
        f"https://steamcommunity.com/inventory/{steamid}/753/6?l=english&count=1"
        # 添加其他需要缓存的URL
    ]

    urls_without_cache = [
        f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2?steamids={steamid}&key={STEAM_WEB_API_KEY}",
        f"https://api.steampowered.com/IPlayerService/GetSteamLevel/v1?steamid={steamid}&key={STEAM_WEB_API_KEY}",
        f"https://steamcommunity.com/profiles/{steamid}/",
        f"https://steamcommunity.com/profiles/{steamid}/?xml=1",
        f"https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1?steamid={steamid}&key={STEAM_WEB_API_KEY}",
        f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1?steamid={steamid}&key={STEAM_WEB_API_KEY}&include_appinfo=true&include_played_free_games=true"
        # 添加其他不需要缓存的URL
    ]

    # 创建一个线程池，最大线程数可以根据需要进行调整
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        # 并行发起HTTP请求，使用缓存的URL
        responses_with_cache = list(executor.map(lambda url: fetch_url(url, use_cache=True), urls_to_cache))
        # 并行发起HTTP请求，不使用缓存的URL
        responses_without_cache = list(executor.map(lambda url: fetch_url(url, use_cache=False), urls_without_cache))

    print(f"[{steamid}] 开始发起 API 请求")
    data_player_info = responses_without_cache[0][0]
    if len(data_player_info["response"]["players"]) == 0:
        return None
    is_visibility = data_player_info["response"]["players"][0]['communityvisibilitystate']
    print(f"是否私密: {is_visibility}")
    data_ban_info = responses_with_cache[0][0]
    data_level = responses_without_cache[1][0]
    data_games_count = responses_without_cache[5][0]
    data_groups = responses_with_cache[1][0]
    if responses_with_cache[2][1] != 200:
        dosent_know_friends = 1
        print("好友列表无法获取:", dosent_know_friends)
    else:
        data_friends_count = responses_with_cache[2][0]
        dosent_know_friends = 0
    if responses_with_cache[1][1] != 200:
        dosent_know_groups = 1
    else:
        dosent_know_groups = 0
    data_recentlyplayed = responses_without_cache[4][0]
    data_inv = responses_with_cache[3][0]
    data_badge = responses_without_cache[2][0]
    data_summary = responses_without_cache[3][0]

    avatar_url = data_player_info["response"]["players"][0]['avatarfull']
    name = data_player_info["response"]["players"][0]['personaname']
    print(f"[{steamid}] 已获取到名称: {name}")
    status = data_player_info["response"]["players"][0]['personastate']
    ban_vac = data_ban_info["players"][0]['VACBanned']
    ban_vac_last = data_ban_info["players"][0]['DaysSinceLastBan']
    ban_cmty = data_ban_info["players"][0]['CommunityBanned']
    ban_game = data_ban_info["players"][0]['NumberOfGameBans']
    url = data_player_info["response"]["players"][0]['profileurl']
    vac_ban_count = data_ban_info["players"][0]['NumberOfVACBans']

    soup = BeautifulSoup(data_summary, 'xml')

    summary_element = soup.find("summary")
    location_element = soup.find("location")
    if summary_element is not None:
        # 去除HTML标签并替换<br>为换行符
        summary = remove_html_tags(summary_element.get_text()).replace("<br>", "\n").strip()
    else:
        summary = '这个人很懒，还没有设置签名。'
    if location_element is not None:
        location = location_element.get_text()
    else:
        location = 'unknown'
    try:
        groups = soup.find('groups')
        group = groups.find('group', isPrimary="1")
        show_group_name_element = soup.find('groupName')
        show_group_headline_element = group.find('headline')
        show_group_avatar_element = group.find('avatarMedium')
        show_group_members_element = group.find('memberCount')
        show_group_online_element = group.find('membersOnline')
        show_group_name = show_group_name_element.get_text() if show_group_name_element is not None else 'unknown'
        show_group_headline = show_group_headline_element.get_text() if show_group_headline_element is not None else 'unknown'
        show_group_avatar = show_group_avatar_element.get_text() if show_group_avatar_element is not None else 'unknown'
        show_group_members = show_group_members_element.get_text() if show_group_members_element is not None else 'unknown'
        show_group_online = show_group_online_element.get_text() if show_group_online_element is not None else 'unknown'
    except Exception as e:
        print(f"[{steamid}] 获取群组信息出错: {e}")
        show_group_name = 'unknown'
        show_group_headline = 'unknown'
        show_group_avatar = 'unknown'
        show_group_members = 'unknown'
        show_group_online = 'unknown'
    '''
        show_group_name = show_group_element.find('groupname').get_text(strip=True)
        show_group_headline = show_group_element.find('headline').get_text(strip=True)
        avatar_medium_element = show_group_element.find('avatarMedium')
        show_group_avatar = avatar_medium_element.find('avatarMedium').get_text(strip=True)
        '''
    state_message_element = soup.find("statemessage")
    if state_message_element is not None:
        state_message = state_message_element.get_text()
        if "In non-Steam game" in state_message:
            not_steam_game = True
        else:
            not_steam_game = False
    else:
        not_steam_game = False

    if data_inv != None:
        inv_count = data_inv["total_inventory_count"]
    else:
        inv_count = 'unknown'

    if 'lastlogoff' in data_player_info["response"]["players"][0]:
        logoff = data_player_info["response"]["players"][0]['lastlogoff']
    else:
        logoff = 'unknown'

    playtime_win = 0
    playtime_mac = 0
    playtime_linux = 0

    if is_visibility != 1 and is_visibility != 2:
        timecreated = data_player_info["response"]["players"][0]['timecreated']
        if 'game_count' in data_games_count["response"]:
            game_count = data_games_count["response"]['game_count']
            if "games" in data_games_count["response"]:
                games = data_games_count["response"]["games"]
                for game in games:
                    if "playtime_windows_forever" in game:
                        playtime_win += game["playtime_windows_forever"]
                        playtime_mac += game["playtime_mac_forever"]
                        playtime_linux += game["playtime_linux_forever"]
                    else:
                        playtime_win = 0
                        playtime_mac = 0
                        playtime_linux = 0
        else:
            game_count = 'NaN'
            playtime_win = 0
            playtime_mac = 0
            playtime_linux = 0

    else:
        country = 'Unknown'
        timecreated = 'Unknown'
        level = '???'
        game_count = '114514'
        realname = 'unknown'

    if 'player_level' in data_level["response"]:
        level = data_level["response"]['player_level']
    else:
        level = "NaN"

    if 'gameextrainfo' in data_player_info["response"]["players"][0]:
        playing = data_player_info["response"]["players"][0]['gameextrainfo']
        playing_gameid = data_player_info["response"]["players"][0]['gameid']
    else:
        playing = 'unknown'
        playing_gameid = '114514'

    if 'realname' in data_player_info["response"]["players"][0]:
        realname = data_player_info["response"]["players"][0]['realname']
    else:
        realname = '-NoRealNameInPYTH'

    if 'loccountrycode' in data_player_info["response"]["players"][0]:
        country = data_player_info["response"]["players"][0]['loccountrycode']
    else:
        country = 'unknown'

    playtime_win = playtime_win / 60
    playtime_mac = playtime_mac / 60
    playtime_linux = playtime_linux / 60

    if is_visibility != 1 and is_visibility != 2:
        if dosent_know_friends == 1:
            friends_count = '获取失败'
        else:
            unique_steamids = set()
            for friend in data_friends_count["friendslist"]["friends"]:
                unique_steamids.add(friend["steamid"])
            friends_count = len(unique_steamids)

        if dosent_know_groups == 1:
            num_unique_gids = 0
        else:
            unique_gids = set()
            for group in data_groups["response"]["groups"]:
                unique_gids.add(group["gid"])
            num_unique_gids = len(unique_gids)

        if game_count != 'NaN':
            games_all = data_games_count["response"]["games"]

            if "total_count" in data_recentlyplayed["response"]:
                if data_recentlyplayed["response"]["total_count"] != 0:
                    games = data_recentlyplayed["response"]["games"]
                    total_playtime_2weeks = sum(game["playtime_2weeks"] for game in games)
                    total_hours = total_playtime_2weeks / 60
                    max_playtime_forever = max(game["playtime_2weeks"] for game in games)
                    game_with_max_playtime = next(game for game in games if game["playtime_2weeks"] == max_playtime_forever)
                    max_playtime_name = game_with_max_playtime["name"]
                    max_playtime_min = game_with_max_playtime["playtime_2weeks"]
                    max_playtime_min_forever = game_with_max_playtime["playtime_forever"]
                    max_playtime_hours = max_playtime_min / 60
                    max_playtime_hours_forever = max_playtime_min_forever / 60
                else:
                    total_hours = '0'
                    max_playtime_hours = '0'
                    max_playtime_name = '最近没玩过任何游戏'
                    max_playtime_hours_forever = 0

                total_playtime_all = sum(game["playtime_forever"] for game in games_all)
                total_hours_all = total_playtime_all / 60

                max_playtime_all = max(game["playtime_forever"] for game in games_all)
                game_with_max_playtime_all = next(game for game in games_all if game["playtime_forever"] == max_playtime_all)
                max_playtime_name_all = game_with_max_playtime_all["name"]
                max_playtime_min_all = game_with_max_playtime_all["playtime_forever"]
                max_playtime_hours_all = max_playtime_min_all / 60
            else:
                total_hours = 'NaN'
                total_hours_all = 'NaN'
                max_playtime_name = '未知'
                max_playtime_name_all = '未知'
                max_playtime_hours = 0
                max_playtime_hours_all = 0
                max_playtime_hours_forever = 0
        else:
            total_hours = 'NaN'
            total_hours_all = 'NaN'
            max_playtime_name = '未知'
            max_playtime_name_all = '未知'
            max_playtime_hours_all = 0
            max_playtime_hours = 0
            max_playtime_hours_forever = 0
    else:
        max_playtime_hours = 0
        max_playtime_hours_all = 0
        friends_count = '114514'
        total_hours = 'NaN'
        total_hours_all = 'NaN'
        max_playtime_name = 'unknown'
        max_playtime_name_all = 'unknown'
        num_unique_gids = '114514'
        max_playtime_hours_forever = 0

    soup = BeautifulSoup(data_badge, 'html.parser')
    try:
        background_element = soup.select_one('#responsive_page_template_content > div.no_header.profile_page.has_profile_background.full_width_background')
        if background_element:
            style = background_element.get('style')
            if style:
                img_url_match = re.search(r"url\(\s*'([^']+)'\s*\)", style)
                if img_url_match:
                    image_url = img_url_match.group(1)
                else:
                    image_url = 'unknown'
            else:
                image_url = 'unknown'
        else:
            image_url = 'unknown'
        if image_url == 'unknown':
            background_element = soup.select_one('#responsive_page_template_content > div.no_header.profile_page.has_profile_background')
            style = background_element.get('style')
            if style:
                img_url_match = re.search(r"url\(\s*'([^']+)'\s*\)", style)
                if img_url_match:
                    image_url = img_url_match.group(1)
                else:
                    image_url = 'unknown'
            else:
                image_url = 'unknown'
        if image_url == 'unknown':
            video_tag = soup.find('video')
            if image_url == None:
                image_url = 'unknown'
            else:
                image_url = video_tag.get('poster')
    except Exception as e:
        #raise
        print("获取个人资料背景时出现错误:",e)
        image_url = 'unknown'

# 解析 badge_icon_url
    try:
        badge_icon_img = soup.select_one('#responsive_page_template_content div.favorite_badge_icon img')
        if badge_icon_img:
            badge_icon_url = badge_icon_img['src']
        else:
            badge_icon_url = "unknown"

        # 解析 badge_url
        badge_name_element = soup.select_one('#responsive_page_template_content div.favorite_badge_description div.name.ellipsis')
        badge_name = badge_name_element.get_text() if badge_name_element else 'unknown'

        div_element = soup.find('div', {'class': 'profile_count_link ellipsis'})

        # 在找到的<div>元素内，再次使用find方法找到具有class="profile_count_link_total"属性的<span>标签，并提取其中的文本内容
        badge_count = div_element.find('span', {'class': 'profile_count_link_total'}).get_text(strip=True)

        print("badge_icon_url:", badge_icon_url)
        print("badge_name:", badge_name)
        print("badge_count:", badge_count)
    except Exception as e:
        print("获取徽章信息时出现错误:",e)
        badge_count = 0
        badge_name = 'unknown'
        badge_icon_img = 'unknown'

    try:
        if playing == 'unknown':
            recent_played_element = soup.select_one("#responsive_page_template_content > div > div.profile_content.has_profile_background > div > div.profile_leftcol > div.recent_games > div:nth-child(1) > div > div.game_info > div.game_name > a:nth-child(1)")
        else:
            recent_played_element = soup.select_one("#responsive_page_template_content > div > div.profile_content.has_profile_background > div > div.profile_leftcol > div.recent_games > div:nth-child(2) > div > div.game_info > div.game_name > a:nth-child(1)")

        print(recent_played_element)

        if recent_played_element:
            recent_played = recent_played_element.text
            if playing == 'unknown':
                game_info_details = recent_played_element = soup.select_one("#responsive_page_template_content > div > div.profile_content.has_profile_background > div > div.profile_leftcol > div.recent_games > div:nth-child(1) > div > div > div.game_info_details")
            else:
                game_info_details = recent_played_element = soup.select_one("#responsive_page_template_content > div > div.profile_content.has_profile_background > div > div.profile_leftcol > div.recent_games > div:nth-child(2) > div > div > div.game_info_details")
            print(game_info_details)
            if game_info_details:
                # 提取 "总时数" 和 "最后运行日期" 的文本内容
                details_text = game_info_details.get_text()
                # 使用正则表达式或其他方法从文本中提取这两个信息
                total_time_match = re.search(r'总时数 (\d+(?:,\d+)?(?:\.\d+)?) 小时', details_text)
                last_run_date_match = re.search(r'最后运行日期：(\d+ 月 \d+ 日)', details_text)
                print("total_time_match:",total_time_match)
                print("last_run_date_match",last_run_date_match)

                if total_time_match and last_run_date_match:
                    total_time = total_time_match.group(1)
                    last_run_date = last_run_date_match.group(1)
                    recent_played_info = f"总时数 {total_time} 小时 | 最后运行日期: {last_run_date}"
                    print(recent_played_info)
                else:
                    print("无法提取所需信息")
                    recent_played_info = f"未知"
            else:
                print("未找到目标元素")
                recent_played_info = f"未知"

        print("recent_played:", recent_played)
    except Exception as e:
        print("获取上次游玩的游戏时出现错误:",e)
        recent_played = 'unknown'
        recent_played_info = 'unknown'

    try:
        avatar_frame_url_element = soup.select_one("#responsive_page_template_content > div > div.profile_header_bg > div > div > div > div.playerAvatar.profile_header_size.online > div > div > img")
        if not avatar_frame_url_element:
            if playing == 'unknown':
                avatar_frame_url_element = soup.select_one("#responsive_page_template_content > div > div.profile_header_bg > div > div > div > div.playerAvatar.profile_header_size.offline > div > div > img")
            else:
                avatar_frame_url_element = soup.select_one("#responsive_page_template_content > div > div.profile_header_bg > div > div > div > div.playerAvatar.profile_header_size.in-game > div > div > img")
        print(avatar_frame_url_element)
        avatar_frame_url = avatar_frame_url_element['src']
    except Exception as e:
        print("获取头像框链接出错:",e)
        avatar_frame_url = None

    valve_employee_element = soup.find('div', class_='profile_header_valve_employee')

    if valve_employee_element == None:
        valve_employee = False
    else:
        valve_employee = True

    print("image_url:", image_url)

    return avatar_url, name, country, timecreated, level, game_count, playing, playing_gameid, realname, status, ban_vac, is_visibility, friends_count, ban_game, total_hours, max_playtime_name, num_unique_gids, max_playtime_name_all, total_hours_all, url, inv_count, logoff, vac_ban_count, summary, not_steam_game, ban_vac_last, location, badge_icon_url, badge_name, valve_employee, badge_count, max_playtime_hours, max_playtime_hours_all, max_playtime_hours_forever, recent_played, recent_played_info, avatar_frame_url, playtime_win, playtime_mac, playtime_linux, show_group_name, show_group_headline, show_group_avatar, show_group_members, show_group_online, image_url

def generate_game_list_image(avatar_url, name, country, timecreated, level, game_count, playing, playing_gameid, realname, status, ban_vac, is_visibility, friends_count, ban_game, total_hours, max_playtime_name, num_unique_gids, max_playtime_name_all, total_hours_all, url, steamid, inv_count, logoff, vac_ban_count, summary, not_steam_game, ban_vac_last, location, badge_icon_url, badge_name, valve_employee, badge_count, max_playtime_hours, max_playtime_hours_all, max_playtime_hours_forever, recent_played, recent_played_info, execution_time_api, avatar_frame_url, playtime_win, playtime_mac, playtime_linux, show_group_name, show_group_headline, show_group_avatar, show_group_members, show_group_online, image_url):
    print(f"[{steamid}] 开始进行图像生成")
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    font_path = f"{parent_directory}//font//STImgFonts-HEF.otf"
    font_bold_path = f"{parent_directory}//font//STImgFonts.otf"
    normal_font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed
    normal_bold_font = ImageFont.truetype(font_bold_path, 16)
    title_font = ImageFont.truetype(font_bold_path, 30)
    level_font = ImageFont.truetype(f"{parent_directory}//font//STImgFonts.otf", 38)
    country_font = ImageFont.truetype(f"{parent_directory}//font//STImgFonts.otf", 16)
    if image_url != 'unknown':
        blank_image = Image.new("RGBA", (600, 830), (233,236,239))
        background_response = LONGTIME_CACHE.get(image_url, verify=False)
        background_image = Image.open(BytesIO(background_response.content))
        img_width, img_height = background_image.size
        target_width = 600
        target_height = 830
        # 计算裁剪区域的坐标
        left = (img_width - target_width) // 2
        top = (img_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        cropped_img = background_image.crop((left, top, right, bottom))
        blurred_img = cropped_img.filter(ImageFilter.GaussianBlur(radius=4))
        enhancer = ImageEnhance.Brightness(blurred_img)  # cropped_img是之前裁剪的图像
        darkened_img = enhancer.enhance(0.7)  # 0.7是亮度的调整因子，可以根据需要调整（0.7表示降低30%的亮度）
        blank_image = darkened_img.copy()
        white_color = 248,249,250
        white_color_2 = 222,226,230
        white_color_3 = 206,212,218
    else:
        blank_image = Image.new("RGBA", (600, 830), (233,236,239))
        white_color = 52,58,64
        white_color_2 = 73,80,87
        white_color_3 = 134,142,150

    avatar_response = LONGTIME_CACHE.get(avatar_url, verify=False)
    avatar_image = Image.open(BytesIO(avatar_response.content))
    avatar_size = (100, 100)
    avatar_image = avatar_image.resize(avatar_size, Image.LANCZOS)
    blank_image.paste(avatar_image, (30, 30))

    try:
        if avatar_frame_url:
            avatar_frame_response = LONGTIME_CACHE.get(avatar_frame_url, verify=False)
            avatar_frame_image = Image.open(BytesIO(avatar_frame_response.content))
            avatar_frame_converted = avatar_frame_image.convert("RGBA")
            avatar_frame_resized = avatar_frame_converted.resize((125,125), Image.LANCZOS)
            blank_image.paste(avatar_frame_resized, (18, 18), avatar_frame_resized)
    except Exception as e:
        print("无法获取此用户的头像框。原因:", e)

    try:
        if badge_icon_url != 'unknown':
            badge_icon_response = LONGTIME_CACHE.get(badge_icon_url, verify=False)
            badge_image = Image.open(BytesIO(badge_icon_response.content))
            badge_image_converted = badge_image.convert("RGBA")
            badge_image_resized = badge_image_converted.resize((31,31), Image.LANCZOS)
            blank_image.paste(badge_image_resized, (400, 195), badge_image_resized)
    except Exception as e:
        print("无法获取此用户的徽章图标。原因:", e)

    if realname == '-NoRealNameInPYTH':
        base_info_y = 10
    else:
        base_info_y = 0

    if realname == '-NoRealNameInPYTH' and location == 'unknown':
        base_info_y = 42

    draw = ImageDraw.Draw(blank_image)
    draw.text((150, 52 + base_info_y), f"{name}", font=title_font, fill=white_color)

    if realname != '-NoRealNameInPYTH':
        draw.text((150, 90), f"{realname}", font=normal_font, fill=white_color)
    if location != 'unknown':
        draw.text((150, 110), f"{location}", font=country_font, fill=white_color)

    draw.line([(30,150), (590,150)], fill=(173,181,189), width=2)

    if playing != 'unknown':
        draw.text((150, 31 + base_info_y), f"\uf144 {playing} ({playing_gameid})", font=normal_font, fill=(55,178,77))
    else:
        if status == 1:
            if not_steam_game:
                draw.text((150, 31 + base_info_y), f"非 Steam 游戏中", font=normal_font, fill=(55,178,77))
            else:
                draw.text((150, 31 + base_info_y), f"在线", font=normal_font, fill=(51,154,240))
        elif status == 0:
            draw.text((150, 31 + base_info_y), f"离线", font=normal_font, fill=white_color_3)
        elif status == 3:
            draw.text((150, 31 + base_info_y), f"\uf186 暂时离开", font=normal_font, fill=(102,217,232))
        elif status == 4:
            draw.text((150, 31 + base_info_y), f"\uf236 离开", font=normal_font, fill=(102,217,232))

    print("total_hours:",total_hours)

    if ban_vac:
        draw.line([(0,820), (600, 820)], fill=(250,82,82), width=48)
        draw.text((30,805), f"{vac_ban_count} 个记录在案的 VAC 封禁 | 上次封禁于 {ban_vac_last} 天前", font=normal_bold_font, fill=(255,255,255))
    elif ban_game > 0:
        draw.line([(0,820), (600, 820)], fill=(255,107,107), width=48)
        draw.text((30,805), f"{ban_game} 个记录在案的游戏封禁", font=normal_bold_font, fill=(255,255,255))
    elif valve_employee:
        draw.line([(0,820), (600, 820)], fill=(26,159,255), width=48)
        draw.text((30,805), f"\uf560 此用户是 Valve 员工", font=normal_bold_font, fill=(255,255,255))
    elif total_hours != 'NaN':
        if int(total_hours) > 400:
            draw.line([(0,820), (600, 820)], fill=(250,176,5), width=48)
            draw.text((30,805), f"! 此项数据异常，该玩家可能使用了第三方软件刷时长，或是已成神", font=normal_font, fill=(255,255,255))
        else:
            print("1")
    else:
        print(f"[{steamid}] 一眼丁真，鉴定为: 绿色玩家")

    if is_visibility != 1 and is_visibility != 2:
        if show_group_avatar != 'unknown':
            group_avatar_response = LONGTIME_CACHE.get(show_group_avatar, verify=False)
            group_avatar_image = Image.open(BytesIO(group_avatar_response.content))
            blank_image.paste(group_avatar_image, (30, 530))
        truncated_mpn = truncate_text(max_playtime_name, max_length)
        truncated_mpna = truncate_text(max_playtime_name_all, max_length)
        if level != "NaN":
            if level > 500:
                level_color = 245,159,0
            elif level > 200:
                level_color = 255,212,59
            elif level > 100:
                level_color = 250,82,82
            elif level > 50:
                level_color = 230,73,128
            elif level > 30:
                level_color = 34,139,230
            elif level > 20:
                level_color = 32,201,151
            elif level > 10:
                level_color = 130,201,30
            else:
                level_color = 73,80,87
        else:
            level_color = 73,80,87
        draw.text((30,170), f"\uf1b6 Steam 等级", font=normal_font, fill=white_color_3)
        draw.text((30,190), f"Lv. {level}", font=title_font, fill=level_color)

        draw.text((30,230), f"\uf11b 拥有游戏 (含免费)", font=normal_font, fill=white_color_3)
        draw.text((30,250), f"{game_count}", font=title_font,fill=white_color_2)

        draw.text((30,290), f"\uf007 好友数量", font=normal_font, fill=white_color_3)
        draw.text((30,310), f"{friends_count}", font=title_font,fill=white_color_2)

        draw.text((30,350), f"\uf500 加入了", font=normal_font, fill=white_color_3)
        draw.text((30,370), f"{num_unique_gids} 个组", font=title_font,fill=white_color_2)

        draw.text((200,170), f"近两周游戏时长", font=normal_font, fill=white_color_3)

        if total_hours == '0' or total_hours == 'NaN':
            draw.text((200,190), f"0 h", font=title_font,fill=white_color_2)
        else:
            draw.text((200,190), f"{total_hours:.1f} h", font=title_font,fill=white_color_2)
            if total_hours > 400:
                draw.text((320,170), f"!", font=normal_font, fill=(250,176,5))
        max_playtime_hours = float(max_playtime_hours)
        max_playtime_hours_forever = float(max_playtime_hours_forever)
        draw.text((200,230), f"近两周最常玩 ({max_playtime_hours:.1f}h / {max_playtime_hours_forever:.1f}h)", font=normal_font, fill=white_color_3)
        draw.text((200,250), f"{truncated_mpn}", font=title_font,fill=white_color_2)

        draw.text((200,290), f"总游戏时长", font=normal_font, fill=white_color_3)

        if total_hours_all != 'NaN':
            draw.text((200,310), f"{total_hours_all:.1f} h", font=title_font,fill=white_color_2)
        else:
            draw.text((200,310), f"未知", font=title_font,fill=white_color_2)

        draw.text((200,350), f"最常玩的游戏 ({max_playtime_hours_all:.1f}h)", font=normal_font, fill=white_color_3)
        draw.text((200,370), f"{truncated_mpna}", font=title_font,fill=white_color_2)

        if inv_count != 'unknown':
            draw.text((400,290), f"库存物品", font=normal_font, fill=white_color_3)
            draw.text((400,310), f"{inv_count} 个", font=title_font,fill=white_color_2)

        if badge_name != 'unknown':
            truncated_badge_name = truncate_text(badge_name, max_length=20)
            draw.text((400,170), f"({badge_count}) {truncated_badge_name}", font=normal_font, fill=white_color_3)

        draw.text((30,410), f"\uf04b 上次游玩了 ({recent_played_info})", font=normal_font, fill=white_color_3)
        if recent_played != 'unknown':
            draw.text((30,430), f"{recent_played}", font=title_font,fill=white_color_2)
        else:
            draw.text((30,430), f"\u003f", font=title_font,fill=white_color_2)

        join_steam_datetime = datetime.datetime.fromtimestamp(timecreated)
        jointime = join_steam_datetime.strftime('%Y-%m-%d %H:%M:%S')

        draw.text((30,470), f"\uf2f6 注册 Steam 账号于", font=normal_font, fill=white_color_3)
        draw.text((30,490), f"{jointime}", font=title_font,fill=white_color_2)

        if show_group_name != 'unknown':
            draw.text((100,530), f"{show_group_name}", font=title_font,fill=white_color_2)
            draw.text((100,562), f"{show_group_headline}", font=normal_bold_font,fill=white_color_2)
            draw.text((100,580), f"展示的组 | {show_group_members} 名成员 | {show_group_online} 名成员在线", font=normal_bold_font, fill=white_color_3)

        truncated_summary = truncate_text(summary, max_length=190)
        split_lines = line_break(truncated_summary, LINE_CHAR_COUNT)  # 使用自动换行函数处理文本
        split_lines = split_lines.split('\n')
        print(f"[{steamid}] 签名: {summary}")
        print(f"[{steamid}] 已省略签名: {truncated_summary}")
        print(f"[{steamid}] 已换行签名: {split_lines}")
        y_position = 635
        for line in split_lines:
            draw.text(xy=(30, y_position), text=line,fill=white_color_2, font=normal_font)
            y_position += normal_font.getbbox(line)[1] + 18  # 根据字体高度和间距调整下一行的位置

        draw.text((30,610), f"\uf129 个人简介", font=normal_font, fill=white_color_3)

    else:
        draw.text((30,170), f"此个人资料是私密的。", font=title_font,fill=white_color_2)
        draw.text((30,210), f"如果这个账号是你的，你可以在 Steam 客户端的\n个人资料 > 编辑个人资料 > 隐私设置 来取消私密。\n由于该玩家的个人资料已被设置为私密，因此我们无法提供更多信息。", font=normal_font, fill=white_color_3)

    formatted_time = datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S')
    draw.text((30,720), f"Steam ID: {steamid}\n{url}\n一些数据存在 15 分钟的缓存，可能会出现数据更新不及时的情况\n由 StStats 生成 | 用时 {execution_time_api:.1f}s | 生成时间 {formatted_time}", font=normal_font, fill=white_color_3)

    return blank_image

def gen_error_image(steamid):
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    font_path = f"{parent_directory}//font//STImgFonts-HEF.otf"
    font_bold_path = f"{parent_directory}//font//STImgFonts.otf"
    normal_font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed
    normal_bold_font = ImageFont.truetype(font_bold_path, 16)
    title_font = ImageFont.truetype(font_bold_path, 30)
    level_font = ImageFont.truetype(f"{parent_directory}//font//STImgFonts.otf", 38)
    country_font = ImageFont.truetype(f"{parent_directory}//font//STImgFonts.otf", 16)
    blank_image = Image.new("RGBA", (600, 620), (255,255,255))

    draw = ImageDraw.Draw(blank_image)
    draw.text((250, 260), f"查无此人", font=title_font, fill=(52,58,64))
    draw.text((30,540), f"Steam ID: {steamid} (查询出错!)", font=normal_font, fill=white_color_3)
    draw.text((30,560), f"由 StStats 生成 | 数据来源于 Steam Web API", font=normal_font, fill=white_color_3)

    return blank_image

def gen_exception_image(e):
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    font_path = f"{parent_directory}//font//hmsc.ttf"
    font_bold_path = f"{parent_directory}//font//STImgFonts.otf"
    normal_font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed
    title_font = ImageFont.truetype(font_bold_path, 30)
    level_font = ImageFont.truetype(f"{parent_directory}//font//STImgFonts-HEF.otf", 38)
    country_font = ImageFont.truetype(f"{parent_directory}//font//STImgFonts-HEF.otf", 16)
    image = Image.new("RGBA", (840, 450), (255,255,255))

    draw = ImageDraw.Draw(image)
    draw.text((8, 10), f"发生内部错误", font=title_font, fill=(52,58,64))
    draw.line([(8,55), (832,55)], fill=(233,236,239), width=2)
    draw.text((8, 60), f"原因: {e}", font=country_font, fill=(52,58,64))
    now_time = time.asctime(time.localtime())
    py_ver = sys.version
    flask_ver = flask.__version__
    draw.text((8, 100), f"你可以:\n● 将错误信息反馈给管理员。\n● 如果是网络错误，请稍后再试。\n● 如果服务器处于大陆，请检查是否已开启加速器或本地反代。\n● 请检查是否已正确配置 Steam Web API Key。\n\n由于程序出现故障，因此本次请求失败，无法返回图片。\n\n\n\n信息:\nTime: {now_time}\nPython Version: {py_ver}\nFlask Version: {flask_ver}", font=normal_font, fill=(52,58,64))

    return image

@userinfo.route('/GetUserInfo', methods=['GET'])
def get_app_list():
    steamid = request.args.get('steamid')
    if not steamid:
        return jsonify({"error": "Missing 'steamid' parameter"}), 400
    print(f"开始 SteamID {steamid} 的图片生成任务")

    try:
        start_time_api = time.time()
        user_info = get_user_info(steamid)  # Retrieve both steam_name and game_list
        if user_info == None:
            image = gen_error_image(steamid)
            end_time_api = time.time()
        else:
            avatar_url, name, country, timecreated, level, game_count, playing, playing_gameid, realname, status, ban_vac, is_visibility, friends_count, ban_game, total_hours, max_playtime_name, num_unique_gids, max_playtime_name_all, total_hours_all, url, inv_count, logoff, vac_ban_count, summary, not_steam_game, ban_vac_last, location, badge_icon_url, badge_name, valve_employee, badge_count, max_playtime_hours, max_playtime_hours_all, max_playtime_hours_forever, recent_played, recent_played_info, avatar_frame_url, playtime_win, playtime_mac, playtime_linux, show_group_name, show_group_headline, show_group_avatar, show_group_members, show_group_online, image_url = user_info
            end_time_api = time.time()
            execution_time_api = end_time_api - start_time_api
            image = generate_game_list_image(avatar_url, name, country, timecreated, level, game_count, playing, playing_gameid, realname, status, ban_vac, is_visibility, friends_count, ban_game, total_hours, max_playtime_name, num_unique_gids, max_playtime_name_all, total_hours_all, url, steamid, inv_count, logoff, vac_ban_count, summary, not_steam_game, ban_vac_last, location, badge_icon_url, badge_name, valve_employee, badge_count, max_playtime_hours, max_playtime_hours_all, max_playtime_hours_forever, recent_played, recent_played_info,execution_time_api, avatar_frame_url, playtime_win, playtime_mac, playtime_linux, show_group_name, show_group_headline, show_group_avatar, show_group_members, show_group_online, image_url)  # Pass both arguments
    except Exception as e:
        print("error: ", e)
        #raise
        image = gen_exception_image(e)

    image_io = io.BytesIO()
    image.save(image_io, format='PNG')
    image_io.seek(0)
    print(f"[{steamid}] 图片已返回")
    return send_file(image_io, mimetype='image/png')

def truncate_text(text, max_length):
    if len(text) > max_length:
        truncated_text = text[:max_length-3] + "..."
        return truncated_text
    else:
        return text

def remove_html_tags(text):
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text()

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
    userinfo.run(debug=False)
