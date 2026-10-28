# Mapshot 运行与部署

## 本机启动

需要 Python 3.9+ 和支持 WebGL / DecompressionStream 的现代浏览器。

在项目目录运行：

```sh
python3 server.py
```

打开 `http://127.0.0.1:8097`。macOS 也可运行 `sh start.sh` 或双击 `start.command`。停止服务使用 Ctrl+C。不要双击 HTML 用 file:// 打开。

默认端口被占用时：`python3 server.py --port 8107`。服务会明确报端口占用，而不会自动连接另一个目录的旧页面。

## 复制到树莓派

在开发机项目根目录生成运行包：

```sh
python3 scripts/package_trial.py
```

把 `dist/mapshot-trial.zip` 拷贝到树莓派，解压后进入其中的 `mapshot` 目录：

```sh
python3 server.py --host 0.0.0.0 --port 8097
```

同一局域网的朋友可打开 `http://树莓派局域网IP:8097`。`0.0.0.0` 是监听地址，不能作为给朋友的网址。压缩包带有文件大小和 SHA-256 清单 `package-manifest.json`。

运行包不含 `.venv`、`data/raw`、开发测试、历史导出图和大源数据。不要把开发目录整体作为公开静态目录。旧 `.venv` 迁移后可能有绝对路径失效，不要复制它到 ARM 树莓派；这个服务不需要它。

## 前端与后端

- `/`：地图编辑页面，预览与出图在浏览器执行。
- `/api/health`：JSON 进程状态，用于检查服务是否启动；它不是完整数据校验。
- `/api/dataset`：当前 OSM 数据版本、范围、图层数量和资源体积。
- 服务端没有作品数据库、管理员网页、用户账户、上传接口或云端出图。
- 配色只在当前网址对应的浏览器存储中保存；换端口/域名/设备前可下载 JSON，再在新网址导入。

## 外网访问与长期运行

此版本是受控朋友试用服务。真正公网开放前需要确定域名和公网/隧道入口，并在前面配置 TLS 反向代理与适合实际流量的连接限制；Python 标准库服务不作为生产级公网服务的性能保证。

可以用 Caddy 在公网入口做反向代理。以下仅为配置示例，需要替换域名，并让域名实际指向可达入口：

```caddyfile
map.example.com {
    reverse_proxy 127.0.0.1:8097
}
```

`map.example.com` 是占位符。本项目没有申请域名、安装 Caddy 或创建隧道，也没有提供公网链接。反向代理时后端通常继续只监听 `127.0.0.1`；隧道也可指向这个本机地址。

需要开机运行时可由 systemd 管理。以下示例须按实际账户与安装位置修改，不能直接假定用户名为 pi：

```ini
[Unit]
Description=Mapshot trial server
After=network.target

[Service]
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/mapshot
ExecStart=/usr/bin/python3 /home/YOUR_USER/mapshot/server.py --host 127.0.0.1 --port 8097
Restart=on-failure
RestartSec=3
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

## 测试与排查

```sh
python3 -m unittest discover -s tests -v
node --check app.js
```

可选浏览器回归：安装开发用 Playwright，保持服务运行，执行 `node scripts/check_browser.mjs`；用 `MAPSHOT_URL` 指定其他地址（保留末尾 `/`），`PLAYWRIGHT_MODULE` 指定已有 Playwright 模块。脚本默认使用系统 Chrome；它不属于运行包依赖。

首次页面需下载约 35.3 MB 几何数据并在客户端处理。它不保证弱网秒开或所有手机都能导出 8K；手机默认 1920×1200。出现内存或画布限制时选择较小尺寸，保留配色后重试。

错误提示出现“地图数据读取失败”时，先访问 `/api/health`，再检查运行包是否完整、网络是否可达。若某文件被代理解压，正确保留 `Content-Encoding` 头；不要把未解压的 `.gz` 当普通 JSON 返回。

公开展示生成图片时，在相邻说明中保留 OpenStreetMap 署名与版权链接。地图 PNG 本身按用户需求不加文字，来源另存于 PNG 元数据。
