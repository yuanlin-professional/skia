# GrStyle

> 源文件
> - src/gpu/ganesh/GrStyle.h
> - src/gpu/ganesh/GrStyle.cpp

## 概述

`GrStyle` 是 Ganesh GPU 后端中用于表示路径样式的核心类，封装了填充（fill）、描边（stroke）以及路径效果（path effect）等绘制样式信息。它是 `GrStyledShape` 系统的关键组成部分，负责将 Skia 的高级样式表示（`SkPaint`、`SkStrokeRec`、`SkPathEffect`）转换为 GPU 可以处理的形式。

该类特别处理了虚线（dashing）效果，将虚线信息从通用的路径效果中提取出来并单独存储，因为虚线是最常见的路径效果，且可以生成确定性的缓存键。这种设计使得 GPU 渲染管道能够更高效地处理样式化的几何图形。

## 架构位置

`GrStyle` 位于 Ganesh 渲染管道的几何处理层：

```
Skia 绘制流程
├── SkPaint (高级绘制样式)
│   ├── SkStrokeRec (描边记录)
│   └── SkPathEffect (路径效果)
│       └── GrStyle (GPU 样式表示)
│           └── GrStyledShape (样式化形状)
│               └── GrOp (GPU 操作)
```

`GrStyle` 作为样式系统的中间层，将 Skia 的样式表示转换为 GPU 友好的格式，同时提供样式应用和键生成功能。

## 主要类与结构体

### GrStyle

主类，表示完整的绘制样式。

**继承关系：**
- 无继承关系，值类型（value type）

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStrokeRec` | `SkStrokeRec` | 描边信息（宽度、连接方式、端点样式等） |
| `fPathEffect` | `sk_sp<SkPathEffect>` | 路径效果（如虚线、自定义效果） |
| `fDashInfo` | `DashInfo` | 提取的虚线信息 |

### DashInfo (私有结构体)

存储虚线效果的详细信息。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fType` | `DashType` | 虚线类型（kNone 或 kDash） |
| `fPhase` | `SkScalar` | 虚线起始相位 |
| `fIntervals` | `skia_private::AutoSTArray<4, SkScalar>` | 虚线间隔数组（开、关长度交替） |

### 枚举类型

#### Apply

```cpp
enum class Apply {
    kPathEffectOnly,           // 仅应用路径效果
    kPathEffectAndStrokeRec    // 应用路径效果和描边
};
```

#### KeyFlags

```cpp
enum KeyFlags {
    kClosed_KeyFlag = 0x1,   // 形状无开放轮廓
    kNoJoins_KeyFlag = 0x2    // 形状无连接点
};
```

## 公共 API 函数

### 静态工厂方法

#### SimpleFill

```cpp
static const GrStyle& SimpleFill()
```

返回简单填充样式的单例引用（无路径效果）。

#### SimpleHairline

```cpp
static const GrStyle& SimpleHairline()
```

返回简单细线描边样式的单例引用（无路径效果）。

### 构造函数

```cpp
GrStyle()  // 默认为填充样式
explicit GrStyle(SkStrokeRec::InitStyle initStyle)
GrStyle(const SkStrokeRec& strokeRec, sk_sp<SkPathEffect> pe)
explicit GrStyle(const SkPaint& paint)
GrStyle(const SkPaint& paint, SkPaint::Style overrideStyle)
```

支持从多种 Skia 类型构造样式对象。

### 样式查询

```cpp
bool isSimpleFill() const        // 是否为简单填充
bool isSimpleHairline() const    // 是否为简单细线
bool hasPathEffect() const       // 是否有路径效果
bool hasNonDashPathEffect() const // 是否有非虚线路径效果
bool isDashed() const            // 是否为虚线
bool applies() const             // 样式是否会改变几何形状
```

### 虚线信息访问

```cpp
SkScalar dashPhase() const
int dashIntervalCnt() const
const SkScalar* dashIntervals() const
```

### 样式应用

#### applyPathEffectToPath

