# Pot Desktop 3.0.7：Ubuntu 26.04 适配

工作分支：`compat/ubuntu-26.04`。上游 `3.0.7` 标签和原始提交保持不变。

本分支保留 Tauri 1.8.1、React/Vite 及原有业务逻辑，通过四个底层 crate
的局部补丁，实际链接 WebKitGTK 4.1、JavaScriptCore 4.1 和 libsoup 3。
补丁来源、原始 SHA256 和变更范围见 `vendor/PATCHES.md`。

## 构建

在 Ubuntu 26.04 amd64 上，若已有 Rust、Node、pnpm 9、GCC、GTK 3、WebKitGTK 4.1
开发包及打包工具，可运行：

```bash
bash scripts/build-ubuntu-26.04.sh
```

本次受限沙盒使用以下方式，将工具和开发包解包到项目 `work/`，不修改系统：

```bash
python3 scripts/bootstrap-local.py
source scripts/local-env.sh
bash scripts/build-ubuntu-26.04.sh --local
```

请在构建停止时运行 bootstrap，避免重新解包正在被编译器读取的文件。
bootstrap 校验 Ubuntu 仓库包的 SHA256、Node 官方 SHA256 和 pnpm npm integrity。
构建缓存和本地工具不进入 Git。

输出位于 `work/packages/`。该脚本从新编译二进制的真实 ELF 符号生成 deb
依赖，另声明动态加载的 Ayatana AppIndicator 和外部执行的 Tesseract。
它不沿用 Tauri 1 bundler 对 WebKitGTK 4.0 的固定依赖。

## 验证方法

- `pnpm install --frozen-lockfile`，保留前端锁定版本；`pnpm build`。
- `cargo check --locked --manifest-path src-tauri/Cargo.toml`。
- 使用 release 构建和 `custom-protocol`，嵌入正式前端资源。
- `scripts/probe-webkit41.c` 验证实际 C ABI、消息头引用计数和版本。
- `scripts/runtime-smoke.py` 通过 WebKitWebDriver 驱动真实应用，使用独立
  X11 显示、D-Bus 会话和配置/缓存，避免覆盖用户剪贴板及 Pot 配置。
- 核对 `readelf`、`ldd` 和 `dpkg-shlibdeps`，禁止残留旧 WebKitGTK/libsoup ABI。
- 对最终 deb 做解包和依赖解析检查；安装验证结果与功能测试结果另行记录。

自动化测试需 Ubuntu 当前版本的 `webkitgtk-webdriver`、Xvfb、Python gi/dbus/Pillow。
沙盒中测试工具也只解包到 `work/`。本分支原有 Bullseye Linux CI 依赖 WebKitGTK 4.0，
不能用于生成本分支的 Ubuntu 26.04 安装包。

## 桌面功能范围

X11/XWayland 下的测试结果不能自动推导为原生 Wayland 全面支持。
尤其是跨应用划词、全局快捷键、屏幕位置和截图，需要桌面协议及 compositor
共同支持。最终报告应分别列明通过、失败及尚未验证的项目。

本包的 `/usr/bin/pot` 是启动脚本，真实程序位于 `/usr/lib/pot/pot`。
检测到 DISPLAY 且用户未指定 GDK_BACKEND 时，启动脚本仅为 Pot 选择 X11/XWayland，
以保留 Tao 0.16 的快捷键功能；不会改写系统会话类型。显式设置 GDK_BACKEND
仍会被尊重。原生 Wayland 的界面已能启动，但快捷键注册实测失败。

联网翻译测试中，Bing 的原有令牌地址返回 404，Google 和 DeepL 免费服务返回
429；不能将这些结果认定为翻译成功。需要使用可用且已授权的服务继续验证。
没有为了获得“通过”结果而改写服务响应、跳过真实请求或替换翻译结果。

本次仅验证 Ubuntu 26.04 amd64；不声明其他发行版、架构或平台已通过回归。
