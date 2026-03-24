# SkPathMeasurePriv

> 源文件
> - src/core/SkPathMeasurePriv.h

## 概述

`SkPathMeasurePriv.h` 定义了路径测量系统的私有辅助工具,包括段类型枚举、段提取函数以及测试辅助接口。该文件是 `SkPathMeasure` 和 `SkContourMeasure` 内部实现的支持组件,对外部用户不可见。

主要内容包括:定义路径段类型枚举(`SkSegType`)、提供段提取函数(`SkPathMeasure_segTo`)、以及测试辅助类(`SkPathMeasurePriv`)。这些工具确保了路径测量功能的正确性和可测试性。

## 架构位置

`SkPathMeasurePriv` 位于 Skia 路径测量系统的内部支持层:

```
include/core/
├── SkPathMeasure (公共接口)
└── SkContourMeasure (轮廓测量)

src/core/
├── SkPathMeasurePriv.h (私有辅助) ← 当前组件
├── SkPathMeasure.cpp (使用辅助工具)
└── SkContourMeasure.cpp (使用 SkSegType)
```

使用关系:
```
SkContourMeasure
    ↓
  使用 SkSegType
    ↓
  调用 SkPathMeasure_segTo
    ↓
  输出到 SkPath
```

## 主要类与结构体

### SkSegType 枚举

路径段类型枚举,用于 `SkContourMeasure::Segment` 结构体。

**枚举值**:

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| kLine_SegType | 0 | 直线段 |
| kQuad_SegType | 1 | 二次贝塞尔曲线 |
| kCubic_SegType | 2 | 三次贝塞尔曲线 |
| kConic_SegType | 3 | 圆锥曲线 |

**注意事项**:
该枚举作为2位字段使用,因此最多支持4种类型。如需增加类型,必须扩大 `SkContourMeasure::Segment` 中的位字段大小。

### SkPathMeasurePriv 类

测试辅助类,提供访问 `SkPathMeasure` 内部状态的接口。

**静态方法**:

```cpp
class SkPathMeasurePriv {
public:
    // 获取当前轮廓的段数量(用于测试)
    static size_t CountSegments(const SkPathMeasure& meas);
};
```

## 公共 API 函数

### SkPathMeasure_segTo 函数

从路径段提取子路径片段。

**函数签名**:

```cpp
void SkPathMeasure_segTo(const SkPoint pts[],
                         unsigned segType,
                         SkScalar startT,
                         SkScalar stopT,
                         SkPath* dst);
```

**参数**:
- `pts`: 段的控制点数组(长度取决于 segType)
- `segType`: 段类型(SkSegType 枚举值)
- `startT`: 起始参数(0.0 到 1.0)
- `stopT`: 结束参数(0.0 到 1.0)
- `dst`: 输出路径对象

**段点数**:
- `kLine_SegType`: 2个点
- `kQuad_SegType`: 3个点
- `kCubic_SegType`: 4个点
- `kConic_SegType`: 3个点 + 权重

**功能**:
将路径段的子区间 [startT, stopT] 提取到目标路径中。

### CountSegments 方法

获取路径测量对象中当前轮廓的段数量。

**函数签名**:

```cpp
static size_t CountSegments(const SkPathMeasure& meas);
```

**实现**(来自 SkPathMeasure.cpp):

```cpp
size_t SkPathMeasurePriv::CountSegments(const SkPathMeasure& meas) {
    if (auto cntr = meas.currentMeasure()) {
        return cntr->fSegments.size();
    }
    return 0;
}
```

**用途**:
主要用于测试,验证轮廓分段的正确性。

## 内部实现细节

### SkSegType 作为位字段

在 `SkContourMeasure::Segment` 中的使用:

```cpp
struct Segment {
    SkScalar fDistance;       // 累积距离
    unsigned fPtIndex : 30;   // 点索引(30位)
    unsigned fType : 2;       // 段类型(2位,SkSegType)
    SkScalar fTValue;         // 参数化值
};
```

2位字段支持4种类型(0-3),与 `SkSegType` 枚举值一一对应。

### SkPathMeasure_segTo 实现逻辑

虽然实现不在头文件中,但其逻辑大致为:

1. **直线段**:
   - 线性插值起止点
   - 添加 `lineTo` 到目标路径

2. **二次曲线**:
   - 使用 De Casteljau 算法分割
   - 提取 [startT, stopT] 区间的曲线

3. **三次曲线**:
   - 递归分割或直接计算子曲线
   - 保持曲线连续性

4. **圆锥曲线**:
   - 考虑权重的分割
   - 计算子圆锥的新权重

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 输出路径 |
| SkPoint | 点坐标 |
| SkGeometry | 曲线分割算法 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkContourMeasure | 使用 SkSegType |
| SkPathMeasure | 使用辅助函数 |
| 测试代码 | 使用 CountSegments |

## 设计模式与设计决策

### 私有头文件模式

使用 `*Priv.h` 命名约定:
- 明确表示内部接口
- 不安装到公共头文件目录
- 允许内部实现细节变更

### 枚举作为位字段

使用紧凑的枚举表示:
```cpp
unsigned fType : 2;  // 2位存储4种类型
```
优点:
- 节省内存
- 缓存友好
- 快速比较

### 测试辅助类

`SkPathMeasurePriv` 提供测试接口:
- 不污染公共API
- 便于单元测试
- 友元访问内部状态

### 函数命名约定

`SkPathMeasure_segTo` 使用模块前缀:
- 避免命名冲突
- 清晰的模块归属
- 非成员辅助函数

## 性能考量

### 位字段优化

2位类型字段:
- 减少内存占用
- 提高缓存利用率
- 结构体更紧凑

### 内联潜力

枚举和小函数:
- 适合内联优化
- 无虚函数开销
- 编译时常量折叠

### 测试开销隔离

`CountSegments` 仅在测试时调用:
- 不影响生产性能
- 可选的调试信息
- 条件编译友好

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPathMeasure.h | 配合 | 公共接口 |
| include/core/SkContourMeasure.h | 使用 | 轮廓测量 |
| src/core/SkPathMeasure.cpp | 实现 | CountSegments 实现 |
| src/core/SkContourMeasure.cpp | 使用 | 使用 SkSegType |
| include/core/SkPath.h | 依赖 | 路径对象 |
| include/core/SkPoint.h | 依赖 | 点坐标 |
| src/core/SkGeometry.h | 依赖 | 曲线几何 |
