# filterfuzz - 滤镜模糊测试工具

## 概述

`experimental/filterfuzz/` 包含一个用于 Skia 图像滤镜的模糊测试（fuzzing）
工具框架。该工具旨在通过随机生成的输入来测试 Skia 滤镜的健壮性和稳定性。

## 目录结构

```
filterfuzz/
└── filterfuzz.cpp          # 模糊测试工具主程序
```

## 关键文件

- **filterfuzz.cpp**: 初始化 Skia 图形系统（`SkGraphics::Init()`），解析
  命令行参数，并执行滤镜的模糊测试。使用 Skia 标准的 `CommandLineFlags` 进行
  参数处理。

## 依赖关系

- Skia 核心库（`SkGraphics`）
- Skia 工具库（`CommandLineFlags`）

## 相关文档与参考

- Skia 图像滤镜: `include/effects/`
- Skia 模糊测试基础设施: `fuzz/`
