# SkMeshGanesh

> 源文件: `include/gpu/ganesh/SkMeshGanesh.h`

## 概述
SkMeshGanesh 为 Skia 的自定义网格渲染系统提供 Ganesh GPU 后端支持。该模块提供了创建 GPU 加速的顶点缓冲区和索引缓冲区的工厂函数,使应用程序能够使用 SkMesh API 在 GPU 上渲染自定义几何体。

## 架构位置
该文件位于 `include/gpu/ganesh` 公共 API 层,是 SkMesh 核心功能与 Ganesh GPU 后端之间的桥梁。它依赖于 SkMesh 的抽象缓冲区接口,为 GPU 渲染管线提供具体的缓冲区实现。

## 命名空间结构

### SkMeshes 命名空间
所有工厂函数封装在 `SkMeshes` 命名空间中,遵循 Skia 现代 API 设计,与 `SkImages`、`SkSurfaces` 等命名空间保持一致。

## 核心 API 函数

### 索引缓冲区创建

#### `MakeIndexBuffer`
```cpp
SK_API sk_sp<SkMesh::IndexBuffer> MakeIndexBuffer(
    GrDirectContext* context,
    const void* data,
    size_t size);
```

**功能**: 创建用于 SkMesh 的索引缓冲区

**参数**:
- `context`: GrDirectContext 指针
  - 如果非空:数据上传到对应 GPU,返回的缓冲区仅与该上下文兼容
  - 如果为空:数据保存在 CPU 内存中,返回 CPU 缓冲区
- `data`: 索引数据指针
  - 如果非空:使用提供的数据填充缓冲区
  - 如果为空:创建零初始化的缓冲区
- `size`: 数据大小(字节),同时也是结果缓冲区的大小

**返回值**: sk_sp<SkMesh::IndexBuffer>,失败返回 nullptr

**应用场景**:
- 三角形网格渲染(使用索引减少顶点重复)
- 动态几何体(传入 nullptr data 后续更新)
- CPU 后备(context 为 nullptr 时的软件渲染)

**内存管理**:
- 返回智能指针自动管理生命周期
- GPU 缓冲区在上下文销毁时释放
- CPU 缓冲区在引用计数为 0 时释放

#### `CopyIndexBuffer`
```cpp
SK_API sk_sp<SkMesh::IndexBuffer> CopyIndexBuffer(
    GrDirectContext* context,
    sk_sp<SkMesh::IndexBuffer> src);
```

**功能**: 复制现有索引缓冲区

**参数**:
- `context`: 目标 GPU 上下文
  - 如果非空:创建 GPU 支持的副本
  - 如果为空:创建 CPU 支持的副本
- `src`: 源索引缓冲区

**返回值**: 新的缓冲区副本,失败返回 nullptr

**应用场景**:
- 跨上下文共享缓冲区数据
- CPU/GPU 缓冲区转换
- 缓冲区数据持久化

**实现细节**:
- 源缓冲区可以是 GPU 或 CPU 缓冲区
- 自动处理 GPU-to-GPU、GPU-to-CPU、CPU-to-GPU 复制
- 数据格式和大小保持不变

### 顶点缓冲区创建

#### `MakeVertexBuffer`
```cpp
SK_API sk_sp<SkMesh::VertexBuffer> MakeVertexBuffer(
    GrDirectContext* context,
    const void* data,
    size_t size);
```

**功能**: 创建用于 SkMesh 的顶点缓冲区

**参数**:
- `context`: GrDirectContext 指针
  - 如果非空:数据上传到对应 GPU
  - 如果为空:数据保存在 CPU 内存
- `data`: 顶点数据指针
  - 如果非空:使用提供的数据填充
  - 如果为空:创建零初始化缓冲区
- `size`: 数据大小(字节)

**返回值**: sk_sp<SkMesh::VertexBuffer>,失败返回 nullptr

**顶点格式**:
- 顶点格式由 SkMesh 的 VertexSpec 定义
- 支持自定义属性(位置、颜色、纹理坐标等)
- 可包含任意数量和类型的顶点属性

**典型顶点数据**:
```cpp
struct Vertex {
    float x, y;        // 位置
    uint32_t color;    // 颜色
    float u, v;        // 纹理坐标
};
```

#### `CopyVertexBuffer`
```cpp
SK_API sk_sp<SkMesh::VertexBuffer> CopyVertexBuffer(
    GrDirectContext* context,
    sk_sp<SkMesh::VertexBuffer> src);
```

**功能**: 复制现有顶点缓冲区

**参数**:
- `context`: 目标 GPU 上下文(可为空)
- `src`: 源顶点缓冲区

**返回值**: 新的缓冲区副本

**应用场景**:
- 动画网格的帧缓存
- 不同 GPU 上下文间共享几何体
- 将 CPU 生成的几何体上传到 GPU

