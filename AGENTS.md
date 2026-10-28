# Mapshot 开发约定

本文件给在此项目工作的编程代理使用。产品范围见 `PRODUCT.md`，第一阶段计划见 `docs/PROJECT.md`，运行部署见 `docs/DEPLOYMENT.md`。

- 当前里程碑：上海单城试用，打开网页、调色、浏览器导出；运行时只要求 Python 3.9+，保持无第三方后端依赖。
- 保留真实 OSM 几何、孔洞、来源和数据日期；未记录的建筑或道路不得补造。航空设施的显示默认宽度不能描述为测量值。
- PNG 保持 16:10，只包含地图像素，不含标题、地点标记、边框或留白；桌面默认 3840×2400，窄屏默认 1920×1200。
- 保留 v1/v2/v3 配色文件兼容及浏览器本地保存。不自动把用户配色上传服务器。
- 沿用现有 MapLibre、静态 HTML/CSS/JavaScript。框架迁移、PMTiles、账号、SQLite 和服务端导出属于后续范围，按需求与测量结果引入。
- 服务器只发布 `server.runtime_files()` 列出的运行资产；不要把原始数据、虚拟环境、源码或整个项目目录直接公开。
- 启动：`python3 server.py --port 8097`。局域网：加 `--host 0.0.0.0`。
- 修改服务后运行：`python3 -m unittest discover -s tests -v`。修改 JS 后运行：`node --check app.js`。
- 涉及地图交互或导出时运行 `scripts/check_browser.mjs`（可选开发依赖 Playwright），检查桌面/窄屏、PNG 尺寸、配置保存、失败提示；记录真实环境，不把桌面模拟说成手机实测。
- 打包：`python3 scripts/package_trial.py`。产物 `dist/mapshot-trial.zip` 不包含原始地图、虚拟环境或生成图片。
- 修改数据后更新清单；不要把旧的验证记录当成本次测试结果。源码与小型清单用 Git，地图二进制与导出物按 `.gitignore` 分开管理。
- 项目原路径为 `Documents/ChatGPT/Map/shanghai_road_studio`，迁移后使用相对路径。迁移来的 `.venv` 是旧开发环境，不是部署依赖；需要重建数据时重新创建环境。
