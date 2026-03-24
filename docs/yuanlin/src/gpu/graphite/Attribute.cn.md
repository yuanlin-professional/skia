# Attribute

> 源文件
> - src/gpu/graphite/Attribute.h

## 概述

`Attribute` 和 `Varying` 是 Graphite 渲染系统中用于描述顶点属性和着色器间插值变量的核心数据结构。它们定义了 CPU 侧数据格式与 GPU 着色器语言类型之间的映射关系，支持 Graphite 的渲染管线构建。

**主要功能**：
- **顶点属性描述**：定义顶点/实例数据的布局和类型
- **类型映射**：连接 CPU 数据格式（`VertexAttribType`）和 GPU 类型（`SkSLType`）
- **Varying 定义**：描述顶点和片段着色器间的插值变量
- **插值模式**：支持透视、线性和平坦插值

## 架构位置

```
Graphite Rendering Pipeline
├── RenderStep (使用 Attribute 定义顶点布局)
│   └── AttributeSet
│       └── Attribute (本类)
├── PipelineDataGatherer (收集顶点数据)
└── ShaderCodeSource (使用 Varying 定义着色器接口)
    └── Varying (本类)
```

## 主要类与结构体

### Attribute 类

```cpp
class Attribute
```

**用途**：描述单个顶点或实例属性

**关键成员**：

| 类型 | 名称 | 说明 |
|------|------|------|
| `const char*` | `fName` | 属性名称（GLSL 变量名） |
| `VertexAttribType` | `fCPUType` | CPU 侧数据类型 |
| `SkSLType` | `fGPUType` | GPU 着色器语言类型 |

### Varying 类

```cpp
class Varying
```

**用途**：描述顶点和片段着色器间的插值变量

**关键成员**：

| 类型 | 名称 | 说明 |
|------|------|------|
| `const char*` | `fName` | Varying 名称 |
| `SkSLType` | `fGPUType` | 着色器语言类型 |
| `Interpolation` | `fInterpolation` | 插值模式 |

### Interpolation 枚举

```cpp
enum class Interpolation {
    kPerspective,  // 透视正确插值（默认）
    kLinear,       // 屏幕空间线性插值
    kFlat          // 平坦插值（无插值）
}
```

## 公共 API 函数

### Attribute 接口

#### 1. 构造函数

```cpp
constexpr Attribute() = default
```
默认构造，创建未初始化的属性。

```cpp
constexpr Attribute(const char* name, VertexAttribType cpuType, SkSLType gpuType)
```
创建属性描述，断言 `name` 非空且 `gpuType` 不为 `kVoid`。

#### 2. 查询方法

```cpp
constexpr bool isInitialized() const
```
返回属性是否已初始化（`fGPUType != SkSLType::kVoid`）。

```cpp
constexpr const char* name() const
constexpr VertexAttribType cpuType() const
constexpr SkSLType gpuType() const
```
获取属性的名称、CPU 类型和 GPU 类型。

#### 3. 尺寸计算

```cpp
constexpr size_t size() const
```
返回属性在顶点缓冲中的字节大小（调用 `VertexAttribTypeSize(fCPUType)`）。

```cpp
constexpr size_t sizeAlign4() const
```
返回 4 字节对齐后的大小（使用 `SkAlign4()`），用于满足 GPU 对齐要求。

### Varying 接口

#### 1. 构造函数

```cpp
constexpr Varying() = default
```
默认构造，创建未初始化的 varying。

```cpp
constexpr Varying(
    const char* name,
    SkSLType gpuType,
    Interpolation interpolation = Interpolation::kPerspective
)
```

**功能**：创建 varying 描述

**自动修正**：
- 如果 `gpuType` 是整型且 `interpolation` 为 `kPerspective`，自动改为 `kFlat`
- 整型不支持 `kLinear`（会触发断言）

**断言检查**：
- `name` 非空且 `gpuType` 不为 `kVoid`
- `gpuType` 必须是标量或向量类型
- 整型只能使用 `kFlat` 或 `kPerspective`（后者会被修正为 `kFlat`）

#### 2. 查询方法

```cpp
constexpr bool isInitialized() const
constexpr const char* name() const
constexpr SkSLType gpuType() const
constexpr Interpolation interpolation() const
```

## 内部实现细节

### 类型系统映射

**CPU 到 GPU 类型映射示例**：

