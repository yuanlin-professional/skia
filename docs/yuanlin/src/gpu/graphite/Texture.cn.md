# Texture

> 源文件: src/gpu/graphite/Texture.h, src/gpu/graphite/Texture.cpp

## 概述

`Texture` 是 Skia Graphite 渲染架构中表示 GPU 纹理资源的核心基类。该类继承自 `Resource`，封装了纹理的维度、格式信息、采样参数以及生命周期管理。`Texture` 提供了纹理资源的统一抽象接口，隐藏了不同后端（Metal、Vulkan、Dawn）的具体实现细节。

该类负责管理纹理的状态变化、内存占用追踪、释放回调以及主机端数据上传能力。所有后端特定的纹理实现（如 `MtlTexture`、`VulkanTexture`）都继承自此基类，并实现后端特定的纹理操作。

## 架构位置

`Texture` 在 Graphite 资源管理层次中的位置：

```
Graphite 资源架构：
  ├── Resource（资源基类）
  │   ├── Buffer（缓冲区）
  │   ├── Sampler（采样器）
  │   └── Texture（纹理）★
  │       ├── MtlTexture（Metal 后端）
  │       ├── VulkanTexture（Vulkan 后端）
  │       └── DawnTexture（Dawn 后端）
  └── ResourceProvider（资源提供者）
      └── TextureProxy（纹理代理）→ Texture（实例化）
```

与相关组件的协作：
- **TextureProxy**: 延迟纹理创建的代理对象，在需要时实例化 `Texture`
- **ResourceProvider**: 创建和缓存 `Texture` 实例
- **TextureInfo**: 描述纹理格式、用途、采样参数的不透明结构
- **UploadSource**: 提供纹理上传数据的源
- **MutableTextureState**: 追踪纹理的状态变化（如布局、访问模式）

## 主要类与结构体

### Texture 类

```cpp
class Texture : public Resource {
public:
    ~Texture() override;

    // 纹理属性访问
    SampleCount sampleCount() const;
    Mipmapped mipmapped() const;
    SkISize dimensions() const;
    const TextureInfo& textureInfo() const;

    // 资源类型识别
    const char* getResourceType() const override;
    const Texture* asTexture() const override;

    // 生命周期管理
    void setReleaseCallback(sk_sp<RefCntedCallback>);

    // 主机端上传接口（后端可选实现）
    virtual bool canUploadOnHost(const UploadSource&) const;
    virtual bool uploadDataOnHost(const UploadSource& source, const SkIRect& dstRect);

protected:
    Texture(const SharedContext*,
            SkISize dimensions,
            const TextureInfo& info,
            bool isTransient,
            sk_sp<MutableTextureState>,
            Ownership,
            std::string_view label);

    MutableTextureState* mutableState() const;
    void invokeReleaseProc() override;
    void onDumpMemoryStatistics(SkTraceMemoryDump*, const char*) const override;

private:
    SkISize fDimensions;                      // 纹理尺寸
    TextureInfo fInfo;                        // 纹理格式和配置信息
    sk_sp<MutableTextureState> fMutableState; // 可变状态（如布局）
    sk_sp<RefCntedCallback> fReleaseCallback; // 释放回调
};
```

### 成员变量说明

| 成员变量 | 类型 | 用途 |
|---------|------|------|
| `fDimensions` | `SkISize` | 纹理的宽度和高度（以像素为单位） |
| `fInfo` | `TextureInfo` | 后端无关的纹理描述（格式、采样数、mipmap 等） |
| `fMutableState` | `sk_sp<MutableTextureState>` | 追踪纹理状态变化的共享对象 |
| `fReleaseCallback` | `sk_sp<RefCntedCallback>` | 纹理释放时的回调函数（用于同步） |

## 公共 API 函数

### 构造函数

```cpp
protected:
Texture(const SharedContext* sharedContext,
        SkISize dimensions,
        const TextureInfo& info,
        bool isTransient,
        sk_sp<MutableTextureState> mutableState,
        Ownership ownership,
        std::string_view label);
```

**参数说明**:
- `sharedContext`: 共享上下文指针，提供后端能力查询
- `dimensions`: 纹理尺寸（宽 × 高）
- `info`: 纹理格式信息（包含格式、采样数、用途等）
- `isTransient`: 是否为瞬态纹理（不计入内存预算）
- `mutableState`: 可变状态对象（跨队列传递时需要）
- `ownership`: 所有权模式（`kOwned` 或 `kWrapped`）
- `label`: 调试标签字符串

**内存计算**: 瞬态纹理的初始 GPU 大小为 0，非瞬态纹理通过 `ComputeSize(dimensions, info)` 计算实际占用。

### 属性访问器

```cpp
SampleCount sampleCount() const;  // 返回多重采样数（1, 2, 4, 8...）
Mipmapped mipmapped() const;      // 返回是否有 mipmap 级别
SkISize dimensions() const;       // 返回纹理尺寸
const TextureInfo& textureInfo() const;  // 返回完整的纹理信息
```

### 生命周期管理

#### setReleaseCallback

