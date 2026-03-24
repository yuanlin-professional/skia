# FuzzPathop

> 源文件: fuzz/oss_fuzz/FuzzPathop.cpp

## 概述

`FuzzPathop.cpp` 是 Skia 中用于模糊测试路径操作(Path Operations)的工具。该模块通过 OSS-Fuzz 框架对路径布尔运算(union, intersect, difference, xor)和路径简化等操作进行自动化安全测试,验证在处理复杂和边界条件路径时的稳定性。路径操作是计算几何中的核心功能,对于 SVG 渲染、矢量图形处理和裁剪等场景至关重要。

## 架构位置

- **路径**: `fuzz/oss_fuzz/FuzzPathop.cpp`
- **模块层次**: 测试工具层 > 模糊测试子系统 > OSS-Fuzz 集成
- **测试目标**: Skia 路径操作引擎(Pathops)

## 主要类与结构体

### 核心函数

#### `fuzz_Pathop`
```cpp
void fuzz_Pathop(Fuzz* f);
```
**功能**: 执行路径操作的模糊测试(外部定义)
**职责**:
- 生成随机路径数据
- 选择随机的路径操作类型
- 执行操作并验证稳定性

#### `LLVMFuzzerTestOneInput`
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
```
**功能**: LibFuzzer 入口点,输入限制 4000 字节

## 公共 API 函数

使用的 Skia Pathops API:
- `Op(const SkPath&, const SkPath&, SkPathOp, SkPath*)`: 路径布尔运算
- `Simplify(const SkPath&, SkPath*)`: 路径简化
- `AsWinding(const SkPath&, SkPath*)`: 转换填充规则
- `TightBounds(const SkPath&, SkRect*)`: 精确边界计算

路径操作类型:
- `kUnion_SkPathOp`: 并集
- `kIntersect_SkPathOp`: 交集
- `kDifference_SkPathOp`: 差集
- `kXOR_SkPathOp`: 异或
- `kReverseDifference_SkPathOp`: 反向差集

## 内部实现细节

### 测试流程
```
输入数据 → Fuzz 对象
  → 生成两个随机路径
  → 选择随机路径操作类型
  → 执行 Op() 或其他操作
  → 验证输出路径有效性
```

### 路径操作的复杂性

**挑战**:
- 处理自相交路径
- 处理退化情况(点、线段)
- 复杂的拓扑关系
- 浮点数精度问题

**测试重点**:
- 边界条件(空路径、单点路径)
- 复杂路径(多个轮廓、自相交)
- 数值稳定性

## 依赖关系

**Pathops 模块**:
- `include/pathops/SkPathOps.h`: 路径操作公共接口
- `src/pathops/`: 路径操作实现(复杂的几何算法)

**核心模块**:
- `include/core/SkPath.h`: 路径数据结构
- `fuzz/Fuzz.h`: 模糊测试框架

## 设计模式与设计决策

### 1. 双路径测试模式

**典型测试场景**:
```cpp
Op(path1, path2, kUnion_SkPathOp, &result);
```
需要生成两个独立的路径,测试它们的组合操作。

### 2. 操作类型枚举

通过随机选择不同的 `SkPathOp`,覆盖所有布尔运算类型。

## 性能考量

### 1. 路径操作的计算复杂度

**算法复杂度**:
- 通常为 O(n log n) 到 O(n²)
- 取决于路径复杂度和相交点数量

**输入大小限制**: 4000 字节控制路径复杂度,避免超时

### 2. 数值精度问题

路径操作涉及大量浮点数运算,需要处理:
- 舍入误差
- 退化情况
- 数值不稳定性

## 相关文件

### 核心依赖

1. **`include/pathops/SkPathOps.h`**
   - 路径操作公共接口

2. **`src/pathops/SkOpBuilder.cpp`**
   - 路径操作构建器实现

3. **`src/pathops/SkPathOpsCommon.cpp`**
   - 路径操作通用算法

### 同类型测试器

4. **`fuzz/oss_fuzz/FuzzParsePath.cpp`**
   - 测试路径解析

5. **`fuzz/oss_fuzz/FuzzCanvas.cpp`**
   - 测试路径绘制

### 测试文件

6. **`tests/PathOpsTest.cpp`**
   - 路径操作的单元测试

7. **`gm/pathops.cpp`**
   - 路径操作的视觉测试

8. **`fuzz/fuzz_pathops.cpp`**: 包含 `fuzz_Pathop` 实现

该模糊测试器为 Skia 的路径操作引擎提供了全面的安全性测试,确保在处理复杂几何运算时的稳定性和正确性,是矢量图形处理质量保证的关键组件。
