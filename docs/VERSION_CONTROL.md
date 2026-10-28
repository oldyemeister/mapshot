# 现在开始使用 Git

Mapshot 已有可运行版本，且正在迁移目录、拆分部署职责，适合立即建立本地版本记录。Git 用于比较和恢复代码；GitHub 是可选的远程托管平台，不影响本地使用 Git。

## 首次记录

迁移完成后在 `Documents/mapshot` 目录执行：

```sh
git init -b main
git status --short
git add .
git diff --cached --stat
git commit -m "Establish Mapshot trial baseline"
```

提交前确认暂存清单不含地图大文件、虚拟环境、生成图片、ZIP、访问凭据。若 Git 要求姓名和邮箱，使用你自己的身份设置，不要使用示例或代理身份。上述命令是操作说明；本次写文档不代表已经初始化或提交仓库。

## 什么进入仓库

- HTML/CSS/JS、Python 服务、脚本与测试。
- README、AGENTS、产品和设计文档。
- 小型数据清单，记录来源、日期、范围和计数。
- 现有第三方运行组件及其许可信息。

`.gitignore` 排除原始地图、生成的压缩几何与瓦片、虚拟环境、PNG、ZIP、日志和本地数据库。原始数据与运行包仍应单独备份；拿到 Git 源码后，要再放入匹配版本的数据包才能运行地图。

## 日常节奏

每完成一个可验证变化就提交一次，例如“增加读取进度”“加入一个城市数据包的配置”“修复导出恢复视野”。提交信息描述变化，测试结果记在相关文档或提交说明中。较大实验可用独立分支。

不要等上线后才开始，也不必每修改一行就提交。上传 GitHub、设置远程仓库权限和公开数据是后续独立决定。

## AGENTS.md 是什么

它是给 Codex 等编程代理看的项目约定：项目要做什么、怎么运行、哪些行为必须保留、改动后检查什么。README 则优先服务人类使用者。

AGENTS.md 是可选文本文件，不是数据库、程序入口或后台进程，也不会自动创建多个代理。保持精简，写真实而稳定的约定，具体里程碑放在项目文档中。

参考：[OpenAI 官方开发工作流说明](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex)。
