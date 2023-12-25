import requests
from flask import Flask, request, Response, send_from_directory, Blueprint, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import io
import os
import base64
from io import BytesIO
import minestat

mcserver = Blueprint('MCServer', __name__)

def generate_image(address):
    # Extract host and port from the address, defaulting to 25565 if port is not specified
    parts = address.split(':')
    server_host = parts[0]
    server_port = int(parts[1]) if len(parts) > 1 else 25565

    image = Image.new("RGB", (460, 480), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    font_path = f"{parent_directory}//font//hmsc.ttf"  # Replace with the actual path to your font file
    print(font_path)
    normal_font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed
    title_font = ImageFont.truetype(font_path, 30)

    draw.text((8,10), f"Minecraft 服务器 {server_host}:{server_port} 的详情", font=normal_font, fill=(52,58,64))
    draw.line([(8,35), (472,35)], fill=(52,58,64), width=2)

    print(server_port)

    ms = minestat.MineStat(server_host, server_port, resolve_srv=True)

    if ms.online:
        if ms.favicon_b64 != None:
            head, context = ms.favicon_b64.split(",")  # 将base64_str以“,”分割为两部分
            img_data = base64.b64decode(context)    # 解码时只要内容部分
            favicon = Image.open(BytesIO(img_data))
            image.paste(favicon, (8, 50))
        else:
            draw.text((8,50), f"没有图标", font=normal_font, fill=(52,58,64))
        draw.text((8,120), f"版本: {ms.version}", font=normal_font, fill=(52,58,64))
        draw.text((8,140), f"延迟: {ms.latency} 毫秒", font=normal_font, fill=(52,58,64))
        draw.text((8,160), f"在线玩家: {ms.current_players}/{ms.max_players}", font=normal_font, fill=(52,58,64))
        draw.text((8,180), f"MOTD:", font=normal_font, fill=(52,58,64))
        draw.text((8,200), f"{ms.stripped_motd}", font=normal_font, fill=(52,58,64))
        print("在线玩家列表:",ms.player_list)
        if ms.player_list != None:
            draw.text((8,250), f"在线玩家列表:", font=normal_font, fill=(52,58,64))
            draw.text((8,270), f"{ms.player_list}", font=normal_font, fill=(52,58,64))
        if ms.plugins != None:
            draw.text((8,350), f"插件列表:", font=normal_font, fill=(52,58,64))
            draw.text((8,370), f"{ms.plugins}", font=normal_font, fill=(52,58,64))
    else:
        draw.text((8,60), "服务器离线!", font=normal_font, fill=(52,58,64))

    return image

@mcserver.route('/GetMCServerStatus', methods=['GET'])
def get_app_list():
    address = request.args.get('address')

    if not address:
        return jsonify({"error": "Missing 'address' parameter"}), 400

    image = generate_image(address)  # Pass the address as a single argument

    image_io = io.BytesIO()
    image.save(image_io, format='PNG')
    image_io.seek(0)

    return send_file(image_io, mimetype='image/png')

if __name__ == '__main__':
    mcserver.run(debug=True)
