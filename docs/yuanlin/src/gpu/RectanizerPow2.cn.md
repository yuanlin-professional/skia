# RectanizerPow2

> 源文件: src/gpu/RectanizerPow2.h, src/gpu/RectanizerPow2.cpp

## 概述

`RectanizerPow2` 是 Skia GPU 层的矩形打包算法实现,采用基于 2 的幂次量化的简化策略。与 `RectanizerSkyline` 相比,该算法将输入矩形的高度量化到 2 的幂次,每个高度最多维护一个活动行,通过牺牲一定的空间利用率来换取更快的分配速度。

该算法适用于对分配速度要求较高但空间利用率要求相对宽松的场景,例如临时渲染目标的动态分配。类被标记为 `final` 以避免虚函数表开销。

## 架构位置

`RectanizerPow2` 位于 Skia GPU 层的资源管理基础设施:

- 命名空间: `skgpu`
- 模块位置: `src/gpu/`
- 继承关系: 继承自抽象基类 `Rectanizer`
- 应用场景: 快速动态分配、临时资源打包

该类是 `Rectanizer` 的替代实现,可通过工厂方法选择使用(默认使用 `RectanizerSkyline`)。

## 主要类与结构体

### 继承关系

```
Rectanizer (抽象基类)
└── RectanizerPow2 (final 实现)
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRows` | `Row[kMaxExponent]` | 行数组,每个索引对应一个 2 的幂次高度 |
| `fNextStripY` | `int` | 下一个可分配条带的 Y 坐标 |
| `fAreaSoFar` | `int32_t` | 已分配的总面积(像素数) |
| `fWidth` | `int` (继承) | 打包空间的总宽度 |
| `fHeight` | `int` (继承) | 打包空间的总高度 |

### 内部结构体

#### Row

```cpp
struct Row {
    SkIPoint16 fLoc;        // 当前行的当前插入位置
    int fRowHeight;         // 行高(也用于标识行是否已初始化)

    // 检查是否可以在当前行添加指定宽度
    bool canAddWidth(int width, int containerWidth) const {
        return fLoc.fX + width <= containerWidth;
    }
};
```

### 常量定义

| 常量 | 值 | 说明 |
|------|------|------|
| `kMIN_HEIGHT_POW2` | 2 | 最小高度(2^1) |
| `kMaxExponent` | 16 | 最大指数,支持 2^16 = 65536 像素 |

## 公共 API 函数

### 构造与析构

```cpp
// 构造函数,指定打包空间大小
RectanizerPow2(int w, int h);

// 析构函数
~RectanizerPow2() final;
```

### 核心接口(覆盖基类)

```cpp
// 重置到初始状态,清空所有已分配区域
void reset() final;

// 尝试添加矩形,成功返回 true 并填充位置
bool addRect(int w, int h, SkIPoint16* loc) final;

// 返回空间使用率(0.0-1.0)
float percentFull() const final;
```

### 继承的基类接口

```cpp
// 获取总宽度和高度
int width() const;
int height() const;

// 添加带边距的矩形
bool addPaddedRect(int width, int height, int16_t padding, SkIPoint16* loc);
```

## 内部实现细节

### Pow2 算法原理

算法的核心思想是将高度量化到 2 的幂次,每个量化的高度对应一个行:

1. **高度量化**: 输入高度 `h` 量化到 `SkNextPow2(h)`
2. **行索引映射**: 通过 `HeightToRowIndex` 将高度映射到 `fRows` 数组索引
3. **行内分配**: 在对应行内尝试水平放置矩形
4. **行满处理**: 当前行满时,分配新的条带并重置该行

### HeightToRowIndex 映射

```cpp
static int HeightToRowIndex(int height) {
    SkASSERT(height >= kMIN_HEIGHT_POW2);
    // 使用前导零计数计算指数
    // 例如: height=4 -> index=2, height=8 -> index=3
    int index = 32 - SkCLZ(height - 1);
    SkASSERT(index < kMaxExponent);
    return index;
}
```

**映射示例**:
| 高度范围 | 量化后高度 | 索引 |
|---------|-----------|------|
| 2 | 2 | 1 |
| 3-4 | 4 | 2 |
| 5-8 | 8 | 3 |
| 9-16 | 16 | 4 |
| 513-1024 | 1024 | 10 |

### addRect 实现流程

```cpp
bool RectanizerPow2::addRect(int width, int height, SkIPoint16* loc) {
    // 1. 边界检查
    if (width > this->width() || height > this->height()) {
        return false;
    }

    // 2. 保存原始面积(高度会被修改)
    int32_t area = width * height;

    // 3. 高度量化到 2 的幂次
    if (height < kMIN_HEIGHT_POW2) {
        height = kMIN_HEIGHT_POW2;
    } else {
        height = SkNextPow2(height);
    }

    // 4. 获取对应的行
    Row* row = &fRows[HeightToRowIndex(height)];

    // 5. 初始化行(如果未初始化)
    if (row->fRowHeight == 0) {
        if (!this->canAddStrip(height)) {
            return false;  // 空间不足
        }
        this->initRow(row, height);
    }
    // 6. 检查当前行是否有空间
    else {
        if (!row->canAddWidth(width, this->width())) {
            // 当前行满,尝试分配新条带
            if (!this->canAddStrip(height)) {
                return false;
            }
            this->initRow(row, height);
        }
    }

    // 7. 在当前行中放置矩形
    *loc = row->fLoc;
    row->fLoc.fX += width;  // 水平前进
    fAreaSoFar += area;     // 累加实际面积
    return true;
}
```

