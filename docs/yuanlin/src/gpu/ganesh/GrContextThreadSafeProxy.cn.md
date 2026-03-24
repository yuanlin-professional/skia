# GrContextThreadSafeProxy

> 源文件
> - include/gpu/ganesh/GrContextThreadSafeProxy.h
> - src/gpu/ganesh/GrContextThreadSafeProxy.cpp

## 概述

`GrContextThreadSafeProxy` 是 Ganesh GPU 后端的线程安全代理类,允许在多线程环境中安全地执行与 `GrContext` 相关的操作,而无需访问底层的 3D API(如 OpenGL、Vulkan)。该类主要用于延迟显示列表(DDL, Deferred Display List)的创建和查询 GPU 能力。

该类实现了引用计数机制,支持在多个线程间共享,同时保证对 GPU 能力信息的只读访问是线程安全的。每个 `GrContext` 都有唯一的线程安全代理实例。

## 架构位置

`GrContextThreadSafeProxy` 位于 Ganesh GPU 后端的核心基础设施层:

```
skia/
  include/gpu/ganesh/
    GrContextThreadSafeProxy.h      # 公共接口
    GrContextOptions.h              # 上下文配置
  src/gpu/ganesh/
    GrContextThreadSafeProxy.cpp    # 实现
    GrContextThreadSafeProxyPriv.h  # 内部接口
    GrCaps.h                        # GPU 能力抽象
    GrThreadSafeCache.h             # 线程安全缓存
    GrThreadSafePipelineBuilder.h  # 管线构建器
```

该类作为 `GrDirectContext` 和 `GrRecordingContext` 的成员,为 DDL 录制提供线程安全的上下文信息。

## 主要类与结构体

### GrContextThreadSafeProxy

线程安全的上下文代理类。

**继承关系:**
- 基类: `SkNVRefCnt<GrContextThreadSafeProxy>`(非虚析构引用计数)
- 派生类: 无(可能被 Vulkan 特定子类继承)

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBackend` | `const GrBackendApi` | GPU 后端类型(OpenGL/Vulkan/Metal 等) |
| `fOptions` | `const GrContextOptions` | 上下文创建选项 |
| `fContextID` | `const uint32_t` | 唯一上下文标识符 |
| `fCaps` | `sk_sp<const GrCaps>` | GPU 能力描述(线程安全只读) |
| `fTextBlobRedrawCoordinator` | `std::unique_ptr<TextBlobRedrawCoordinator>` | 文本绘制协调器 |
| `fThreadSafeCache` | `std::unique_ptr<GrThreadSafeCache>` | 线程安全缓存 |
| `fPipelineBuilder` | `sk_sp<GrThreadSafePipelineBuilder>` | 管线构建器 |
| `fAbandoned` | `std::atomic<bool>` | 上下文是否已放弃(原子操作) |

## 公共 API 函数

### 创建表面特征化

```cpp
GrSurfaceCharacterization createCharacterization(
    size_t cacheMaxResourceBytes,
    const SkImageInfo& ii,
    const GrBackendFormat& backendFormat,
    int sampleCount,
    GrSurfaceOrigin origin,
    const SkSurfaceProps& surfaceProps,
    skgpu::Mipmapped isMipmapped,
    bool willUseGLFBO0 = false,
    bool isTextureable = true,
    skgpu::Protected isProtected = GrProtected::kNo,
    bool vkRTSupportsInputAttachment = false,
    bool forVulkanSecondaryCommandBuffer = false);
