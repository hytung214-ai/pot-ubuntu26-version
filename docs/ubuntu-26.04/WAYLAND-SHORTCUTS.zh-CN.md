# Ubuntu 26.04 / GNOME Wayland 划词快捷键

2026-11-04：当前已部署并经过用户实际按键验证。

## 使用

- Firefox 普通网页：直接拖选文字，然后 Ctrl+T。用户已确认正确显示。
- Zotero 10.0.7 的 PDF 标签页：按住 Alt 拖选文字，松开 Alt，再按 Ctrl+T。用户已确认正确显示。普通拖选可能没有更新系统主选区，Pot 会读到上一次内容。
- Ctrl+T 会唤起并激活 Pot，覆盖 Firefox 的新建标签页快捷键。
- 本次验证了取词和前台激活，没有验证联网翻译结果。Google 429 是独立的服务问题。

## 修改原因和实现

Pot 原 selection 1.2.0 在 GNOME 的 Wayland 读取失败后回退到 X11 PRIMARY，导致跨应用时读到旧数据。新的辅助脚本启动独立的原生 Wayland GTK 小窗口，获得焦点后接收 PRIMARY 选区，经现有本地 /translate 入口发送给 Pot；随后通过 EWMH 激活 Pot 窗口。没有重写 Pot 的翻译业务或迁移 Tauri。

选区来源应用必须发布选中的文字：单凭页面高亮无法保证发布成功。Zotero PDF 的这一限制和 Alt 选区办法有官方论坛记录：https://forums.zotero.org/discussion/96038/cant-use-primary-selection-in-built-in-pdf-viewer-zotero6 。原生读取器不回退到旧 X11 选区，但也无法识别来源应用没有发布新内容的情况。

系统中已有 /usr/bin/python3、python3-gi、GTK 3 introspection、libX11 和 x11-utils。未安装系统包、未修改系统关键配置或 Wayland 安全策略。选中文字只经过内存和本机请求，不写入调用日志。启动 Pot 时只重试连接拒绝，不重试已接受后超时的翻译请求。

GNOME 快捷键命令仍引用本目录的 pot-shortcut.py，请保留目录。此次无需重新安装 deb。源码在 compat/wayland-shortcuts 分支。重启后这次最终取词路径尚未验证。

## 排查记录

- XWayland 的直接快捷键无法覆盖原生 Wayland 应用：改用 GNOME 用户快捷键，保留原设置备份。
- 窗口已显示却被挡住：添加前台激活，用户确认生效。
- GNOME 主选区开关单独开启无效，已恢复原默认 false；备份 state/primary-selection-before.json。
- 先激活 Pot 再读取 X11 选区的实验无效，已移除。
- AT-SPI 实验没有取得正确选区，已完全移除。
- 测试期间 Pot 出现 SIGSEGV；报告没有调用栈，原因未确定。系统当时约 7.7 GiB 可用内存，不能将分析报告生成失败等同于 OOM。后续测试不能单独证明崩溃已修复。
- 最终原生 Wayland 路径：用户确认 Firefox 正常、Zotero Alt 拖选正常；调用记录核实请求成功及窗口前台激活。

## 撤销 GNOME 快捷键

```bash
/usr/bin/python3 "/home/huanyu/Documents/Codex/2026-11-03/pot-desktop-3-0-7-ubuntu/outputs/wayland-hotkeys/pot-gnome-shortcut.py" --helper "/home/huanyu/Documents/Codex/2026-11-03/pot-desktop-3-0-7-ubuntu/outputs/wayland-hotkeys/pot-shortcut.py" --state "/home/huanyu/Documents/Codex/2026-11-03/pot-desktop-3-0-7-ubuntu/outputs/wayland-hotkeys/state" --remove
```

只恢复此工具的用户快捷键；其他快捷键保持不变。安装前设置保存在 state/gnome-before.json。旧脚本备份只供排查，不建议覆盖使用，因为旧版仍可能读错选区。