### 辅助方法

```cpp
// 检查是否可以添加新的条带
bool canAddStrip(int height) const {
    return fNextStripY + height <= this->height();
}

// 初始化行
void initRow(Row* row, int rowHeight) {
    row->fLoc.set(0, fNextStripY);  // 从左上角开始
    row->fRowHeight = rowHeight;
    fNextStripY += rowHeight;       // 更新下一个条带位置
}
```

### reset 实现

```cpp
void reset() final {
    fNextStripY = 0;
    fAreaSoFar = 0;
    sk_bzero(fRows, sizeof(fRows));  // 清零所有行
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| Rectanizer | 基类接口 | `src/gpu/Rectanizer.h` |
| SkIPoint16 | 16 位整数点 | `src/core/SkIPoint16.h` |
| SkMathPriv | 数学工具(SkNextPow2, SkCLZ) | `src/base/SkMathPriv.h` |
| SkAssert | 断言检查 | `include/private/base/SkAssert.h` |
| SkMalloc | 内存工具(sk_bzero) | `include/private/base/SkMalloc.h` |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| 动态资源分配器 | 潜在使用方 | 需要快速分配的场景 |
| 临时纹理管理 | 潜在使用方 | 短期纹理图集 |

## 设计模式与设计决策

### 1. 量化策略

将高度量化到 2 的幂次:
- **优点**: 简化管理,快速索引
- **缺点**: 空间浪费(例如高度 3 量化到 4,浪费 25%)

### 2. 单行策略

每个高度最多维护一个活动行:
- **优点**: 状态简单,分配 O(1)
- **缺点**: 一行满后立即分配新条带,可能增加碎片

### 3. final 关键字优化

```cpp
class RectanizerPow2 final : public Rectanizer
```

避免虚函数表查找,允许编译器内联和去虚拟化。

### 4. 固定数组而非动态结构

使用固定大小数组 `fRows[kMaxExponent]`:
- **优点**: 无动态分配开销,缓存友好
- **缺点**: 固定内存占用(16 * sizeof(Row) ≈ 192 字节)

### 5. 面积跟踪

记录实际分配面积,而非量化后面积:

```cpp
int32_t area = width * height;  // 使用原始高度
// ... 量化高度 ...
fAreaSoFar += area;  // 累加原始面积
```

这样 `percentFull()` 反映真实的空间利用率。

## 性能考量

### 1. 时间复杂度

- **addRect**: O(1) 平均情况,常数时间操作
  - 高度映射: O(1)
  - 行查找: O(1) 数组访问
  - 位置分配: O(1)
- **reset**: O(1)
- **percentFull**: O(1)

### 2. 空间复杂度

- 固定开销: `sizeof(Row) * 16` ≈ 192 字节
- 无额外动态分配

### 3. 与 RectanizerSkyline 对比

| 指标 | RectanizerPow2 | RectanizerSkyline |
|------|---------------|------------------|
| 分配速度 | O(1) | O(n^2) 最坏 |
| 空间利用率 | 70-85% | 85-95% |
| 内存开销 | 192 字节 | 动态,取决于矩形数 |
| 适用场景 | 快速动态分配 | 长期高效缓存 |

### 4. 优化技术

**位运算**:
```cpp
int index = 32 - SkCLZ(height - 1);  // 快速计算 log2
```

**提前返回**:
```cpp
if (row->fRowHeight == 0) {
    // 快速路径: 首次使用
}
```

**静态断言**:
```cpp
static_assert(kMIN_HEIGHT_POW2 > 0);
static_assert(kMIN_HEIGHT_POW2 == SkNextPow2(kMIN_HEIGHT_POW2));
```

### 5. 空间浪费分析

主要浪费来源:
1. **高度量化**: 例如高度 3 量化到 4,浪费 25%
2. **行末碎片**: 每行末尾可能有小段剩余空间
3. **条带切换**: 行满后切换新条带,旧条带末尾浪费

典型利用率: 70-85%,取决于输入矩形的尺寸分布。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/Rectanizer.h` | 基类 | 抽象接口定义 |
| `src/gpu/RectanizerSkyline.h` | 同级实现 | 基于天际线的优化算法 |
| `src/core/SkIPoint16.h` | 依赖 | 16 位坐标点 |
| `src/base/SkMathPriv.h` | 依赖 | 数学工具函数 |
| `include/private/base/SkAssert.h` | 依赖 | 断言宏 |
| `tests/RectanizerTest.cpp` | 测试 | 单元测试 |
