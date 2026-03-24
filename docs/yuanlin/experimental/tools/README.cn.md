# tools - 实验性辅助工具

## 概述

`experimental/tools/` 包含各种辅助开发的脚本和工具程序，用于 Android 调试、
PDF 转换、Gerrit 交互、Unicode 测试等场景。

## 目录结构

```
tools/
├── android_skp_capture.sh        # Android SKP 录制脚本
├── coreGraphicsPdf2png.cpp       # Core Graphics PDF 转 PNG 工具
├── generate-unicode-test-txt     # Unicode 测试文件生成器
├── gerrit_percent_encode         # Gerrit URL 百分号编码工具
├── mskp_parser.py                # MSKP 文件解析器（Python）
├── pdf-comparison.py             # PDF 比较工具（Python）
├── set-change-id-hook            # Git Change-Id 钩子安装脚本
├── web_to_mskp                   # 网页转 MSKP 工具
└── web_to_skp                    # 网页转 SKP 工具
```

## 关键文件

- **android_skp_capture.sh**: 从 Android 设备录制 SKP（Skia Picture）文件
- **set-change-id-hook**: 安装 Gerrit 所需的 Change-Id 提交钩子
- **gerrit_percent_encode**: 对 Gerrit 推送消息进行百分号编码
- **mskp_parser.py**: 解析多页 SKP 文件格式
- **coreGraphicsPdf2png.cpp**: macOS 上使用 Core Graphics 将 PDF 转换为 PNG

## 依赖关系

- Shell 脚本: bash/sh
- Python 脚本: Python 3
- C++ 工具: macOS Core Graphics 框架

## 相关文档与参考

- Gerrit 使用指南: `experimental/documentation/gerrit.md`
- Skia 工具目录: `tools/`