```
**功能:** 为 DDL 创建表面特征化描述
**参数:**
- `cacheMaxResourceBytes` - DDL 录制时的最大资源预算
- `ii` - 目标表面的图像信息
- `backendFormat` - 后端格式信息
- `sampleCount` - MSAA 采样数
- `origin` - 表面原点(左上/左下)
- `surfaceProps` - 表面属性
- `isMipmapped` - 是否支持 mipmap
- `willUseGLFBO0` - 是否使用 OpenGL 的 FBO 0(默认帧缓冲)
- `isTextureable` - 是否可作为纹理
- `isProtected` - 是否受保护内容
- `vkRTSupportsInputAttachment` - Vulkan 输入附件支持
- `forVulkanSecondaryCommandBuffer` - 是否用于 Vulkan 二级命令缓冲

**返回:** 有效的 `GrSurfaceCharacterization` 或无效对象
**用途:** DDL 录制前验证目标表面兼容性

### 格式查询

```cpp
GrBackendFormat defaultBackendFormat(SkColorType ct, GrRenderable renderable) const;
```
**功能:** 获取指定颜色类型的默认后端格式
**参数:**
- `ct` - Skia 颜色类型
- `renderable` - 是否需要可渲染

**返回:** 有效的 `GrBackendFormat` 或无效格式

```cpp
GrBackendFormat compressedBackendFormat(SkTextureCompressionType c) const;
```
**功能:** 获取压缩纹理的后端格式
**参数:** `c` - 压缩类型(如 ETC2、BC1)
**返回:** 有效的 `GrBackendFormat` 或无效格式

### 能力查询

```cpp
int maxSurfaceSampleCountForColorType(SkColorType colorType) const;
```
**功能:** 获取指定颜色类型的最大 MSAA 采样数
**返回:**
- `0` - 不支持渲染
- `1` - 仅支持非 MSAA 渲染
- `>1` - 支持的最大 MSAA 采样数

### 有效性检查

```cpp
bool isValid() const;
```
**功能:** 检查代理是否已初始化(是否有有效的 `fCaps`)
**返回:** `true` 表示代理有效

### 操作符重载

```cpp
bool operator==(const GrContextThreadSafeProxy& that) const;
bool operator!=(const GrContextThreadSafeProxy& that) const;
```
**功能:** 比较代理是否指向同一上下文
**实现:** 比较对象指针(每个上下文只有一个代理)

### 内部访问

```cpp
GrContextThreadSafeProxyPriv priv();
const GrContextThreadSafeProxyPriv priv() const;
```
**功能:** 访问私有接口(友元类模式)

## 内部实现细节

### 上下文 ID 生成

使用原子计数器生成唯一 ID:

```cpp
static uint32_t next_id() {
    static std::atomic<uint32_t> nextID{1};
    uint32_t id;
    do {
        id = nextID.fetch_add(1, std::memory_order_relaxed);
    } while (id == SK_InvalidGenID);
    return id;
}
```

**特点:**
- 线程安全的原子操作
- 跳过无效 ID(`SK_InvalidGenID`)
- 使用 `memory_order_relaxed` 优化性能

### 延迟初始化

构造函数仅设置后端类型和选项,实际能力信息通过 `init()` 方法延迟初始化:

```cpp
void GrContextThreadSafeProxy::init(sk_sp<const GrCaps> caps,
                                    sk_sp<GrThreadSafePipelineBuilder> pipelineBuilder) {
    fCaps = std::move(caps);
    fTextBlobRedrawCoordinator = std::make_unique<...>(fContextID);
    fThreadSafeCache = std::make_unique<GrThreadSafeCache>();
    fPipelineBuilder = std::move(pipelineBuilder);
}
```

### 表面特征化验证

`createCharacterization` 执行大量验证:

1. **后端格式验证** - 检查格式是否有效
2. **后端匹配检查** - 验证 OpenGL/Vulkan 特定标志
3. **Mipmap 支持** - 根据硬件能力调整
4. **尺寸限制** - 检查是否超出最大渲染目标大小
5. **颜色类型兼容性** - 验证颜色类型与格式匹配
6. **采样数调整** - 根据硬件能力调整 MSAA 采样数
7. **纹理性验证** - 检查是否可作为纹理使用

### Vulkan 特定验证

虚函数 `isValidCharacterizationForVulkan` 由 Vulkan 子类实现:

```cpp
virtual bool isValidCharacterizationForVulkan(...) {
    return false;  // 基类默认返回 false
}
```

### 放弃上下文

使用原子操作确保线程安全:

```cpp
void GrContextThreadSafeProxy::abandonContext() {
    if (!fAbandoned.exchange(true)) {
        fTextBlobRedrawCoordinator->freeAll();
    }
}
```

**特点:**
- `exchange` 返回旧值,确保仅释放一次
- 释放文本 blob 缓存

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/gpu/GpuTypes.h` | GPU 类型定义 |
| `include/gpu/ganesh/GrContextOptions.h` | 上下文配置选项 |
| `src/gpu/ganesh/GrCaps.h` | GPU 能力抽象 |
| `src/gpu/ganesh/GrThreadSafeCache.h` | 线程安全缓存 |
| `src/gpu/ganesh/GrThreadSafePipelineBuilder.h` | 管线构建器 |
| `src/text/gpu/TextBlobRedrawCoordinator.h` | 文本 blob 协调器 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `GrDirectContext` | 持有代理实例 |
| `GrRecordingContext` | 使用代理查询能力 |
| `GrSurfaceCharacterization` | 接收代理引用 |
| DDL 录制 API | 使用代理创建特征化 |
| 多线程渲染 | 跨线程共享代理 |

