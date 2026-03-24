# FixedCountBufferUtils

> 源文件
> - src/gpu/tessellate/FixedCountBufferUtils.h
> - src/gpu/tessellate/FixedCountBufferUtils.cpp

## 概述

`FixedCountBufferUtils` 是 Skia GPU 镶嵌化（Tessellation）系统中用于固定数量顶点缓冲管理的工具类集合。该模块为三种不同的镶嵌化模式（填充曲线、填充楔形、描边）提供了静态工具函数，用于预分配实例属性空间、生成模板顶点和索引缓冲区，以支持基于实例化的 GPU 渲染。

固定数量镶嵌化（Fixed-Count Tessellation）是一种 GPU 渲染优化技术，它使用预先生成的顶点和索引模板，通过实例化渲染来高效地绘制大量曲线和路径。与传统的动态细分不同，固定数量方法使用固定的最大细分级别，并通过索引选择实际需要的细分级别。

该模块包含三个主要工具类：
- **FixedCountCurves** - 用于填充路径中的曲线镶嵌化
- **FixedCountWedges** - 用于带扇形三角形的路径填充镶嵌化
- **FixedCountStrokes** - 用于路径描边镶嵌化

## 架构位置

`FixedCountBufferUtils` 位于 Skia GPU 镶嵌化渲染系统的缓冲管理层：

```
skgpu::tess (镶嵌化渲染)
  ├── Tessellation (核心镶嵌化算法)
  ├── LinearTolerances (线性容差计算)
  ├── PatchWriter (实例属性写入)
  ├── FixedCountBufferUtils (缓冲管理工具 - 本模块)
  │   ├── FixedCountCurves
  │   ├── FixedCountWedges
  │   └── FixedCountStrokes
  └── 各种着色器和渲染路径
```

在渲染管线中的位置：
```
路径数据
  ↓
PatchWriter (写入实例属性)
  ← FixedCountBufferUtils::PreallocCount (预分配计算)
  ↓
GPU 实例化渲染
  ← 静态顶点缓冲 (FixedCountBufferUtils::WriteVertexBuffer)
  ← 静态索引缓冲 (FixedCountBufferUtils::WriteIndexBuffer)
  ↓
镶嵌化着色器 (根据实例属性和容差选择细分级别)
  ↓
光栅化输出
```

## 主要类与结构体

### FixedCountCurves

用于填充路径中曲线的固定数量镶嵌化工具类。

**特点：**
- 仅镶嵌化曲线本身，不包括填充内部空间的额外几何
- 需要配合其他技术填充曲线控制点之间的间隙
- 适用于复杂路径的曲线部分渲染

**主要方法：**
- `PreallocCount(int totalCombinedPathVerbCnt)` - 计算预分配实例数
- `VertexCount(const LinearTolerances&)` - 根据容差计算顶点数
- `VertexBufferSize() / IndexBufferSize()` - 返回缓冲区大小
- `WriteVertexBuffer(...) / WriteIndexBuffer(...)` - 写入静态缓冲区数据

### FixedCountWedges

用于带扇形三角形的路径填充镶嵌化工具类。

**特点：**
- 在曲线镶嵌化基础上添加扇形三角形（Fan Triangle）
- 所有曲线共享一个扇形顶点（Fan Point），形成楔形
- 与 `PatchAttribs::kFanPoint` 属性配合使用
- 适用于简单路径的单次绘制完整填充

**主要方法：**
- 提供与 `FixedCountCurves` 相同的接口
- 顶点缓冲额外包含扇形顶点
- 索引缓冲额外包含扇形三角形

### FixedCountStrokes

用于路径描边镶嵌化的工具类。

**特点：**
- 专门用于描边渲染，而非填充
- 顶点与连接点、端点、径向段、参数段相关
- 仅在不支持 `sk_VertexID` 内置变量时需要静态顶点缓冲
- 不使用索引缓冲（与曲线和楔形不同）

**常量：**
- `kMaxEdges = (1 << 14) - 1` - 最大边数（16383）
- `kMaxEdgesNoVertexIDs = 1024` - 无顶点 ID 支持时的最大边数

