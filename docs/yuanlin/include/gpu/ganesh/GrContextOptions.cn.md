# GrContextOptions

> 源文件: `include/gpu/ganesh/GrContextOptions.h`

## 概述

`GrContextOptions` 是 Skia Ganesh GPU 引擎的全局配置结构体，用于在创建 `GrDirectContext` 时自定义 GPU 渲染管线的各项行为。该结构体提供了对着色器缓存策略、字形渲染、多重采样、驱动兼容性修复、资源管理限制以及众多渲染路径选项的细粒度控制。

作为 Ganesh 引擎的核心配置入口，`GrContextOptions` 允许客户端根据目标平台、GPU 硬件特性和应用场景调整渲染行为，既支持性能优化，也支持规避已知的驱动程序缺陷。该结构体的所有字段均提供合理的默认值，大多数应用场景无需修改任何选项。

## 架构位置

```
应用层
│
├── GrContextOptions                  <-- 本文件：上下文配置
│   ├── PersistentCache (内嵌类)       着色器持久化缓存接口
│   ├── ShaderErrorHandler             着色器编译错误回调
│   └── SkExecutor                     多线程任务执行器
│
├── GrDirectContext                    Ganesh 直接上下文（消费 GrContextOptions）
│   ├── GrGpu                          GPU 后端抽象
│   │   ├── GrGLGpu (OpenGL)
│   │   ├── GrVkGpu (Vulkan)
│   │   ├── GrMtlGpu (Metal)
│   │   └── GrD3DGpu (Direct3D)
│   ├── GrResourceCache               资源缓存管理
│   └── GrAtlasManager                图集管理器
│
└── GrRecordingContext                 录制上下文（GrDirectContext 的基类）
```

`GrContextOptions` 位于应用层和 Ganesh 引擎内核之间，是客户端影响 GPU 渲染行为的主要手段。它在 `GrDirectContext` 创建时传入，并在上下文生命周期内不再改变（即"一次配置，终身有效"的模式）。

## 主要类与结构体

### GrContextOptions（主结构体）

导出属性为 `SK_API`，即公共 API 的一部分。所有成员变量均为公开字段，采用 `f` 前缀命名规范（Skia 的字段命名约定）。

### Enable 枚举

```cpp
enum class Enable {
    kNo,       // 强制禁用
    kYes,      // 强制启用
    kDefault   // 使用 Skia 的默认行为（可能基于运行时检测）
};
```

三态开关枚举，用于那些需要在"强制开/关/自动"之间选择的选项。`kDefault` 表示 Skia 将根据运行时环境（如驱动版本、GPU 型号）自动判断最优策略。

### ShaderCacheStrategy 枚举

```cpp
enum class ShaderCacheStrategy {
    kSkSL,            // 缓存 SkSL 中间表示
    kBackendSource,   // 缓存后端着色器源码（如 GLSL）
    kBackendBinary,   // 缓存后端编译后的二进制（如 GL Program Binary）
};
```

控制持久化缓存中存储的着色器数据格式。三种策略在编译速度和兼容性之间进行不同取舍。

### PersistentCache 抽象类

```cpp
class SK_API PersistentCache {
public:
    virtual ~PersistentCache() = default;
    virtual sk_sp<SkData> load(const SkData& key) = 0;
    virtual void store(const SkData& key, const SkData& data,
                       const SkString& description);
};
```

跨会话持久化缓存的接口抽象。客户端通过继承此类实现自定义的缓存存储后端（如文件系统、数据库等），用于存储编译好的着色器二进制，避免每次启动时的着色器重编译开销。

**关键特性**：
- 禁止拷贝构造和赋值（`delete`），确保缓存对象不被意外复制
- `store` 方法有 2 参数和 3 参数两个重载，3 参数版本提供人类可读的描述信息
- 使用 `sk_sp<SkData>` 智能指针管理返回的缓存数据

## 公共 API 函数

`GrContextOptions` 本身是一个 POD-like 结构体，没有复杂的成员函数。它的所有配置通过公开字段进行设置。以下按功能分类详述各字段。

### PersistentCache 接口方法

#### `PersistentCache::load`

```cpp
virtual sk_sp<SkData> load(const SkData& key) = 0;
```

根据给定键从缓存中加载数据。如果缓存命中则返回对应的 `SkData`，否则返回 `nullptr`。这是纯虚函数，子类必须实现。

