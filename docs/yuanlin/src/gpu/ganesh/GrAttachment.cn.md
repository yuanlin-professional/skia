# GrAttachment

> 源文件: src/gpu/ganesh/GrAttachment.h, src/gpu/ganesh/GrAttachment.cpp

## 概述

`GrAttachment` 是 Ganesh GPU 后端中表示通用 GPU 附件的抽象类,代表单个 GPU 内存分配,可用作模板附件、颜色附件或纹理。该类是 Skia 逐步将纹理和渲染目标从传统钻石继承结构中分离的过渡性设计,旨在建立更清晰的表面(Surface)和帧缓冲(Framebuffer)架构。

`GrAttachment` 继承自 `GrSurface`,封装了使用标志(Usage Flags)、采样数(Sample Count)、Mipmap 状态等通用属性,并提供了基于这些属性的缓存键生成机制。该类支持在多个渲染目标间共享附件,通过唯一键(Unique Key)实现资源复用。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrSurface.h                # 表面基类
    │   └── GrAttachment.h/cpp     # [本模块] 通用附件类
    │       ├── GrRenderTarget.h   # 渲染目标(使用 Attachment)
    │       └── GrTexture.h        # 纹理(内部包含 Attachment)
    ├── GrGpu.h                    # GPU 设备抽象
    ├── GrResourceCache.h          # 资源缓存系统
    └── vk/GrVkImage.h             # Vulkan 实现(GrAttachment 子类)
```

该模块位于 Ganesh 资源管理层的核心,为上层渲染目标和纹理提供统一的 GPU 内存抽象。

## 主要类与结构体

### GrAttachment 类

**继承关系**:
```
GrGpuResource
    └── GrSurface
            └── GrAttachment (抽象类)
                    ├── GrVkImage (Vulkan 实现)
                    ├── GrMtlAttachment (Metal 实现)
                    └── GrGLAttachment (OpenGL 实现)
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSupportedUsages` | `UsageFlags` | 支持的使用类型(位掩码) |
| `fSampleCnt` | `int` | 多重采样数(1 表示无 MSAA) |
| `fMipmapped` | `skgpu::Mipmapped` | 是否包含 Mipmap 链 |
| `fHasPerformedInitialClear` | `bool` | 是否已执行初始清除 |
| `fMemoryless` | `GrMemoryless` | 是否为无内存附件(移动 GPU) |

### UsageFlags 枚举

```cpp
enum class UsageFlags : uint8_t {
    kStencilAttachment = 0x1,  // 可用作模板附件
    kColorAttachment   = 0x2,  // 可用作颜色附件
    kTexture           = 0x4,  // 可用作可采样纹理
};
```

**位操作支持**: 通过 `SK_DECL_BITFIELD_CLASS_OPS_FRIENDS` 宏支持位运算符(&, |, ~)。

## 公共 API 函数

### 属性查询

```cpp
UsageFlags supportedUsages() const
int numSamples() const
skgpu::Mipmapped mipmapped() const
```

**功能**: 查询附件的基本属性。

**使用场景**:
- 在绑定附件前验证兼容性
- 资源缓存查找时匹配条件
- 内存统计和调试信息收集

### 初始清除状态管理

```cpp
bool hasPerformedInitialClear() const
void markHasPerformedInitialClear()
```

**功能**: 跟踪附件是否已执行首次清除操作。

**设计理由**:
- **安全性**: 未初始化的 GPU 内存可能包含随机数据
- **性能优化**: 避免重复清除已知清洁的附件
- **Vulkan 要求**: 某些后端要求首次使用前明确清除

**使用模式**:
```cpp
if (!attachment->hasPerformedInitialClear()) {
    clearAttachment(attachment);
    attachment->markHasPerformedInitialClear();
}
```

### 缓存键生成

#### 唯一键生成(共享附件)

```cpp
static void ComputeSharedAttachmentUniqueKey(
    const GrCaps& caps,
    const GrBackendFormat& format,
    SkISize dimensions,
    UsageFlags requiredUsage,
    int sampleCnt,
    skgpu::Mipmapped mipmapped,
    GrProtected isProtected,
    GrMemoryless memoryless,
    skgpu::UniqueKey* key)