**主要方法：**
- `PreallocCount(...)` - 预分配计算（考虑分割和端点）
- `VertexCount(...)` - 根据容差计算顶点数
- `WriteVertexBuffer(...)` - 写入顶点 ID 回退缓冲区

## 公共 API 函数

### PreallocCount

```cpp
// FixedCountCurves
static constexpr int PreallocCount(int totalCombinedPathVerbCnt)

// FixedCountWedges
static constexpr int PreallocCount(int totalCombinedPathVerbCnt)

// FixedCountStrokes
static constexpr int PreallocCount(int totalCombinedPathVerbCnt)
```

**功能：** 在使用 `PatchWriter` 写入实例属性前，估算需要预分配的实例数量。

**参数：** `totalCombinedPathVerbCnt` - 所有路径的动词（verb）总数

**返回值：** 预分配的实例数量

**实现细节：**

**FixedCountCurves:**
```cpp
// 过度分配足够的曲线，假设 1/4 的曲线需要分割
// 每次分割产生 2 个新补丁：一个曲线补丁 + 一个连接三角形
// 即 + 2 * ((count + 3) / 4) == (count + 3) / 2
totalCombinedPathVerbCnt + (totalCombinedPathVerbCnt + 3) / 2
```

**FixedCountWedges:**
```cpp
// 过度分配足够的楔形，假设 1/4 需要分割
// ceil(maxWedges * 5/4) == (count * 5 + 3) / 4
(totalCombinedPathVerbCnt * 5 + 3) / 4
```

**FixedCountStrokes:**
```cpp
// 假设每个描边分割一次，并额外添加 8 个端点
// 由于需要在拐点、180度旋转点和高段数处分割，许多描边会被分割
(totalCombinedPathVerbCnt * 2) + 8
```

**溢出保护：** 所有实现都包含溢出检查，限制输入值在安全范围内。

### VertexCount

```cpp
// FixedCountCurves
static int VertexCount(const LinearTolerances& tolerances)

// FixedCountWedges
static int VertexCount(const LinearTolerances& tolerances)

// FixedCountStrokes
static int VertexCount(const LinearTolerances& tolerances)
```

**功能：** 根据累积的最坏情况容差，计算实例化索引绘制调用需要的顶点数量。

**参数：** `tolerances` - 线性容差对象，包含所需的细分级别

**返回值：** 顶点数量（传递给 `glDrawArraysInstanced` 或类似函数）

**实现细节：**

**FixedCountCurves:**
```cpp
// 确保细分级别不超过 kMaxResolveLevel
int resolveLevel = std::min(tolerances.requiredResolveLevel(), kMaxResolveLevel);
// 返回该级别的三角形数量 * 3（每个三角形 3 个顶点）
return NumCurveTrianglesAtResolveLevel(resolveLevel) * 3;
```

**FixedCountWedges:**
```cpp
// 曲线三角形 + 1 个扇形三角形
int resolveLevel = std::min(tolerances.requiredResolveLevel(), kMaxResolveLevel);
return (NumCurveTrianglesAtResolveLevel(resolveLevel) + 1) * 3;
```

**FixedCountStrokes:**
```cpp
// 每条边 2 个顶点，限制在 kMaxEdges 以内
return std::min(tolerances.requiredStrokeEdges(), kMaxEdges) * 2;
```

### WriteVertexBuffer

```cpp
static void WriteVertexBuffer(VertexWriter vertexWriter, size_t bufferSize)
```

**功能：** 填充静态顶点缓冲区的内容，该缓冲区作为实例化渲染的模板。

**参数：**
- `vertexWriter` - 顶点写入器对象
- `bufferSize` - 缓冲区大小（字节）

**FixedCountCurves 实现：**

生成"中间向外"（middle-out）顺序的顶点：
```
T = 0/1, 1/1,              // resolveLevel=0 (起点和终点)
    1/2,                   // resolveLevel=1 (中点)
    1/4, 3/4,              // resolveLevel=2
    1/8, 3/8, 5/8, 7/8,    // resolveLevel=3
    ...
```

每个顶点包含两个浮点数：
- `resolveLevel` - 细分级别
- `idx` - 在该级别中的索引