| CPU 类型 (`VertexAttribType`) | GPU 类型 (`SkSLType`) | 用途 |
|-------------------------------|----------------------|------|
| `kFloat` | `kFloat` | 单精度浮点 |
| `kFloat2` | `kFloat2` | 2D 向量 |
| `kFloat3` | `kFloat3` | 3D 向量（位置） |
| `kFloat4` | `kFloat4` | 4D 向量（颜色） |
| `kUByte4_norm` | `kHalf4` | 归一化字节颜色 |
| `kUShort2_norm` | `kHalf2` | 归一化 UV 坐标 |

### 插值模式的自动修正

```cpp
fInterpolation(SkSLTypeIsIntegralType(gpuType) ? Interpolation::kFlat : interpolation)
```

**逻辑**：
- 整型变量强制使用 `kFlat` 插值（硬件限制）
- 浮点型变量保持用户指定的插值模式

### 对齐计算

```cpp
constexpr size_t sizeAlign4() const { return SkAlign4(this->size()); }
```

**原因**：
- GPU 通常要求 4 字节对齐
- Metal 和 D3D12 有严格的对齐要求
- Vulkan 推荐对齐以提高性能

### constexpr 设计

所有方法标记为 `constexpr`，支持：
- 编译期常量表达式
- 零运行时开销
- 更好的优化机会

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkSLTypeShared` | `SkSLType` 枚举和类型查询函数 |
| `DrawTypes` | `VertexAttribType` 定义 |
| `SkAlign` | 对齐计算工具 |
| `SkAssert` | 编译期和运行期断言 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `RenderStep` | 定义顶点属性布局 |
| `ShaderCodeSource` | 生成着色器代码 |
| `PipelineDataGatherer` | 收集顶点数据 |
| `UniformManager` | 处理 varying 接口 |

## 设计模式与设计决策

### 1. 值语义设计

```cpp
constexpr Attribute(const Attribute&) = default;
Attribute& operator=(const Attribute&) = default;
```

- 支持高效拷贝
- 无动态分配
- 适合嵌入到容器中

### 2. 类型安全

通过强类型枚举（`VertexAttribType` 和 `SkSLType`）避免类型混淆：
```cpp
constexpr Attribute(const char* name, VertexAttribType cpuType, SkSLType gpuType)
```

### 3. 编译期验证

使用 `constexpr` 和 `SkASSERT` 在编译期捕获错误：
```cpp
SkASSERT(name && gpuType != SkSLType::kVoid);
SkASSERT(SkSLTypeVecLength(gpuType) >= 1); // 只允许标量/向量
```

### 4. 自动类型修正

整型 varying 自动使用 `kFlat` 插值：
```cpp
fInterpolation(SkSLTypeIsIntegralType(gpuType) ? Interpolation::kFlat : interpolation)
```

**设计原因**：
- 符合 GPU 硬件限制
- 避免用户错误配置
- 简化 API 使用

### 5. 不可变性

所有成员变量为私有，只提供 `const` 访问器：
- 防止运行时修改
- 支持编译期常量
- 提高代码安全性

## 性能考量

### 1. 零开销抽象

```cpp
constexpr size_t size() const { return VertexAttribTypeSize(fCPUType); }
```

- 所有计算在编译期完成
- 运行时等价于直接访问常量
- 无虚函数调用开销

### 2. 内存布局优化

```cpp
struct Attribute {
    const char* fName;        // 8 字节
    VertexAttribType fCPUType; // 1 字节
    SkSLType fGPUType;        // 1 字节
    // 6 字节填充
};
```

总大小：16 字节（针对 64 位系统）

### 3. 对齐优化

`sizeAlign4()` 确保顶点数据满足 GPU 对齐要求：
- 减少未对齐访问导致的性能损失
- 提高内存带宽利用率
- 兼容不同 GPU 架构

### 4. 编译期常量传播

```cpp
static constexpr Attribute kPosition{"position", VertexAttribType::kFloat3, SkSLType::kFloat3};
```

编译器可以将整个属性描述内联为常量。

### 5. 类型查询开销

`SkSLTypeIsIntegralType()` 等函数通常实现为 switch-case，编译器优化后接近 O(1)。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/DrawTypes.h` | 依赖 | 定义 `VertexAttribType` |
| `src/core/SkSLTypeShared.h` | 依赖 | 定义 `SkSLType` |
| `src/gpu/graphite/RenderStep.h` | 使用者 | 定义顶点属性集 |
| `src/gpu/graphite/Renderer.h` | 使用者 | 组合多个 RenderStep |
| `src/gpu/graphite/PipelineDataGatherer.h` | 使用者 | 收集顶点数据 |
| `src/gpu/graphite/ShaderCodeSource.h` | 使用者 | 生成着色器代码 |
| `include/private/base/SkAlign.h` | 依赖 | 对齐计算 |
| `include/private/base/SkAssert.h` | 依赖 | 断言宏 |
