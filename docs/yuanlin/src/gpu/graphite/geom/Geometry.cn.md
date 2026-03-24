# Geometry - 几何类型联合容器

> 源文件: `src/gpu/graphite/geom/Geometry.h`

## 概述

Geometry 是 Skia Graphite 渲染后端中的几何类型联合容器，能够存储 Shape、SkVertices、SubRunData（文本子运行）、EdgeAAQuad（带边缘AA的四边形）、CoverageMaskShape（覆盖率遮罩形状）和 AnalyticBlurMask（解析模糊遮罩）六种不同的几何类型。

Geometry 使用 C++ 匿名联合体（union）和类型标签实现类型安全的变体容器。它是 Graphite 绘制管线中几何数据从 Device 传递到 DrawPass 的标准载体，每个绘制操作（DrawCommand）都包含一个 Geometry 实例来描述其几何形状。

## 架构位置

```
Graphite 绘制管线
  -> Device::drawGeometry()
    -> Geometry (统一几何容器)
      +--> Shape         (路径形状)
      +--> SkVertices    (顶点网格)
      +--> SubRunData    (文本字形)
      +--> EdgeAAQuad    (AA四边形)
      +--> CoverageMaskShape (覆盖率遮罩)
      +--> AnalyticBlurMask  (解析模糊)
```

Geometry 是所有绘制操作几何数据的统一入口点，通过类型标签区分实际存储的几何类型。

## 主要类与结构体

### `Geometry`
- **Type 枚举**: `kEmpty, kShape, kVertices, kSubRun, kEdgeAAQuad, kCoverageMaskShape, kAnalyticBlur`
- **存储**: 使用 C++ 匿名 union 存储所有可能的几何类型
- **类型标签**: `fType` 成员变量标识当前活跃的联合成员
- **拷贝/移动语义**: 支持拷贝构造、拷贝赋值、移动构造和移动赋值

## 公共 API 函数

### 构造函数
| 函数 | 说明 |
|------|------|
| `Geometry()` | 默认构造，类型为 kEmpty |
| `Geometry(const Shape&)` | 从 Shape 构造 |
| `Geometry(const SubRunData&)` | 从 SubRunData 构造 |
| `Geometry(sk_sp<SkVertices>)` | 从 SkVertices 构造 |
| `Geometry(const EdgeAAQuad&)` | 从 EdgeAAQuad 构造 |
| `Geometry(const CoverageMaskShape&)` | 从 CoverageMaskShape 构造 |
| `Geometry(const AnalyticBlurMask&)` | 从 AnalyticBlurMask 构造 |

### 类型查询
| 函数 | 说明 |
|------|------|
| `type()` | 返回当前存储的几何类型 |
| `isShape()` / `isVertices()` / `isSubRun()` 等 | 类型检查快捷方法 |
| `isEmpty()` | 判断是否为空（包括空的非反向 Shape） |

### 类型安全访问
| 函数 | 说明 |
|------|------|
| `shape()` | 获取 Shape 引用（断言当前类型为 Shape） |
| `subRunData()` | 获取 SubRunData 引用 |
| `edgeAAQuad()` | 获取 EdgeAAQuad 引用 |
| `coverageMaskShape()` | 获取 CoverageMaskShape 引用 |
| `analyticBlurMask()` | 获取 AnalyticBlurMask 引用 |
| `vertices()` | 获取 SkVertices 原始指针 |
| `refVertices()` | 获取 SkVertices 的 sk_sp 引用 |

### 设置函数
| 函数 | 说明 |
|------|------|
| `setShape(const Shape&)` | 设置为 Shape 类型 |
| `setSubRun(const SubRunData&)` | 设置为 SubRunData 类型 |
| `setVertices(sk_sp<SkVertices>)` | 设置为 SkVertices 类型 |
| `setEdgeAAQuad(const EdgeAAQuad&)` | 设置为 EdgeAAQuad 类型 |
| `setCoverageMaskShape(const CoverageMaskShape&)` | 设置为 CoverageMaskShape 类型 |
| `setAnalyticBlur(const AnalyticBlurMask&)` | 设置为 AnalyticBlurMask 类型 |

### 统一接口
| 函数 | 说明 |
|------|------|
| `bounds()` | 根据当前类型调度到对应类型的 bounds() 方法 |

