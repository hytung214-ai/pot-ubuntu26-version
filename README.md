# Pot Ubuntu 修改版 / Ubuntu Modification

## 中文

基于原作者及贡献者开发的 [Pot Desktop 3.0.7](https://github.com/pot-app/pot-desktop)，使用 AI 辅助修改；非原创项目，非官方发行版。原有版权、署名及 [GPL-3.0 许可证](LICENSE) 保留。

- **依赖兼容**：针对 Ubuntu 26.04 缺少旧版 libsoup 2 / WebKitGTK 4.0 开发依赖的问题，对四个底层 crate 做局部补丁，改用 WebKitGTK 4.1、JavaScriptCore 4.1 和 libsoup 3，保留 Tauri 1 架构。
- **打包依赖**：从实际编译程序生成 deb 依赖，保留 AppIndicator 托盘、libxdo、libXrandr 和 Tesseract OCR 等运行依赖。
- **桌面使用**：提供 XWayland 启动及可选 GNOME 快捷键辅助脚本，处理原生 Wayland 应用中的划词获取和翻译窗口前置；另附可选 Zotero PDF 划词桥接插件。

适配目标为 Ubuntu 26.04 amd64，不保证所有 Wayland 桌面均可使用。曾出现的 SIGSEGV 尚未确认修复；本次发布未重新编译或执行完整回归测试。构建步骤、依赖详情和已有测试记录见 [适配文档](docs/ubuntu-26.04/README.zh-CN.md)。

## English

An unofficial modification of [Pot Desktop 3.0.7](https://github.com/pot-app/pot-desktop), developed by its original authors and contributors. Changes were made with AI assistance. We do not claim original authorship; existing attribution, copyrights and the [GPL-3.0 license](LICENSE) are retained.

- **Dependency compatibility:** patches four underlying crates to use WebKitGTK 4.1, JavaScriptCore 4.1 and libsoup 3 on Ubuntu 26.04, addressing unavailable legacy libsoup 2 / WebKitGTK 4.0 development dependencies while retaining Tauri 1.
- **Packaging:** derives deb dependencies from the compiled executable and retains runtime requirements for AppIndicator, libxdo, libXrandr and Tesseract OCR.
- **Desktop integration:** adds an XWayland launcher and optional GNOME shortcut helpers for selection capture and window activation, plus an optional Zotero PDF selection bridge.

Targets Ubuntu 26.04 amd64; universal Wayland support is not claimed. A previously observed SIGSEGV remains unresolved. This publication did not include a fresh build or full regression run. See the [compatibility notes](docs/ubuntu-26.04/README.zh-CN.md) for build instructions and recorded tests.
