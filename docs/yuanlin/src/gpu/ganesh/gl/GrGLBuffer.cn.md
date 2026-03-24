# GrGLBuffer

> 源文件
> - src/gpu/ganesh/gl/GrGLBuffer.h
> - src/gpu/ganesh/gl/GrGLBuffer.cpp

## 概述

`GrGLBuffer` 是 Skia Ganesh 渲染引擎中用于管理 OpenGL 缓冲区对象的核心类。它继承自 `GrGpuBuffer`，为各种类型的 GPU 缓冲区（顶点缓冲区、索引缓冲区、传输缓冲区等）提供统一的 OpenGL 实现。该类封装了 OpenGL 缓冲区对象的生命周期管理、内存映射、数据传输等操作，并针对不同的 OpenGL 版本和扩展提供了适配逻辑。

## 架构位置

`GrGLBuffer` 位于 Ganesh GPU 后端的 OpenGL 实现层：

```
src/gpu/ganesh/
├── GrGpuBuffer (抽象基类)
│   └── gl/
│       └── GrGLBuffer (OpenGL 实现)
└── GrGLGpu (OpenGL GPU 管理类)
```

该类是 GPU 缓冲区抽象在 OpenGL 后端的具体实现，与 `GrGLGpu`、`GrGLCaps` 紧密协作。

## 主要类与结构体

### GrGLBuffer

**继承关系：**
```
GrResource
  └── GrGpuResource
      └── GrGpuBuffer
          └── GrGLBuffer
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fIntendedType` | `GrGpuBufferType` | 缓冲区的预期用途类型（顶点、索引、传输等） |
| `fBufferID` | `GrGLuint` | OpenGL 缓冲区对象 ID |
| `fUsage` | `GrGLenum` | OpenGL usage hint（STATIC_DRAW、DYNAMIC_DRAW 等） |
| `fHasAttachedToTexture` | `bool` | 是否已附加到纹理（用于纹理缓冲区） |

## 公共 API 函数

### 创建与销毁

| 函数 | 功能 |
|------|------|
| `Make(GrGLGpu*, size_t, GrGpuBufferType, GrAccessPattern)` | 静态工厂方法，创建 OpenGL 缓冲区对象 |
| `~GrGLBuffer()` | 析构函数，确保资源已释放 |
| `bufferID()` | 获取 OpenGL 缓冲区 ID |

### 纹理附加管理

| 函数 | 功能 |
|------|------|
| `setHasAttachedToTexture()` | 标记缓冲区已附加到纹理 |
| `hasAttachedToTexture()` | 查询是否已附加到纹理 |

## 内部实现细节

### 缓冲区创建流程

1. **生成缓冲区对象**：调用 `glGenBuffers` 创建 OpenGL 缓冲区
2. **绑定缓冲区**：通过 `GrGLGpu::bindBuffer` 绑定到对应的目标
3. **分配存储空间**：使用 `glBufferData` 分配内存，传入 `nullptr` 仅分配空间
4. **错误检查**：通过 `GL_ALLOC_CALL` 宏检查内存分配是否成功
5. **注册到缓存**：调用 `registerWithCache` 将缓冲区纳入资源管理

### Usage Pattern 映射

`gr_to_gl_access_pattern` 函数将 Skia 的访问模式映射到 OpenGL usage hint：

- **Dynamic 模式**：映射为 `GL_STREAM_DRAW`（针对 Chromium 优化）
- **Static 模式**：映射为 `GL_STATIC_DRAW`
- **Stream 模式**：映射为 `GL_STREAM_DRAW`
- **传输缓冲区**：根据传输方向选择 DRAW 或 READ usage

### 内存映射机制

支持三种映射方式：

1. **MapBuffer**：传统的 `glMapBuffer` 方式（OpenGL 1.5+）
2. **MapBufferRange**：更灵活的 `glMapBufferRange`（OpenGL 3.0+）
3. **Chromium MapSubData**：Chrome 特定的映射扩展

映射前会根据类型决定是否调用 `invalidate_buffer` 使旧数据失效。

### 数据更新策略

