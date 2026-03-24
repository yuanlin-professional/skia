# SkMesh

> 源文件: include/core/SkMesh.h, src/core/SkMesh.cpp

## 概述

`SkMesh` 是 Skia 的自定义网格渲染系统,允许开发者使用自定义着色器定义顶点属性、变量插值和片段着色逻辑。该系统由两个核心类组成:`SkMeshSpecification` 定义网格的数据结构和着色器程序,`SkMesh` 则包含实际的顶点数据、索引数据和 uniform 参数。

该模块将 SkSL(Skia Shader Language)与可编程网格管线结合,支持三角形和三角形带拓扑,提供了比传统路径更灵活的自定义渲染能力。网格可以通过 `SkCanvas::drawMesh()` 绘制,并与 `SkShader`、`SkBlender` 等 Skia 组件无缝集成。

## 架构位置

`SkMesh` 位于 Skia 核心 API 层,是可编程渲染管线的重要组成部分:

```
include/core/
├── SkCanvas.h              # 提供 drawMesh() 接口
├── SkMesh.h                # 网格规范和网格类(公共 API)
└── SkRuntimeEffect.h       # 提供 Uniform/Child 类型定义

src/core/
├── SkMesh.cpp              # 网格实现(本模块)
├── SkMeshPriv.h            # 内部辅助类型
└── SkRuntimeEffectPriv.h  # Runtime effect 私有功能

src/sksl/
└── SkSLCompiler.h          # 编译顶点和片段着色器
```

该模块桥接了高层绘图 API(Canvas)和底层着色器编译系统(SkSL),是自定义渲染能力的核心。

## 主要类与结构体

### SkMeshSpecification

网格规范类,定义顶点结构和着色器程序。

**继承关系**: `SkNVRefCnt<SkMeshSpecification>` ← `SkMeshSpecification`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAttributes` | `std::vector<Attribute>` | 顶点属性列表 |
| `fVaryings` | `std::vector<Varying>` | 顶点着色器输出的变量 |
| `fUniforms` | `std::vector<Uniform>` | Uniform 变量列表 |
| `fChildren` | `std::vector<Child>` | 子效果(shader/blender/colorFilter) |
| `fVS` | `std::unique_ptr<const SkSL::Program>` | 编译后的顶点着色器 |
| `fFS` | `std::unique_ptr<const SkSL::Program>` | 编译后的片段着色器 |
| `fStride` | `size_t` | 顶点步长(字节) |
| `fHash` | `uint32_t` | 规范的哈希值 |
| `fColorType` | `ColorType` | 片段着色器颜色输出类型(None/Half4/Float4) |
| `fColorSpace` | `sk_sp<SkColorSpace>` | 输出颜色空间 |
| `fAlphaType` | `SkAlphaType` | Alpha 类型(Premul/Unpremul) |

### SkMesh

网格实例,包含实际的顶点/索引数据和绘制参数。

**继承关系**: 无(值类型)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSpec` | `sk_sp<SkMeshSpecification>` | 关联的网格规范 |
| `fVB` | `sk_sp<VertexBuffer>` | 顶点缓冲区 |
| `fIB` | `sk_sp<IndexBuffer>` | 索引缓冲区(可选) |
| `fUniforms` | `sk_sp<const SkData>` | Uniform 数据 |
| `fChildren` | `STArray<2, ChildPtr>` | 子效果实例 |
| `fVOffset` / `fVCount` | `size_t` | 顶点偏移和数量 |
| `fIOffset` / `fICount` | `size_t` | 索引偏移和数量 |
| `fMode` | `Mode` | 拓扑模式(Triangles/TriangleStrip) |
| `fBounds` | `SkRect` | 网格边界 |

### Attribute

顶点属性描述。

| 成员 | 类型 | 说明 |
|------|------|------|
| `type` | `Type` | 属性类型(Float/Float2/Float3/Float4/UByte4_unorm) |
| `offset` | `size_t` | 在顶点中的字节偏移 |
| `name` | `SkString` | 属性名称 |

