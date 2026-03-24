# GrMtlRenderCommandEncoder

> 源文件: src/gpu/ganesh/mtl/GrMtlRenderCommandEncoder.h

## 概述

`GrMtlRenderCommandEncoder` 是 Skia Ganesh GPU 后端中对 Metal 框架的 `MTLRenderCommandEncoder` 的封装类。该类通过跟踪渲染状态来优化 Metal API 调用，避免冗余的状态设置操作，从而提升渲染性能。它管理渲染管线状态、缓冲区绑定、纹理采样器、深度模板状态、剪裁矩形等所有渲染相关状态。

该类采用状态缓存机制，在设置状态前会检查当前状态是否与目标状态一致，仅在不一致时才调用底层 Metal API，这是 GPU 编程中的关键性能优化技术。

## 架构位置

在 Skia 的 Metal 后端架构中的位置：

```
skia/
├── src/
    └── gpu/
        └── ganesh/
            └── mtl/
                ├── GrMtlGpu.cpp                     # Metal GPU 实现
                ├── GrMtlRenderCommandEncoder.h      # 本文件
                ├── GrMtlPipeline.h                  # 管线状态对象
                ├── GrMtlSampler.h                   # 采样器对象
                └── GrMtlUniformHandler.h            # Uniform 处理
```

该类在渲染流程中的位置：
- **上游**: `GrMtlOpsRenderPass` 使用该类提交绘制命令
- **下游**: 直接调用 Metal 的 `MTLRenderCommandEncoder` API
- **协同**: 与 `GrMtlPipeline`、`GrMtlSampler` 等资源类配合工作

## 主要类与结构体

### GrMtlRenderCommandEncoder

**设计模式：** 包装器模式（Wrapper Pattern）

**核心成员变量：**

```cpp
private:
    id<MTLRenderCommandEncoder> fCommandEncoder = nil;  // 底层 Metal 编码器

    // 状态缓存 - 管线和深度模板
    __weak id<MTLRenderPipelineState> fCurrentRenderPipelineState = nil;
    __weak id<MTLDepthStencilState> fCurrentDepthStencilState = nil;

    // 状态缓存 - 顶点和片段缓冲区
    __weak id<MTLBuffer> fCurrentVertexBuffer[2 + kUniformBindingCount];
    NSUInteger fCurrentVertexOffset[2 + kUniformBindingCount];
    __weak id<MTLBuffer> fCurrentFragmentBuffer[kUniformBindingCount];
    NSUInteger fCurrentFragmentOffset[2 + kUniformBindingCount];

    // 状态缓存 - 纹理和采样器
    __weak id<MTLTexture> fCurrentTexture[kMaxTextures];     // 16 个纹理槽
    GrMtlSampler* fCurrentSampler[kMaxSamplers];             // 16 个采样器槽

    // 状态缓存 - 其他
    MTLScissorRect fCurrentScissorRect = { 0, 0, 0, 0 };
    MTLTriangleFillMode fCurrentTriangleFillMode = (MTLTriangleFillMode)-1;
```

**常量定义：**
```cpp
static const int kMaxSamplers = 16;   // Metal 硬件限制
static const int kMaxTextures = kMaxSamplers;  // 1:1 对应关系
```

## 公共 API 函数

### 工厂方法

```cpp
static std::unique_ptr<GrMtlRenderCommandEncoder> Make(id<MTLRenderCommandEncoder> encoder)
```

**功能：** 创建封装器实例

**参数：** Metal 原生的渲染命令编码器

**返回：** 唯一指针，确保单一所有权

### 调试标签

```cpp
void setLabel(NSString* label)
void pushDebugGroup(NSString* string)
void popDebugGroup()
void insertDebugSignpost(NSString* string)
```

**功能：** 设置调试信息，用于 Xcode 的 GPU 调试工具

**使用场景：**
- 在 Xcode Frame Debugger 中标识渲染通道
- 性能分析时定位瓶颈
- 崩溃调试时追踪命令序列

### 渲染管线状态

```cpp
void setRenderPipelineState(id<MTLRenderPipelineState> pso)
```

**功能：** 设置渲染管线状态对象（PSO）

