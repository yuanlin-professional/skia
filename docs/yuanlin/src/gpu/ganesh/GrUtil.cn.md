# GrUtil

> 源文件: src/gpu/ganesh/GrUtil.h, src/gpu/ganesh/GrUtil.cpp

## 概述

`GrUtil` 是 Skia Ganesh GPU 后端的通用工具模块,提供一系列与平台无关的辅助函数和类型转换工具。主要功能包括 Intel GPU 系列识别、笔画渲染优化判断、GLSL 纹理类型映射,以及各种 Ganesh 类型的字符串转换。

该模块作为 Ganesh 后端的基础工具库,为上层提供硬件检测、性能优化决策和调试信息格式化等支持。其设计强调零依赖、内联优化和编译时计算。

## 架构位置

`GrUtil` 在 Ganesh 系统中的位置:

- **层级**: 基础工具层,被整个 Ganesh 后端广泛使用
- **依赖**: 依赖 Skia 核心类型和 GPU 类型定义
- **被依赖**: 几乎所有 Ganesh 模块都可能使用其工具函数

该模块是水平切分的基础设施,不参与渲染管线的执行,仅提供辅助能力。

## 主要类与结构体

### GrIntelGpuFamily 枚举

标识 Intel GPU 的架构代别。

```cpp
enum GrIntelGpuFamily {
    kUnknown_IntelGpuFamily,

    // 6th gen
    kSandyBridge_IntelGpuFamily,

    // 7th gen
    kIvyBridge_IntelGpuFamily,
    kValleyView_IntelGpuFamily,    // aka BayTrail
    kHaswell_IntelGpuFamily,

    // 8th gen
    kCherryView_IntelGpuFamily,    // aka Braswell
    kBroadwell_IntelGpuFamily,

    // 9th gen
    kApolloLake_IntelGpuFamily,
    kSkyLake_IntelGpuFamily,
    kGeminiLake_IntelGpuFamily,
    kKabyLake_IntelGpuFamily,
    kCoffeeLake_IntelGpuFamily,

    // 11th gen
    kIceLake_IntelGpuFamily,
};
```

**用途**: 用于硬件特定的优化和 Bug 绕过逻辑。

## 公共 API 函数

### GrGetIntelGpuFamily

```cpp
GrIntelGpuFamily GrGetIntelGpuFamily(uint32_t deviceID)
```

**功能**: 根据 PCI 设备 ID 识别 Intel GPU 架构。

**实现**: 通过掩码和位模式匹配识别 GPU 系列。

**算法**:
```cpp
uint32_t maskedID = deviceID & 0xFF00;
switch (maskedID) {
    case 0x0100: // Sandy Bridge / Ivy Bridge / Valley View
    case 0x0F00: // Valley View
    case 0x0400: case 0x0A00: case 0x0D00: // Haswell
    // ... 更多模式
}
```

**数据来源**: 基于维基百科的 Intel GPU 列表。

**特殊处理**: 0x0100 系列需要进一步细分:
```cpp
case 0x0100:
    switch (deviceID & 0xFFF0) {
        case 0x0150:
            if (deviceID == 0x0155 || deviceID == 0x0157) {
                return kValleyView_IntelGpuFamily;
            }
            // ...
    }
```

### GrIsStrokeHairlineOrEquivalent

```cpp
bool GrIsStrokeHairlineOrEquivalent(const GrStyle& style,
                                    const SkMatrix& matrix,
                                    SkScalar* outCoverage)
```

**功能**: 判断笔画是否可以视为细线(hairline)并用覆盖率表示。

**参数**:
- `style`: 绘制样式(包含笔画宽度)
- `matrix`: 变换矩阵
- `outCoverage`: 输出计算的覆盖率(可选)

**返回值**: `true` 表示可以用细线优化渲染。