```

**功能**: 为可在多个渲染目标间共享的附件生成唯一键。

**关键点**:
- **单一用途限制**: 当前仅支持单一 `UsageFlags`(如纯模板附件)
- **共享条件**: 相同尺寸、格式、采样数和用途的附件可共享
- **未来扩展**: 注释指出需支持多用途附件的查找逻辑

**键结构** (5个 uint32_t):
```
[0]: 宽度
[1]: 高度
[2]: 格式键低32位
[3]: 格式键高32位
[4]: (protected << 0) | (memoryless << 1) | (usage << 2) | (sampleCnt << 10)
```

#### 临时键生成(Scratch Key)

```cpp
static void ComputeScratchKey(
    const GrCaps& caps,
    const GrBackendFormat& format,
    SkISize dimensions,
    UsageFlags requiredUsage,
    int sampleCnt,
    skgpu::Mipmapped mipmapped,
    GrProtected,
    GrMemoryless,
    skgpu::ScratchKey* key)
```

**功能**: 为短期使用的附件生成临时缓存键。

**与 UniqueKey 的区别**:
- **Scratch Key**: 任何匹配属性的附件都可复用
- **Unique Key**: 必须完全匹配特定资源

**缓存策略**:
- 模板附件使用唯一键共享
- 纹理附件不生成 Scratch Key(由 `GrTexture` 管理)
- MSAA 颜色附件使用 Scratch Key 临时分配

## 内部实现细节

### 构造函数

```cpp
GrAttachment(GrGpu* gpu,
             SkISize dimensions,
             UsageFlags supportedUsages,
             int sampleCnt,
             skgpu::Mipmapped mipmapped,
             GrProtected isProtected,
             std::string_view label,
             GrMemoryless memoryless = GrMemoryless::kNo)
```

**参数说明**:
- `gpu`: 拥有该附件的 GPU 设备
- `dimensions`: 附件尺寸
- `supportedUsages`: 支持的用途(可为多个标志的组合)
- `sampleCnt`: 采样数(1 表示非 MSAA)
- `mipmapped`: Mipmap 状态
- `isProtected`: 是否为受保护内存(DRM 内容)
- `label`: 调试标签
- `memoryless`: 是否为 Memoryless 附件(移动 GPU 优化)

### GPU 内存大小计算

```cpp
size_t GrAttachment::onGpuMemorySize() const
```

**实现逻辑**:
```cpp
if (!(fSupportedUsages & UsageFlags::kTexture) && fMemoryless == GrMemoryless::kNo) {
    GrBackendFormat format = this->backendFormat();
    SkTextureCompressionType compression = GrBackendFormatToCompressionType(format);

    uint64_t size = skgpu::NumCompressedBlocks(compression, this->dimensions());
    size *= GrBackendFormatBytesPerBlock(this->backendFormat());
    size *= this->numSamples();
    return size;
}
return 0;  // 纹理附件由 GrTexture 报告大小
```

**特殊处理**:
- **纹理附件**: 返回 0(避免与 `GrTexture` 重复计数)
- **Memoryless 附件**: 返回 0(无实际内存占用)
- **MSAA 附件**: 乘以采样数计算实际内存

**设计权衡**:
- **优点**: 避免资源大小重复统计
- **缺点**: 增加理解成本,需结合注释阅读

### Scratch Key 生成实现

```cpp
void GrAttachment::computeScratchKey(skgpu::ScratchKey* key) const
```

**排除条件**:
```cpp
if (!SkToBool(fSupportedUsages & UsageFlags::kStencilAttachment) &&
    !SkToBool(fSupportedUsages & UsageFlags::kTexture)) {
    // 仅为非模板、非纹理附件生成 Scratch Key
    ComputeScratchKey(*this->getGpu()->caps(), ...);
}
```

**理由**:
- **模板附件**: 通过唯一键共享,不使用 Scratch 机制
- **纹理附件**: 由 `GrTexture` 管理缓存,避免重复缓存导致内存泄漏

### 键构建辅助函数

```cpp
static void build_key(skgpu::ResourceKey::Builder* builder,
                      const GrCaps& caps,
                      const GrBackendFormat& format,
                      SkISize dimensions,
                      GrAttachment::UsageFlags requiredUsage,
                      int sampleCnt,
                      skgpu::Mipmapped mipmapped,
                      GrProtected isProtected,
                      GrMemoryless memoryless)
```

**功能**: UniqueKey 和 ScratchKey 共享的键构建逻辑。

**位打包优化**:
```cpp
(*builder)[4] = (static_cast<uint32_t>(isProtected) << 0) |
                (static_cast<uint32_t>(memoryless) << 1) |
                (static_cast<uint32_t>(requiredUsage) << 2) |
                (static_cast<uint32_t>(sampleCnt) << 10);