```cpp
void setReleaseCallback(sk_sp<RefCntedCallback> releaseCallback);
```

**功能**: 设置纹理释放时的回调函数。

**使用场景**:
- 外部资源包装（如 `SkImage` 从后端纹理创建）
- CPU-GPU 同步（确保纹理不再使用后释放外部资源）
- 纹理销毁通知

**调用时机**: 回调在 `invokeReleaseProc()` 中触发，通常在析构函数或资源回收时。

### 主机端上传接口

#### canUploadOnHost

```cpp
virtual bool canUploadOnHost(const UploadSource& source) const;
```

**功能**: 查询是否可以在主机端（CPU 侧）直接上传数据到纹理。

**返回值**: 默认返回 `false`，后端实现可以覆盖（如 Metal 的共享纹理）。

**适用场景**:
- 映射的纹理内存（如 Metal 的 `MTLStorageModeShared`）
- UMA 架构（如移动设备的统一内存）

#### uploadDataOnHost

```cpp
virtual bool uploadDataOnHost(const UploadSource& source, const SkIRect& dstRect);
```

**功能**: 在主机端直接写入数据到纹理的指定矩形区域。

**前提条件**: `canUploadOnHost()` 返回 `true`。

**返回值**: `false` 表示驱动调用失败，`true` 表示成功。

**默认实现**: 调用 `SK_ABORT("Not implemented")`，需要后端覆盖。

### 内部方法

#### mutableState

```cpp
protected:
MutableTextureState* mutableState() const;
```

**功能**: 获取可变状态对象指针，用于跨队列同步。

**使用场景**:
- Vulkan 的图像布局转换
- Metal 的资源状态追踪
- 队列所有权转移

#### invokeReleaseProc

```cpp
protected:
void invokeReleaseProc() override;
```

**功能**: 触发释放回调函数。

**实现细节**:
```cpp
void Texture::invokeReleaseProc() {
    if (fReleaseCallback) {
        // 重置智能指针可能触发回调（取决于引用计数）
        fReleaseCallback.reset();
    }
}
```

#### onDumpMemoryStatistics

```cpp
protected:
void onDumpMemoryStatistics(SkTraceMemoryDump* traceMemoryDump,
                            const char* dumpName) const override;
```

**功能**: 向内存追踪工具报告纹理的统计信息。

**输出信息**:
- `dimensions`: 纹理尺寸（如 "(1024x768)"）
- `textureInfo`: 纹理格式字符串（通过 `TextureInfo::toString()` 生成）

## 内部实现细节

### 内存大小计算

```cpp
// 构造函数中：
Resource(sharedContext, ownership,
         isTransient ? 0 : ComputeSize(dimensions, info),
         label)
```

**瞬态纹理**: 初始 GPU 大小为 0，不计入预算。用于帧缓冲附件、临时渲染目标等。

**非瞬态纹理**: 通过 `TextureUtils::ComputeSize()` 计算：
```cpp
size_t ComputeSize(SkISize dimensions, const TextureInfo& info) {
    // 基础大小 = width * height * bytesPerPixel
    size_t size = dimensions.width() * dimensions.height() * info.bytesPerPixel();

    // 添加 mipmap 级别（约 1/3 额外空间）
    if (info.mipmapped() == Mipmapped::kYes) {
        size += size / 3;  // 1 + 1/4 + 1/16 + ... ≈ 4/3
    }

    // 多重采样倍数
    size *= info.sampleCount();

    return size;
}
```

### 状态管理

**MutableTextureState 的作用**:
- **Vulkan**: 追踪 `VkImageLayout` 和访问掩码
- **Metal**: 通常为 `nullptr`（Metal 自动管理状态）
- **队列转移**: 在不同命令队列间传递纹理时保持状态一致

**状态访问**:
```cpp
MutableTextureState* Texture::mutableState() const {
    return fMutableState.get();
}
```

### 释放回调机制

**回调设计目的**:
1. **外部资源同步**: 包装的后端纹理需要在 Skia 释放后通知外部
2. **延迟销毁**: 某些资源可能在 GPU 仍在使用时被 CPU 释放
3. **资源跟踪**: 应用层统计纹理生命周期

**引用计数保护**:
```cpp
void Texture::invokeReleaseProc() {
    if (fReleaseCallback) {
        fReleaseCallback.reset();  // 减少引用计数，可能触发回调
    }
}
```

如果其他对象持有 `fReleaseCallback` 的引用，回调不会立即执行。

### 虚函数扩展点

**后端实现需要覆盖的虚函数**:
1. `canUploadOnHost()`: 主机端上传能力查询
2. `uploadDataOnHost()`: 主机端上传实现
3. `onDumpMemoryStatistics()`: 后端特定的内存统计（可选）

