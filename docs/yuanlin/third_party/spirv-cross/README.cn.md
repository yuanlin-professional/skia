# third_party/spirv-cross - SPIR-V 着色器转译器

## 概述

`third_party/spirv-cross/` 包含 SPIRV-Cross 着色器转译器的 Skia 构建配置。
SPIRV-Cross 将 SPIR-V 中间表示翻译为各平台的着色器语言（GLSL、HLSL、MSL），
是 Skia GPU 后端跨平台着色器支持的关键组件。

## 目录结构

```
spirv-cross/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 SPIRV-Cross 的编译选项和目标语言支持

## 依赖关系

- SPIRV-Cross 源码（通过 DEPS 拉取）

## 相关文档与参考

- SPIRV-Cross: https://github.com/KhronosGroup/SPIRV-Cross
- SPIR-V 规范: https://www.khronos.org/spir/
- Skia SkSL 编译器: `src/sksl/`
