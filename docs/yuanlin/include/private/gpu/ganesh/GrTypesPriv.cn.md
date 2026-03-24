# GrTypesPriv

> 源文件: `include/private/gpu/ganesh/GrTypesPriv.h`

## 概述
GrTypesPriv 是 Skia Ganesh GPU 后端的核心类型定义文件,包含 958 行代码,定义了图形管线的基本类型、枚举和工具函数。它涵盖了几何图元、颜色类型、顶点属性、GPU 缓冲区、资源管理、抗锯齿等各个方面的类型定义,是 Ganesh 后端类型系统的基础。

## 架构位置
该文件位于 Skia GPU 后端 Ganesh 子系统的最底层,是私有类型定义层。它为整个 Ganesh 架构提供类型基础,被几乎所有 GPU 相关模块依赖。它是 Skia 公共 API(GrTypes.h)的私有扩展,包含了内部实现所需的额外类型。

## 核心类型分类

### 几何图元类型

#### GrPrimitiveType
定义了 GPU 支持的几何图元类型:
```cpp
enum class GrPrimitiveType : uint8_t {
    kTriangles,      // 三角形列表
    kTriangleStrip,  // 三角形带
    kPoints,         // 点
    kLines,          // 线段(1像素宽)
    kLineStrip,      // 线带(1像素宽)
};
```

**辅助函数**:
- `GrIsPrimTypeLines(type)`: 判断是否为线类型图元
- `GrPrimitiveRestart`: 是否启用图元重启(用于优化索引绘制)

### 颜色类型系统

#### GrColorType
定义了 GPU 内部使用的颜色类型,比 SkColorType 更底层:
- 包含 43 种颜色类型,从 kAlpha_8 到 kARGB_4444
- 支持标准格式(RGBA_8888)、高精度格式(RGBA_F32)、压缩格式等
- 区分 sRGB 和线性空间(RGBA_8888 vs RGBA_8888_SRGB)

**关键转换函数**:
```cpp
static constexpr SkColorType GrColorTypeToSkColorType(GrColorType ct);
static constexpr GrColorType SkColorTypeToGrColorType(SkColorType ct);
```

#### GrColorFormatDesc
描述颜色格式的位深度和编码方式:
```cpp
class GrColorFormatDesc {
    int r(), g(), b(), a();      // 各通道位数
    int gray();                   // 灰度通道位数
    GrColorTypeEncoding encoding(); // 编码类型(Unorm/sRGB/Float)
};
```

**工厂方法**:
- `MakeRGBA(int rgba, GrColorTypeEncoding)`: 创建 RGBA 格式描述
- `MakeAlpha(int a, GrColorTypeEncoding)`: 创建 Alpha 格式描述
- `MakeGray(int grayBits, GrColorTypeEncoding)`: 创建灰度格式描述

#### GrColorTypeEncoding
颜色通道的编码方式:
```cpp
enum class GrColorTypeEncoding {
    kUnorm,      // 无符号归一化 [0, 1]
    kSRGBUnorm,  // sRGB 编码的归一化
    kFloat,      // 浮点数
};
```

### 顶点属性类型

#### GrVertexAttribType
定义了顶点属性的数据类型(26 种):
```cpp
enum GrVertexAttribType {
    kFloat_GrVertexAttribType,      // 单个 float
    kFloat2_GrVertexAttribType,     // 2D float 向量
    kFloat4_GrVertexAttribType,     // 4D float 向量
    kHalf_GrVertexAttribType,       // 半精度浮点
    kInt2_GrVertexAttribType,       // 2D int 向量
    kByte4_GrVertexAttribType,      // 4 个有符号字节
    kUByte4_norm_GrVertexAttribType, // 4 个归一化无符号字节
    // ... 等 26 种类型
};
```

### GPU 缓冲区类型

#### GrGpuBufferType
GPU 缓冲区的用途分类:
```cpp
enum class GrGpuBufferType {
    kVertex,        // 顶点缓冲区
    kIndex,         // 索引缓冲区
    kDrawIndirect,  // 间接绘制缓冲区
    kXferCpuToGpu,  // CPU 到 GPU 传输缓冲区
    kXferGpuToCpu,  // GPU 到 CPU 传输缓冲区
    kUniform,       // Uniform 缓冲区
};
```

#### GrAccessPattern
缓冲区访问模式提示:
```cpp
enum GrAccessPattern {
    kDynamic_GrAccessPattern,  // 频繁重写,频繁使用
    kStatic_GrAccessPattern,   // 一次写入,多次使用
    kStream_GrAccessPattern,   // 一次写入,少次使用
};
```

### 资源管理类型

#### GrBudgetedType
资源的预算管理策略:
```cpp
enum class GrBudgetedType : uint8_t {
    kBudgeted,                // 受预算约束,可被清除
    kUnbudgetedUncacheable,   // 不受预算约束,无引用立即清除
    kUnbudgetedCacheable,     // 不受预算约束,但有唯一键时可缓存
};
```