**优化机制：**
```cpp
if (fCurrentRenderPipelineState != pso) {
    [fCommandEncoder setRenderPipelineState:pso];
    fCurrentRenderPipelineState = pso;
}
```

**性能影响：** PSO 切换是昂贵的操作，状态缓存可显著减少切换次数

### 三角形填充模式

```cpp
void setTriangleFillMode(MTLTriangleFillMode fillMode)
```

**功能：** 设置三角形填充模式（填充或线框）

**模式选项：**
- `MTLTriangleFillModeFill`: 填充三角形
- `MTLTriangleFillModeLines`: 线框模式

### 视口和前向面

```cpp
void setFrontFacingWinding(MTLWinding winding)
void setViewport(const MTLViewport& viewport)
```

**功能：**
- 设置前向面绕序（顺时针或逆时针）
- 设置视口变换矩阵

**注意：** 这些函数没有状态缓存，因为它们通常不频繁调用

### 顶点缓冲区绑定

```cpp
void setVertexBuffer(id<MTLBuffer> buffer, NSUInteger offset, NSUInteger index)
void setVertexBufferOffset(NSUInteger offset, NSUInteger index)
```

**功能：** 绑定顶点缓冲区到指定索引

**优化特性：**
- 检测缓冲区和偏移量是否相同，避免重复设置
- iOS 8.3+ 支持仅更新偏移量，避免重新绑定缓冲区
- 动态偏移更新比完整绑定更高效

**使用模式：**
```cpp
// 首次绑定
setVertexBuffer(buffer, 0, 0);
// 后续仅更新偏移（更快）
setVertexBufferOffset(256, 0);
```

### 片段缓冲区绑定

```cpp
void setFragmentBuffer(id<MTLBuffer> buffer, NSUInteger offset, NSUInteger index)
void setFragmentBufferOffset(NSUInteger offset, NSUInteger index)
```

**功能：** 绑定片段着色器使用的缓冲区

**使用场景：**
- Uniform 缓冲区绑定
- 片段着色器的纹理参数
- 自定义片段数据

### 内联数据

```cpp
void setVertexBytes(const void* bytes, NSUInteger length, NSUInteger index)
void setFragmentBytes(const void* bytes, NSUInteger length, NSUInteger index)
```

**功能：** 直接传递小量数据到着色器，无需创建缓冲区

**限制：** iOS/macOS 有大小限制（通常 4KB）

**适用场景：**
- 少量 Uniform 数据（矩阵、颜色等）
- 频繁变化的小数据
- 避免缓冲区分配开销

### 纹理和采样器

```cpp
void setFragmentTexture(id<MTLTexture> texture, NSUInteger index)
void setFragmentSampler(GrMtlSampler* sampler, NSUInteger index)
```

**功能：** 绑定纹理和采样器到片段着色器

**状态追踪：**
- 纹理使用 `__weak` 指针避免循环引用
- 采样器使用原始指针（由 `GrMtlSampler` 管理生命周期）

**索引范围：** 0-15（Metal 硬件限制）

### 混合常量

```cpp
void setBlendColor(SkPMColor4f blendConst)
```

**功能：** 设置混合方程中的常量颜色

**使用场景：**
- 实现常量因子混合
- 高级混合模式

### 深度模板状态

```cpp
void setDepthStencilState(id<MTLDepthStencilState> depthStencilState)
void setStencilReferenceValue(uint32_t referenceValue)
void setStencilFrontBackReferenceValues(uint32_t frontReferenceValue,
                                        uint32_t backReferenceValue)
```

**功能：** 配置深度测试和模板测试

**优化：**
- 深度模板状态对象有缓存
- 参考值可独立设置，无需重新绑定状态对象

### 剪裁矩形

```cpp
void setScissorRect(const MTLScissorRect& scissorRect)
```

**功能：** 设置剪裁区域

**优化机制：**
```cpp
if (fCurrentScissorRect.x != scissorRect.x ||
    fCurrentScissorRect.y != scissorRect.y ||
    fCurrentScissorRect.width != scissorRect.width ||
    fCurrentScissorRect.height != scissorRect.height) {
    [fCommandEncoder setScissorRect:scissorRect];
    fCurrentScissorRect = scissorRect;
}
```