#### `PersistentCache::store`（双参数版本）

```cpp
virtual void store(const SkData& key, const SkData& data);
```

将数据存入缓存。此版本是一个过渡性占位实现，内部触发 `SkASSERT(false)`。当所有客户端都迁移到三参数版本后，此方法将被移除。

#### `PersistentCache::store`（三参数版本）

```cpp
virtual void store(const SkData& key, const SkData& data, const SkString& description);
```

将数据存入缓存，并附带人类可读的描述信息。默认实现调用双参数版本，以便向后兼容。

### 回调与生命周期管理

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fContextDeleteContext` | `GrDirectContextDestroyedContext` | `nullptr` | 传递给销毁回调的用户数据 |
| `fContextDeleteProc` | `GrDirectContextDestroyedProc` | `nullptr` | `GrDirectContext` 销毁时调用的回调函数 |

当 `GrDirectContext` 即将被销毁时，会调用 `fContextDeleteProc` 并传入 `fContextDeleteContext`。这为客户端提供了一个安全的时机来释放底层 GPU 后端上下文（如 `VkDevice`、`id<MTLDevice>` 等）。

### 多线程与执行器

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fExecutor` | `SkExecutor*` | `nullptr` | 工作线程执行器 |

如果提供了 `SkExecutor` 实例，Ganesh 将使用工作线程来加速某些 CPU 密集型任务（如软件路径光栅化）。如果为 `nullptr`，所有工作将在主线程串行完成。

### 着色器管理

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fPersistentCache` | `PersistentCache*` | `nullptr` | 着色器持久化缓存实例 |
| `fShaderErrorHandler` | `ShaderErrorHandler*` | `nullptr` | 着色器编译失败的错误回调 |
| `fShaderCacheStrategy` | `ShaderCacheStrategy` | `kBackendBinary` | 着色器缓存存储策略 |
| `fReducedShaderVariations` | `bool` | `false` | 减少着色器变体数量以降低编译卡顿 |

**着色器缓存策略详解**：

| 策略 | 编译速度 | 跨版本兼容性 | 说明 |
|------|---------|-------------|------|
| `kSkSL` | 最慢（需重新编译） | 最高 | 缓存 Skia 的中间着色器语言 |
| `kBackendSource` | 较快 | 中等 | 缓存 GLSL 等后端源码，省去 SkSL 翻译 |
| `kBackendBinary` | 最快（直接加载） | 最低 | 缓存编译后的 GPU 程序二进制 |

### 纹理与缓冲区设置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fMinimumStagingBufferSize` | `size_t` | `64 * 1024` (64KB) | 纹理上传暂存缓冲区的最小尺寸 |
| `fGlyphCacheTextureMaximumBytes` | `size_t` | `2048 * 1024 * 4` (8MB) | 字形缓存纹理的最大字节数 |
| `fMaxTextureSizeOverride` | `int` | `SK_MaxS32` | 纹理尺寸上限的覆盖值 |
| `fBufferMapThreshold` | `int` | `-1`（自动） | 使用缓冲区映射 API 的数据大小阈值 |

`fMinimumStagingBufferSize` 控制纹理上传时暂存缓冲区的最小尺寸。较大的值可以将多次小尺寸上传合并到一个缓冲区中，减少 GPU 提交次数；但会增加未使用的 GPU 内存。超过此最小值的单次大尺寸上传会分配专用缓冲区。

### 字形渲染选项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fAllowMultipleGlyphCacheTextures` | `Enable` | `kDefault` | 是否允许字形图集使用多张纹理 |
| `fMinDistanceFieldFontSize` | `float` | `18` | 使用距离场字体的最小设备空间尺寸 |
| `fGlyphsAsPathsFontSize` | `float` | 平台相关 | 超过此尺寸时将字形渲染为路径 |
| `fSupportBilerpFromGlyphAtlas` | `bool` | `false` | 在字形图集中添加 1 像素填充以支持双线性插值 |

**`fGlyphsAsPathsFontSize` 平台差异**：

| 平台 | 默认值 |
|------|--------|
| Android (`SK_BUILD_FOR_ANDROID`) | 384 |
| macOS (`SK_BUILD_FOR_MAC`) | 256 |
| 其他平台 | 324 |

较大的字形使用路径渲染而非位图纹理，因为大尺寸位图会消耗过多的图集空间。不同平台的阈值差异反映了各平台 GPU 性能和字体渲染特性的不同。

