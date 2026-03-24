# sktext - 实验性文本渲染引擎

## 概述

`experimental/sktext/` 是 Skia 的实验性高级文本渲染引擎。它在 Skia 核心文本功能之上
提供了更丰富的文本处理能力，包括文本塑形（shaping）、Unicode 处理、文本选择、自动换行
以及一个原型文本编辑器实现。该模块需要 Unicode 支持（ICU、libgrapheme 或 icu4x）和
HarfBuzz 文本塑形引擎。

## 目录结构

```
sktext/
├── BUILD.gn                 # GN 构建配置
├── sktext.gni               # GN 导入文件（源文件列表）
├── include/                 # 公共头文件
├── src/                     # 核心实现源码
├── editor/                  # 原型文本编辑器
│   ├── App.cpp              # 编辑器应用程序入口
│   ├── Cursor.cpp           # 光标管理
│   ├── Editor.cpp           # 编辑器核心逻辑
│   ├── Mouse.cpp            # 鼠标交互处理
│   ├── Selection.cpp        # 文本选择功能
│   └── Texts.cpp            # 文本内容管理
├── slides/                  # 演示幻灯片
│   └── Text.cpp             # 文本渲染演示
└── tests/                   # 单元测试
    ├── FontResolvedText.cpp # 字体解析测试
    ├── SelectableText.cpp   # 可选择文本测试
    ├── ShapedText.cpp       # 文本塑形测试
    ├── UnicodeText.cpp      # Unicode 文本测试
    └── WrappedText.cpp      # 文本换行测试
```

## 关键文件

- **BUILD.gn**: 构建配置，定义了 `skia_enable_sktext` 开关，默认启用
- **editor/**: 完整的文本编辑器原型，支持光标、选择、鼠标交互
- **tests/**: 覆盖文本处理各环节的测试用例

## 构建条件

该模块仅在以下条件全部满足时才会编译：
- Unicode 支持已启用（`skia_use_icu` 或 `skia_use_libgrapheme` 或 `skia_use_icu4x`）
- `skia_enable_sktext = true`
- SkShaper 模块已启用（`skia_enable_skshaper = true`）
- HarfBuzz 已启用（`skia_use_harfbuzz = true`）

## 依赖关系

- `skia` 核心库
- `modules/skshaper` - 文本塑形模块
- `modules/skunicode` - Unicode 处理模块
- HarfBuzz - 文本塑形引擎
- ICU / libgrapheme / icu4x - Unicode 支持库

## 相关文档与参考

- SkParagraph 模块: `modules/skparagraph/`（生产级文本排版）
- SkShaper 模块: `modules/skshaper/`
- Skia 文本渲染架构: `docs/architecture/CPU.md` 中的文本渲染章节
