# skcms/src - 色彩管理系统内部实现

## 概述

`modules/skcms/src/` 目录包含 skcms 色彩管理系统的内部实现文件。这里的代码分为三个层次:公共 API 定义 (`skcms_public.h`)、内部共享工具 (`skcms_internals.h`) 和性能关键的颜色转换管线 (`Transform_inl.h` 及其平台特化实现)。

颜色转换管线是整个 skcms 的性能核心。`Transform_inl.h` 作为模板头文件被三个不同的编译单元包含:基线实现 (`skcms_TransformBaseline.cc`)、Haswell AVX2 实现 (`skcms_TransformHsw.cc`) 和 Skylake-X AVX-512 实现 (`skcms_TransformSkx.cc`)。每个编译单元使用各自的编译器标志来生成不同指令集的优化代码。

`skcms_internals.h` 定义了 ICC 标签结构 (`skcms_ICCTag`)、标签查找函数以及可移植数学函数。该头文件仅供 skcms 内部和测试工具使用,不属于公共 API。

## 目录结构

```
src/
+-- skcms_public.h            # 完整公共 API (C 接口, ~495 行)
+-- skcms_internals.h         # 内部共享 API (标签操作/数学函数)
+-- skcms_Transform.h         # Transform 管线内部分派接口
+-- Transform_inl.h           # Transform 核心逻辑模板
+-- skcms_TransformBaseline.cc # 基线实现 (通用 CPU)
+-- skcms_TransformHsw.cc     # Haswell AVX2 优化实现
+-- skcms_TransformSkx.cc     # Skylake-X AVX-512 优化实现
```

## 关键类与函数

| 文件 | 核心内容 |
|------|---------|
| `skcms_public.h` | 全部公共 API: skcms_Transform, skcms_Parse, 传递函数, 像素格式枚举 |
| `skcms_internals.h` | `skcms_ICCTag` 结构体, `skcms_GetTagBySignature()`, 可移植数学 (`powf_`, `floorf_`) |
| `skcms_Transform.h` | Transform 管线的内部函数声明和分派逻辑 |
| `Transform_inl.h` | 像素解包/打包, 传递函数应用, 矩阵变换, CLUT 查表 |

## 设计模式分析

- **模板方法 (Template Method)**: `Transform_inl.h` 定义了转换管线的骨架算法,由不同编译单元的 SIMD 内在函数提供具体实现。
- **编译期策略选择**: 通过预处理器宏 (`SKCMS_DISABLE_HSW`, `SKCMS_DISABLE_SKX`) 和 `[[clang::musttail]]` 属性控制代码生成策略。

## 相关文档与参考

- skcms 公共 API: `modules/skcms/skcms.h`
- ICC 配置文件解析: `modules/skcms/skcms.cc`
