# Pot 划词桥接插件（Zotero 10.0）

目标：在 Zotero PDF 中普通拖选后直接 Ctrl+T 调用 Pot，不必按 Alt 拖选。

原理：监听 Zotero 提供的 renderTextSelectionPopup 事件，将 params.annotation.text 写入 Linux PRIMARY 主选区。普通 Ctrl+C/粘贴使用的 CLIPBOARD 不变。没有联网、读取全文、修改 PDF、添加批注或调用翻译服务的代码。

## 安装

1. Zotero 菜单：工具 → 插件（Tools → Plugins，某些版本称附加组件）。
2. 点击插件管理页面的齿轮 → 从文件安装插件。
3. 选择本目录的 pot-zotero-primary-bridge-0.1.1.xpi，确认安装。
4. 回到 PDF，普通拖选一小段文字，松开鼠标，再按 Ctrl+T。

使用前请确保 Pot 的 GNOME 快捷键及原生 Wayland 辅助脚本仍在。插件名称为 Pot Primary Selection Bridge。安装通常可以立即生效；如没有变化，可关闭 PDF 标签页后重新打开，不需要修改系统设置。

## 撤销

在 Zotero 插件管理页面停用或卸载 Pot Primary Selection Bridge 即可。插件会注销事件监听器。卸载后恢复 Zotero 原来的行为，需要使用 Alt 拖选。

## 版本与验证

- 当前宿主：Zotero 10.0.7；读取已安装程序的 reader.js，确认事件、参数和注册/注销 API。
- manifest 限定 10.0.*，没有宣称其他版本已经验证。
- Node 合约测试已通过：只写 PRIMARY、Unicode/多行文字、选区弹窗参数不变、忽略空值、停用清理、平台错误隔离、Linux 限制、异步启动取消。
- 真实 Zotero 10.0.7 的隔离配置测试通过：实际加载 bootstrap、注册选区事件、通过 XPCOM 写入 PRIMARY、外部 GTK 客户端读回 Unicode 文字，同时验证正常 CLIPBOARD 的基线内容未改变。测试程序 scripts/test-zotero-primary-runtime.py。
- 该隔离测试主动调用真实事件处理器，未自动模拟 PDF 拖选。用户随后在日常 Zotero 中安装 0.1.1，确认普通拖选 PDF 文字后按 Ctrl+T 已正常显示，无需 Alt。批注编辑回归和再次重启尚未单独测试。
- 0.1.0 被拒绝是因为清单缺少 Zotero 强制要求的 update_url。0.1.1 补齐该字段，不放宽兼容性或关闭安全校验。此插件仅手动更新，update_url 使用保留的 updates.invalid 域名表示没有在线更新服务；不要期待自动更新。

源码：plugins/zotero-primary-bridge，独立分支 compat/zotero-primary-bridge。

参考：
- https://www.zotero.org/support/dev/zotero_7_for_developers （bootstrap 与 manifest 机制）
- 已安装的 /opt/zotero/app/omni.ja 内 chrome/content/zotero/xpcom/reader.js （实际选区事件 API）
- https://raw.githubusercontent.com/mozilla-firefox/firefox/main/widget/nsIClipboardHelper.idl （PRIMARY 专用写入 API）