### Varying

顶点着色器输出到片段着色器的插值变量。

| 成员 | 类型 | 说明 |
|------|------|------|
| `type` | `Type` | 变量类型(Float/Float2/Float3/Float4/Half/Half2/Half3/Half4) |
| `name` | `SkString` | 变量名称 |

## 公共 API 函数

### SkMeshSpecification::Make

```cpp
static Result Make(SkSpan<const Attribute> attributes,
                   size_t vertexStride,
                   SkSpan<const Varying> varyings,
                   const SkString& vs,
                   const SkString& fs,
                   sk_sp<SkColorSpace> cs,
                   SkAlphaType at)
```

**功能**: 创建网格规范,编译并验证顶点和片段着色器。

**参数**:
- `attributes`: 顶点属性数组,至少包含一个属性
- `vertexStride`: 顶点步长,必须是 4 字节对齐
- `varyings`: 变量数组,可为空
- `vs`: 顶点着色器源码,签名为 `Varyings main(const Attributes)`
- `fs`: 片段着色器源码,返回 `float2` 或 `float2 main(const Varyings, out half4/float4 color)`
- `cs`: 颜色空间,片段着色器返回颜色时必需
- `at`: Alpha 类型,不能为 `kUnknown`

**返回值**: `Result` 结构,包含 `specification` 和 `error` 字符串。

**约束**:
- 最多 8 个属性(`kMaxAttributes`)
- 最多 6 个变量(`kMaxVaryings`)
- 顶点步长不超过 1024 字节(`kMaxStride`)
- 属性偏移和大小必须在步长范围内
- 必须包含名为 `position` 的 `float2` 变量(自动添加或用户提供)

### SkMesh::Make / MakeIndexed

```cpp
static Result Make(sk_sp<SkMeshSpecification> spec,
                   Mode mode,
                   sk_sp<VertexBuffer> vb,
                   size_t vertexCount,
                   size_t vertexOffset,
                   sk_sp<const SkData> uniforms,
                   SkSpan<ChildPtr> children,
                   const SkRect& bounds)
```

**功能**: 创建非索引网格。

**参数**:
- `spec`: 网格规范
- `mode`: 拓扑模式(Triangles/TriangleStrip)
- `vb`: 顶点缓冲区
- `vertexCount`: 顶点数量,至少 3 个
- `vertexOffset`: 顶点起始偏移,必须是 `stride` 的倍数
- `uniforms`: Uniform 数据,大小必须 ≥ `spec->uniformSize()`
- `children`: 子效果数组
- `bounds`: 网格边界矩形

**返回值**: `Result` 结构,包含 `mesh` 和 `error` 字符串。

**索引版本**(`MakeIndexed`):
- 额外参数: `sk_sp<IndexBuffer> ib`, `size_t indexCount`, `size_t indexOffset`
- `indexOffset` 必须是 2 字节对齐(uint16_t)
- `indexCount` 至少 3

### SkMeshes 命名空间函数

```cpp
sk_sp<SkMesh::IndexBuffer> MakeIndexBuffer(const void* data, size_t size)
sk_sp<SkMesh::VertexBuffer> MakeVertexBuffer(const void* data, size_t size)
sk_sp<SkMesh::IndexBuffer> CopyIndexBuffer(const sk_sp<SkMesh::IndexBuffer>&)
sk_sp<SkMesh::VertexBuffer> CopyVertexBuffer(const sk_sp<SkMesh::VertexBuffer>&)
```

**功能**: 创建和复制 CPU 后端的缓冲区对象。

## 内部实现细节

### 着色器编译流程