## 使用模式

### 创建 GPU 网格
```cpp
// 1. 创建顶点数据
std::vector<Vertex> vertices = { /* ... */ };
auto vertexBuffer = SkMeshes::MakeVertexBuffer(
    context, vertices.data(), vertices.size() * sizeof(Vertex));

// 2. 创建索引数据
std::vector<uint16_t> indices = { /* ... */ };
auto indexBuffer = SkMeshes::MakeIndexBuffer(
    context, indices.data(), indices.size() * sizeof(uint16_t));

// 3. 创建 SkMesh 对象
auto mesh = SkMesh::Make(spec, mode, vertexBuffer, /* ... */, indexBuffer);

// 4. 绘制网格
canvas->drawMesh(mesh, /* ... */);
```

### CPU 后备渲染
```cpp
// 传入 nullptr context 创建 CPU 缓冲区
auto cpuVertexBuffer = SkMeshes::MakeVertexBuffer(nullptr, data, size);
auto cpuIndexBuffer = SkMeshes::MakeIndexBuffer(nullptr, indices, indexSize);
```

### 跨上下文复制
```cpp
// 从一个 GPU 上下文复制到另一个
auto buffer1 = SkMeshes::MakeVertexBuffer(context1, data, size);
auto buffer2 = SkMeshes::CopyVertexBuffer(context2, buffer1);
```

## 内部实现细节

### 缓冲区类型
- **GPU 缓冲区**: 封装平台特定的 GPU 缓冲区对象(VBO/IBO)
- **CPU 缓冲区**: 简单的内存分配,供软件光栅化使用

### 上下文绑定
GPU 缓冲区与创建时的 GrDirectContext 绑定:
- 不能跨不兼容的上下文使用
- 上下文销毁时缓冲区失效
- 通过 CopyBuffer 实现跨上下文共享

### 零初始化缓冲区
当 data 参数为 nullptr 时:
- 分配指定大小的缓冲区
- 内存清零(GPU 或 CPU)
- 用于动态更新场景

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkMesh.h | SkMesh 核心类型定义 |
| include/core/SkRefCnt.h | sk_sp 智能指针 |
| GrDirectContext | GPU 上下文和资源管理 |
| include/private/base/SkAPI.h | API 导出宏 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkCanvas | drawMesh 方法使用这些缓冲区 |
| SkMesh | 组装顶点和索引缓冲区为可绘制网格 |
| 游戏引擎 | 自定义几何体渲染 |
| 3D 可视化工具 | 科学数据可视化 |

## 设计模式与设计决策

### 工厂函数模式
使用独立的工厂函数而非类静态方法:
- 清晰的命名空间组织
- 避免 SkMesh 类膨胀
- 后端特定实现解耦

### CPU/GPU 统一接口
通过 context 参数控制缓冲区位置:
- 简化 API 设计
- 支持渐进式 GPU 迁移
- 便于测试和调试(CPU 路径)

### 智能指针资源管理
返回 sk_sp 确保:
- 自动引用计数
- 异常安全
- 无需手动释放

## 性能考量

### GPU 上传开销
- MakeBuffer 会立即上传数据到 GPU
- 大缓冲区可能阻塞渲染管线
- 考虑使用零初始化 + 异步更新

### 缓冲区复用
- 复用缓冲区对象比重新创建更高效
- 动态网格应保持缓冲区并更新数据
- 避免每帧创建新缓冲区

### 索引缓冲区优化
- 使用索引缓冲区减少顶点数据重复
- 三角形带(triangle strip)比索引三角形更高效
- 顶点缓存优化(考虑顶点访问顺序)

## 平台相关说明

### OpenGL/OpenGL ES
- 使用 GL_ARRAY_BUFFER 和 GL_ELEMENT_ARRAY_BUFFER
- 默认 GL_STATIC_DRAW 使用模式
- 支持 VAO(顶点数组对象)缓存

### Vulkan
- 使用 VkBuffer + VkDeviceMemory
- 缓冲区分配可能使用内存池
- 支持传输队列异步上传

### Metal
- 使用 MTLBuffer
- 支持共享内存(iOS)和托管内存(macOS)
- 利用 Metal 的零拷贝特性

### Direct3D 12
- 使用 ID3D12Resource
- 上传堆(Upload Heap)用于 CPU 可见缓冲区
- 默认堆(Default Heap)用于 GPU 专用缓冲区

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkMesh.h | 网格核心接口定义 |
| src/gpu/ganesh/GrGpuBuffer.h | Ganesh GPU 缓冲区实现基类 |
| src/core/SkMeshPriv.h | 网格私有实现细节 |
| include/gpu/ganesh/GrDirectContext.h | GPU 上下文管理 |
