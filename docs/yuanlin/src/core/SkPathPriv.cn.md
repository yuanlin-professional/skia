# SkPathPriv

> 源文件
> - src/core/SkPathPriv.h
> - src/core/SkPathPriv.cpp

## 概述

`SkPathPriv` 是 Skia 路径系统的内部辅助类,提供了对 `SkPath` 类私有功能的访问接口。该类包含了一系列静态工具函数,用于执行路径的几何分析、形状识别、变换处理以及内部状态访问等操作。它是 Skia 内部实现中不可或缺的组件,为路径的高级操作提供了底层支持。

该类的设计遵循 C++ 的友元模式,允许内部代码绕过 `SkPath` 的封装访问其私有成员,同时保持对外部用户的隐藏性。`SkPathPriv` 不包含任何实例成员,所有功能均通过静态方法实现。

## 架构位置

`SkPathPriv` 位于 Skia 核心图形层的路径子系统中:

```
src/core/
├── SkPath (公共路径类)
├── SkPathPriv (路径私有辅助类) ← 当前组件
├── SkPathData (路径数据容器)
├── SkPathBuilder (路径构建器)
├── SkPathRaw (原始路径数据)
└── SkPathEnums (路径枚举定义)
```

该类主要服务于:
- 路径渲染器和光栅化模块
- 路径效果(SkPathEffect)处理
- 路径几何计算和分析
- 内部优化和缓存机制

## 主要类与结构体

### SkPathPriv 类

**继承关系**: 无(纯静态工具类)

**关键成员变量**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| kW0PlaneDistance | constexpr SkScalar | W平面裁剪的距离阈值(1/16384) |

**嵌套类型**:

| 类型 | 说明 |
|------|------|
| RRectAsEnum | 圆角矩形简化类型枚举(kRect/kOval/kRRect) |
| RectContour | 矩形轮廓识别结果 |
| Iterate | 路径迭代器适配器 |

### SkPathEdgeIter 类

**继承关系**: 无

**关键成员变量**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fVerbs | const SkPathVerb* | 当前动词指针 |
| fPts | const SkPoint* | 当前点指针 |
| fConicWeights | const SkScalar* | 圆锥曲线权重指针 |
| fNeedsCloseLine | bool | 是否需要自动闭合线 |
| fNextIsNewContour | bool | 下一个是否为新轮廓 |

## 公共 API 函数

### 凸性计算

```cpp
// 计算路径的凸性
static SkPathConvexity ComputeConvexity(
    SkSpan<const SkPoint> pts,
    SkSpan<const SkPathVerb> verbs,
    SkSpan<const float> conicWeights);

// 变换后的凸性
static SkPathConvexity TransformConvexity(
    const SkMatrix& matrix,
    SkSpan<const SkPoint> pts,
    SkPathConvexity convexity);
```

### 形状识别

```cpp
// 判断是否为矩形
static std::optional<SkPathRectInfo> IsSimpleRect(
    const SkPath& path,
    bool isSimpleFill);

// 判断是否为椭圆
static std::optional<SkPathOvalInfo> IsOval(const SkPath& path);

// 判断是否为圆角矩形
static std::optional<SkPathRRectInfo> IsRRect(const SkPath& path);

// 判断是否为嵌套填充矩形
static bool IsNestedFillRects(
    const SkPathRaw& raw,
    SkRect rect[2],
    SkPathDirection dirs[2]);
```

### 方向计算

```cpp
// 计算第一方向
static SkPathFirstDirection ComputeFirstDirection(const SkPathRaw&);
static SkPathFirstDirection ComputeFirstDirection(const SkPath&);

// 反转方向
static SkPathFirstDirection OppositeFirstDirection(SkPathFirstDirection dir);
```

### 边界计算

```cpp
// 计算紧凑边界
static SkRect ComputeTightBounds(
    SkSpan<const SkPoint> points,
    SkSpan<const SkPathVerb> verbs,
    SkSpan<const float> conicWeights);

// 修剪边界(移除尾部移动点)
static std::optional<SkRect> TrimmedBounds(
    SkSpan<const SkPoint> pts,
    SkSpan<const SkPathVerb> vbs);
```

### 几何判断

```cpp
// 判断点是否在路径内
static bool Contains(const SkPathRaw& raw, SkPoint p);

// 判断是否轴对齐
static bool IsAxisAligned(SkSpan<const SkPoint> pts);

// 判断是否为闭合单轮廓
static bool IsClosedSingleContour(SkSpan<const SkPathVerb> verbs);
```

### 路径操作

```cpp
// 反转路径
static SkPath ReversePath(const SkPath& reverseMe);

// 透视裁剪
static bool PerspectiveClip(
    const SkPath& src,
    const SkMatrix& matrix,
    SkPath* result);

// 创建绘制弧路径
static SkPath CreateDrawArcPath(
    const SkArc& arc,
    bool isFillNoPathEffect);
```

### 内部状态访问

```cpp
// 获取/设置凸性
static SkPathConvexity GetConvexity(const SkPath& path);
static void SetConvexity(const SkPath& path, SkPathConvexity c);

// 添加 GenID 变更监听器
static void AddGenIDChangeListener(
    const SkPath& path,
    sk_sp<SkIDChangeListener> listener);

// 获取原始数据
static std::optional<SkPathRaw> Raw(
    const SkPath& path,
    SkResolveConvexity rc);
```

