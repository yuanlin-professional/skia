# GrTestUtils

> 源文件: src/gpu/ganesh/GrTestUtils.h, src/gpu/ganesh/GrTestUtils.cpp

## 概述

`GrTestUtils` 是 Ganesh GPU 后端的测试工具模块，提供了一套用于单元测试和随机化测试的辅助函数和类。该模块通过预定义的测试数据集（矩阵、路径、颜色等）和随机生成器，帮助开发者创建可重复、覆盖面广的 GPU 相关测试用例。

所有代码都被 `#if defined(GPU_TEST_UTILS)` 宏保护，只在测试构建中编译。该模块封装在 `GrTest` 命名空间下，包含了从基础几何图形到复杂路径效果的各种测试数据生成器，是 Ganesh GPU 后端质量保障的重要组成部分。

## 架构位置

`GrTestUtils` 位于 Ganesh GPU 后端的测试基础设施层：

- **使用场景**: 单元测试、fuzzing、随机化测试、GPU processor 测试
- **服务对象**: `GrFragmentProcessor`、`GrGeometryProcessor`、各种 GPU effects 的测试
- **测试框架**: 与 `GrProcessorUnitTest` 配合使用
- **独立性**: 仅在测试构建中可用，不影响生产代码

该模块为测试代码提供了统一的随机数据生成接口，确保测试的可重复性和覆盖率。

## 主要类与结构体

### GrTest 命名空间函数

所有函数都是命名空间级别的工具函数，无继承关系。

### TestAsFPArgs 类

**用途**: 为 fragment processor 测试提供参数封装

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorInfoStorage` | `std::unique_ptr<GrColorInfo>` | 颜色信息存储 |
| `fSurfaceProps` | `SkSurfaceProps` | Surface 属性 |
| `fArgs` | `GrFPArgs` | Fragment processor 参数 |

**公共接口:**
```cpp
TestAsFPArgs(GrProcessorTestData*);
~TestAsFPArgs();
const GrFPArgs& args() const;
```

### TestDashPathEffect 类

**用途**: 简化的虚线路径效果（避免依赖可选的 effects 模块）

**继承关系:**
- 基类: `SkPathEffectBase`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fIntervals` | `skia_private::AutoTArray<SkScalar>` | 虚线间隔数组 |
| `fPhase` | `SkScalar` | 虚线相位 |
| `fInitialDashLength` | `SkScalar` | 初始虚线长度 |
| `fInitialDashIndex` | `size_t` | 初始虚线索引 |
| `fIntervalLength` | `SkScalar` | 间隔总长度 |

**公共接口:**
```cpp
static sk_sp<SkPathEffect> Make(SkSpan<const SkScalar> intervals, SkScalar phase);
```

## 公共 API 函数

### 矩阵生成函数

```cpp
const SkMatrix& TestMatrix(SkRandom*)
// 返回随机矩阵（包括透视矩阵）

const SkMatrix& TestMatrixPreservesRightAngles(SkRandom*)
// 返回保持直角的矩阵（identity、translation、scale、orthogonal rotation）

const SkMatrix& TestMatrixRectStaysRect(SkRandom*)
// 返回保持矩形性质的矩阵（不包括斜切和一般旋转）

const SkMatrix& TestMatrixInvertible(SkRandom*)
// 返回可逆矩阵（非透视）

const SkMatrix& TestMatrixPerspective(SkRandom*)
// 返回透视矩阵
```

### 几何图形生成函数

```cpp
const SkRect& TestRect(SkRandom*)
// 返回预定义的测试矩形（包括极端尺寸）

const SkRect& TestSquare(SkRandom*)
// 返回简单的正方形（用于需要规范输入的测试）

const SkRRect& TestRRectSimple(SkRandom*)
// 返回简单的圆角矩形

const SkPath& TestPath(SkRandom*)
// 返回各种路径（直线、二次曲线、圆锥曲线、三次曲线）

const SkPath& TestPathConvex(SkRandom*)
// 返回凸多边形路径
```

### 样式和属性生成函数

```cpp
SkStrokeRec TestStrokeRec(SkRandom*)
// 返回随机描边记录

void TestStyle(SkRandom*, GrStyle*)
// 生成随机样式（包括虚线路径效果）

void TestWrapModes(SkRandom*, GrSamplerState::WrapMode[2])
// 生成随机纹理环绕模式

sk_sp<SkColorSpace> TestColorSpace(SkRandom*)
// 返回测试色彩空间（nullptr、sRGB、color-spin sRGB）

sk_sp<GrColorSpaceXform> TestColorXform(SkRandom*)
// 返回色彩空间变换
```

