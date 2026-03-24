# third_party/icu - ICU 国际化组件

## 概述

`third_party/icu/` 包含 ICU（International Components for Unicode）库的
Skia 构建配置。ICU 是业界标准的 Unicode 和国际化支持库，Skia 使用它提供
Unicode 文本处理、文本分段、双向文本支持等功能。

## 目录结构

```
icu/
├── BUILD.gn             # GN 构建配置
├── config/              # ICU 配置文件
├── icu.gni              # GN 导入配置
├── make_data_cpp.py     # ICU 数据文件生成脚本
├── SkLoadICU.cpp        # Skia ICU 加载实现
└── SkLoadICU.h          # Skia ICU 加载头文件
```

## 关键文件

- **BUILD.gn**: ICU 的 Skia 构建配置，通过 `skia_use_icu` 开关控制
- **icu.gni**: ICU 相关的 GN 配置变量
- **SkLoadICU.cpp/h**: Skia 专用的 ICU 初始化代码，处理 ICU 数据文件的加载
- **make_data_cpp.py**: 将 ICU 数据文件转换为 C++ 数组

## 依赖关系

- ICU 源码（通过 DEPS 拉取）

## 相关文档与参考

- ICU 官网: https://icu.unicode.org/
- ICU4X 替代: `third_party/icu4x/`
- ICU BiDi: `third_party/icu_bidi/`
- Skia Unicode 模块: `modules/skunicode/`
