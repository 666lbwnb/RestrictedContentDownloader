# RestrictedContentDownloader
Restricted Content Download Robot

这个脚本直接用了[vasusen-code](https://github.com/vasusen-code)这个大佬写的[SaveRestrictedContentBot/main/plugins/progress.py ](https://github.com/vasusen-code/SaveRestrictedContentBot/blob/master/main/plugins/progress.py)文件

### 优点

- 可以下载一整个消息组的文件了
- 可以下载一个消息区间了 `https://t.me/c/123456789/1 999999` 直接发给机器人就行了
- 把机器人拉到频道里 直接在频道里发命令 机器人就直接在频道里提取信息了...
- 不用获取session string
- 能zha干闲置VPS的流量(大概)

### 缺点

- 不能下载单个文件 如果文件在一个消息组里 那么会把整个消息组上传上来
- 只下载一个消息组或者单文件 也要带上后面的参数 比如 `https://t.me/c/123456789/1 1`
- 没有做一些因为网络原因引发的错误的处理,只做了洪水的处理

### 待改进

- 对于下载过的文件,file_id没有存进数据库里,公开的file id可以直接发送,节省VPS流量

### 使用方法 

- 你需要把config.py里面的参数改成你自己的
- 安装依赖库 `pip3 install pyrogram tgcrypto`
- 最后 python main.py 就可以在机器人里发指令即可
- 可以直接在Windows里运行,安卓手机安装一个[Termux](https://www.bilibili.com/read/cv17211082)也可以运行...

### 请我喝奶茶

如果这个脚本帮到了你,可以请我喝杯奶茶~~

<img src="https://s2.loli.net/2023/06/26/KHrT7CZvNdcobmg.jpg" width="400px" alt="">

