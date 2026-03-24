# SkPath_interpolate

> 源文件
> - src/core/SkPath_interpolate.cpp

## 概述

`SkPath_interpolate.cpp` 实现了 Skia 路径插值功能，允许在两个结构相同的路径之间进行线性插值。该模块提供了路径变形（morphing）和动画的基础能力，通过对路径的控制点进行插值计算，生成中间状态的路径。这些功能主要面向外部客户（如 Chrome 和 Android），可以被提取到客户端代码中，Skia 内部并不使用这些功能。

## 架构位置

`SkPath_interpolate` 位于 Skia 核心路径系统的扩展工具层：

- 位于 `src/core` 目录，属于核心路径模块
- 为 `SkPath` 类提供插值扩展方法
- 与路径数据结构（点、动词、圆锥曲线权重）直接交互
- 独立于渲染管线，专注于几何变换
- 可被提取到客户端代码（Chrome/Android）使用

## 主要类与结构体

该文件不定义新的类或结构体，而是为 `SkPath` 提供扩展方法。

## 公共 API 函数

### SkPath::isInterpolatable

```cpp
bool SkPath::isInterpolatable(const SkPath& compare) const;
```

判断两个路径是否可以插值：

- 检查点数是否相同
- 检查动词序列是否相同
- 检查圆锥曲线权重是否相同
- 返回 `true` 表示可以进行插值

### SkPath::makeInterpolate

```cpp
SkPath SkPath::makeInterpolate(const SkPath& ending, SkScalar weight) const;
```

创建插值后的路径：

- `ending`: 目标路径
- `weight`: 权重参数，通常在 [0, 1] 范围内
  - `weight = 0` 返回当前路径
  - `weight = 1` 返回目标路径
  - 中间值返回插值路径
- 如果路径不可插值，返回空路径
- 返回新的路径对象

### SkPath::interpolate

```cpp
bool SkPath::interpolate(const SkPath& ending, SkScalar weight, SkPath* out) const;
```

插值路径并输出到指定对象：

- `ending`: 目标路径
- `weight`: 权重参数
- `out`: 输出路径指针
- 返回 `true` 表示插值成功，`false` 表示路径不可插值
- 通过参数返回结果，避免返回值优化问题

## 内部实现细节

### 插值条件检查

`CanInterpolate` 函数检查两个路径是否满足插值条件：

```cpp
bool CanInterpolate(const SkPath& from, const SkPath& to) {
    return from.points().size() == to.points().size() &&
           span_equal(from.verbs(), to.verbs()) &&
           span_equal(from.conicWeights(), to.conicWeights());
}
```

**检查项目**

1. **点数相同**: 两个路径必须有相同数量的控制点
2. **动词相同**: 路径命令序列必须完全一致（Move、Line、Quad、Conic、Cubic、Close）
3. **圆锥曲线权重相同**: 如果包含圆锥曲线，权重必须相同

### 跨度相等性检查

`span_equal` 模板函数高效检查两个跨度是否相等：

```cpp
template <typename T> bool span_equal(SkSpan<T> a, SkSpan<T> b) {
    if (a.size() != b.size()) {
        return false;
    }
    if (a.empty()) {
        return true;
    }
    return (a.data() == b.data()) || std::equal(a.begin(), a.end(), b.begin());
}
```

**优化点**

- 首先检查大小是否相同（O(1)）
- 空跨度快速返回
- 检查指针是否指向同一数据（避免比较）
- 使用 `std::equal` 进行实际比较

### 点插值

使用线性插值（lerp）计算中间点：

```cpp
SkPoint lerp(SkPoint from, SkPoint to, float t) {
    return from + t * (to - from);
}
```

数学公式：`P(t) = (1 - t) * P_from + t * P_to`

### 插值实现

`Interpolate` 函数执行实际插值：

```cpp
std::optional<SkPath> Interpolate(const SkPath& from, const SkPath& to, float t) {
    if (!CanInterpolate(from, to)) {
        return {};
    }

    const SkPathFillType fillType = from.getFillType();
    const SkSpan<const SkPoint> fromPts = from.points(),
                                  toPts = to.points();

    std::vector<SkPoint> dst(fromPts.size());

    for (size_t i = 0; i < fromPts.size(); ++i) {
        dst[i] = lerp(fromPts[i], toPts[i], t);
    }
    return SkPath::Raw({dst.data(), dst.size()}, from.verbs(), from.conicWeights(), fillType);
}
```

**步骤**

