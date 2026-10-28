# Mapshot · 上海路网调色台

OpenStreetMap 地图调色与壁纸导出工具，当前提供上海单城朋友试用版。地图、主题与组件随项目提供，服务器不调用外部地图 API；浏览器负责实时预览与 PNG 导出。

在项目目录运行 `python3 server.py`，打开 http://127.0.0.1:8097 。需要 Python 3.9+；不需要安装第三方 Python 包。macOS 可双击 `start.command`。局域网使用 `python3 server.py --host 0.0.0.0`。

**复制到树莓派：**运行 `python3 scripts/package_trial.py`，将生成的 `dist/mapshot-trial.zip` 拷贝过去解压；无需复制开发虚拟环境和原始地图大文件。目前尚未部署树莓派或开通公网网址。

- [项目范围、架构与后续计划](docs/PROJECT.md)
- [启动、部署、接口与排查](docs/DEPLOYMENT.md)
- [本次验证记录](docs/VERIFICATION.md)
- [开始用 Git](docs/VERSION_CONTROL.md)
- [编程代理工作约定](AGENTS.md)

首次打开会读取约 35.3 MB 压缩地理数据，显示读取进度后绘制地图。当前仍为完整几何下载，尚未切换 PMTiles；手机内存和网络体验需要真机试用。首次完整浏览器检查通过，但第二轮重复加载出现 Chromium 页面崩溃，当前定位为桌面试用候选版，详见验证文档。配色只保存在当前浏览器，可下载 JSON 备份。

## 操作

- 调整各等级道路的颜色、线宽和显示状态；匝道跟随所属道路。线宽以 z11 为基准，随缩放变化。
- 背景、江河湖泊、海域、细小河道分别调色。默认使用精细江河湖泊多边形；湿地使用草地颜色。海域与海岸线仍为缓存底图。
- 建筑、公园、树林、草地、住宅用地、工业用地、农田、其他用地分别设置颜色、可见性和不透明度。
- 机场设施中的跑道、滑行道、停机坪可分别调色、隐藏和设置不透明度；与预设主题、配色保存和 PNG 导出联动。
- 拖动和滚轮缩放；“全范围”复位，人民广场和滴水湖按钮用于近景。
- 设置自动保存到浏览器；“保存配色”和“载入配色”用于 JSON 文件。旧版配色文件可载入，新图层会采用默认值。

## 16:10 壁纸导出

选择 1920 × 1200、3840 × 2400（桌面默认）或 7680 × 4800，然后点击导出 PNG。窄屏默认 1920 × 1200，以降低导出内存需求。输出为严格的 16:10 比例，取当前地图视野。

只有地图像素，不包含标题、地点文字、圆点、标尺、按钮、边框、留白。预览标记开关不影响导出。输出时提高真实渲染像素密度，不放大低清截图。超过 4096px 的输出分成多个小于显卡限制的区块，以相同地图缩放级别和像素密度绘制后无缝拼接，降低峰值显存占用。导出期间暂停交互，结束后恢复视野和预览像素密度。

3840px 在 300 DPI 下宽约 32.5 cm；7680px 宽约 65.0 cm。提高像素数可让细线更清晰，不会增加未被 OSM 记录的建筑，也不会提高原始水域数据的地理精度。

PNG 文本元数据保存来源、OSM 时间、地理范围和像素尺寸。公开展示/印刷时，应在相邻说明、版面或作品说明中提供 OpenStreetMap 署名和版权链接。

## 主题