**逻辑**:
1. 如果有路径效果,返回 `false`
2. 如果已经是细线样式,覆盖率为 1.0,返回 `true`
3. 如果是笔画样式,调用 `skcpu::DrawTreatAAStrokeAsHairline` 判断变换后是否等效于细线

**性能优势**: 细线渲染比常规笔画快很多,与 Raster 设备的优化一致。

### SkSLCombinedSamplerTypeForTextureType

```cpp
static inline SkSLType SkSLCombinedSamplerTypeForTextureType(GrTextureType type)
```

**功能**: 将 Ganesh 纹理类型映射到 GLSL 采样器类型。

**映射表**:

| GrTextureType | SkSLType |
|--------------|----------|
| `k2D` | `kTexture2DSampler` |
| `kRectangle` | `kTexture2DRectSampler` |
| `kExternal` | `kTextureExternalSampler` |

**错误处理**: 未知类型触发 `SK_ABORT`。

**内联优化**: 使用 `static inline` 在调用点展开,零开销。

### GrBackendApiToStr

```cpp
static constexpr const char* GrBackendApiToStr(GrBackendApi api)
```

**功能**: 将后端 API 枚举转换为字符串。

**映射**:
- `kOpenGL` → "OpenGL"
- `kVulkan` → "Vulkan"
- `kMetal` → "Metal"
- `kDirect3D` → "Direct3D"
- `kMock` → "Mock"
- `kUnsupported` → "Unsupported"

**constexpr**: 编译时计算,字符串字面量,无运行时开销。

### GrColorTypeToStr

```cpp
static constexpr const char* GrColorTypeToStr(GrColorType ct)
```

**功能**: 将颜色类型枚举转换为字符串。

**覆盖类型**: 支持 40+ 种颜色格式,包括:
- 标准格式: `kRGBA_8888`, `kBGRA_8888`
- 高精度: `kRGBA_F16`, `kRGBA_F32`
- 压缩格式: `kRGB_565`, `kABGR_4444`
- 特殊格式: `kAlpha_8`, `kGray_8`, `kRG_88`

**用途**: 调试日志和错误消息。

### GrSurfaceOriginToStr

```cpp
static constexpr const char* GrSurfaceOriginToStr(GrSurfaceOrigin origin)
```

**功能**: 转换表面原点枚举为字符串。

**映射**:
- `kTopLeft_GrSurfaceOrigin` → "kTopLeft"
- `kBottomLeft_GrSurfaceOrigin` → "kBottomLeft"

## 内部实现细节

### Intel GPU 识别的位掩码逻辑

**高 8 位识别主系列**:
```cpp
uint32_t maskedID = deviceID & 0xFF00;
```

大多数 GPU 系列通过高 8 位区分。

**细粒度识别**:
```cpp
switch (deviceID & 0xFFF0) {
    case 0x0100: case 0x0110: case 0x0120:
        return kSandyBridge_IntelGpuFamily;
}
```

部分系列需要检查高 12 位。

**特殊设备处理**:
```cpp
if (deviceID == 0x0155 || deviceID == 0x0157) {
    return kValleyView_IntelGpuFamily;
}
```

少数设备需要完整 ID 匹配。

### 笔画优化的判断逻辑

**快速路径**:
```cpp
if (stroke.isHairlineStyle()) {
    if (outCoverage) {
        *outCoverage = SK_Scalar1;
    }
    return true;
}
```

显式细线样式直接返回。

**等效判断**:
```cpp
return stroke.getStyle() == SkStrokeRec::kStroke_Style &&
       skcpu::DrawTreatAAStrokeAsHairline(stroke.getWidth(), matrix, outCoverage);
```

委托给 CPU 渲染器的判断逻辑,确保一致性。

### constexpr 字符串映射

所有 `*ToStr` 函数使用 `constexpr`:

**优点**:
1. 编译时计算,无运行时查表
2. 字符串字面量直接嵌入代码段
3. 优化器可内联整个函数