## 设计模式与设计决策

### 设计模式

1. **代理模式 (Proxy Pattern)**
   - 代理 `GrDirectContext`,提供线程安全的子集功能
   - 不直接访问 GPU,仅访问只读能力信息

2. **单例保证**
   - 每个 `GrContext` 只有一个代理
   - 通过对象指针比较实现 `operator==`

3. **友元类访问 (Friend Pattern)**
   - `GrContextThreadSafeProxyPriv` 提供内部接口
   - 避免公开过多实现细节

4. **引用计数管理**
   - 使用 `SkNVRefCnt` 支持智能指针 `sk_sp`
   - 线程安全的引用计数

### 设计决策

1. **线程安全性**
   - 所有公共方法访问只读数据(`const GrCaps`)
   - 放弃操作使用原子变量
   - 不涉及 GPU 命令提交,避免同步问题

2. **延迟初始化**
   - 构造函数不初始化能力信息
   - 避免构造时依赖未创建的 GPU 对象

3. **DDL 支持**
   - 特征化允许离线验证目标表面
   - 录制和重放可在不同线程

4. **后端抽象**
   - 虚函数 `isValidCharacterizationForVulkan` 支持后端特定逻辑
   - 基类提供通用验证

5. **能力缓存**
   - `fCaps` 使用 `sk_sp<const GrCaps>`,确保不可变
   - 多线程可安全并发访问

## 性能考量

1. **线程安全开销**
   - 只读访问无需锁,无同步开销
   - 原子操作仅在放弃时使用,频率低

2. **引用计数**
   - 使用原子引用计数,轻量线程安全
   - 避免虚析构函数开销(`SkNVRefCnt`)

3. **内存布局**
   - `fCaps` 使用智能指针,避免大对象复制
   - 缓存和协调器使用 `unique_ptr`,延迟分配

4. **特征化创建**
   - 大量验证逻辑,但仅在 DDL 创建时执行
   - 录制时开销可接受

5. **ID 生成**
   - 使用 `memory_order_relaxed`,减少内存屏障开销
   - ID 生成频率低,性能影响小

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/gpu/ganesh/GrContextThreadSafeProxy.h` | 公共接口 |
| `src/gpu/ganesh/GrContextThreadSafeProxy.cpp` | 实现 |
| `src/gpu/ganesh/GrContextThreadSafeProxyPriv.h` | 内部接口 |
| `include/private/chromium/GrSurfaceCharacterization.h` | 表面特征化 |
| `src/gpu/ganesh/GrCaps.h` | GPU 能力抽象 |
| `include/gpu/ganesh/GrDirectContext.h` | 直接上下文 |
| `include/gpu/ganesh/GrRecordingContext.h` | 录制上下文 |
| `src/gpu/ganesh/GrThreadSafeCache.h` | 线程安全缓存 |
