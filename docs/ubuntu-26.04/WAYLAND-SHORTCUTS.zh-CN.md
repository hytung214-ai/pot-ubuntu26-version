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