**示例**:
```cpp
GrBackendApiToStr(GrBackendApi::kVulkan)
// 编译后直接变成字符串字面量 "Vulkan"
```

### SkUNREACHABLE 宏

所有 switch 后使用 `SkUNREACHABLE`:

```cpp
switch (origin) {
    case kTopLeft_GrSurfaceOrigin:    return "kTopLeft";
    case kBottomLeft_GrSurfaceOrigin: return "kBottomLeft";
}
SkUNREACHABLE;
```

**作用**:
- 提示编译器所有 case 已覆盖
- 避免"missing return"警告
- 优化生成的代码

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkScalar`, `SkTypes` | Skia 核心类型定义 |
| `GrTypes`, `GrTypesPriv` | Ganesh GPU 类型定义 |
| `SkSLType` | 着色器语言类型枚举 |
| `GrStyle` | 绘制样式封装 |
| `SkMatrix` | 变换矩阵 |
| `SkStrokeRec` | 笔画记录 |
| `SkDrawProcs` | CPU 绘制辅助函数 |

### 被依赖的模块

该工具模块被广泛使用于:
- GPU 设备初始化(Intel GPU 检测)
- 路径渲染器(笔画优化判断)
- 着色器构建器(采样器类型映射)
- 调试日志(类型转换为字符串)
- 性能分析工具

## 设计模式与设计决策

### 函数式工具库

所有函数为纯函数或静态内联函数:
- 无状态
- 无副作用
- 可独立测试

### 编译时计算

大量使用 `constexpr` 和 `static inline`:

**优势**:
- 零运行时开销
- 编译器优化友好
- 类型安全

### 单一职责

每个函数只做一件明确的事:
- `GrGetIntelGpuFamily`: 只识别 GPU
- `GrIsStrokeHairlineOrEquivalent`: 只判断笔画
- `*ToStr`: 只做字符串转换

### 防御性编程

未知输入触发 `SK_ABORT`:

```cpp
default:
    SK_ABORT("Unexpected texture type");
```

**理由**: 工具函数的输入应在调用前验证,内部错误应立即暴露。

### 平台无关性

尽管函数名包含"Intel",但实现不依赖平台特定 API:
- 只使用标准 C++ 和 Skia 类型
- 可在任何平台编译和测试

## 性能考量

### 内联函数的零开销

```cpp
static inline SkSLType SkSLCombinedSamplerTypeForTextureType(...)
```

调用点展开为直接的枚举值赋值,无函数调用开销。

### constexpr 的编译时优化

```cpp
constexpr const char* str = GrBackendApiToStr(api);
```

编译器在编译期计算结果,运行时直接使用字面量。

### Switch 语句优化

现代编译器将 switch 优化为跳转表或位测试:
- Intel GPU 识别: O(1) 跳转表
- 字符串转换: 编译时消除

### 缓存友好的数据结构

函数不分配堆内存,不破坏缓存:
- 返回栈上的值或字符串字面量
- 无动态内存操作

### 早期返回

```cpp
if (style.pathEffect()) {
    return false;  // 快速路径
}
```

最常见的情况优先处理,减少分支预测失败。

### 位运算的高效性

Intel GPU 识别使用位掩码:

```cpp
uint32_t maskedID = deviceID & 0xFF00;  // 单条指令
```

比字符串解析或复杂逻辑快数百倍。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/ganesh/GrTypes.h` | 公共 GPU 类型定义 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 私有 GPU 类型 |
| `src/core/SkSLTypeShared.h` | 着色器类型枚举 |
| `src/gpu/ganesh/GrStyle.h` | 绘制样式类 |
| `include/core/SkMatrix.h` | 变换矩阵 |
| `include/core/SkStrokeRec.h` | 笔画记录 |
| `src/core/SkDrawProcs.h` | CPU 绘制辅助函数 |
| `include/core/SkScalar.h` | 标量类型定义 |