#### GrWrapOwnership
外部资源导入时的所有权规则:
```cpp
enum GrWrapOwnership {
    kBorrow_GrWrapOwnership,  // 借用,Skia 不释放
    kAdopt_GrWrapOwnership,   // 采纳,Skia 负责释放
};
```

#### GrWrapCacheable
包装资源的缓存策略:
```cpp
enum class GrWrapCacheable : bool {
    kNo = false,   // 无引用时立即从缓存移除
    kYes = true,   // 允许在有唯一键时保留在缓存中
};
```

### 渲染管线类型

#### GrLoadOp / GrStoreOp
渲染通道的加载/存储操作:
```cpp
enum class GrLoadOp {
    kLoad,     // 加载现有内容
    kClear,    // 清除为指定颜色
    kDiscard,  // 丢弃旧内容(性能优化)
};

enum class GrStoreOp {
    kStore,    // 保存渲染结果
    kDiscard,  // 丢弃渲染结果(临时缓冲区优化)
};
```

#### GrAAType
抗锯齿类型:
```cpp
enum class GrAAType : unsigned {
    kNone,      // 无抗锯齿
    kCoverage,  // 基于覆盖率的片段着色器抗锯齿
    kMSAA,      // 多重采样抗锯齿(硬件)
};
```

**辅助函数**:
- `GrAATypeIsHW(type)`: 判断是否为硬件抗锯齿

#### GrQuadAAFlags
矩形/四边形的边缘抗锯齿标志:
```cpp
enum class GrQuadAAFlags {
    kLeft   = 0b0001,
    kTop    = 0b0010,
    kRight  = 0b0100,
    kBottom = 0b1000,
    kNone   = 0b0000,
    kAll    = 0b1111,
};
```

用于平铺渲染时实现无缝边界(内边缘不抗锯齿,外边缘抗锯齿)。

### 纹理和表面类型

#### GrTextureType
纹理类型枚举:
```cpp
enum class GrTextureType {
    kNone,       // 无效类型
    k2D,         // 标准 2D 纹理
    kRectangle,  // 矩形纹理(非归一化坐标)
    kExternal,   // 外部纹理(如 Android 的 OES 纹理)
};
```

**限制检查**:
- `GrTextureTypeHasRestrictedSampling(type)`: Rectangle 和 External 纹理不支持 MIP map 和高级采样模式

#### GrInternalSurfaceFlags
表面的内部标志位:
```cpp
enum class GrInternalSurfaceFlags {
    kReadOnly = 1 << 0,                  // 纹理只读
    kGLRTFBOIDIs0 = 1 << 1,              // OpenGL 默认帧缓冲
    kRequiresManualMSAAResolve = 1 << 2, // 需要手动 MSAA 解析
    kFramebufferOnly = 1 << 3,           // 仅帧缓冲(Dawn/Metal)
    kVkRTSupportsInputAttachment = 1 << 4, // Vulkan 输入附件支持
};
```

### 其他重要类型

#### GrClipEdgeType
裁剪边缘类型:
```cpp
enum class GrClipEdgeType {
    kFillBW,         // 填充,无抗锯齿
    kFillAA,         // 填充,抗锯齿
    kInverseFillBW,  // 反向填充,无抗锯齿
    kInverseFillAA,  // 反向填充,抗锯齿
};
```

#### GrMipLevel
单个 Mipmap 层级的数据描述:
```cpp
struct GrMipLevel {
    const void* fPixels = nullptr;       // 像素数据指针
    size_t fRowBytes = 0;                // 行字节数
    sk_sp<SkData> fOptionalStorage;      // 可选的数据持有者
};
```

#### GrDstSampleFlags
目标采样标志:
```cpp
enum class GrDstSampleFlags {
    kNone = 0,
    kRequiresTextureBarrier = 1 << 0,  // 需要纹理屏障
    kAsInputAttachment = 1 << 1,       // 作为输入附件
};
```

## 工具函数

### 几何计算
```cpp
static inline constexpr size_t GrSizeDivRoundUp(size_t x, size_t y);
```
向上取整除法,常用于计算块数。

### 填充规则转换
```cpp
inline GrFillRule GrFillRuleForPathFillType(SkPathFillType fillType);
inline GrFillRule GrFillRuleForSkPath(const SkPath& path);
```
将 Skia 路径填充类型转换为 Gr 填充规则。

### 颜色类型查询
```cpp
static constexpr uint32_t GrColorTypeChannelFlags(GrColorType ct);
static constexpr bool GrColorTypeIsAlphaOnly(GrColorType ct);
static constexpr bool GrColorTypeHasAlpha(GrColorType ct);
static constexpr size_t GrColorTypeBytesPerPixel(GrColorType ct);
static constexpr bool GrColorTypeIsWiderThan(GrColorType colorType, int n);
```

### 钳位类型查询
```cpp
static constexpr GrClampType GrColorTypeClampType(GrColorType colorType);
```
确定颜色类型的钳位行为(自动/手动/无)。

