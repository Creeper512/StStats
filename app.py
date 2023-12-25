from flask import Flask
from api.FriList import frilist
from api.AppInfo import appinfo
from api.AppList import applist
from api.GameList import gamelist
from api.UserInfo import userinfo
from api.MCServer import mcserver
from api.UserInfoFromURL import userinfofromurl

app = Flask(__name__)

app.register_blueprint(frilist, url_prefix='/api')
app.register_blueprint(appinfo, url_prefix='/api')
app.register_blueprint(applist, url_prefix='/api')
app.register_blueprint(gamelist, url_prefix='/api')
app.register_blueprint(userinfo, url_prefix='/api')
app.register_blueprint(mcserver, url_prefix='/api')
app.register_blueprint(userinfofromurl, url_prefix='/api')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8090)