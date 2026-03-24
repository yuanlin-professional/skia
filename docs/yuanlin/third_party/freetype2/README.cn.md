# third_party/freetype2 - FreeType 字体引擎

## 概述

`third_party/freetype2/` 包含 FreeType 字体渲染引擎的 Skia 构建配置和
自定义头文件。FreeType 是一个广泛使用的开源字体引擎，Skia 使用它来加载
和渲染 TrueType、OpenType 等字体格式。

## 目录结构

```
freetype2/
├── BUILD.gn                 # GN 构建配置
├── roll-freetype.sh         # FreeType 版本更新脚本
└── include/                 # 自定义配置头文件
    ├── freetype-android/    # Android 平台配置
    ├── freetype-no-type1/   # 禁用 Type1 字体配置
    └── README.md            # 配置说明
```

## 关键文件

- **BUILD.gn**: FreeType 的 Skia 定制构建配置，包括平台特定选项
- **roll-freetype.sh**: 用于更新 FreeType 版本的自动化脚本
- **include/**: 不同平台和配置的 FreeType 头文件覆盖

## 依赖关系

- FreeType 源码（通过 DEPS 拉取）
- libpng（嵌入式 PNG 字形支持，可选）
- zlib（压缩字体数据解压）

## 相关文档与参考

- FreeType 官网: https://freetype.org/
- Skia 字体移植层: `src/ports/` (SkFontHost_FreeType.cpp)
- Fontations 替代: `src/ports/fontations/`
