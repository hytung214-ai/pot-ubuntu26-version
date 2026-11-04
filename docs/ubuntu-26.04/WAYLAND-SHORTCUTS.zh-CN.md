# GNOME / Wayland 快捷键修复

原因：Pot 3.0.7 使用的 Tao 通过 X11 XGrabKey 注册快捷键。XWayland 中注册成功，并不能证明焦点在原生 Wayland 应用中时也能触发。此前的隔离 X11 测试没有覆盖 Firefox/PDF 的真实焦点场景。

本次在独立分支 `compat/wayland-shortcuts` 增加两个辅助脚本。GNOME 的用户自定义快捷键 Ctrl+T 调用 Pot 原有的本地 `/selection_translate` 入口；保留 Pot 源码、系统 Wayland 安全设置和其他用户快捷键。Ctrl+T 会覆盖 Firefox 的新建标签页快捷键。

## 当前状态

- 已在当前用户中安装快捷键，并在独立进程中读回验证。
- 已备份该自定义快捷键原值：`state/gnome-before.json`。
- Pot 本地服务端口读取自用户配置，不保存 API 密钥。
- 四个动作的本地 HTTP 路由测试通过；每次只发一个空请求，不在已接受请求超时后重试。
- 日志 `state/invocations.log` 只记录动作和调用结果，不记录选中文字或翻译结果。
- 用户已在 Firefox/PDF 场景实按 Ctrl+T，确认 Pot 弹出并显示选中文字。此次未验证联网翻译服务的返回结果。
- 本次不需要重新安装 deb。请保留本目录，GNOME 的命令引用这里的脚本。

## 撤销

在终端运行：

```bash
/usr/bin/python3 "/home/huanyu/Documents/Codex/2026-11-03/pot-desktop-3-0-7-ubuntu/outputs/wayland-hotkeys/pot-gnome-shortcut.py" --helper "/home/huanyu/Documents/Codex/2026-11-03/pot-desktop-3-0-7-ubuntu/outputs/wayland-hotkeys/pot-shortcut.py" --state "/home/huanyu/Documents/Codex/2026-11-03/pot-desktop-3-0-7-ubuntu/outputs/wayland-hotkeys/state" --remove
```

撤销只处理本工具创建的绑定；如果之后手工编辑了该绑定，脚本会拒绝覆盖。其他自定义快捷键保持原样。

背景资料：[GNOME 的 XGrabKey / Wayland 问题记录](https://bugzilla.gnome.org/show_bug.cgi?id=765739)。长期集成可以采用 [XDG GlobalShortcuts portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html)，需要实现会话、绑定授权和 Activated 事件；本次采用现有服务接口减少改动。

## 2026-11-04：窗口被其他应用遮挡

重启后的检查表明 GNOME 快捷键和脚本路径仍然存在；日志记录 Pot 已接受多次请求。实际翻译窗口处于 IsViewable 状态，但带有 `_NET_WM_STATE_DEMANDS_ATTENTION`，不是 `_NET_ACTIVE_WINDOW`。用户随后也确认窗口被其他页面挡住。

修复：辅助脚本在 Pot 接受划词/输入请求后，识别 WM_CLASS 为 pot/Pot 且标题为 Translate 的 XWayland 窗口，发送 EWMH `_NET_ACTIVE_WINDOW` 请求，并独立核实是否成为当前窗口。不会在激活失败后重复翻译请求，不设置永久置顶、不改 GNOME 的安全策略。使用当前系统已有的 libX11 和 x11-utils 的 xprop，未安装系统包。

实测：现有窗口激活实验成功；部署后的辅助脚本 input 动作返回 HTTP 200，且记录 `window activation: verified`。用户已实按 Ctrl+T，确认 Pot 到最前面并带入选中文字。原脚本备份为 `pot-shortcut.before-activation.py`。本次不修改 deb；GNOME 仍引用同一路径，重启后该文件和绑定均可保留，但重启验证尚未执行。

协议依据：https://specifications.freedesktop.org/wm/latest/ar01s09.html#sourceindication