```cpp
[[nodiscard]] bool applyPathEffectToPath(
    SkPath* dst,
    SkStrokeRec* remainingStroke,
    const SkPath& src,
    SkScalar scale) const
```

仅应用路径效果到路径，返回剩余的描边信息。

**参数：**
- `dst`: 输出路径
- `remainingStroke`: 应用路径效果后剩余的描边信息
- `src`: 输入路径
- `scale`: 缩放因子（通常从视图矩阵计算）

**返回值：** 成功返回 true，失败返回 false

#### applyToPath

```cpp
[[nodiscard]] bool applyToPath(
    SkPath* dst,
    SkStrokeRec::InitStyle* fillOrHairline,
    const SkPath& src,
    SkScalar scale) const
```

应用完整样式（路径效果 + 描边）到路径。

**返回值：**
- 成功返回 true，`fillOrHairline` 指示结果路径应如何渲染
- 失败返回 false（无样式需要应用）

### 边界调整

```cpp
void adjustBounds(SkRect* dst, const SkRect& src) const
```

根据样式计算应用样式后的边界框。考虑路径效果和描边膨胀。

### 键生成

#### KeySize

```cpp
static int KeySize(const GrStyle& style, Apply apply, uint32_t flags = 0)
```

计算样式键的长度（以 uint32_t 为单位）。返回负值表示无法生成键（存在非虚线的通用路径效果）。

#### WriteKey

```cpp
static void WriteKey(
    uint32_t* key,
    const GrStyle& style,
    Apply apply,
    SkScalar scale,
    uint32_t flags = 0)
```

将样式信息写入键缓冲区，用于缓存和去重。

**键的组成：**
1. 如果是虚线：缩放因子 + 虚线相位 + 虚线间隔数组
2. 如果需要描边：缩放因子 + 样式/连接/端点 + 斜接限制 + 宽度

## 内部实现细节

### 虚线检测与提取

`initPathEffect` 方法负责检测和提取虚线信息：

```cpp
void GrStyle::initPathEffect(sk_sp<SkPathEffect> pe) {
    if (!pe) return;
    if (auto info = as_PEB(pe)->asADash()) {
        // 检查描边样式是否兼容
        if (recStyle != SkStrokeRec::kFill_Style &&
            recStyle != SkStrokeRec::kStrokeAndFill_Style) {
            fDashInfo.fType = DashType::kDash;
            // 复制虚线间隔和相位
            fDashInfo.fIntervals.reset(info->fIntervals.size());
            memcpy(...);
            fDashInfo.fPhase = info->fPhase;
            fPathEffect = std::move(pe);
        }
    } else {
        fPathEffect = std::move(pe);
    }
}
```

### 虚线应用

对于虚线效果，`applyPathEffect` 使用 `SkDashPath` 手动应用而非通用路径效果：

```cpp
if (DashType::kDash == fDashInfo.fType) {
    // 计算虚线参数
    SkDashPath::CalcDashParameters(phase, intervals,
                                    &initialLength, &initialIndex, &intervalLength);
    // 应用虚线，禁止自动应用描边
    SkDashPath::InternalFilter(&builder, src, strokeRec, nullptr, intervals,
                                initialLength, initialIndex, intervalLength, phase,
                                SkDashPath::StrokeRecApplication::kDisallow);
}
```

这种设计确保了虚线应用与描边应用的分离，满足键生成的需求。

### 键生成策略

键的生成采用紧凑的位打包策略：

```cpp
// 描边键格式（伪代码）
key[i++] = scale;
key[i++] = (style << 0) | (join << kJoinShift) | (cap << kCapShift);
key[i++] = miterLimit;
key[i++] = width;
```

**优化点：**
1. 根据 `KeyFlags` 排除不相关的信息（如封闭形状不需要端点样式）
2. 虚线键和描边键可以独立生成并连接
3. 使用 memcpy 直接复制浮点数值，保证位级精确性

### 缩放因子

`MatrixToScaleFactor` 从变换矩阵提取缩放因子：

