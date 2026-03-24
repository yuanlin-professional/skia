# third_party/harfbuzz - HarfBuzz 文本塑形引擎

## 概述

`third_party/harfbuzz/` 包含 HarfBuzz 文本塑形引擎的 Skia 构建配置。
HarfBuzz 是业界标准的 OpenType 文本塑形引擎，负责将 Unicode 文本转换为
正确排列的字形序列，处理连字、字距调整、复杂文字排版等。

## 目录结构

```
harfbuzz/
├── BUILD.gn                 # GN 构建配置
├── config-override.h        # Skia 定制配置
├── LICENSE                  # 许可证
├── README                   # 说明文档
└── roll-harfbuzz.sh         # 版本更新脚本
```

## 关键文件

- **BUILD.gn**: HarfBuzz 的 Skia 构建配置，通过 `skia_use_harfbuzz` 开关控制
- **config-override.h**: Skia 特定的 HarfBuzz 配置覆盖
- **roll-harfbuzz.sh**: 自动更新 HarfBuzz 到新版本的脚本

## 依赖关系

- HarfBuzz 源码（通过 DEPS 拉取）
- FreeType（字体加载后端）
- ICU（Unicode 数据，可选）

## 相关文档与参考

- HarfBuzz: https://harfbuzz.github.io/
- Skia SkShaper 模块: `modules/skshaper/`
- Skia 文本渲染: `src/text/`