### 颜色生成函数

```cpp
GrColor RandomColor(SkRandom* random)
// 生成随机颜色（全1、全0、alpha=1、完全随机）

uint8_t RandomCoverage(SkRandom* random)
// 生成随机覆盖率（0、255、随机）
```

## 内部实现细节

### 静态数据缓存策略

所有生成函数都使用静态局部变量缓存预定义数据：

```cpp
static SkMatrix gMatrices[5];
static bool gOnce;
if (!gOnce) {
    gOnce = true;
    // 初始化数据
}
return gMatrices[random->nextULessThan(count)];
```

**优势:**
- 只初始化一次，提高性能
- 数据一致性保证
- 线程安全（通过 `SkOnce` 实现）

### 矩阵测试集

#### TestMatrix 集合
包含 5 个矩阵：
1. Identity（单位矩阵）
2. Translation（平移）
3. Rotation 17°（旋转）
4. Complex（旋转 + 平移 + 缩放）
5. Perspective（透视矩阵）

#### TestMatrixPreservesRightAngles 集合
包含 5 个矩阵，都满足 `preservesRightAngles()`：
- Identity
- Translation
- Uniform scale
- Non-uniform scale + translation
- Orthogonal rotation（正交旋转）

#### TestMatrixRectStaysRect 集合
包含 6 个矩阵，都满足 `rectStaysRect()`：
- Identity
- Translation
- Scale
- Scale + translation
- Reflection（反射）
- 90° rotation

### 路径测试集

`TestPath()` 提供 7 种路径：
1. **Line**: 直线段
2. **Quad**: 二次贝塞尔曲线
3. **Conic**: 圆锥曲线
4. **Cubic**: 三次贝塞尔曲线
5. **Mixed**: 包含所有类型
6. **Convex**: 凸多边形（正方形）
7. **Concave**: 凹多边形

`TestPathConvex()` 提供 3 种凸路径：
1. **Narrow rect**: 窄矩形（测试极端宽高比）
2. **Degenerate**: 退化路径（极小尺寸）
3. **Clipped triangle**: 剪裁三角形

### 矩形测试集

`TestRect()` 提供 7 种矩形：
- 1x1 小矩形
- 1x256 窄高矩形
- 256x1 宽扁矩形
- Largest（最大矩形）
- 大范围矩形（-65535 到 65535）
- 普通矩形（-10 到 10）

### 颜色生成策略

`RandomColor()` 使用枚举控制颜色模式：
- **kAllOnes_ColorMode**: 0xFFFFFFFF（全白不透明）
- **kAllZeros_ColorMode**: 0x00000000（全透明）
- **kAlphaOne_ColorMode**: RGB 随机，alpha=0xFF
- **kRandom_ColorMode**: 预乘 alpha（RGB <= alpha）

这些模式覆盖了常见的边界情况和随机情况。

### TestDashPathEffect 实现

虚线路径效果的简化实现：
```cpp
TestDashPathEffect::TestDashPathEffect(SkSpan<const SkScalar> intervals, SkScalar phase) {
    fIntervals.reset(intervals.size());
    memcpy(fIntervals.get(), intervals.data(), intervals.size_bytes());
    SkDashPath::CalcDashParameters(phase, fIntervals, &fInitialDashLength,
                                   &fInitialDashIndex, &fIntervalLength, &fPhase);
}
```

使用 `SkDashPath` 的内部工具函数计算虚线参数。

### TestStyle 实现

随机生成 `GrStyle`：
1. 随机初始化 `SkStrokeRec`
2. 50% 概率添加虚线路径效果：
   - 随机生成间隔数组（1-50 对间隔）
   - 间隔值范围: 0.01 到 10.0
   - 随机相位
3. 组合成 `GrStyle`

### 色彩空间生成

使用 `SkOnce` 确保单次初始化：
```cpp
static SkColorSpace* gColorSpaces[3];
static SkOnce once;
once([] {
    gColorSpaces[0] = nullptr;  // legacy mode
    gColorSpaces[1] = SkColorSpace::MakeSRGB().release();
    gColorSpaces[2] = SkColorSpace::MakeSRGB()->makeColorSpin().release();
});
```

