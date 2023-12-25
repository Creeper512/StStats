这是一个使用 Python + Flash 编写的 API，可用于查询 Steam 用户、游戏的一些信息并以图片的形式返回。

`.env`中的配置项。
```
STEAM_WEB_API_KEY= # 你的 Steam Web API 密钥，可在 https://steamcommunity.com/dev/apikey 获得
STEAM_COOKIE= # 你的 Steam 社区的 Cookie，如果不填写可能会导致在获取个人资料时，无法获取库存物品的数量
```

## 使用教程

所有的 API 接口都位于`/api`下，程序默认在`127.0.0.1:8090`下运行。

* `/api/GetAppInfo?appid=<AppID>` 通过小黑盒的 API 接口和 Steam Web API 以及 Augmented Steam 的 API 来查询某个游戏的详情。
* `/api/GetAppList?query=<keyword>` 通过 Steam Web API 来在 Steam 上搜索游戏。
* `/api/GetUserInfo?steamid=<steamid>` 通过 Steam Web API 来查询某个 Steam 用户的数据。
* `/api/GetGameList?steamid=<steamid>` 通过 Steam Web API 来查询某个 Steam 用户拥有的所有游戏。
* `/api/getSteamFriends?steamid=<steamid>` 通过 Steam Web API 来查询某个 Steam 用户的好友列表，可显示其在线状态以及成为好友时间。为了加快图片生成速度目前仅返回最多50 个好友。**这个 API 正打算重写**
* `/api/GetMCServerStatus?address=<address>` 查询某个 Minecraft 服务器的信息，目前对 SRV 解析支持不完善，貌似只支持 Java 版服务器，基岩版没试过。