1. 验证路径可插值性
2. 获取源路径的填充类型
3. 提取源和目标路径的点数据
4. 对每个点进行线性插值
5. 使用插值后的点和原动词/权重创建新路径

### 权重参数转换

公共 API 使用 `weight` 参数，但内部使用 `1 - weight`：

```cpp
SkPath SkPath::makeInterpolate(const SkPath& ending, SkScalar weight) const {
    return Interpolate(*this, ending, 1 - weight).value_or(SkPath());
}
```

这样 `weight = 0` 表示当前路径，`weight = 1` 表示目标路径，符合直觉。

### 填充类型处理

插值结果使用源路径（`from`）的填充类型：

```cpp
const SkPathFillType fillType = from.getFillType();
```

如果两个路径的填充类型不同，由调用者负责处理。

### 返回值优化

提供两种返回方式：

1. **返回新对象**（`makeInterpolate`）：使用 `std::optional` 和 `value_or`
2. **输出参数**（`interpolate`）：避免返回值拷贝，提供更明确的成功/失败指示

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkPath` | 路径类，提供点、动词、权重访问 |
| `SkPoint` | 点数据类型 |
| `SkSpan` | 只读数组视图 |
| `std::vector` | 存储插值后的点 |
| `std::optional` | 表示可选返回值 |

**被依赖的模块**

| 模块 | 关系 |
|------|------|
| Chrome | 使用路径插值实现动画效果 |
| Android | 使用路径插值实现形状变形 |
| 动画系统 | 基于路径插值实现平滑过渡 |

## 设计模式与设计决策

### 自由函数模式

内部实现使用匿名命名空间中的自由函数：

- `CanInterpolate` 和 `Interpolate` 是独立函数
- 不依赖 `SkPath` 的私有成员
- 可以轻松提取到客户端代码

### 模板化通用算法

`span_equal` 使用模板支持不同类型：

- 适用于动词（`SkPathVerb`）和权重（`float`）
- 代码复用，类型安全
- 编译时优化

### 不可变性

插值函数不修改原路径：

- `const` 成员函数
- 返回新的路径对象
- 函数式编程风格

### 可选返回值

使用 `std::optional<SkPath>` 表示可能失败的操作：

- 明确表达"可能无结果"的语义
- 避免异常或特殊值
- 类型安全的错误处理

### 提取友好设计

代码设计便于提取到客户端：

- 注释明确说明可以拷贝到 Chrome/Android
- 不依赖 Skia 私有 API
- 自包含，易于移植

### 插值参数设计

`weight` 参数的含义：

- API 层面：`weight = 0` → 源路径，`weight = 1` → 目标路径
- 内部实现：使用 `1 - weight` 转换
- 符合用户直觉，与常见插值约定一致

## 性能考量

### 预检查优化

在执行插值前进行快速检查：

- 点数比较（O(1)）
- 动词和权重比较（O(n)，但通常很小）
- 避免不必要的点插值计算

### 内存分配

使用 `std::vector<SkPoint>` 存储插值点：

- 单次堆分配
- 预知大小，避免重新分配
- 使用移动语义返回

### 指针相等性检查

`span_equal` 检查指针是否相同：

- 如果两个路径共享数据，直接返回 `true`
- 避免不必要的逐元素比较

### 循环优化

点插值循环简单直接：

- 顺序访问内存，缓存友好
- 可被编译器向量化
- 无分支，流水线友好

### 适用场景

最佳使用场景：

- 路径变形动画（图标形状过渡）
- 矢量图形动画
- UI 形状过渡效果
- 路径关键帧插值

### 性能权衡

- **优势**：简单、快速、可预测
- **劣势**：要求路径结构完全相同（限制灵活性）
- **权衡**：适合已知可插值路径的动画

### 限制和约束

**不支持的情况**

- 不同动词序列的路径（无法插值）
- 不同点数的路径（无法对应）
- 不同圆锥曲线权重的路径（形状会扭曲）

**解决方案**

对于不可插值的路径，可以考虑：

- 路径分解和重组
- 使用多个路径片段分别插值
- 使用交叉淡入淡出（cross-fade）代替形状插值

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/core/SkPath.h` | 路径类定义和接口声明 |
| `src/core/SkPath.cpp` | 路径类主要实现 |
| `include/core/SkPoint.h` | 点数据类型 |
| `include/core/SkSpan.h` | 跨度模板类 |
| `include/core/SkPathTypes.h` | 路径类型（动词、填充类型等） |
