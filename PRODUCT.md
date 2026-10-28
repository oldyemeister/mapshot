# 上海路网调色台
<!-- impeccable:product-schema 1 -->
## Platform
web
## Users
用户本人及少量朋友；桌面优先，支持窄屏浏览与较小尺寸导出。
## Product Purpose
用 OpenStreetMap 展示人民广场居中、西至青浦西部、东南覆盖临港与滴水湖的路网，交互调整各等级道路、背景和水系颜色。
## Operating Context
已确认制作可复制到树莓派 5（约 4GB）的试用版。先支持上海；由轻量 Python 服务提供文件，浏览器调色和出图。树莓派及公网尚未部署。保留本机离线使用。
## Capabilities and Constraints
各类道路颜色、线宽、可见性；背景、水域、河道颜色；平移缩放；保存配色；导出地图图片。用户明确要求导出只有地图，不含地点文字、圆点、边框或留白，并提高分辨率。数据必须为真实 OSM 几何，说明范围、下载量和数据日期。小路完整程度取决于 OSM 记录。
## Stack
实现选择：沿用现有地图项目的静态 HTML/CSS/JavaScript、MapLibre 本地组件和 Python 3.9+ 标准库服务；只读健康/数据接口，配色 localStorage + JSON 导入导出。当前无 SQLite、账号或服务端渲染。

## Confirmed follow-up requirements
16:10 MacBook wallpaper; pure map only, no text/markers/frame/padding; native 3840×2400 and 7680×4800 export. Download buildings, green space/land use and detailed water polygons. Add theme presets based on originalankur/maptoposter themes while retaining offline use and per-layer editing.

## Trial milestone
朋友通过网址独立完成打开上海地图、调色和下载图片。下载进度与失败重试可见；桌面默认 3840×2400，窄屏默认 1920×1200。项目迁移为 Documents/mapshot；实际部署入口待用户提供。详细范围与后续决策见 docs/PROJECT.md。