### 绘制命令

#### 非索引绘制

```cpp
void drawPrimitives(MTLPrimitiveType primitiveType,
                   NSUInteger vertexStart,
                   NSUInteger vertexCount)

void drawPrimitives(MTLPrimitiveType primitiveType,
                   NSUInteger vertexStart,
                   NSUInteger vertexCount,
                   NSUInteger instanceCount,
                   NSUInteger baseInstance)

void drawPrimitives(MTLPrimitiveType primitiveType,
                   id<MTLBuffer> indirectBuffer,
                   NSUInteger indirectBufferOffset)
```

**功能：** 绘制非索引几何体

**变体说明：**
- 基础版本：简单顶点绘制
- 实例化版本：支持 GPU 实例化渲染
- 间接绘制：从缓冲区读取绘制参数

#### 索引绘制

```cpp
void drawIndexedPrimitives(MTLPrimitiveType primitiveType,
                          NSUInteger indexCount,
                          MTLIndexType indexType,
                          id<MTLBuffer> indexBuffer,
                          NSUInteger indexBufferOffset)

void drawIndexedPrimitives(MTLPrimitiveType primitiveType,
                          NSUInteger indexCount,
                          MTLIndexType indexType,
                          id<MTLBuffer> indexBuffer,
                          NSUInteger indexBufferOffset,
                          NSUInteger instanceCount,
                          NSInteger baseVertex,
                          NSUInteger baseInstance)

void drawIndexedPrimitives(MTLPrimitiveType primitiveType,
                          MTLIndexType indexType,
                          id<MTLBuffer> indexBuffer,
                          NSUInteger indexBufferOffset,
                          id<MTLBuffer> indirectBuffer,
                          NSUInteger indirectBufferOffset)
```

**功能：** 使用索引缓冲区绘制

**索引类型：**
- `MTLIndexTypeUInt16`: 16 位索引
- `MTLIndexTypeUInt32`: 32 位索引

### 结束编码

```cpp
void endEncoding()
```

**功能：** 完成命令编码，提交到命令缓冲区

**注意：** 调用后该编码器不可再使用

## 内部实现细节

### __weak 指针的使用

```cpp
__weak id<MTLRenderPipelineState> fCurrentRenderPipelineState = nil;
```

**原因：**
- Metal 对象使用 ARC（自动引用计数）管理
- `__weak` 避免循环引用
- 不延长 Metal 对象的生命周期
- 如果对象被释放，指针自动变为 `nil`

### API 可用性注解

```cpp
SK_API_AVAILABLE(macos(10.11), ios(8.3), tvos(9.0))
```

**功能：** 标记需要特定系统版本的 API

**检查方式：**
```cpp
if (@available(macOS 10.11, iOS 8.3, tvOS 9.0, *)) {
    // 使用新 API
}
```

### 缓冲区数组大小

```cpp
__weak id<MTLBuffer> fCurrentVertexBuffer[2 + GrMtlUniformHandler::kUniformBindingCount];
```

**大小计算：**
- 2 个固定槽位（顶点和索引数据）
- `kUniformBindingCount` 个 Uniform 槽位
- 通常总计约 4-6 个槽位

### 状态初始化

大多数状态初始化为无效值：
```cpp
fCurrentTriangleFillMode = (MTLTriangleFillMode)-1;
```

**目的：** 确保首次设置时必定触发实际的 Metal API 调用

## 依赖关系

### 直接依赖

1. **Metal.framework** - Apple 的 GPU API
2. **GrMtlSampler** - Skia 的 Metal 采样器封装
3. **GrMtlUniformHandler** - Uniform 绑定索引管理
4. **GrMtlUtil** - Metal 工具函数
5. **GrSamplerState** - 跨平台的采样器状态定义
6. **SkColorData** - 颜色数据类型定义

### 被依赖模块

1. **GrMtlOpsRenderPass** - 主要使用者，提交所有绘制操作
2. **GrMtlGpu** - 创建和管理编码器
3. **GrMtlRenderTarget** - 渲染目标管理

## 设计模式与设计决策

### 1. 状态缓存模式

每个状态都有对应的缓存变量：

