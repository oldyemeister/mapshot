#!/bin/zsh
cd "${0:A:h}"
printf '上海路网调色台\n请在浏览器打开 http://127.0.0.1:8097\n按 Ctrl+C 停止服务。\n'
python3 server.py