**FixedCountWedges 实现：**

首先写入扇形顶点：
```cpp
vertexWriter << -1.f << -1.f;  // 负值表示扇形顶点
```

然后调用 `FixedCountCurves::WriteVertexBuffer` 写入其余顶点。

**FixedCountStrokes 实现：**

写入顶点 ID 回退数据（用于不支持 `sk_VertexID` 的平台）：
```cpp
for (int i = 0; i < edgeCount; ++i) {
    vertexWriter << (float)i << (float)-i;  // 正负对，用于区分边的两侧
}
```

### WriteIndexBuffer

```cpp
static void WriteIndexBuffer(VertexWriter vertexWriter, size_t bufferSize)
```

**功能：** 填充静态索引缓冲区的内容，定义顶点的连接方式。

**参数：**
- `vertexWriter` - 顶点写入器（用于写入索引数据）
- `bufferSize` - 缓冲区大小（字节）

**实现细节（FixedCountCurves）：**

使用"中间向外"三角剖分（middle-out triangulation）连接顶点：

1. **细分级别 1：** 单个三角形 `[0, 2, 1]`（对应 T = [0, 1, 1/2]）

2. **细分级别 2..maxResolveLevel：**
   - 每个级别的三角形数量翻倍
   - 新三角形成对生成，共享上一级别的边
   - 第一个三角形共享左边
   - 第二个三角形共享右边

**示例（细分级别 2）：**
```
级别 1: [0, 2, 1]
级别 2: [0, 3, 1] 和 [1, 4, 2]
```

**FixedCountWedges 实现：**

首先写入扇形三角形：
```cpp
vertexWriter << (uint16_t)0 << (uint16_t)1 << (uint16_t)2;
```

然后调用 `write_curve_index_buffer_base_index` 写入曲线索引，`baseIndex` 设为 1（因为索引 0 被扇形顶点占用）。

**FixedCountStrokes：** 不提供索引缓冲区函数（描边不使用索引缓冲）。

### 缓冲区大小计算

**FixedCountCurves:**
```cpp
static constexpr size_t VertexBufferSize() {
    return (kMaxParametricSegments + 1) * 2 * sizeof(float);
}

static constexpr size_t IndexBufferSize() {
    return NumCurveTrianglesAtResolveLevel(kMaxResolveLevel) * 3 * sizeof(uint16_t);
}
```

**FixedCountWedges:**
```cpp
static constexpr size_t VertexBufferSize() {
    return ((kMaxParametricSegments + 1) + 1) * 2 * sizeof(float);
    // +1 for fan vertex
}

static constexpr size_t IndexBufferSize() {
    return (NumCurveTrianglesAtResolveLevel(kMaxResolveLevel) + 1) * 3 * sizeof(uint16_t);
    // +1 for fan triangle
}
```

**FixedCountStrokes:**
```cpp
static constexpr size_t VertexBufferSize() {
    return 2 * kMaxEdgesNoVertexIDs * sizeof(float);
}
```

## 内部实现细节

### 中间向外顶点布局

中间向外布局是一种巧妙的顶点组织方式，用于支持动态细分级别选择：

**优点：**
1. **无需重新生成缓冲区：** 所有细分级别共享同一缓冲区
2. **连续的级别范围：** 细分级别 N 使用级别 0..N 的所有顶点
3. **高效索引：** 索引缓冲区可以通过简单的公式计算偏移量

**顶点生成算法：**
```cpp
for (int resolveLevel = 0; resolveLevel <= maxResolveLevel; ++resolveLevel) {
    int numSegments = 1 << resolveLevel;  // 2^resolveLevel
    for (int i = (resolveLevel == 0 ? 0 : 1); i < numSegments; i += 2) {
        // 只写入奇数索引（偶数索引已在前面的级别中写入）
        float t = (float)i / numSegments;
        vertexWriter << (float)resolveLevel << (float)i;
    }
}
```

### 中间向外三角剖分

索引缓冲区的生成使用递归式的三角剖分策略：