### 多重采样（MSAA）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fInternalMultisampleCount` | `int` | `4` | 内部 MSAA 绘制的采样数 |
| `fAllowMSAAOnNewIntel` | `bool` | `false` | 是否在新款 Intel GPU 上启用 MSAA |

设为 0 将禁用所有内部使用 MSAA 的代码路径。实际采样数还受硬件能力的限制。

### 渲染路径控制

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fDisableCoverageCountingPaths` | `bool` | `true` | 禁用覆盖计数路径渲染 |
| `fDisableDistanceFieldPaths` | `bool` | `false` | 禁用距离场路径渲染 |
| `fAllowPathMaskCaching` | `bool` | `true` | 是否允许缓存路径遮罩纹理 |
| `fDisableTessellationPathRenderer` | `bool` | `false` | 禁用曲面细分路径渲染器 |
| `fEnableExperimentalHardwareTessellation` | `bool` | `false` | **已弃用**：启用实验性硬件曲面细分 |

### 驱动兼容性与修复

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fDriverBugWorkarounds` | `GrDriverBugWorkarounds` | 默认构造 | 驱动缺陷修复列表 |
| `fDisableDriverCorrectnessWorkarounds` | `bool` | `false` | 禁用所有驱动正确性修复 |
| `fDoManualMipmapping` | `bool` | `false` | 手动生成 mipmap（规避 `glGenerateMipmap` 缺陷） |
| `fAvoidStencilBuffers` | `bool` | `false` | 避免分配模板缓冲区（防止内存泄漏） |
| `fAlwaysUseTexStorageWhenAvailable` | `bool` | `false` | 始终使用 `glTexStorage`（仅 GL 后端） |

### GL 后端专用选项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fSkipGLErrorChecks` | `Enable` | `kDefault` | 跳过非关键的 GL 错误检查 |
| `fPreferExternalImagesOverES3` | `bool` | `false` | 在 ES3 上下文中优先使用 ES2 外部图像扩展 |

### 渲染质量控制

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fSharpenMipmappedTextures` | `bool` | `true` | 锐化 mipmap 纹理采样 |
| `fDisableGpuYUVConversion` | `bool` | `false` | 禁用 GPU 端 YUV->RGB 转换 |
| `fSuppressMipmapSupport` | `bool` | `false` | 完全禁用 mipmap 支持 |

### 运行时缓存

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fRuntimeProgramCacheSize` | `int` | `256` | 运行时 GPU 程序/管线缓存上限 |
| `fMaxCachedVulkanSecondaryCommandBuffers` | `int` | `-1`（自动） | Vulkan 次级命令缓冲区缓存数量 |

### 性能优化

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fReduceOpsTaskSplitting` | `Enable` | `kDefault` | 减少渲染通道切分以降低通道数 |
| `fUseDrawInsteadOfClear` | `Enable` | `kDefault` | 使用绘制代替硬件清除操作 |

### 其他选项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fSuppressPrints` | `bool` | `false` | 抑制 GrContext 的打印输出 |

### 测试专用选项 (GPU_TEST_UTILS)

以下选项仅在定义了 `GPU_TEST_UTILS` 宏时可用，用于 Skia 内部测试：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fGpuPathRenderers` | `GpuPathRenderers` | `kDefault` | 指定可用的 GPU 路径渲染器 |
| `fResourceCacheLimitOverride` | `int` | `-1` | 覆盖 GPU 资源缓存限制 |
| `fMaxTextureAtlasSize` | `int` | `2048` | 纹理图集最大尺寸 |
| `fFailFlushTimeCallbacks` | `bool` | `false` | 模拟 flush 回调分配失败 |
| `fSuppressDualSourceBlending` | `bool` | `false` | 禁用双源混合 |
| `fSuppressAdvancedBlendEquations` | `bool` | `false` | 禁用高级混合方程 |
| `fSuppressFramebufferFetch` | `bool` | `false` | 禁用帧缓冲区读取 |
| `fAllPathsVolatile` | `bool` | `false` | 将所有路径标记为易变 |
| `fWireframeMode` | `bool` | `false` | 线框渲染模式 |
| `fClearAllTextures` | `bool` | `false` | 创建时清除所有纹理 |
| `fRandomGLOOM` | `bool` | `false` | 随机生成 GL_OUT_OF_MEMORY 错误 |
| `fDisallowWriteAndTransferPixelRowBytes` | `bool` | `false` | 禁用写入/传输像素行步长 |

## 内部实现细节

### 初始化策略

`GrContextOptions` 采用"零配置即可工作"的设计理念。所有字段都有经过考量的默认值：

- 布尔字段默认为安全/保守的选择
- 数值字段默认为 `-1`（自动选择）或经验最优值
- 指针字段默认为 `nullptr`（禁用对应功能）
- `Enable` 类型字段默认为 `kDefault`（运行时自动判断）

### PersistentCache 的演化

`PersistentCache::store` 方法有两个重载：
1. 旧版 2 参数：`store(key, data)` -- 标记为未来将移除
2. 新版 3 参数：`store(key, data, description)` -- 增加人类可读描述

3 参数版本默认调用 2 参数版本，这是一种**渐进式 API 迁移**策略，确保旧客户端代码不会立即中断。

### 条件编译

测试专用选项通过 `#if defined(GPU_TEST_UTILS)` 保护，确保发布构建不包含这些仅用于测试的字段。`fGlyphsAsPathsFontSize` 通过平台宏实现跨平台的最优默认值：