`onUpdateData` 实现：
- **非保留模式**：先调用 `invalidate_buffer` 废弃旧数据
- **子数据更新**：使用 `glBufferSubData` 更新部分数据
- **清零操作**：优先尝试映射清零，失败则分配临时内存清零

### 缓冲区失效方法

根据 `GrGLCaps::InvalidateBufferType` 支持：
- **None**：不执行失效操作
- **NullData**：调用 `glBufferData(target, size, nullptr, usage)` 重新分配
- **Invalidate**：调用 `glInvalidateBufferData(bufferID)` 标记失效

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | OpenGL GPU 管理，缓冲区绑定操作 |
| `GrGLCaps` | 查询 OpenGL 能力和扩展支持 |
| `GrGLInterface` | OpenGL 函数指针表 |
| `GrGLUtil` | OpenGL 工具函数和宏定义 |
| `GrGpuResourcePriv` | GPU 资源私有访问接口 |
| `SkTraceMemoryDump` | 内存追踪和诊断 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrGLGpu` | 作为缓冲区资源被 GPU 管理 |
| `GrDrawOp` | 提供顶点和索引缓冲区存储 |
| `GrTransferBuffer` | 实现 CPU-GPU 数据传输 |

## 设计模式与设计决策

### 工厂模式

使用静态 `Make` 方法而非公共构造函数：
- 允许在创建失败时返回 `nullptr`
- 封装复杂的初始化逻辑
- 支持能力检查（如传输缓冲区类型检查）

### RAII 资源管理

通过继承 `GrGpuBuffer` 实现自动资源管理：
- 析构时断言缓冲区 ID 为 0（必须显式释放或放弃）
- `onRelease` 和 `onAbandon` 确保资源正确清理
- 防止资源泄漏

### 延迟映射策略

`MapType` 参数区分读写意图：
- `kRead`：使用 `GL_READ_ONLY`
- `kWriteDiscard`：使用 `GL_WRITE_ONLY | GL_MAP_INVALIDATE_BUFFER_BIT`
- 避免不必要的缓冲区失效操作

### Chromium 特殊优化

针对 Chromium GPU 进程的优化：
- 使用 `GL_STREAM_DRAW` 触发客户端数组优化
- 支持 `CHROMIUM_map_sub` 扩展
- 处理平铺延迟架构（tile-deferred architectures）

## 性能考量

### 动态绘制优化

对于动态内容，在 Chromium 中使用 `GL_STREAM_DRAW`：
- 在平铺延迟架构上触发客户端侧数组实现
- 避免频繁的 VBO 状态切换开销

### 映射性能权衡

- **MapBufferRange** 比 **MapBuffer** 更高效（支持部分映射）
- **INVALIDATE_BUFFER_BIT** 避免驱动同步等待
- **Chromium MapSubData** 在命令缓冲架构下性能更优

### 内存对齐

`GL_ALLOC_CALL` 宏确保内存分配成功检查：
- 跳过错误检查的路径用于高性能场景
- OOM 检测保证内存安全

### 清零性能

`onClearToZero` 实现优先级：
1. **首选**：通过映射清零（避免临时内存分配）
2. **降级**：分配临时内存后用 `updateData` 上传
3. 未来可优化：使用 `glClearBufferData`（GL 4.3+）

### 标签调试

`onSetLabel` 支持通过 `GL_KHR_debug` 设置对象标签：
- 便于 RenderDoc、Apitrace 等工具调试
- 前缀 `_Skia_` 标识 Skia 创建的对象

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrGpuBuffer.h/cpp` | 基类 | 定义缓冲区抽象接口 |
| `GrGLGpu.h/cpp` | 协作者 | 管理 OpenGL 上下文和缓冲区绑定 |
| `GrGLCaps.h/cpp` | 配置提供者 | 查询 OpenGL 能力 |
| `GrGLDefines.h` | 常量定义 | OpenGL 常量宏定义 |
| `GrGLUtil.h` | 工具函数 | OpenGL 调用包装宏 |
| `GrGLVertexArray.cpp` | 使用者 | 绑定顶点缓冲区到 VAO |
| `GrGLOpsRenderPass.cpp` | 使用者 | 绑定索引和顶点缓冲区进行绘制 |