**算法：**
```cpp
// 级别 1: 基础三角形
triangles[0] = {0, 2, 1};

// 级别 2..maxResolveLevel
for (int level = 2; level <= maxResolveLevel; ++level) {
    for (每个上一级别的三角形 [a, b, c]) {
        int newVertex1 = nextIndex++;
        int newVertex2 = nextIndex++;
        // 分裂为两个三角形
        triangles.push({a, newVertex1, b});
        triangles.push({b, newVertex2, c});
    }
}
```

**特点：**
- 每个级别的三角形数量是上一级别的两倍
- 新顶点总是插入在边的中点
- 保持拓扑连续性

### 描边顶点 ID 回退

对于不支持 `sk_VertexID` 的平台，需要显式提供顶点 ID：

```cpp
void WriteVertexBuffer(VertexWriter vertexWriter, size_t bufferSize) {
    int edgeCount = bufferSize / (sizeof(float) * 2);
    for (int i = 0; i < edgeCount; ++i) {
        vertexWriter << (float)i << (float)-i;
    }
}
```

**数据格式：**
- 每条边 2 个顶点
- 第一个顶点存储正值 ID：`i`
- 第二个顶点存储负值 ID：`-i`
- 着色器通过 ID 的符号判断顶点位于边的哪一侧

### 溢出保护

所有 `PreallocCount` 函数都包含溢出保护：

```cpp
// FixedCountCurves 示例
constexpr int kMaxVerbCount = std::numeric_limits<int>::max() >> 2;
totalCombinedPathVerbCnt = std::min(kMaxVerbCount, totalCombinedPathVerbCnt);
```

**作用：**
- 防止整数溢出导致的错误分配
- 将输入限制在安全范围内（通常是 `INT_MAX / 4`）
- 确保后续计算（如 `count * 2` 或 `count * 5/4`）不会溢出

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `src/gpu/tessellate/LinearTolerances.h` | 线性容差计算，确定细分级别 |
| `src/gpu/tessellate/Tessellation.h` | 核心镶嵌化算法和常量 |
| `src/gpu/BufferWriter.h` | `VertexWriter` 类型定义 |
| `src/base/SkMathPriv.h` | 数学工具（如 `SkPrevLog2`） |
| `<algorithm>` | `std::min` 等标准算法 |
| `<cstdint>` | `uint16_t` 等整数类型 |
| `<limits>` | `std::numeric_limits` |

### 被依赖关系

该模块被以下组件使用：
- **PatchWriter** - 使用 `PreallocCount` 预分配实例属性空间
- **VulkanResourceProvider / MtlResourceProvider** - 创建静态顶点和索引缓冲区
- **固定数量镶嵌化着色器** - 使用生成的缓冲区进行实例化渲染
- **路径渲染器** - 调用 `VertexCount` 确定绘制调用参数

## 设计模式与设计决策

### 静态工具类模式

所有类都禁用构造函数，仅包含静态方法：
```cpp
class FixedCountCurves {
    FixedCountCurves() = delete;  // 禁止实例化
public:
    static constexpr int PreallocCount(...) { ... }
    static void WriteVertexBuffer(...) { ... }
};
```

**优点：**
- 明确表示无状态工具类
- 避免误用（无法创建实例）
- 所有方法可内联，无虚函数开销

### 编译时常量表达式

大量使用 `constexpr` 和 `constexpr size_t` 返回值：
```cpp
static constexpr size_t VertexBufferSize() {
    return (kMaxParametricSegments + 1) * 2 * sizeof(float);
}
```

**优点：**
- 在编译时计算缓冲区大小
- 可用于静态数组声明
- 零运行时开销

### 过度分配启发式

`PreallocCount` 使用启发式算法过度分配：
- **FixedCountCurves:** 额外分配 50% 用于分割
- **FixedCountWedges:** 额外分配 25% 用于分割
- **FixedCountStrokes:** 翻倍并添加 8 个端点

**权衡：**
- 内存浪费 vs. 重新分配开销
- 大多数情况下避免动态扩展
- 未使用的空间不会提交到 GPU

### 中间向外布局

核心设计决策，影响整个渲染管线：

**优点：**
- 单一静态缓冲区支持所有细分级别
- GPU 友好的索引模式
- 简化着色器逻辑