```cpp
#if defined(SK_BUILD_FOR_ANDROID)
    float fGlyphsAsPathsFontSize = 384;
#elif defined(SK_BUILD_FOR_MAC)
    float fGlyphsAsPathsFontSize = 256;
#else
    float fGlyphsAsPathsFontSize = 324;
#endif
```

### 覆盖值的单向约束

`fMaxTextureSizeOverride` 等覆盖选项的设计原则是"只能减少，不能增加"。默认值为 `SK_MaxS32`（即不做任何限制），客户端可以将其设为更小的值来限制纹理尺寸，但无法超过硬件实际支持的最大值。这是一种防御性设计，防止客户端配置超出硬件能力的值导致未定义行为。

## 依赖关系

```
GrContextOptions.h
├── include/core/SkData.h                     数据容器（PersistentCache 使用）
├── include/core/SkString.h                   字符串类型（缓存描述）
├── include/core/SkTypes.h                    核心基础类型
├── include/gpu/ShaderErrorHandler.h          着色器错误处理接口
├── include/gpu/ganesh/GrDriverBugWorkarounds.h  驱动缺陷修复列表
├── include/gpu/ganesh/GrTypes.h              Ganesh 基础类型
├── include/private/gpu/ganesh/GrTypesPriv.h  Ganesh 私有类型
├── <optional>                                C++ 标准库
└── <vector>                                  C++ 标准库
```

前向声明的类型：
- `SkExecutor` -- 多线程任务执行器

主要消费者：
- `GrDirectContext` -- 在创建时接收并存储 `GrContextOptions`
- `GrContextFactory`（测试工具）-- 构建不同配置的测试上下文
- 各种 Skia 工具和应用（`Viewer`、`skottie` 等）

## 设计模式与设计决策

### 配置对象模式（Configuration Object Pattern）

`GrContextOptions` 是经典的**配置对象模式**的实现。将数十个配置选项集中在一个结构体中，相比于在构造函数中传递大量参数，具有以下优势：

1. **可选性**：所有字段都有默认值，客户端只需设置关心的选项
2. **可扩展性**：新增配置项不会破坏现有 API
3. **可读性**：每个配置字段都有明确的名称和文档注释

### 三态开关设计

`Enable` 枚举提供了 `kNo/kYes/kDefault` 三种状态，其中 `kDefault` 允许 Skia 根据运行时环境自动决策。这种设计在"客户端显式控制"和"引擎智能选择"之间取得了平衡。

### 策略模式（Strategy Pattern）

`PersistentCache` 和 `ShaderErrorHandler` 采用**策略模式**，通过抽象接口将缓存存储和错误报告的具体实现与 Ganesh 引擎解耦。客户端可以注入自定义实现来适配不同的运行环境。

### 观察者模式（Observer Pattern）

`fContextDeleteProc` 回调实现了简单的观察者模式，允许客户端在上下文销毁时得到通知，从而安全地释放关联资源。

### 防御性默认值

许多安全相关选项默认取保守值。例如：
- `fDisableCoverageCountingPaths = true` -- 默认禁用可能产生视觉伪影的覆盖计数路径
- `fSharpenMipmappedTextures = true` -- 默认启用视觉质量优化
- `fAllowPathMaskCaching = true` -- 默认启用性能优化

