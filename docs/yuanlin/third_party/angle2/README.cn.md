# third_party/angle2 - ANGLE OpenGL ES 实现

## 概述

`third_party/angle2/` 包含 ANGLE（Almost Native Graphics Layer Engine）的
Skia 构建配置。ANGLE 将 OpenGL ES API 翻译为各平台的原生图形 API
（Direct3D、Vulkan、Metal），使 Skia 的 OpenGL ES 后端可以在不原生支持
OpenGL 的平台上运行。

## 目录结构

```
angle2/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 ANGLE 的编译选项和后端选择

## 依赖关系

- ANGLE 源码（通过 DEPS 拉取）
- 平台图形 API（Direct3D、Vulkan 或 Metal）

## 相关文档与参考

- ANGLE: https://chromium.googlesource.com/angle/angle
- Skia GL 后端: `src/gpu/ganesh/gl/`
- Skia ANGLE 集成: `include/gpu/ganesh/gl/`