返回的是静态指针，避免重复创建。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkRandom` | 随机数生成 |
| `SkMatrix` | 矩阵测试数据 |
| `SkPath` / `SkPathBuilder` | 路径测试数据 |
| `SkColorSpace` | 色彩空间 |
| `GrColorSpaceXform` | 色彩空间变换 |
| `GrStyle` | 样式测试 |
| `GrProcessorTestData` | Processor 测试数据 |
| `SkDashPath` | 虚线路径计算 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrFragmentProcessor` 测试 | 使用 `TestAsFPArgs` |
| `GrGeometryProcessor` 测试 | 使用各种测试数据生成器 |
| GPU effect 测试 | 使用随机矩阵、路径、颜色 |
| Fuzzing 测试 | 使用随机生成函数 |
| 单元测试 | 使用预定义测试数据 |

## 设计模式与设计决策

### 静态数据池模式

所有测试数据都预先定义并缓存：
- **优势**: 快速访问、数据一致性、可重复性
- **实现**: 静态数组 + `gOnce` 标志
- **线程安全**: 使用 `SkOnce` 保证单次初始化

### 随机选择 vs 随机生成

采用"随机选择预定义数据"而非"完全随机生成"：
- **优势**: 数据质量可控、边界情况覆盖、调试友好
- **适用性**: 适合单元测试，不适合 fuzzing（fuzzing 需要更随机的数据）

### 命名空间封装

使用 `GrTest` 命名空间：
- 避免全局命名冲突
- 清晰表明测试专用
- 易于条件编译（`#if defined(GPU_TEST_UTILS)`）

### TestDashPathEffect 的简化实现

不依赖 `SkDashPathEffect`（在可选模块 effects 中）：
- **原因**: 测试代码不应依赖可选模块
- **实现**: 直接使用 `SkDashPath` 的内部函数
- **限制**: 返回 nullptr 作为 factory 和 typeName（测试中不需要）

### TestAsFPArgs 的 RAII 设计

封装 `GrFPArgs` 的构造：
- 自动管理 `GrColorInfo` 的生命周期
- 提供统一的测试参数创建接口
- 避免测试代码中的重复初始化

### 边界情况优先

测试数据集优先包含边界情况：
- 极端尺寸（1x256、最大矩形）
- 特殊值（identity、0、255）
- 退化情况（极小路径）

## 性能考量

### 静态数据缓存

**收益:**
- 避免每次测试重新创建数据
- 减少内存分配
- 提高测试执行速度

**代价:**
- 增加少量静态内存占用
- 只在测试构建中存在，不影响生产代码

### SkOnce 的使用

```cpp
static SkOnce once;
once([] { /* 初始化 */ });
```

**优势:**
- 线程安全的单次初始化
- 无需手动加锁
- 编译器优化友好

**实现**: 使用低级原子操作，性能接近手写双检锁。

### 数据集大小权衡

大多数测试集包含 5-7 个元素：
- **足够覆盖**: 涵盖主要情况和边界
- **不过大**: 避免测试时间过长
- **可管理**: 调试时易于理解

### 随机数生成效率

使用 `SkRandom` 的快速方法：
- `nextULessThan()`: O(1) 模运算
- `nextRangeScalar()`: 简单线性映射
- 避免复杂的分布计算

### TestDashPathEffect 的性能

**优化点:**
- 使用 `AutoTArray` 避免多次分配
- `memcpy` 批量复制间隔数据
- 预计算虚线参数（`CalcDashParameters`）

**适用性**: 测试用途，性能要求不高。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrProcessorUnitTest.h` | 测试框架 | Processor 单元测试基础设施 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 被测试对象 | Fragment processor |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 被测试对象 | Geometry processor |
| `src/base/SkRandom.h` | 依赖 | 随机数生成器 |
| `include/core/SkMatrix.h` | 测试数据 | 矩阵类型 |
| `include/core/SkPath.h` | 测试数据 | 路径类型 |
| `src/gpu/ganesh/GrStyle.h` | 测试数据 | 样式类型 |
| `src/gpu/ganesh/GrColorSpaceXform.h` | 测试数据 | 色彩空间变换 |
| `src/utils/SkDashPathPriv.h` | 依赖 | 虚线路径内部函数 |
| `src/gpu/ganesh/GrColor.h` | 依赖 | 颜色打包函数 |