**示例：Metal 后端**:
```cpp
class MtlTexture : public Texture {
    bool canUploadOnHost(const UploadSource& source) const override {
        return fMtlTexture.storageMode == MTLStorageModeShared;
    }

    bool uploadDataOnHost(const UploadSource& source, const SkIRect& dstRect) override {
        void* mapped = [fMtlTexture contents];
        // 拷贝 source 的数据到 mapped 内存
        return true;
    }
};
```

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `Resource` | 基类，提供内存管理和缓存支持 |
| `TextureInfo` | 描述纹理的格式和属性 |
| `SharedContext` | 提供后端能力查询 |
| `MutableTextureState` | 追踪纹理状态变化 |
| `RefCntedCallback` | 引用计数的回调函数 |
| `UploadSource` | 纹理上传数据的源接口 |
| `TextureUtils` | 纹理大小计算辅助函数 |

### 外部依赖

| 依赖 | 用途 |
|------|------|
| Skia Core (`SkISize`, `SkIRect`) | 尺寸和区域表示 |
| `SkTraceMemoryDump` | 内存追踪支持 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `TextureProxy` | 延迟实例化 `Texture` 对象 |
| `ResourceProvider` | 创建和缓存 `Texture` 实例 |
| `BackendTexture` | 包装后端特定的纹理句柄 |
| `CommandBuffer` | 纹理绑定和渲染操作 |
| `SkImage_Graphite` | 图像数据的 GPU 表示 |

## 设计模式与设计决策

### 模板方法模式

基类定义了通用的纹理接口和生命周期管理，后端实现覆盖虚函数以提供特定行为：
```cpp
// 基类定义框架
class Texture : public Resource {
    virtual bool canUploadOnHost(...) const { return false; }
    virtual bool uploadDataOnHost(...);  // 默认 SK_ABORT
};

// 后端实现具体策略
class MtlTexture : public Texture {
    bool canUploadOnHost(...) const override { /* Metal 特定逻辑 */ }
    bool uploadDataOnHost(...) override { /* Metal 特定实现 */ }
};
```

### RAII 资源管理

纹理的生命周期通过 `sk_sp` 智能指针管理：
- 构造时分配 GPU 资源
- 析构时自动触发 `invokeReleaseProc()` 和资源回收
- 引用计数确保纹理在使用中不会被释放

### 策略模式

**所有权策略**:
- `Ownership::kOwned`: Skia 拥有并管理纹理生命周期
- `Ownership::kWrapped`: 纹理由外部管理，Skia 仅包装使用

**瞬态标记策略**:
- `isTransient = true`: 不计入预算，通常用于帧内临时资源
- `isTransient = false`: 计入预算，可能被缓存重用

### 延迟绑定设计

- **TextureInfo 不透明性**: `TextureInfo` 是不透明结构，避免基类依赖后端特定类型
- **状态延迟查询**: 通过 `mutableState()` 获取状态，而非在基类存储具体状态

### 关键设计决策

1. **纯虚函数最小化**: 仅 `uploadDataOnHost()` 默认未实现，避免强制所有后端实现
2. **可变状态分离**: `MutableTextureState` 独立管理，避免基类膨胀
3. **内存统计可扩展**: `onDumpMemoryStatistics()` 虚函数允许后端添加额外信息
4. **回调可选性**: `setReleaseCallback()` 仅在需要时设置，避免所有纹理开销

## 性能考量

### 内存占用

1. **瞬态纹理优化**: 标记为瞬态的纹理不占用预算，允许更激进的临时资源使用
2. **精确大小计算**: `ComputeSize()` 包含 mipmap 和多重采样开销，确保预算准确
3. **智能指针开销**: 每个 `Texture` 有 2 个 `sk_sp` 成员（约 16 字节额外开销）

### 缓存友好性

- **只读信息聚合**: `fDimensions` 和 `fInfo` 常被一起访问，布局在相邻内存
- **状态指针延迟解引用**: `fMutableState` 通过指针访问，不在热路径

### 虚函数开销

- **虚函数调用**: 每个 `Texture` 对象有虚函数表指针（8 字节）
- **内联优化**: `sampleCount()` 等简单访问器可能被编译器去虚化

### 主机端上传优化

```cpp
if (texture->canUploadOnHost(source)) {
    // 避免 GPU 拷贝，直接在主机端写入
    texture->uploadDataOnHost(source, dstRect);
} else {
    // 使用传统的 GPU 上传路径
    uploadViaCommandBuffer(texture, source, dstRect);
}
```

对于共享内存架构，避免额外的数据拷贝和 GPU 命令。

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `include/gpu/graphite/TextureInfo.h` | 纹理格式和配置的描述符 |
| `src/gpu/graphite/Resource.h` | 资源基类 |
| `src/gpu/graphite/TextureProxy.h` | 纹理的延迟实例化代理 |
| `src/gpu/graphite/TextureUtils.h` | 纹理大小计算等辅助函数 |
| `src/gpu/graphite/ResourceProvider.h` | 纹理创建和缓存管理 |
| `include/gpu/MutableTextureState.h` | 可变纹理状态接口 |
| `src/gpu/RefCntedCallback.h` | 引用计数的回调函数 |
| `src/gpu/graphite/mtl/MtlTexture.h` | Metal 后端实现 |
| `src/gpu/graphite/vk/VulkanTexture.h` | Vulkan 后端实现 |
| `src/gpu/graphite/dawn/DawnTexture.h` | Dawn 后端实现 |
