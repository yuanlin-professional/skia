# GrColorInfo

> 源文件
> - src/gpu/ganesh/GrColorInfo.h
> - src/gpu/ganesh/GrColorInfo.cpp

## 概述

`GrColorInfo` 是 Ganesh GPU 后端中用于封装颜色解释所需的全部信息的类。它整合了颜色类型（`GrColorType`）、透明度类型（`SkAlphaType`）和颜色空间（`SkColorSpace`）三个关键属性，并缓存了从 sRGB 颜色空间的转换信息。

该类的主要作用是提供一个统一的接口来处理 GPU 渲染中的颜色信息，简化颜色管理和转换操作。通过预先计算和缓存从 sRGB 的颜色空间转换（`GrColorSpaceXform`），该类优化了常见的颜色转换场景，因为 sRGB 是最常用的源颜色空间（如 `SkColor`、网络图像等）。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrColorInfo` 位于颜色管理层：

```
GrRecordingContext
    └── GrColorInfo (颜色信息封装)
        ├── GrColorType (GPU 颜色类型)
        ├── SkAlphaType (透明度类型)
        └── GrColorSpaceXform (颜色空间转换)
```

该类被广泛用于各种 GPU 渲染组件中，包括纹理、渲染目标、片段处理器等，作为颜色配置的标准表示。

## 主要类与结构体

### GrColorInfo

该类是颜色信息的完整封装。

**继承关系：** 无继承关系，独立的值类型。

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorSpace` | `sk_sp<SkColorSpace>` | 颜色空间，定义颜色的解释方式 |
| `fColorXformFromSRGB` | `sk_sp<GrColorSpaceXform>` | 从 sRGB 到当前颜色空间的转换，缓存常用转换 |
| `fColorType` | `GrColorType` | GPU 颜色类型，定义像素格式 |
| `fAlphaType` | `SkAlphaType` | 透明度类型（预乘、非预乘、不透明、未知） |

## 公共 API 函数

### 构造函数

```cpp
GrColorInfo();
GrColorInfo(const GrColorInfo&);
GrColorInfo(GrColorType, SkAlphaType, sk_sp<SkColorSpace>);
/* implicit */ GrColorInfo(const SkColorInfo&);
```

**功能：** 提供多种构造方式来创建颜色信息对象。

- **默认构造函数**：创建无效的颜色信息（`GrColorType::kUnknown`）
- **拷贝构造函数**：复制另一个颜色信息对象
- **完整构造函数**：指定所有三个颜色属性
- **隐式转换构造**：从 Skia 的 `SkColorInfo` 转换（用于 CPU 和 GPU 之间的互操作）

完整构造函数还会预先计算从 sRGB 的颜色空间转换，这是该类的核心优化。

### 比较运算符

```cpp
bool operator==(const GrColorInfo& that) const;
bool operator!=(const GrColorInfo& that) const;
```

**功能：** 比较两个颜色信息对象是否相等。

相等判断基于：
- 颜色类型相同
- 透明度类型相同
- 颜色空间相同（使用 `SkColorSpace::Equals()` 进行深度比较）

### 属性访问器

```cpp
GrColorType colorType() const;
SkAlphaType alphaType() const;
SkColorSpace* colorSpace() const;
sk_sp<SkColorSpace> refColorSpace() const;
```

**功能：** 提供对内部属性的只读访问。

### 颜色空间转换访问

```cpp
GrColorSpaceXform* colorSpaceXformFromSRGB() const;
sk_sp<GrColorSpaceXform> refColorSpaceXformFromSRGB() const;
```

**功能：** 获取预先计算的从 sRGB 的颜色空间转换对象。这是性能优化的关键，避免重复创建相同的转换。

### 查询方法

```cpp
bool isLinearlyBlended() const;
bool isAlphaOnly() const;
bool isValid() const;
```

**功能：** 提供关于颜色信息的各种查询。

- `isLinearlyBlended()`: 返回颜色空间是否使用线性 gamma（用于正确的颜色混合）
- `isAlphaOnly()`: 返回颜色类型是否仅表示透明度通道
- `isValid()`: 返回颜色信息是否有效（颜色类型和透明度类型均非未知）

### 修改方法

```cpp
GrColorInfo makeColorType(GrColorType ct) const;
```

**功能：** 创建一个新的颜色信息对象，使用不同的颜色类型但保持相同的透明度类型和颜色空间。这是一个不可变对象的修改模式（返回新对象而非修改自身）。

## 内部实现细节

### sRGB 转换缓存

在完整构造函数中，代码会立即创建从 sRGB 到目标颜色空间的转换：

```cpp
fColorXformFromSRGB = GrColorSpaceXform::Make(sk_srgb_singleton(), kUnpremul_SkAlphaType,
                                              fColorSpace.get(),   kUnpremul_SkAlphaType);
```

这个设计决策基于观察：sRGB 是最常见的源颜色空间（`SkColor`、PNG/JPEG 图像等），因此预先计算这个转换可以显著提高性能。转换使用 `kUnpremul_SkAlphaType` 是因为颜色空间转换通常在非预乘的颜色上进行。