**缺点：**
- 顶点顺序不直观
- 索引生成算法较复杂

### 类型安全的顶点写入

使用 `VertexWriter` 类而非原始指针：
```cpp
vertexWriter << (float)resolveLevel << (float)idx;
```

**优点：**
- 类型检查，减少错误
- 自动推进指针
- 支持复杂类型（如数组）

### 三模式设计

将固定数量镶嵌化分为三种模式（Curves、Wedges、Strokes）：

**优点：**
- 每种模式针对特定用例优化
- 代码清晰，职责分明
- 易于独立测试和调试

**缺点：**
- 代码有一定重复（通过私有辅助函数缓解）
- 需要在调用侧选择正确的模式

## 性能考量

### 预分配策略

1. **避免动态扩展**
   - 启发式过度分配减少 `realloc` 调用
   - 内存局部性更好，缓存友好

2. **内存使用权衡**
   - 过度分配通常在 25%-100% 范围
   - 对于大规模路径，节省的 CPU 时间远大于内存开销

### 静态缓冲区复用

1. **GPU 内存效率**
   - 静态缓冲区在应用启动时创建一次
   - 所有绘制调用共享相同缓冲区
   - 通常只需几十 KB（如 `kMaxParametricSegments = 1024`）

2. **驱动优化**
   - 静态缓冲区可被驱动优化（如常驻 VRAM）
   - 减少绑定切换开销

### 中间向外布局优化

1. **顶点重用**
   - 低细分级别的顶点被高细分级别重用
   - 减少顶点着色器调用

2. **索引缓存友好**
   - 三角形按细分级别组织
   - 相邻三角形访问相近的顶点，提高缓存命中率

### 描边渲染优化

1. **顶点 ID 内置支持检测**
   - 优先使用 `sk_VertexID` 内置变量（无需缓冲区）
   - 仅在不支持时使用回退缓冲区

2. **边数限制**
   - `kMaxEdges = 16383` 确保使用 `int16_t` 索引
   - `kMaxEdgesNoVertexIDs = 1024` 控制回退缓冲区大小

### 最佳实践

1. **预计算缓冲区大小**
   - 使用 `constexpr` 函数在编译时计算
   - 避免运行时计算开销

2. **批量绘制**
   - 累积多个路径的实例属性
   - 单次绘制调用渲染所有实例

3. **细分级别选择**
   - 根据 `LinearTolerances` 动态选择
   - 避免过度细分（浪费 GPU）和欠细分（视觉质量差）

4. **缓冲区生命周期管理**
   - 静态缓冲区在应用启动时创建，退出时销毁
   - 实例属性缓冲区每帧重新填充

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/tessellate/Tessellation.h` | 核心算法 | 定义 `kMaxResolveLevel`、`kMaxParametricSegments` 等常量 |
| `src/gpu/tessellate/LinearTolerances.h` | 容差计算 | 计算所需的细分级别，输入到 `VertexCount` |
| `src/gpu/tessellate/PatchWriter.h` | 实例写入 | 使用 `PreallocCount` 预分配空间，写入实例属性 |
| `src/gpu/BufferWriter.h` | 写入工具 | `VertexWriter` 类型定义 |
| `src/gpu/graphite/vk/VulkanResourceProvider.h` | Vulkan 后端 | 创建和管理 Vulkan 缓冲区 |
| `src/gpu/graphite/mtl/MtlResourceProvider.h` | Metal 后端 | 创建和管理 Metal 缓冲区 |
| `src/gpu/tessellate/shaders/*` | 着色器 | 使用生成的缓冲区进行镶嵌化渲染 |
| `src/gpu/tessellate/PathCurveTessellator.h` | 曲线镶嵌器 | 使用 `FixedCountCurves` 渲染路径曲线 |
| `src/gpu/tessellate/PathWedgeTessellator.h` | 楔形镶嵌器 | 使用 `FixedCountWedges` 渲染路径填充 |
| `src/gpu/tessellate/StrokeTessellator.h` | 描边镶嵌器 | 使用 `FixedCountStrokes` 渲染路径描边 |
