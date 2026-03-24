# Skia skdiff 图像差异比较工具

## 概述

`tools/skdiff` 是 Skia 的图像差异比较工具。给定两个目录（基准目录和对比目录），它会找到同名的图像文件并逐像素比较差异，生成差异图像和 HTML 报告。这是 Skia 质量保证流程中的核心工具，用于检测渲染回归、验证平台一致性、以及审查视觉变更。

## 目录结构

```
tools/skdiff/
├── BUILD.bazel       # Bazel 构建配置
├── skdiff.h          # 核心数据结构（DiffResource、DiffRecord）和比较算法
├── skdiff.cpp        # 差异计算实现（compute_diff）
├── skdiff_main.cpp   # 命令行主程序入口
├── skdiff_html.h     # HTML 报告生成器声明
├── skdiff_html.cpp   # HTML 报告生成器实现
├── skdiff_utils.h    # 工具函数声明（图像读取、解码）
└── skdiff_utils.cpp  # 工具函数实现
```

## 核心数据结构

### DiffResource

表示参与比较的单个图像资源，包含状态追踪：

```
状态层级（从最完整到最不完整）：
kDecoded_Status      -> 已指定、存在、已读取、已解码
kCouldNotDecode_Status -> 已指定、存在、已读取、但无法解码
kRead_Status         -> 已指定、存在、已读取
kCouldNotRead_Status -> 已指定、存在、但无法读取
kExists_Status       -> 已指定、存在
kDoesNotExist_Status -> 已指定、但不存在
kSpecified_Status    -> 已指定
kUnspecified_Status  -> 未指定
```

### DiffRecord

存储一对图像的完整比较结果：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fBase` | `DiffResource` | 基准图像 |
| `fComparison` | `DiffResource` | 对比图像 |
| `fDifference` | `DiffResource` | 生成的差异图像 |
| `fWhite` | `DiffResource` | 白底差异图像 |
| `fFractionDifference` | `float` | 不同像素的比例 |
| `fWeightedFraction` | `float` | 加权差异度 |
| `fMaxMismatch{R,G,B}` | `uint32_t` | 各通道最大差异值 |
| `fAverageMismatch{R,G,B}` | `float` | 各通道平均差异值 |
| `fResult` | `Result` | 比较结果分类 |

### 比较结果分类

```
kEqualBits_Result        -> 二进制完全相同
kEqualPixels_Result      -> 像素值相同（编码可能不同）
kDifferentPixels_Result  -> 像素值不同
kDifferentSizes_Result   -> 图像尺寸不同
kCouldNotCompare_Result  -> 无法进行比较
```

## 差异计算

### 像素级比较

`compute_diff_pmcolor()` 函数计算两个像素的差异：

```cpp
// 对每个颜色通道取绝对差值
dr = |R0 - R1|, dg = |G0 - G1|, db = |B0 - B1|
result = SkPackARGB32(0xFF, dr, dg, db)
```

### 排序算法

提供多种排序策略用于报告生成：

- **CompareDiffMetrics**: 按不同像素比例排序（最大到最小）
- **CompareDiffWeighted**: 按加权差异度排序
- **CompareDiffMeanMismatches**: 按平均 RGB 差异排序
- **CompareDiffMaxMismatches**: 按最大 RGB 差异排序

## 命令行用法

```bash
# 基本用法：比较两个目录，输出差异到第三个目录
skdiff baseDir comparisonDir diffDir

# 递归比较（默认行为）
skdiff --norecurse baseDir comparisonDir diffDir

# 指定颜色阈值
skdiff --threshold 10 baseDir comparisonDir diffDir
```

## HTML 报告

`skdiff_html.cpp` 生成交互式 HTML 报告（`index.html`），包含：

- 按差异程度排序的图像对列表
- 基准图像、对比图像和差异图像的并排展示
- 统计摘要（总文件数、匹配数、差异数、错误数）
- 支持按状态过滤查看

## 构建

```bash
# Bazel 构建
bazel build //tools/skdiff:skdiff

# GN 构建
ninja -C out/Release skdiff
```

## 与其他模块的关系

- **dm（DM 测试工具）**: DM 生成的渲染结果可通过 skdiff 进行回归比较
- **Gold（skia.org/infra/gold）**: 线上图像比较系统，skdiff 是其离线替代方案
- **tools/skp/**: SKP 回放结果的视觉比较
