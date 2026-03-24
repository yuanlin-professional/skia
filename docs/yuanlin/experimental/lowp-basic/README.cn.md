# lowp-basic - 低精度图形渲染实验

## 概述

`experimental/lowp-basic/` 包含低精度（low-precision）图形渲染的实验代码。
这些实验探索在降低数值精度的情况下进行图形计算，以期获得更好的性能表现，
特别适用于低功耗设备和特定的 SIMD 优化场景。

## 目录结构

```
lowp-basic/
├── CMakeLists.txt           # CMake 构建配置
├── lowp_experiments.cpp     # 低精度渲染实验主程序
├── QMath.h                  # 量化数学工具头文件
├── lerp-study.cpp           # 线性插值（lerp）研究
└── bilerp-study.cpp         # 双线性插值（bilerp）研究
```

## 关键文件

- **lowp_experiments.cpp**: 低精度图形管线的核心实验，编译为 `lowp` 可执行文件
- **QMath.h**: 量化数学库，提供低精度计算的基础工具
- **lerp-study.cpp**: 研究低精度下线性插值的精度和性能特性
- **bilerp-study.cpp**: 研究低精度下双线性插值的精度和性能特性

## 构建方式

使用独立的 CMake 构建系统（不依赖 Skia 主构建）：
```bash
$ cd experimental/lowp-basic
$ cmake -B build
$ cmake --build build
```

生成三个可执行文件：`lowp`、`lerp`、`bilerp`。

## 依赖关系

- CMake 3.20+
- C++17 标准编译器
- 无外部库依赖（独立实验）

## 相关文档与参考

- Skia 光栅管线: `src/opts/`（SIMD 优化实现）
- SkRasterPipeline: `src/core/SkRasterPipeline.h`