### 从 SkColorInfo 的转换

隐式转换构造函数使用 `SkColorTypeToGrColorType()` 将 Skia 的 CPU 颜色类型映射到 GPU 颜色类型：

```cpp
GrColorInfo::GrColorInfo(const SkColorInfo& ci)
        : GrColorInfo(SkColorTypeToGrColorType(ci.colorType()),
                      ci.alphaType(),
                      ci.refColorSpace()) {}
```

这允许在 CPU 和 GPU 代码路径之间无缝传递颜色信息。

### 默认成员和特殊函数

该类使用编译器生成的默认实现：
- 拷贝赋值运算符
- 析构函数

这些函数在 `.cpp` 文件中显式声明为 `= default`，这是一种现代 C++ 的最佳实践，确保编译器能够生成最优化的实现。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrColorType` | 定义 GPU 颜色像素格式 |
| `SkAlphaType` | 定义透明度类型枚举 |
| `SkColorSpace` | Skia 颜色空间表示 |
| `GrColorSpaceXform` | GPU 颜色空间转换实现 |
| `SkColorInfo` | Skia CPU 颜色信息 |
| `SkColorSpacePriv` | 访问内部颜色空间工具（如 `sk_srgb_singleton()`） |

### 被依赖的模块

`GrColorInfo` 被广泛使用于：

| 模块 | 使用方式 |
|------|---------|
| `GrSurfaceProxy` | 描述表面的颜色配置 |
| `GrTextureProxy` | 纹理的颜色信息 |
| `GrRenderTargetProxy` | 渲染目标的颜色配置 |
| `GrFragmentProcessor` | 片段处理器的输入/输出颜色信息 |
| `GrColorSpaceXform` | 创建颜色空间转换 |
| `GrProgramInfo` | 程序配置中的颜色信息 |

## 设计模式与设计决策

### 值语义

`GrColorInfo` 设计为值类型而非引用类型，这意味着：
- 可以按值传递和存储
- 拷贝开销较低（只包含智能指针和枚举）
- 简化了所有权管理

这种设计简化了使用，因为用户不需要担心对象的生命周期管理。

### 不可变性

虽然该类提供了拷贝和赋值操作，但大部分方法是 `const` 的，且 `makeColorType()` 返回新对象而非修改自身。这种设计倾向于不可变性，有助于：
- 线程安全（多个线程可以安全地读取同一个对象）
- 减少意外修改
- 更易于推理代码行为

### 缓存优化

预先计算 sRGB 转换是一种缓存优化策略。这基于以下观察：
- sRGB 是最常见的源颜色空间
- 颜色空间转换计算成本高
- 多次使用同一个 `GrColorInfo` 对象时避免重复计算

这是以空间换时间的经典权衡，每个 `GrColorInfo` 对象额外存储一个智能指针（8 字节），换取避免重复计算转换矩阵。

### 隐式转换

提供从 `SkColorInfo` 的隐式转换构造函数是一个便利性设计，允许：
```cpp
void someFunction(const GrColorInfo& ci);
SkColorInfo skci = ...;
someFunction(skci);  // 自动转换
```

这简化了 CPU 和 GPU 代码之间的互操作。

## 性能考量

### sRGB 转换预计算

通过在构造时计算 sRGB 转换，该类避免了运行时的重复计算。对于频繁使用的颜色信息对象，这可以显著减少 CPU 开销。

### 智能指针开销

使用 `sk_sp<SkColorSpace>` 和 `sk_sp<GrColorSpaceXform>` 涉及引用计数操作。虽然有一定开销，但相比创建新的颜色空间对象，这个开销是可接受的。

### 相等性比较

相等性比较需要深度比较颜色空间（通过 `SkColorSpace::Equals()`），这可能涉及比较转换矩阵和传输函数。对于性能敏感的场景，应考虑缓存比较结果。

### 线性混合查询

`isLinearlyBlended()` 查询颜色空间的 gamma 曲线，这对于正确的混合至关重要。在非线性颜色空间中混合会导致视觉上不正确的结果。

### 内存占用

每个 `GrColorInfo` 对象占用约 32 字节（两个智能指针 + 两个 4 字节枚举 + padding），这对于大多数场景是可接受的。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | 定义 `GrColorType` 枚举 |
| `include/core/SkAlphaType.h` | 依赖 | 定义透明度类型 |
| `include/core/SkColorSpace.h` | 依赖 | Skia 颜色空间类 |
| `src/gpu/ganesh/GrColorSpaceXform.h` | 依赖 | GPU 颜色空间转换 |
| `src/core/SkColorSpacePriv.h` | 依赖 | 内部颜色空间工具 |
| `include/core/SkImageInfo.h` | 依赖 | 定义 `SkColorInfo` |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 使用者 | 表面代理使用颜色信息 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 使用者 | 片段处理器使用颜色信息 |
