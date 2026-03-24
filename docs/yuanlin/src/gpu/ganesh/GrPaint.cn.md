# GrPaint

> 源文件: src/gpu/ganesh/GrPaint.h, src/gpu/ganesh/GrPaint.cpp

## 概述

`GrPaint` 是 Ganesh GPU 后端中描述像素颜色和覆盖率计算方式的核心类,类似于 CPU 渲染中的 `SkPaint`。该类封装了颜色、片段处理器(Fragment Processors)和混合模式(Blend Mode),定义了绘制操作的像素着色管线。

主要功能包括:
- **初始颜色**: 设置绘制图元的基础颜色
- **片段处理器**: 支持颜色和覆盖率两个独立的片段处理器链
- **混合模式**: 通过 XPFactory 控制与目标缓冲区的混合方式
- **优化标记**: 追踪 Paint 是否为"平凡"的(仅 src-over 且无处理器)
- **常量分析**: 判断输出颜色是否为常量,用于优化

该类是 `GrPipeline` 的输入之一,在绘制操作准备阶段被转换为 GPU 管线状态。

## 架构位置

该模块位于 Ganesh 渲染管线的抽象层:

```
src/gpu/ganesh/
├── GrPaint.h/cpp                  # Paint 抽象(当前模块)
├── GrPipeline.h/cpp               # 管线状态(使用 Paint)
├── GrFragmentProcessor.h          # 片段处理器基类
├── GrXferProcessor.h              # 混合处理器基类
└── ops/
    └── GrOp.cpp                   # 绘制操作使用 Paint
```

**数据流**:
```
SkPaint → GrPaint → GrPipeline → GPU 着色器
```

## 主要类与结构体

### GrPaint
GPU 绘制的 Paint 对象。

```cpp
class GrPaint {
public:
    GrPaint() = default;
    static GrPaint Clone(const GrPaint& src);

    void setColor4f(const SkPMColor4f& color);
    const SkPMColor4f& getColor4f() const;

    void setXPFactory(const GrXPFactory* xpFactory);
    void setPorterDuffXPFactory(SkBlendMode mode);
    void setCoverageSetOpXPFactory(SkRegion::Op, bool invertCoverage);

    void setColorFragmentProcessor(std::unique_ptr<GrFragmentProcessor> fp);
    void setCoverageFragmentProcessor(std::unique_ptr<GrFragmentProcessor> fp);

    bool usesLocalCoords() const;
    bool isConstantBlendedColor(SkPMColor4f* constantColor) const;
    bool isTrivial() const;

private:
    const GrXPFactory* fXPFactory = nullptr;
    std::unique_ptr<GrFragmentProcessor> fColorFragmentProcessor;
    std::unique_ptr<GrFragmentProcessor> fCoverageFragmentProcessor;
    bool fTrivial = true;
    SkPMColor4f fColor = SK_PMColor4fWHITE;
};
```

**成员变量**:
- `fColor`: 绘制图元的初始颜色,默认为不透明白色
- `fColorFragmentProcessor`: 颜色片段处理器,可选
- `fCoverageFragmentProcessor`: 覆盖率片段处理器,可选
- `fXPFactory`: 混合处理器工厂,`nullptr` 表示 src-over
- `fTrivial`: 优化标志,表示是否为简单 Paint

## 公共 API 函数

### GrPaint::Clone
静态克隆方法,深度复制 Paint 对象。

```cpp
static GrPaint Clone(const GrPaint& src)
```

**实现**: 调用私有拷贝构造函数,克隆所有片段处理器。

**原因**: Paint 复制涉及处理器克隆,成本较高,通过静态方法显式化操作。

### GrPaint::setColor4f
设置绘制图元的初始颜色。

```cpp
void setColor4f(const SkPMColor4f& color)
```

**颜色格式**: 预乘 Alpha 的浮点 RGBA 颜色。

### GrPaint::setPorterDuffXPFactory
设置 Porter-Duff 混合模式。

```cpp
void setPorterDuffXPFactory(SkBlendMode mode)
```

**实现**: 调用 `GrPorterDuffXPFactory::Get(mode)` 获取对应的工厂。