## 内部实现细节

### Placement New 构造
当类型切换时（例如从 Shape 变为 SubRunData），Geometry 先析构旧对象，再使用 placement new 在 union 内存上构造新对象：
```cpp
void setSubRun(const SubRunData& subRun) {
    if (fType == Type::kSubRun) {
        fSubRunData = subRun;  // 同类型直接赋值
    } else {
        this->setType(Type::kSubRun);    // 析构旧对象
        new (&fSubRunData) SubRunData(subRun);  // placement new
    }
}
```

### setType 的析构逻辑
`setType()` 方法在类型切换时负责析构当前活跃的联合成员。它利用了 `EdgeAAQuad` 是平凡析构类型（`trivially_destructible`）的特性，对其跳过显式析构调用（通过 `static_assert` 验证）。

### 移动语义实现
移动构造/赋值在移动数据后将源对象设置为 `kEmpty` 状态。对于 `SkVertices` 类型，使用 `std::move` 转移 `sk_sp` 所有权。

### isEmpty 的特殊判断
`isEmpty()` 不仅检查 `kEmpty` 类型，还检查是否为空的非反向 Shape。反向 Shape 即使几何为空，在渲染时仍然会影响整个画布，因此不被视为"空"。

### bounds() 的类型调度
bounds() 使用 switch-case 根据当前类型调用对应类型的边界计算方法。对于 `kAnalyticBlur` 类型调用的是 `drawBounds()` 而非 `bounds()`，反映了该类型特殊的边界语义。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/geom/Shape.h` | Shape 几何类型 |
| `src/gpu/graphite/geom/SubRunData.h` | 文本子运行数据类型 |
| `src/gpu/graphite/geom/EdgeAAQuad.h` | 边缘AA四边形类型 |
| `src/gpu/graphite/geom/CoverageMaskShape.h` | 覆盖率遮罩类型 |
| `src/gpu/graphite/geom/AnalyticBlurMask.h` | 解析模糊遮罩类型 |
| `src/gpu/graphite/geom/Rect.h` | bounds() 返回类型 |
| `include/core/SkVertices.h` | 顶点网格类型 |
| `include/core/SkRefCnt.h` | sk_sp 智能指针 |

## 设计模式与设计决策

1. **标签联合（Tagged Union）**: 使用 C++ union + 类型枚举标签实现变体容器，替代 `std::variant`。这是因为需要手动控制构造/析构行为，且 union 的内存布局更紧凑可控。

2. **显式生命周期管理**: 由于 union 中包含非平凡析构类型（Shape、SubRunData、sk_sp），需要手动管理析构。`setType()` 是唯一负责调用析构的入口点。

3. **类型安全访问**: 所有访问器都包含 `SkASSERT` 断言验证类型匹配，在调试构建中提供运行时安全检查。

4. **explicit 构造函数**: 所有从具体类型构造的构造函数都标记为 `explicit`，防止隐式类型转换。

## 性能考量

1. **union 大小**: Geometry 的大小等于最大联合成员的大小加上类型标签（1 字节）和 padding。SubRunData 和 CoverageMaskShape 是较大的成员。
2. **避免虚函数**: 使用标签联合而非继承多态，避免了虚函数表指针和虚调用开销。
3. **类型切换成本**: 在不同几何类型之间切换需要析构旧对象和构造新对象，但这通常只在绘制操作初始化时发生。
4. **bounds() 分发**: switch-case 分发在类型数量有限的情况下通常比虚函数调用更快（编译器可优化为跳转表）。

## 相关文件

- `src/gpu/graphite/geom/Shape.h` - 路径形状类型
- `src/gpu/graphite/geom/SubRunData.h` - 文本子运行数据
- `src/gpu/graphite/geom/EdgeAAQuad.h` - 带边缘AA的四边形
- `src/gpu/graphite/geom/CoverageMaskShape.h` - 覆盖率遮罩形状
- `src/gpu/graphite/geom/AnalyticBlurMask.h` - 解析模糊遮罩
- `src/gpu/graphite/Device.h` - 创建 Geometry 的主要来源
- `src/gpu/graphite/DrawPass.h` - 处理 Geometry 的绘制阶段