1. **预处理**: 自动添加 `position` varying(如果缺失)
2. **结构体生成**: 将 attributes 和 varyings 转为 SkSL 结构体
3. **着色器组合**: 将结构体定义与用户代码拼接
4. **SkSL 编译**: 调用 `SkSL::Compiler::convertProgram()`
5. **Uniform 收集**: 通过 `gather_uniforms_and_check_for_main()` 提取并验证 uniform
6. **颜色转换检测**: 禁止使用 `toLinearSrgb()` 等颜色转换内建函数
7. **优化分析**: 检测直通(passthrough)局部坐标和死变量(dead varyings)

### 验证机制

#### 规范验证(`MakeFromSourceWithStructs`)
- 检查属性偏移对齐(4 字节)
- 验证属性名称合法性(字母数字和下划线)
- 限制变量数量不超过 `kMaxVaryings`
- 确保 uniform 在 VS 和 FS 中声明一致

#### 网格验证(`SkMesh::validate`)
- 顶点缓冲区大小检查: `vertexOffset + stride * vertexCount ≤ vb->size()`
- 索引缓冲区大小检查: `indexOffset + sizeof(uint16_t) * indexCount ≤ ib->size()`
- Uniform 数据大小验证
- 子效果类型匹配
- 最小顶点/索引数量检查(至少 3)

### 哈希计算

规范的哈希值基于:
1. 顶点着色器源码
2. 片段着色器源码
3. 属性偏移和类型
4. 顶点步长
5. 颜色空间哈希
6. Alpha 类型

用于缓存和管线状态对象(PSO)生成。

### 局部坐标优化

通过 `check_for_passthrough_local_coords_and_dead_varyings()` 检测片段着色器是否直接返回某个 varying:
```glsl
float2 main(const Varyings v) {
    return v.texCoord;  // 直通优化
}
```
这种情况下后端可以避免额外插值计算。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRuntimeEffect` | 提供 `Uniform`/`Child` 定义和辅助函数 |
| `SkSL::Compiler` | 编译 SkSL 着色器代码 |
| `SkSL::Analysis` | 分析着色器内建函数使用 |
| `SkColorSpace` | 颜色空间管理 |
| `SkData` | Uniform 数据容器 |
| `SkChecksum` | 计算规范哈希值 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SkCanvas` | `drawMesh(const SkMesh&, SkBlender*, const SkPaint&)` |
| `SkDevice` | 实际渲染网格 |
| GPU 后端(Ganesh/Graphite) | 编译为 GPU 着色器并绘制 |

## 设计模式与设计决策

### 不可变规范(Immutable Specification)

`SkMeshSpecification` 一旦创建不可修改:
- 所有成员变量为 `const`
- 删除拷贝和移动构造函数
- 通过引用计数共享

这确保多个 `SkMesh` 可以安全共享同一规范,且后端可以缓存编译结果。

### 值语义的 Mesh

`SkMesh` 是值类型,支持拷贝和移动:
```cpp
SkMesh mesh1 = ...;
SkMesh mesh2 = mesh1;  // 浅拷贝,共享缓冲区
```
这与 Skia 的其他绘图对象(如 `SkPath`)保持一致。

### 双重验证策略

1. **创建时验证**: `Make()` 时检查所有参数,失败返回空对象和错误信息
2. **绘制时检查**: `SkMesh::isValid()` 快速检查是否有效

这避免了异常处理,符合 Skia 的 C++ 风格。

### 分离的缓冲区接口

`IndexBuffer` 和 `VertexBuffer` 是抽象基类:
- 支持 CPU 后端(`SkMeshPriv::CpuIndexBuffer`)
- 支持 GPU 后端(通过 `GrDirectContext` 更新)
- 统一的 `update()` 接口,4 字节对齐要求

## 性能考量

### 编译时优化

1. **死变量剔除**: 片段着色器未使用的 varying 通过 `fDeadVaryingMask` 标记
2. **内存池禁用**: `settings.fUseMemoryPool = false` 避免长期规范占用内存池
3. **哈希缓存**: 规范哈希用于避免重复编译

### 运行时优化

1. **对齐要求**:
   - 步长 4 字节对齐,适配 GPU 常量
   - 偏移 4 字节对齐,优化内存访问