### 格式描述
```cpp
static constexpr GrColorFormatDesc GrGetColorTypeDesc(GrColorType ct);
```
获取颜色类型的详细格式描述。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkColor | 颜色定义 |
| SkColorType | Skia 颜色类型 |
| SkPath | 路径填充规则转换 |
| SkRefCnt | 引用计数基础 |
| SkData | 数据持有者 |
| SkAssert | 断言宏 |
| SkDebug | 调试输出 |
| SkMacros | 宏定义 |
| SkTypeTraits | 类型特征 |

### 被依赖的模块
几乎所有 Ganesh GPU 后端模块:
- GrOpsRenderPass: 使用渲染管线类型
- GrTexture/GrRenderTarget: 使用表面和纹理类型
- GrResourceCache: 使用资源管理类型
- GrPipeline: 使用颜色类型和抗锯齿类型
- GrGeometryProcessor: 使用顶点属性类型
- GrGpu: 使用 GPU 缓冲区类型
- 所有 GPU 后端实现(GL/Vulkan/Metal/D3D)

## 设计模式与设计决策

### 强类型枚举
大量使用 `enum class` 而非传统 C 枚举:
- 类型安全,防止隐式转换
- 避免命名空间污染
- 明确类型意图

### 编译期计算
所有查询函数都声明为 `constexpr`:
- 编译期求值,零运行时开销
- 支持在常量表达式中使用
- 优化器可以完全消除函数调用

### 位域标志
使用 `SK_MAKE_BITFIELD_CLASS_OPS` 为标志枚举生成位运算符:
```cpp
SK_MAKE_BITFIELD_CLASS_OPS(GrQuadAAFlags)
SK_MAKE_BITFIELD_CLASS_OPS(GrInternalSurfaceFlags)
```

### 双向映射
提供 GrColorType ↔ SkColorType 的双向转换:
- 保持公共 API 和内部实现的解耦
- 允许内部使用更丰富的类型系统

### 统一抽象
GrColorType 统一了跨平台的颜色格式:
- 不同后端的纹理格式映射到统一的 GrColorType
- 上层代码不需要关心平台差异

## 性能考量

### 内联和 constexpr
所有小函数都声明为 `inline` 和/或 `constexpr`:
- 消除函数调用开销
- 编译期计算,零运行时成本
- 优化器可以进行常量折叠

### 紧凑的数据类型
枚举使用最小的底层类型:
```cpp
enum class GrPrimitiveType : uint8_t { ... }
enum class GrBudgetedType : uint8_t { ... }
```
减少内存占用和缓存压力。

### 访问模式提示
GrAccessPattern 帮助驱动程序优化缓冲区放置:
- kStatic 可能放在 GPU 专用内存
- kDynamic 可能放在共享内存
- kStream 可能使用流式缓冲区

### Mipmap 优化
GrMipLevel 使用可选的 sk_sp<SkData> 持有数据:
- 避免不必要的数据复制
- 共享内存所有权
- 自动生命周期管理

### 可重定位类型
GrMipLevel 标记为 trivially relocatable:
```cpp
using sk_is_trivially_relocatable = std::true_type;
```
允许容器进行高效的内存重排。

## 类型覆盖范围

### 颜色类型 (43 种)
- 标准格式: Alpha_8, RGBA_8888, BGRA_8888
- 压缩格式: BGR_565, ABGR_4444
- 高精度: RGBA_F16, RGBA_F32
- 特殊用途: Alpha_8xxx(读回类型), RGB_888(初始化用)
- 10-bit: RGBA_1010102, RGB_101010x

### 顶点属性 (26 种)
- Float: Float, Float2, Float3, Float4
- Half: Half, Half2, Half4
- Int: Int, Int2, Int3, Int4
- Byte: Byte, Byte2, Byte4, UByte, UByte2, UByte4
- Normalized: UByte_norm, UByte4_norm, UShort2_norm, UShort4_norm
- Short: Short2, Short4, UShort2

### GPU 缓冲区 (6 种)
Vertex, Index, DrawIndirect, XferCpuToGpu, XferGpuToCpu, Uniform

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/GrTypes.h | 公共类型定义,本文件的扩展 |
| include/core/SkColorType.h | Skia 颜色类型,与 GrColorType 映射 |
| include/core/SkPath.h | 路径填充规则转换的依赖 |
| src/gpu/ganesh/GrCaps.h | 使用这些类型查询能力 |
| src/gpu/ganesh/GrResourceCache.h | 使用资源管理类型 |
| src/gpu/ganesh/GrOpsRenderPass.h | 使用渲染管线类型 |
| src/gpu/ganesh/GrGeometryProcessor.h | 使用顶点属性类型 |
| src/gpu/ganesh/glsl/GrGLSLShaderBuilder.h | 使用着色器类型 |
| src/gpu/ganesh/*/Gr*Gpu.h | 各后端使用这些类型 |