```

**容量限制断言**:
```cpp
SkASSERT(static_cast<uint32_t>(sampleCnt) < (1u << (32 - 10)));  // 最多 22 位
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖关系 | 用途说明 |
|---------|---------|---------|
| `GrSurface.h` | 继承 | 表面基类 |
| `GrBackendSurface.h` | 强依赖 | 后端格式定义 |
| `GrCaps.h` | 强依赖 | GPU 能力查询,格式键计算 |
| `GrBackendUtils.h` | 强依赖 | 格式查询工具 |
| `ResourceKey.h` | 强依赖 | 缓存键类型 |
| `DataUtils.h` | 强依赖 | 压缩块数量计算 |

### 被依赖的模块

| 模块名称 | 使用场景 |
|---------|---------|
| `GrRenderTarget` | 包含颜色/模板附件 |
| `GrTexture` | 内部持有 Attachment 实现 |
| `GrResourceCache` | 基于键查找和缓存附件 |
| `GrVkImage` | Vulkan 图像实现 |
| `GrMtlAttachment` | Metal 附件实现 |
| `GrGLAttachment` | OpenGL 附件实现 |

## 设计模式与设计决策

### 桥接模式 (Bridge Pattern)

将附件抽象与具体后端实现分离:
```
GrAttachment (抽象)
    ├── 公共接口
    └── 虚函数挂钩点
         ↓
后端实现 (GrVkImage, GrMtlAttachment, ...)
```

**优势**:
- 添加新后端无需修改公共接口
- 统一的资源管理逻辑

### 模板方法模式

`onGpuMemorySize()` 定义算法框架,子类可覆盖:
```cpp
final size_t gpuMemorySize() const {
    return this->onGpuMemorySize();  // 虚函数调用
}
```

### 策略模式 - 缓存键策略

不同类型的附件使用不同缓存策略:
- **共享模板附件**: Unique Key 策略
- **临时 MSAA 附件**: Scratch Key 策略
- **纹理附件**: 无独立缓存策略

### 延迟初始化(状态跟踪)

通过 `fHasPerformedInitialClear` 标志实现延迟清除:
```cpp
// 首次使用时才清除,避免无谓开销
if (!hasPerformedInitialClear()) { ... }
```

## 性能考量

### 内存对齐

键构建使用 32 位对齐:
```cpp
skgpu::UniqueKey::Builder builder(&key, kDomain, 5);  // 5 * 4 = 20 字节
```

**优势**:
- CPU 缓存行友好
- 哈希计算更快

### 缓存分离

模板附件和颜色附件使用不同缓存机制:
- **减少锁竞争**: 不同类型资源独立管理
- **提高命中率**: 避免不相关资源驱逐有用缓存

### Memoryless 优化

移动 GPU 支持的 Memoryless 附件:
```cpp
GrMemoryless fMemoryless;  // 标识附件无持久化内存
```

**效果**:
- **移动平台**: 节省带宽(TBDR 架构优化)
- **桌面平台**: 标志被忽略

### MSAA 内存计算

```cpp
size *= this->numSamples();  // 多重采样乘以采样数
```

**实例**: 1920x1080 RGBA8 4xMSAA:
- 基础大小: 1920 * 1080 * 4 = 8,294,400 字节
- 实际大小: 8,294,400 * 4 = 33,177,600 字节 (约 31.6 MB)

## 相关文件

| 文件路径 | 关系类型 | 说明 |
|---------|---------|------|
| `src/gpu/ganesh/GrSurface.h` | 基类 | 表面抽象基类 |
| `include/gpu/ganesh/GrBackendSurface.h` | 类型依赖 | 后端格式定义 |
| `src/gpu/ganesh/GrCaps.h` | 能力查询 | GPU 能力和格式键计算 |
| `src/gpu/ganesh/GrBackendUtils.h` | 工具依赖 | 格式查询函数 |
| `src/gpu/ResourceKey.h` | 键类型 | Unique/Scratch 键定义 |
| `src/gpu/ganesh/vk/GrVkImage.h` | 子类实现 | Vulkan 图像附件 |
| `src/gpu/ganesh/mtl/GrMtlAttachment.h` | 子类实现 | Metal 附件 |
| `src/gpu/ganesh/gl/GrGLAttachment.h` | 子类实现 | OpenGL 附件 |
| `src/gpu/ganesh/GrRenderTarget.h` | 使用者 | 渲染目标包含附件 |
| `src/gpu/ganesh/GrTexture.h` | 使用者 | 纹理包含附件实现 |
| `src/gpu/ganesh/GrResourceCache.h` | 缓存系统 | 基于键缓存附件 |
