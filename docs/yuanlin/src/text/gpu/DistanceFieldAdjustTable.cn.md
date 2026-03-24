# DistanceFieldAdjustTable - 距离场调整表

> 源文件: `src/text/gpu/DistanceFieldAdjustTable.h`, `src/text/gpu/DistanceFieldAdjustTable.cpp`

## 概述

DistanceFieldAdjustTable 为距离场文本（SDF Text）渲染提供 gamma 校正调整值。它预计算一张查找表，根据亮度值提供距离场阈值的调整量，使得 SDF 文本在不同背景颜色下都能获得视觉上正确的覆盖度。

该表解决了 mask gamma hack 在距离场文本中的等价问题：通过调整距离场的几何（而非调整覆盖值），实现与光栅文本一致的 gamma 校正效果。

## 架构位置

```
sktext::gpu 命名空间
  └── DistanceFieldAdjustTable (单例)
```

- **使用者**: SDFTSubRun 和 GPU 后端的 SDF 文本渲染管线
- **数据来源**: SkScalerContext 的 Gamma LUT

## 主要类与结构体

### DistanceFieldAdjustTable
**成员变量**:
- `fTable` (SkScalar*): 标准 gamma（SK_GAMMA_EXPONENT）的调整表
- `fGammaCorrectTable` (SkScalar*): gamma=1.0 的调整表

**常量**:
- `kDistanceAdjustLumShift = 5`: 亮度值右移位数，将 256 级亮度映射到 8 个桶

## 公共 API 函数

```cpp
static const DistanceFieldAdjustTable* Get();
```
获取全局单例（使用 SkNoDestructor 实现）。

```cpp
SkScalar getAdjustment(int lum, bool useGammaCorrectTable) const;
```
根据亮度值（0-255）和是否使用 gamma 校正表返回距离调整值。亮度值右移 5 位后作为索引。

## 内部实现细节

### 调整表构建（build_distance_adjust_table）
1. 使用 `SkScalerContext::GetGammaLUTSize/Data` 获取 gamma 查找表
2. 表的高度为 8 行（对应 8 个亮度桶），每行对应一个亮度级别
3. 对每行，找到覆盖度达到 0.5（~127.5）的位置
4. 计算该覆盖度对应的 smoothstep 近似反函数值 t
5. 将 t 转换为距离调整值 d = 2*AAFactor*t - AAFactor

### 原理说明
- 黑色文本（在白色背景上）: 覆盖度降低 -> 文本变细 -> 距离调整为正
- 白色文本（在黑色背景上）: 覆盖度增加 -> 文本加粗 -> 距离调整为负
- 中灰文本: 无调整

### 构造函数
构建两张表：
- `fTable`: 使用 `SK_GAMMA_EXPONENT`（设备 gamma 指数）
- `fGammaCorrectTable`: 使用 `SK_Scalar1`（线性 gamma）

## 依赖关系

- `SkScalerContext` — 提供 Gamma LUT 数据
- `SkNoDestructor` — 全局单例存储
- `SK_GAMMA_CONTRAST` / `SK_GAMMA_EXPONENT` — Gamma 配置宏

## 设计模式与设计决策

1. **单例模式**: 使用 `SkNoDestructor` 确保全局唯一且永不销毁
2. **预计算**: 表在首次访问时构建一次，后续直接查表
3. **亮度分桶**: 8 个桶（256>>5）是精度和内存的折中

## 性能考量

- 运行时仅需一次位移和数组访问，O(1) 复杂度
- 表仅构建一次，8 个 SkScalar 的内存开销极小
- SK_DistanceFieldAAFactor = 0.65f 是经验值，与 smoothstep 反函数匹配

## 相关文件

- `src/core/SkScalerContext.h` — Gamma LUT 提供者
- `src/text/gpu/SubRunContainer.cpp` — SDFTSubRun 使用此表
- `src/core/SkDistanceFieldGen.h` — 距离场生成
