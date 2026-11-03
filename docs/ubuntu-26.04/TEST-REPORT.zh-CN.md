# Pot Desktop 3.0.7 Ubuntu 26.04 测试报告

日期：2026-11-04（Europe/Stockholm）。

结论：原生 release 与 deb 构建成功，安装依赖可解析，deb 解包后的实际程序可以运行。
X11/XWayland 下的本地功能验证通过。联网翻译尚未通过，不能称为全部验收完成。

## 基线与修改

- 基线：上游 3.0.7，d05a436c9f426a94c38e176f096aeca04c3bf06a。
- 分支：compat/ubuntu-26.04；原标签和历史保留。
- 工作目录：/home/huanyu/Documents/Codex/pot_modify。
- 保留 Tauri 1.8.1、tauri-build 1.5.5、Wry 0.24.11、GTK/GLib 0.15。
- 局部适配四个底层 crate：实际使用 WebKitGTK/JavaScriptCore 4.1 与 soup3 0.2.3。
- 其余 807 个 Rust 包版本不变；前端锁文件和 Pot Rust 业务源码未改动。
- /usr/bin/pot 启动脚本在 DISPLAY 可用且 GDK_BACKEND 未指定时，为 Pot 选择
  X11/XWayland。它不改写 XDG_SESSION_TYPE 或 WAYLAND_DISPLAY。
- 所有编译器与开发依赖仅解包在 work/；没有向系统安装旧库、修改关键配置或重新挂载磁盘。

## 系统和工具

Ubuntu 26.04 LTS amd64；GTK 3.24.52；WebKitGTK/JavaScriptCore 2.52.6；
libsoup 3.6.6；Ayatana AppIndicator 0.5.94。
Rust 1.93.1，GCC 15.2，Node 22.22.1，pnpm 9.15.9。

## 构建和包验证

| 检查 | 结果与证据 |
| --- | --- |
| 原版 cargo check --locked | 复现 soup2-sys 找不到 libsoup-2.4.pc |
| 原锁文件前端安装与构建 | 通过；Vite build 完成 |
| 补丁 cargo check --locked | 通过 |
| cargo build --release --locked --features custom-protocol | 通过，首次构建耗时 13m49s |
| 原生 C ABI 探针 | 通过；验证消息头引用计数、Cookie 与真实库版本 |
| readelf 与 ldd | 实际使用 libwebkit2gtk-4.1.so.0、libjavascriptcoregtk-4.1.so.0、libsoup-3.0.so.0；没有旧 ABI，也没有本地 sysroot 的 RPATH/RUNPATH |
| deb 生成 | 通过；Depends 来自真实 ELF 的 dpkg-shlibdeps，加上动态加载及外部命令依赖 |
| apt-get -s install 本地 deb | 通过；依赖可由 Ubuntu 26.04 仓库满足，无需旧版 WebKitGTK/libsoup |
| 最终 deb 解包运行 | 通过；实际使用包内启动脚本和已 strip 的程序完成测试 |
| 真实系统 dpkg/apt 安装 | 未执行；当前沙盒不能写系统目录，本次没有修改系统包数据库 |

## 功能测试

通过 WebKitWebDriver 驱动真实 release WebView 和真实 Rust IPC，没有用模拟翻译
结果替代网络服务。测试使用独立配置、缓存、Xvfb X11 显示及私有 D-Bus，避免覆盖
用户的 Pot 配置和剪贴板。另在当前真实 Wayland 桌面验证了启动与快捷键注册。

| 功能 | 结果 | 范围 |
| --- | --- | --- |
| 设置界面与前端渲染 | 通过 | X11 及真实 Wayland 均显示设置内容；截图已检查 |
| Rust IPC | 通过 | font_list 返回 231 项字体 |
| 剪贴板读写 | 通过 | 中英文测试文本往返一致，使用隔离 X11 剪贴板 |
| 系统 OCR | 通过 | 实际 Tesseract 识别图片得到 Pot Ubuntu translation test 123 |
| 截图 | 通过 | 原始 screenshot 命令生成 1280×900 图像，范围为隔离 X11 显示 |
| 托盘 | 通过 | 实际 Ayatana AppIndicator 注册为 Active，菜单更新成功；通过 D-Bus 点击 Input Translate 打开翻译窗口 |
| 快捷键 | 通过 | 隔离 X11 下实际发送 Ctrl+Alt+Shift+F9，打开翻译窗口 |
| 原生 Wayland 快捷键 | 失败，已提供 XWayland 默认启动方式 | Tao 0.16 返回 Unable to register global shortcut |
| 最终包在当前 Wayland 桌面启动 | 通过 | 默认启动脚本选择 XWayland，界面正常、同一快捷键注册成功 |
| Bing 联网翻译 | 未通过 | 原有 edge.microsoft.com/translate/auth 返回 HTTP 404 |
| Google 联网翻译 | 未通过 | 原有服务返回 HTTP 429；独立于 Tauri 的请求也收到 429 |
| DeepL 免费联网翻译 | 未通过 | 原有 www2.deepl.com/jsonrpc 返回 HTTP 429 |

## 未完成的验收

- 需要可用且已授权的翻译服务继续完成实际译文验证；没有更换原有服务实现来掩盖失败。
- 真实系统 apt 安装与桌面菜单启动，需要在沙盒外完成。
- GNOME 面板中托盘图标的视觉显示尚未验收；已验证底层注册、菜单和动作。
- Wayland 截图门户的授权流程、原生 Wayland 跨应用划词、剪贴板监控、多显示器/缩放
  与其他翻译/OCR 插件尚未全面回归。X11 测试不代表这些场景已经通过。
- macOS、Windows、其他 Linux 版本与架构未回归。

## 构建注意事项

使用 scripts/build-ubuntu-26.04.sh；受限环境先运行 bootstrap-local.py，再 source
scripts/local-env.sh。不要在构建期间重新解包工具链。
原 Bullseye Linux CI 和 Tauri 1 的默认 deb bundler 仍面向 WebKitGTK 4.0，不能用于
本分支 Ubuntu 包。使用本分支的独立打包脚本。

详细日志保存在项目 work/logs，机器可读功能结果位于 work/runtime-test/results.json，
原生 Wayland 与默认启动方式的结果分别位于 work/wayland-test/results.json 和
work/host-xwayland-test/results.json。修改记录见 CHANGES.md。