### 驱动兼容层

`fDriverBugWorkarounds`、`fDoManualMipmapping`、`fAvoidStencilBuffers` 等选项构成了一个驱动兼容性层，允许规避已知的 GPU 驱动缺陷。`fDisableDriverCorrectnessWorkarounds` 提供了一个总开关来禁用所有自动修复，主要用于测试场景。

### 渐进式 API 迁移

`PersistentCache::store` 提供了双参数和三参数两个版本，反映了 API 正在渐进式迁移的状态。旧版 2 参数方法通过 `SkASSERT(false)` 标记为不应被直接调用，鼓励客户端迁移到 3 参数版本，同时通过默认调用链保持向后兼容。

## 性能考量

### 着色器编译卡顿

着色器编译是 GPU 渲染中最常见的卡顿源之一。`GrContextOptions` 提供了多种手段来缓解：

1. **`fPersistentCache`**：将编译好的着色器缓存到持久存储中，避免每次启动时重新编译。使用 `kBackendBinary` 策略时效果最佳，因为跳过了整个编译过程。

2. **`fReducedShaderVariations`**：减少着色器变体数量。虽然可能降低稳态性能，但显著减少了首次遇到新渲染场景时的编译卡顿。

3. **`fRuntimeProgramCacheSize`**：控制内存中缓存的 GPU 程序数量，在内存占用和缓存命中率之间取舍。

### 渲染通道优化

`fReduceOpsTaskSplitting` 选项（默认启用）允许 Ganesh 更激进地重排渲染操作，将离屏绘制提前执行，减少渲染通道的切换次数。这可能增加显存峰值使用量，但通常能显著提升渲染吞吐量。

### 内存控制

- `fMinimumStagingBufferSize`：较大的暂存缓冲区减少 GPU 提交次数但增加内存占用
- `fGlyphCacheTextureMaximumBytes`：限制字形缓存的显存使用
- `fMaxCachedVulkanSecondaryCommandBuffers`：控制 Vulkan 命令缓冲区的缓存数量
- `fMaxTextureSizeOverride`：可用于限制纹理尺寸以减少显存使用

### 多线程加速

通过设置 `fExecutor`，CPU 密集型任务（如软件路径光栅化）可以分发到工作线程，释放主线程用于 GPU 提交和渲染。

### 字形渲染路径选择

`fMinDistanceFieldFontSize` 和 `fGlyphsAsPathsFontSize` 控制字形渲染在位图纹理、距离场和路径之间的切换阈值，影响渲染质量和性能的权衡：

- 小字号（< 18pt）：使用位图纹理，保持提示信息（hinting）
- 中字号（18pt ~ 阈值）：使用距离场字体，节省图集空间
- 大字号（> 阈值）：使用路径渲染，避免占用大量图集空间

### 缓冲区映射阈值

`fBufferMapThreshold` 控制何时使用映射 API（如 `glMapBuffer`）而非直接复制来更新顶点和索引缓冲区。值为 `-1` 时由 Skia 根据平台特性自动选择最优策略。映射 API 对于大块数据传输通常更高效，但对小块数据可能引入额外开销。

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/gpu/ganesh/GrDirectContext.h` | Ganesh 直接上下文，在创建时消费 `GrContextOptions` |
| `include/gpu/ganesh/GrTypes.h` | Ganesh 基础类型定义（`GrBackendApi`、`GrDirectContextDestroyedProc` 等） |
| `include/gpu/ganesh/GrDriverBugWorkarounds.h` | 驱动缺陷修复列表类型 |
| `include/gpu/ShaderErrorHandler.h` | 着色器错误处理接口 |
| `include/gpu/GpuTypes.h` | 所有 GPU 后端共享的基础类型 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | Ganesh 私有类型（含 `GpuPathRenderers` 等） |
| `include/core/SkData.h` | 数据容器，用于 `PersistentCache` 的键值存储 |
| `include/core/SkString.h` | 字符串类型，用于缓存条目描述 |
| `tools/ganesh/GrContextFactory.h` | 测试工具，使用 `GrContextOptions` 创建测试上下文 |
| `tools/window/DisplayParams.h` | 窗口显示参数，包含 `GrContextOptions` 成员 |
| `tools/flags/CommonFlagsGanesh.cpp` | 命令行标志到 `GrContextOptions` 的映射 |