2. **顶点步长验证**: 提前计算避免越界访问
3. **SafeMath**: 使用 `SkSafeMath` 检测整数溢出

### 最大限制

```cpp
static constexpr size_t kMaxStride = 1024;        // 单个顶点最大字节数
static constexpr size_t kMaxAttributes = 8;       // 最大属性数
static constexpr size_t kMaxVaryings = 6;         // 最大变量数
static constexpr size_t kStrideAlignment = 4;     // 步长对齐
static constexpr size_t kOffsetAlignment = 4;     // 偏移对齐
```

这些限制确保与 ES 2.0 和 Vulkan 1.0 兼容。

## 使用示例

### 创建简单网格

```cpp
// 定义顶点属性
Attribute attrs[] = {
    {Attribute::Type::kFloat2, 0, SkString("position")},
    {Attribute::Type::kFloat2, 8, SkString("texCoord")}
};

// 顶点着色器
SkString vs = R"(
    Varyings main(const Attributes a) {
        Varyings v;
        v.position = a.position;
        return v;
    }
)";

// 片段着色器
SkString fs = R"(
    float2 main(const Varyings v) {
        return v.position;  // 使用位置作为局部坐标
    }
)";

// 创建规范
auto [spec, error] = SkMeshSpecification::Make(attrs, 16, {}, vs, fs);

// 创建顶点缓冲区
float vertices[] = {0,0, 0,1,  100,0, 1,1,  100,100, 1,0};
auto vb = SkMeshes::MakeVertexBuffer(vertices, sizeof(vertices));

// 创建网格
auto [mesh, meshError] = SkMesh::Make(
    spec, SkMesh::Mode::kTriangles, vb, 3, 0, nullptr, {}, SkRect::MakeWH(100, 100));

// 绘制
canvas->drawMesh(mesh, nullptr, paint);
```

### 带索引的网格

```cpp
uint16_t indices[] = {0, 1, 2, 2, 1, 3};
auto ib = SkMeshes::MakeIndexBuffer(indices, sizeof(indices));

auto [mesh, error] = SkMesh::MakeIndexed(
    spec, SkMesh::Mode::kTriangles, vb, 4, 0, ib, 6, 0, nullptr, {}, bounds);
```

### 更新缓冲区

```cpp
float newData[] = {...};
vb->update(context, newData, 0, sizeof(newData));
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkCanvas.h` | 使用者 | 提供 `drawMesh()` 方法 |
| `include/effects/SkRuntimeEffect.h` | 依赖 | Uniform/Child 类型定义 |
| `src/core/SkMeshPriv.h` | 内部 | CPU/GPU 缓冲区实现 |
| `src/sksl/SkSLCompiler.h` | 依赖 | SkSL 编译器 |
| `src/gpu/ganesh/GrMeshDrawTarget.h` | 使用者 | GPU 后端渲染 |
| `src/gpu/graphite/DrawWriter.h` | 使用者 | Graphite 后端渲染 |

## 注意事项

1. **着色器签名严格**: 顶点着色器必须返回 `Varyings`,片段着色器必须返回 `float2`
2. **颜色转换禁止**: 不能在网格着色器中使用 `toLinearSrgb()` 等内建函数
3. **position 变量必需**: 即使未显式声明,系统会自动添加 `float2 position` varying
4. **CPU 缓冲区限制**: `MakeVertexBuffer/MakeIndexBuffer` 创建的缓冲区为 CPU 后端,GPU 绘制时会上传
5. **索引类型固定**: 当前仅支持 `uint16_t` 索引,不支持 32 位索引
6. **边界必需**: 必须提供准确的边界,否则裁剪可能不正确
7. **Uniform 对齐**: Uniform 数据布局由 `SkRuntimeEffect::Uniform::offset` 决定,需手动对齐

该模块为 Skia 提供了强大的自定义渲染能力,是实现粒子系统、网格变形、自定义滤镜等高级效果的基础。
