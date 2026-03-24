# GrMtlCaps

> 源文件
> - src/gpu/ganesh/mtl/GrMtlCaps.h
> - src/gpu/ganesh/mtl/GrMtlCaps.mm

## 概述

`GrMtlCaps` 是 Skia 图形库中 Metal 后端的能力查询和特性管理类,继承自 `GrCaps` 基类。该类负责检测 Metal 设备的硬件能力、支持的像素格式、采样级别、纹理特性等,并根据设备类型(Mac、Apple Silicon、Intel)和系统版本进行能力初始化。它是 Metal 后端适配不同硬件和系统的核心组件。

## 架构位置

`GrMtlCaps` 位于 Skia 的 GPU Ganesh 渲染架构中的 Metal 后端能力层,是连接硬件抽象层和上层渲染逻辑的桥梁。

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrCaps              (抽象能力基类)
    ├── GrContext           (渲染上下文)
    └── mtl/
        ├── GrMtlGpu        (Metal GPU实例)
        ├── GrMtlCaps       (Metal能力查询) ← 当前类
        └── GrMtlDevice     (Metal设备管理)
```

## 主要类与结构体

### GrMtlCaps

Metal 设备能力查询类,提供格式支持、渲染能力、采样级别等信息。

**继承关系:**
- 基类: `GrCaps`
- 派生类: 无(终端类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGPUFamily` | `GPUFamily` | GPU 家族类型(Mac/Apple/MacIntel) |
| `fFamilyGroup` | `int` | GPU 家族代数(1-7) |
| `fFormatTable` | `FormatInfo[kNumMtlFormats]` | 支持的像素格式表 |
| `fColorTypeToFormatTable` | `MTLPixelFormat[kGrColorTypeCnt]` | 颜色类型到 Metal 格式映射 |
| `fSampleCounts` | `SkTDArray<int>` | 支持的多重采样级别 |
| `fPreferredStencilFormat` | `MTLPixelFormat` | 首选模板缓冲格式 |
| `fStoreAndMultisampleResolveSupport` | `bool` | 是否支持存储并多重采样解析 |

### FormatInfo

像素格式能力信息结构体。

**关键成员:**

| 成员 | 类型 | 说明 |
|-----|------|------|
| `fFlags` | `uint16_t` | 格式标志(可纹理/可渲染/MSAA/解析) |
| `fColorTypeInfos` | `unique_ptr<ColorTypeInfo[]>` | 支持的颜色类型数组 |
| `fColorTypeInfoCount` | `int` | 颜色类型数量 |

### ColorTypeInfo

颜色类型配置信息。

| 成员 | 类型 | 说明 |
|-----|------|------|
| `fColorType` | `GrColorType` | Skia 颜色类型 |
| `fFlags` | `uint32_t` | 支持标志(上传/渲染) |
| `fReadSwizzle` | `skgpu::Swizzle` | 读取混洗模式 |
| `fWriteSwizzle` | `skgpu::Swizzle` | 写入混洗模式 |

## 公共 API 函数

### 初始化与构造

```cpp
GrMtlCaps(const GrContextOptions& contextOptions,
          id<MTLDevice> device);
```
构造函数,根据 Metal 设备初始化所有能力信息。

### 格式查询方法

| 方法 | 说明 |
|-----|------|
| `isFormatSRGB(const GrBackendFormat&)` | 检查格式是否为 sRGB |
| `isFormatTexturable(const GrBackendFormat&, GrTextureType)` | 检查格式是否支持纹理采样 |
| `isFormatRenderable(const GrBackendFormat&, int sampleCount)` | 检查格式是否可渲染 |
| `isFormatCopyable(const GrBackendFormat&)` | 检查格式是否可复制 |

### 采样级别查询

```cpp
int getRenderTargetSampleCount(int requestedCount,
                               const GrBackendFormat&) const;
int maxRenderTargetSampleCount(const GrBackendFormat&) const;
```
查询支持的最大采样数和满足请求的实际采样数。

### 复制能力查询

```cpp
bool canCopyAsBlit(MTLPixelFormat dstFormat, int dstSampleCount,
                   MTLPixelFormat srcFormat, int srcSampleCount,
                   const SkIRect& srcRect, const SkIPoint& dstPoint,
                   bool areDstSrcSameObj) const;

bool canCopyAsResolve(MTLPixelFormat dstFormat, int dstSampleCount,
                      MTLPixelFormat srcFormat, int srcSampleCount,
                      bool srcIsRenderTarget, const SkISize srcDimensions,
                      const SkIRect& srcRect, const SkIPoint& dstPoint,
                      bool areDstSrcSameObj) const;
```
检查是否可以通过 Blit 或 Resolve 操作进行表面复制。

### 设备类型判断

| 方法 | 说明 |
|-----|------|
| `isMac()` | 是否为 Mac 设备(包含 Intel Mac) |
| `isApple()` | 是否为 Apple Silicon |
| `isIntel()` | 是否为 Intel GPU |

## 内部实现细节

### GPU 家族检测流程

1. **首选新 API:** 使用 `MTLGPUFamily` 枚举(macOS 10.15+)
2. **降级旧 API:** 旧系统使用 `MTLFeatureSet` 接口
3. **代数识别:** 从高到低依次检测 Family 7/6/.../1
4. **Intel 特判:** 通过设备名称字符串识别 Intel GPU