```cpp
static SkScalar MatrixToScaleFactor(const SkMatrix& matrix) {
    // getMaxScale 对于透视矩阵返回 -1，此时使用 1.0
    return SkScalarAbs(matrix.getMaxScale());
}
```

缩放因子用于：
- 路径效果的几何近似（如虚线段长度）
- 描边宽度的计算

## 依赖关系

### 依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| `SkStrokeRec` | 组合 | 存储描边信息 |
| `SkPathEffect` | 组合 | 存储路径效果 |
| `SkPaint` | 输入 | 从 Paint 构造样式 |
| `SkPath` | 操作对象 | 样式应用的目标 |
| `SkDashPath` | 使用 | 手动应用虚线效果 |
| `SkPathEffectBase` | 使用 | 检测虚线效果 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|------|---------|------|
| `GrStyledShape` | 组合 | 样式化形状的样式部分 |
| `GrShape` | 间接使用 | 形状处理流程 |
| GPU 操作生成器 | 键生成 | 使用样式键进行缓存和去重 |

## 设计模式与设计决策

### 值语义设计

`GrStyle` 采用值语义而非指针/引用：
- 支持拷贝和移动，便于存储和传递
- 内存布局紧凑，减少间接访问
- 使用智能指针 `sk_sp<SkPathEffect>` 管理路径效果的生命周期

### 特殊化虚线处理

将虚线从通用路径效果中分离的设计动机：
1. **可缓存性**：虚线效果可以生成确定性的键，而通用路径效果不行
2. **性能优化**：虚线是最常见的路径效果，值得特殊优化
3. **控制描边应用**：虚线应用时需要阻止自动描边，以保持键的一致性

### 懒应用策略

样式不会自动应用到路径，而是提供 `applyToPath` 等方法：
- 调用者决定何时应用样式
- 支持分步应用（先路径效果，后描边）
- 便于中间结果的缓存和复用

### 标志位优化

`KeyFlags` 允许键生成时排除不相关的信息：
- `kClosed_KeyFlag`：封闭形状不需要端点样式
- `kNoJoins_KeyFlag`：无连接点的形状不需要连接样式

这减少了键的变化，提高了缓存命中率。

## 性能考量

### 键生成效率

- **位打包**：使用位移和或运算紧凑存储信息
- **memcpy 优化**：直接复制浮点数和数组，避免序列化开销
- **条件排除**：根据标志位跳过不必要的字段

### 虚线缓存

虚线信息的提取和存储使得样式对象可以快速检查是否为虚线：
```cpp
bool isDashed() const { return DashType::kDash == fDashInfo.fType; }
```

避免了重复的类型检查和转换。

### 内存布局

使用 `AutoSTArray<4, SkScalar>` 存储虚线间隔：
- 小数组（≤4 个元素）使用栈内存，避免堆分配
- 大数组自动切换到堆分配
- 大多数虚线只有 2-4 个间隔，栈优化有效

### 边界计算

`adjustBounds` 提供快速路径计算应用样式后的边界：
- 对于路径效果，调用 `computeFastBounds`（可能不精确但保守）
- 对于描边，使用膨胀半径 `getInflationRadius`
- 避免了完整的路径应用开销

### 样式检查优化

提供多个快速检查方法：
```cpp
bool isSimpleFill() const { return fStrokeRec.isFillStyle() && !fPathEffect; }
bool applies() const {
    return this->pathEffect() ||
           (!fStrokeRec.isFillStyle() && !fStrokeRec.isHairlineStyle());
}
```

这些方法可以在不应用样式的情况下快速判断是否需要处理。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkPaint.h` | 输入源 | 高级绘制样式 |
| `include/core/SkStrokeRec.h` | 组合 | 描边信息记录 |
| `include/core/SkPathEffect.h` | 组合 | 路径效果接口 |
| `src/core/SkPathEffectBase.h` | 使用 | 虚线检测 |
| `src/utils/SkDashPathPriv.h` | 使用 | 虚线应用实现 |
| `include/core/SkPath.h` | 操作对象 | 路径表示 |
| `include/core/SkMatrix.h` | 工具 | 提取缩放因子 |