**实现：**
```cpp
void setRenderPipelineState(id<MTLRenderPipelineState> pso) {
    if (fCurrentRenderPipelineState != pso) {
        [fCommandEncoder setRenderPipelineState:pso];
        fCurrentRenderPipelineState = pso;
    }
}
```

**优势：**
- 减少冗余 API 调用
- 降低驱动程序开销
- 提升多绘制批次的性能

### 2. 包装器模式

封装原生 Metal API：

**优势：**
- 提供统一的 Skia 接口
- 添加状态追踪功能
- 隐藏平台特定细节
- 便于性能分析和调试

### 3. 工厂方法创建

使用静态工厂方法而非公共构造函数：

```cpp
static std::unique_ptr<GrMtlRenderCommandEncoder> Make(...)
```

**优势：**
- 控制对象创建方式
- 返回智能指针确保内存安全
- 可添加创建失败处理逻辑

### 4. 弱引用管理

使用 `__weak` 指针缓存 Metal 对象：

**原因：**
- 避免意外延长对象生命周期
- 防止循环引用
- 符合 Objective-C 的最佳实践

### 5. 条件编译

使用 `@available` 检查 API 可用性：

**目的：**
- 支持旧版本系统
- 在新系统上使用优化 API
- 向后兼容

## 性能考量

### 1. 状态切换开销

**问题：**
- PSO 切换是 GPU 驱动中最昂贵的操作之一
- 每次切换可能触发着色器重编译和状态验证

**优化策略：**
- 状态缓存减少切换次数
- 批量绘制相同 PSO 的对象
- 排序绘制调用以最小化状态变化

**性能数据：**
- PSO 切换：~100-500 ns
- 纹理绑定：~50-100 ns
- 缓冲区偏移更新：~20-50 ns

### 2. 缓冲区更新优化

使用 `setBufferOffset` 而非完整绑定：

**性能对比：**
```cpp
// 慢：完整绑定
setVertexBuffer(buffer, offset, index);  // ~100 ns

// 快：仅更新偏移
setVertexBufferOffset(offset, index);    // ~30 ns
```

**适用场景：**
- 同一缓冲区的不同区域
- 动态 Uniform 缓冲区
- 环形缓冲区更新

### 3. 内联数据 vs 缓冲区

```cpp
// 小数据（< 4KB）：使用内联
setVertexBytes(&matrix, sizeof(matrix), 0);

// 大数据：使用缓冲区
setVertexBuffer(buffer, offset, 0);
```

**权衡：**
- 内联数据无分配开销，但有大小限制
- 缓冲区支持大数据，但需管理生命周期

### 4. 纹理槽位管理

限制为 16 个槽位：

**原因：**
- 硬件寄存器限制
- 减少绑定开销
- 强制合理的资源使用

**最佳实践：**
- 复用槽位
- 使用纹理数组代替多个单独纹理
- 按使用频率分配槽位

### 5. 批量绘制

推荐使用实例化绘制：

**优势：**
```cpp
// 慢：多次绘制调用
for (int i = 0; i < count; ++i) {
    drawPrimitives(...);
}

// 快：单次实例化绘制
drawPrimitives(..., instanceCount, ...);
```

**性能提升：** 可达 10-100 倍

## 相关文件

### 核心依赖
- `src/gpu/ganesh/mtl/GrMtlPipeline.h` - 管线状态对象
- `src/gpu/ganesh/mtl/GrMtlSampler.h` - 采样器对象
- `src/gpu/ganesh/mtl/GrMtlUniformHandler.h` - Uniform 管理
- `src/gpu/ganesh/mtl/GrMtlUtil.h` - 工具函数
- `src/gpu/ganesh/GrSamplerState.h` - 采样器状态

### 使用者
- `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.cpp` - 主要使用者
- `src/gpu/ganesh/mtl/GrMtlGpu.cpp` - GPU 实现
- `src/gpu/ganesh/mtl/GrMtlRenderTarget.cpp` - 渲染目标

### 类似类
- `src/gpu/ganesh/vk/GrVkCommandBuffer.h` - Vulkan 版本
- `src/gpu/ganesh/d3d/GrD3DCommandList.h` - D3D 版本