**支持模式**: 所有标准 Porter-Duff 混合模式(kSrc, kDst, kSrcOver 等)。

### GrPaint::setCoverageSetOpXPFactory
设置覆盖率集合操作混合模式。

```cpp
void setCoverageSetOpXPFactory(SkRegion::Op regionOp, bool invertCoverage)
```

**用途**: 用于裁剪等场景,执行覆盖率的集合操作(并集、交集等)。

### GrPaint::setColorFragmentProcessor
设置颜色片段处理器。

```cpp
void setColorFragmentProcessor(std::unique_ptr<GrFragmentProcessor> fp)
```

**约束**:
- 只能设置一次(断言 `fColorFragmentProcessor == nullptr`)
- 设置后 `fTrivial` 标志置为 `false`

**处理器链**: 颜色从 `fColor` 开始,经过颜色处理器,输出到混合阶段。

### GrPaint::setCoverageFragmentProcessor
设置覆盖率片段处理器。

```cpp
void setCoverageFragmentProcessor(std::unique_ptr<GrFragmentProcessor> fp)
```

**用途**: 处理覆盖率信息,如抗锯齿、渐变透明等。

### GrPaint::usesLocalCoords
判断 Paint 是否使用局部坐标。

```cpp
bool usesLocalCoords() const
```

**实现**: 检查两个处理器是否调用 `usesSampleCoords()`。

**用途**: 决定几何处理器是否需要输出局部坐标到片段着色器。

### GrPaint::isConstantBlendedColor
判断混合后的输出是否为常量颜色。

```cpp
bool isConstantBlendedColor(SkPMColor4f* constantColor) const
```

**实现逻辑**:
1. 如果混合模式为 `kClear`,返回透明色
2. 如果无颜色处理器且混合模式为 `kSrc`,或默认模式且颜色不透明,返回 `fColor`
3. 否则返回 `false`

**优化**: 常量颜色可以跳过片段着色器,直接清屏或填充。

### GrPaint::isTrivial
判断是否为平凡 Paint。

```cpp
bool isTrivial() const
```

**平凡条件**:
- 无颜色片段处理器
- 无覆盖率片段处理器
- 混合模式为默认 src-over(`fXPFactory == nullptr`)

**优化**: 平凡 Paint 可以使用快速路径。

## 内部实现细节

### 拷贝构造函数

私有拷贝构造函数执行深度复制:

```cpp
GrPaint::GrPaint(const GrPaint& that)
        : fXPFactory(that.fXPFactory)
        , fTrivial(that.fTrivial)
        , fColor(that.fColor) {
    if (that.fColorFragmentProcessor) {
        fColorFragmentProcessor = that.fColorFragmentProcessor->clone();
    }
    if (that.fCoverageFragmentProcessor) {
        fCoverageFragmentProcessor = that.fCoverageFragmentProcessor->clone();
    }
}
```

**关键点**:
- `GrXPFactory` 是全局单例,只复制指针
- 片段处理器调用 `clone()` 深度复制

### fTrivial 标志维护

设置处理器或非默认混合时更新 `fTrivial`:

```cpp
void setXPFactory(const GrXPFactory* xpFactory) {
    fXPFactory = xpFactory;
    fTrivial &= !SkToBool(xpFactory);  // 非 nullptr 则非平凡
}

void setColorFragmentProcessor(...) {
    ...
    fTrivial = false;
}
```

**优化**: 避免每次调用 `isTrivial()` 时重新计算。

### 常量颜色判断简化

`isConstantBlendedColor` 曾经有更复杂的分析,现在简化为显式模式检查:

```cpp
static const GrXPFactory* kSrc = GrPorterDuffXPFactory::Get(SkBlendMode::kSrc);
static const GrXPFactory* kClear = GrPorterDuffXPFactory::Get(SkBlendMode::kClear);
if (kClear == fXPFactory) {
    *constantColor = SK_PMColor4fTRANSPARENT;
    return true;
}
if (kSrc == fXPFactory || (!fXPFactory && fColor.isOpaque())) {
    *constantColor = fColor;
    return true;
}
```

**原因**: 完整分析涉及处理器树遍历,成本高且收益有限。

### 调试支持