## 内部实现细节

### 矩形识别算法

矩形识别通过 `IsRectContour` 实现,采用方向跟踪算法:

1. **快速路径**: 对于标准矩形(5个动词:Move+3xLine+Close),直接验证向量正交性
2. **复杂路径**: 跟踪方向变化,允许共线段和单点
3. **方向编码**: 使用2位编码表示水平/垂直和方向(0-3)
4. **有效性检查**: 验证4个角、对边反向、无对角线

```cpp
// 方向编码:
// 0x1: 是否水平
// 0x2: 是否向右或向下
static int rect_make_dir(SkScalar dx, SkScalar dy) {
    return ((0 != dx) << 0) | ((dx > 0 || dy > 0) << 1);
}
```

### 凸性计算

凸性计算使用 `Convexicator` 状态机:

1. **符号检查**: 快速检测是否有超过3次方向改变
2. **详细分析**: 跟踪向量叉积的符号一致性
3. **退化处理**: 允许最多2次反转(180度转向)
4. **多轮廓**: 多轮廓路径直接判定为凹

### 点包含测试

使用 winding number 算法判断点是否在路径内:

1. **边界检查**: 先快速排除路径边界外的点
2. **射线法**: 从点发出水平射线,计算与路径边的交点
3. **分段处理**: 针对线段、二次、圆锥、三次曲线分别计算
4. **特殊情况**: 处理点在曲线上的情况,使用切线检测重合

### 变换方向和起点

`TransformDirAndStart` 处理变换后的方向和起点索引:

```cpp
// 判断变换类型:
// - 对角线非零 → 旋转(保持方向)
// - 反对角线非零 → 镜像(反转方向)
// 通过矩阵元素符号计算新起点
```

### 紧凑边界计算

`ComputeTightBounds` 计算真实几何边界:

1. 对线段:直接使用端点
2. 对二次曲线:计算极值点 t = -B/(2A)
3. 对圆锥曲线:使用 `SkConic::findXExtrema/findYExtrema`
4. 对三次曲线:求解一阶导数=0的点

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 主要操作对象 |
| SkPathData | 路径数据访问 |
| SkPathRef | 路径引用管理 |
| SkMatrix | 几何变换 |
| SkGeometry | 曲线几何计算 |
| SkCubicClipper | 三次曲线裁剪 |
| SkIDChangeListener | GenID 监听器 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 内部实现调用 |
| SkPathBuilder | 路径构建 |
| SkPathEffect | 路径效果 |
| SkDraw | 绘制系统 |
| SkScan | 光栅化 |
| GPU 渲染器 | 路径渲染 |

## 设计模式与设计决策

### 友元访问模式

通过友元关系突破封装边界:
- `SkPath` 声明 `SkPathPriv` 为友元
- 保持公共 API 简洁
- 内部代码可访问优化路径

### 静态工具类

所有方法均为静态:
- 无需实例化
- 无状态存储
- 纯功能性操作
- 便于内联优化

### 迭代器适配器

`Iterate` 提供范围 for 循环支持:
```cpp
for (auto [verb, pts, weights] : SkPathPriv::Iterate(skPath)) {
    // 处理每个动词
}
```

### 可选返回值

广泛使用 `std::optional`:
- 表示可能失败的操作
- 避免异常开销
- 清晰的语义

### 内联几何计算

关键路径内联优化:
- `PtsInVerb`: 返回动词点数(查表)
- `IsInverseFillType`: 位运算检查
- `AsFirstDirection`: 类型转换(数值兼容)

## 性能考量

### 快速路径优化

1. **标准形状识别**: `trivial_rect` 快速识别标准矩形
2. **符号检查**: `IsConcaveBySign` 在完整分析前快速判定凹性
3. **轴对齐检测**: 单次遍历检查轴对齐

### 缓存友好设计

1. **顺序访问**: 迭代器顺序遍历点和动词
2. **数据局部性**: 相关数据紧密排列
3. **避免分支**: 查表代替 switch-case

### 避免重复计算

1. **凸性缓存**: 计算结果存储在路径中
2. **边界缓存**: TrimmedBounds 结果可复用
3. **条件计算**: SkResolveConvexity 控制是否计算

### 数值稳定性

1. **双精度提升**: 叉积计算在必要时使用 double
2. **零值处理**: `cross_prod` 检测下溢并提升精度
3. **NaN 检测**: 通过 `!` 表达式捕获 NaN

### 内存效率

1. **栈分配**: 临时缓冲区使用栈数组
2. **视图传递**: 使用 SkSpan 避免拷贝
3. **惰性计算**: 仅在需要时计算凸性

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPath.h | 配合 | 公共路径 API |
| src/core/SkPathData.h | 使用 | 不可变路径数据 |
| src/core/SkPathBuilder.h | 配合 | 路径构建器 |
| src/core/SkPathRaw.h | 使用 | 原始路径数据视图 |
| src/core/SkPathEnums.h | 使用 | 路径枚举定义 |
| src/core/SkGeometry.h | 依赖 | 曲线几何计算 |
| include/core/SkMatrix.h | 依赖 | 矩阵变换 |
| include/core/SkRRect.h | 依赖 | 圆角矩形 |
| src/core/SkCubicClipper.h | 依赖 | 三次曲线裁剪 |
| include/private/SkIDChangeListener.h | 依赖 | GenID 监听 |