内置清绘、蓝图、墨色、夜航；新增来自 [originalankur/maptoposter](https://github.com/originalankur/maptoposter/tree/main/themes) 的六个预设：

- Noir / 黑白
- Midnight Blue / 午夜蓝
- Japanese Ink / 日式墨绘
- Copper Patina / 铜绿
- Pastel Dream / 柔彩
- Terracotta / 陶土

背景、水域、公园及道路沿用原主题色值。道路映射与原项目一致：trunk 跟随 primary；unclassified 跟随 residential；服务道路、小路等使用 road_default。建筑、航空设施和原项目未定义的土地用途通过原主题颜色混合生成，并在界面注明适配。保留当前工具线宽及操作逻辑，不引入原项目海报文字或渐变遮罩。

原始主题 JSON、文件哈希及 MIT 许可证在 `vendor/maptoposter/`；Copyright (c) 2026 Ankur Gupta。

## 数据范围与容量

16:10 视野：120.6143053902–122.3330946098°E，30.7700–31.6885676823°N，约164 × 102公里。Web Mercator 投影，以人民广场（121.4737,31.2304）为中心；包含青浦西部和临港周边，宽屏两侧也包含江苏、浙江部分地区。

现用道路、建筑、土地用途和水系图层为 **2026-10-27T21:23:59Z** 的 Geofabrik / OSM 数据：

| 数据 | 要素数量 | 压缩文件大小 |
|---|---:|---:|
| 道路 / 河道 | 285,159 / 14,939 | 16.08 MB |
| 建筑 | 224,700 | 11.14 MB |
| 土地用途 / 绿地 | 38,679 | 4.50 MB |
| 水域（含湿地等原始类别） | 8,708 | 3.41 MB |
| 航空设施（含中心线和面） | 1,456 | 0.14 MB |

离线运行资源约 **45.15 MB**。当前使用的源数据包下载合计 **220.1 MB**；包括早期 Overpass 下载的本次累计约 **371.0 MB**（不含少量开发依赖和 HTTP 开销）。原始数据保留用于复现，不随日常运行加载；历史 July JSON 已不再用于现有地图。1 MB = 1,000,000 字节。

细节与限制：

- 多边形保留内部孔洞；上海源与周边源按几何及 OSM 身份去重，避免行政界限处截断。
- OSM 为社区记录，未显示某要素不表示现实中不存在。道路标签不等同于中国法定行政道路等级或限速。
- 精细内陆水面来自原始矢量数据；海域/海岸线仍来自 OpenFreeMap 2026-10-25 的 z7–11 缓存。关闭精细水域可查看缓存基础水面。
- 原始水域有一条标为 glacier 的异常源记录，保留在数据中供追溯，但不作为开阔水面绘制。湿地单独按草地色显示。
- 建筑提供平面轮廓；此次没有补造高度、楼层或立面。

数据统计和校验记录：`data/manifest.json`、`data/roads-manifest.json`、`data/surfaces-manifest.json`。开发目录中重建流程依次为 `scripts/build_surfaces.py`、`.venv/bin/python scripts/extend_surfaces.py jiangsu zhejiang`、`.venv/bin/python scripts/build_regional_roads.py`、`scripts/update_manifest.py`。重建需原始 GeoPackage/PBF 和 osmium；离线使用包不需要这些开发依赖。

## 航空设施

新增航空设施来自独立的 Overpass 提取，范围与当前地图一致；本次服务器返回的快照为 **2026-05-31T22:37:44Z**，与其余图层时间不同。额外源数据下载约 **1.37 MB**，离线压缩图层约 **141 KB**。包含 23 个跑道要素、1,370 个滑行道要素、63 个停机坪要素；要素数包含分段及面轮廓，不等于独立跑道数量。保留原始跑道、滑行道、停机坪多边形及孔洞；被同类面轮廓覆盖的中心线保留在数据中，但不重复绘制；中心线优先按 OSM `width` 标签绘制。缺少或无法解析宽度时，跑道以 45 m、滑行道以 23 m 作为**显示默认宽度**，不代表测量值；远景保留 0.55 CSS 像素的最小线宽，以便识别。点击设施可查看类型、宽度来源及 OSM 原始记录。

航空设施在土地用途上方、建筑和道路下方绘制。配色格式升级为 v3；v1/v2 文件仍可载入，旧有设置保留，新增设施使用相应主题默认色。源查询为 `data/raw/query-aviation.overpass`，原始数据为 `data/raw/aviation.osm`，统计和快照时间见 `data/aviation-manifest.json`。使用 `.venv/bin/python scripts/build_aviation.py` 重建，再运行 `python3 scripts/update_manifest.py` 更新资源总量。

## 来源与许可

- 地图数据 © OpenStreetMap contributors，ODbL 1.0：https://www.openstreetmap.org/copyright
- Geofabrik 数据：https://download.geofabrik.de/asia/china.html
- OpenFreeMap / OpenMapTiles：https://openfreemap.org
- MapLibre GL JS 5.10.0，BSD 3-Clause：https://github.com/maplibre/maplibre-gl-js/blob/v5.10.0/LICENSE.txt
- 主题 originalankur/maptoposter，MIT，许可证随包附带。