调试模式下使用 `fAlive` 标志检测 moved-from 对象:

```cpp
SkDEBUGCODE(bool fAlive = true;)

friend void assert_alive(GrPaint& p) {
    SkASSERT(p.fAlive);
}
```

## 依赖关系

### 外部依赖
```cpp
#include "src/gpu/ganesh/GrFragmentProcessor.h"      // 片段处理器基类
#include "src/gpu/ganesh/effects/GrPorterDuffXferProcessor.h" // Porter-Duff 混合
#include "src/gpu/ganesh/effects/GrCoverageSetOpXP.h"         // 覆盖率集合操作
```

### 被依赖模块
- `src/gpu/ganesh/GrPipeline.cpp` - 从 Paint 构建管线
- `src/gpu/ganesh/ops/GrOp.cpp` - 绘制操作使用 Paint
- `src/gpu/ganesh/GrProcessorSet.cpp` - 处理器集合

## 设计模式与设计决策

### 1. 不可变性限制
拷贝构造函数为私有,只能通过 `Clone()` 静态方法复制:

```cpp
GrPaint(const GrPaint&);  // private
GrPaint& operator=(const GrPaint&) = delete;
```

**原因**: 强制显式复制,避免意外的高成本操作。

### 2. 工厂模式
混合处理器通过工厂创建:

```cpp
void setXPFactory(const GrXPFactory* xpFactory);
```

**优势**: 延迟处理器实例化,支持多态和共享。

### 3. 单一所有权
片段处理器使用 `unique_ptr`:

```cpp
std::unique_ptr<GrFragmentProcessor> fColorFragmentProcessor;
```

**语义**: Paint 拥有处理器,移动语义转移所有权。

### 4. 优化标志缓存
`fTrivial` 标志避免重复计算:

```cpp
bool fTrivial = true;
```

在热路径(如批处理判断)中查询频繁,缓存提高性能。

### 5. nullptr 表示默认值
`fXPFactory == nullptr` 表示默认 src-over 混合:

```cpp
if (!fXPFactory && fColor.isOpaque()) {
    *constantColor = fColor;
    return true;
}
```

**优势**: 节省内存,无需为常见情况分配对象。

## 性能考量

### 1. 轻量级默认构造
默认构造仅初始化几个标量:

```cpp
GrPaint() = default;
```

**成员初始化**: `fColor`, `fTrivial`, 指针初始化为 `nullptr`。

### 2. 移动语义
使用 `std::move` 转移处理器所有权:

```cpp
void setColorFragmentProcessor(std::unique_ptr<GrFragmentProcessor> fp) {
    fColorFragmentProcessor = std::move(fp);
}
```

避免不必要的引用计数或复制。

### 3. 常量分析优化
`isConstantBlendedColor` 允许绘制操作跳过复杂管线:
- 常量透明色可以跳过绘制
- 常量不透明色可以使用快速填充路径

### 4. 平凡标志快速路径
`isTrivial()` 的 O(1) 查询允许批处理系统快速决策:
- 平凡 Paint 可以批处理
- 复杂 Paint 可能需要独立绘制

### 5. 单例工厂复用
Porter-Duff 工厂为全局单例:

```cpp
GrPorterDuffXPFactory::Get(mode)  // 返回全局实例指针
```

避免重复分配相同混合模式的工厂对象。

## 相关文件

### 核心实现
- `src/gpu/ganesh/GrPipeline.h/cpp` - GPU 管线状态
- `src/gpu/ganesh/GrProcessorSet.h/cpp` - 处理器集合

### 处理器
- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
- `src/gpu/ganesh/GrXferProcessor.h` - 混合处理器基类

### 工厂实现
- `src/gpu/ganesh/effects/GrPorterDuffXferProcessor.h/cpp` - Porter-Duff 混合
- `src/gpu/ganesh/effects/GrCoverageSetOpXP.h/cpp` - 覆盖率集合操作

### 使用模块
- `src/gpu/ganesh/ops/GrDrawOp.cpp` - 绘制操作
- `src/gpu/ganesh/SurfaceDrawContext.cpp` - 表面绘制上下文

### 测试文件
- `tests/ProcessorTest.cpp` - 处理器和 Paint 测试