```cpp
bool GrMtlCaps::getGPUFamily(id<MTLDevice> device,
                             GPUFamily* gpuFamily,
                             int* group) {
    if (@available(macOS 10.15, iOS 13.0, *)) {
        // 检测 Apple7/6/5...
        if ([device supportsFamily:MTLGPUFamilyApple7]) {
            *gpuFamily = GPUFamily::kApple;
            *group = 7;
            return true;
        }
        // Mac 设备特殊处理
        bool isIntel = [device.name containsString:@"Intel"];
        if ([device supportsFamily:MTLGPUFamilyMac2]) {
            *gpuFamily = isIntel ? GPUFamily::kMacIntel : GPUFamily::kMac;
            *group = 2;
            return true;
        }
    }
    // 降级到 FeatureSet API...
}
```

### 格式表初始化

`initFormatTable()` 方法为 18-19 种 Metal 像素格式建立详细的能力映射:

**支持的格式:**
- **8位格式:** R8Unorm, A8Unorm, RG8Unorm, RGBA8Unorm
- **16位格式:** R16Float, R16Unorm, RG16Float, RG16Unorm, RGBA16Float, RGBA16Unorm
- **特殊格式:** B5G6R5Unorm, ABGR4Unorm, RGB10A2Unorm, BGR10A2Unorm
- **sRGB:** RGBA8Unorm_sRGB
- **压缩:** ETC2_RGB8(iOS), BC1_RGBA(Mac)

**格式标志:**
- `kTexturable_Flag` (0x1): 可用于纹理采样
- `kRenderable_Flag` (0x2): 可用作渲染目标
- `kMSAA_Flag` (0x4): 支持多重采样
- `kResolve_Flag` (0x8): 支持 MSAA 解析

### 颜色类型映射

为 Skia 的抽象颜色类型(`GrColorType`)建立到 Metal 像素格式的优先级映射:

```cpp
this->setColorType(GrColorType::kRGBA_8888,
                   { MTLPixelFormatRGBA8Unorm });
this->setColorType(GrColorType::kAlpha_8,
                   { MTLPixelFormatR8Unorm, MTLPixelFormatA8Unorm });
```

### 驱动兼容性处理

`applyDriverCorrectnessWorkarounds()` 方法当前为空,预留用于处理特定驱动 Bug 的修正。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrCaps` | 基类,提供跨后端能力接口 |
| `GrShaderCaps` | 着色器能力管理 |
| `GrProgramDesc` | 程序描述符生成 |
| `Metal/Metal.h` | Metal API 访问 |
| `SkCompressedDataUtils` | 压缩纹理工具 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMtlGpu` | 持有 GrMtlCaps 实例,查询设备能力 |
| `GrMtlRenderTarget` | 查询采样级别和格式支持 |
| `GrMtlTexture` | 检查纹理格式是否可用 |
| `GrMtlCommandBuffer` | 根据能力选择最优命令编码方式 |

## 设计模式与设计决策

### 能力查询缓存模式
在对象构造时一次性检测所有能力并缓存,避免运行时重复查询,以空间换时间。

### 版本兼容策略
通过三级降级机制支持广泛的系统版本:
1. **首选:** MTLGPUFamily API (macOS 10.15+)
2. **降级:** MTLFeatureSet API (macOS 10.11+)
3. **默认:** 假设最低能力级别

### 格式能力表设计
使用结构化数据表(`fFormatTable`)而非动态查询,优点:
- 快速查找(数组索引访问)
- 编译时可验证完整性
- 支持条件编译(iOS/Mac 差异)

### 设备类型枚举
定义 `GPUFamily` 枚举区分 Apple/Mac/MacIntel,便于实施平台特定优化:
- **Apple Silicon:** 支持 tile-based rendering 优化
- **Intel Mac:** 避免向量运算 Bug(禁用 `fVectorClampMinMaxSupport`)
- **Mac Pro(AMD):** 启用全部特性

## 性能考量

### 初始化开销
构造函数执行大量系统查询,但仅在 GPU 上下文创建时调用一次,摊销成本可忽略。

### 查询优化
- **格式查询:** O(1) 数组索引查找
- **采样级别:** 预排序数组,二分查找复杂度 O(log n)
- **能力判断:** 位标志位运算,常数时间

### 内存占用
- 格式表: ~18 * sizeof(FormatInfo) ≈ 2KB
- 颜色映射表: kGrColorTypeCnt * sizeof(MTLPixelFormat) ≈ 200字节
- 总计: 约 2-3KB,对于能力类可接受

### 平台特定优化开关
```cpp
// Apple Silicon 优化
fStoreAndMultisampleResolveSupport =
    (fGPUFamily == GPUFamily::kApple && fFamilyGroup >= 3);
fPreferDiscardableMSAAAttachment =
    (fGPUFamily == GPUFamily::kApple);
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrCaps.h` | 基类 | 平台无关能力抽象 |
| `src/gpu/ganesh/GrShaderCaps.h` | 组合 | 着色器能力子系统 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h` | 使用者 | GPU 类持有 Caps 实例 |
| `src/gpu/ganesh/mtl/GrMtlUtil.h` | 工具 | 格式转换辅助函数 |
| `src/gpu/ganesh/mtl/GrMtlRenderTarget.h` | 依赖方 | 查询 MSAA 支持 |
| `src/gpu/ganesh/GrProgramDesc.h` | 协作 | 使用 Caps 生成程序描述符 |
