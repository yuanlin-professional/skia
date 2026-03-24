# DitherUtils

> 源文件: src/gpu/DitherUtils.h, src/gpu/DitherUtils.cpp

## 概述

`DitherUtils` 是 Skia GPU 渲染中的抖动(dithering)工具模块,用于减少因位深度不足导致的色带效应(color banding)。该模块提供了两个核心功能:计算特定颜色格式的抖动范围,以及生成用于着色器的抖动查找表(LUT)。

抖动技术通过在相邻像素间引入受控的噪声,使人眼感知到更平滑的颜色渐变,是低位深渲染目标(如 RGB565、RGBA4444)和高动态范围内容向低动态范围转换的关键技术。该模块的设计遵循 Skia CPU 后端的抖动算法,确保 GPU 和 CPU 路径的视觉一致性。

## 架构位置

在 Skia 架构中,`DitherUtils` 位于以下位置:

- **条件编译**: 在 `SK_IGNORE_GPU_DITHER` 未定义时启用
- **上游依赖**: 依赖 `SkColorType` 定义的颜色格式
- **下游使用**: 被 GPU 着色器生成模块使用
- **应用场景**: 低位深目标渲染、梯度绘制、HDR 到 LDR 转换

该模块是跨平台的,不依赖特定的 GPU API,提供通用的抖动支持。

## 主要类与结构体

本模块主要提供静态工具函数,内部定义了以下结构体:

### DitherTable (内部)
```cpp
static constexpr struct DitherTable {
    constexpr DitherTable() : data() {
        // 编译时初始化8×8抖动矩阵
    }
    uint8_t data[64];
} gTable;
```
**设计**: `constexpr` 构造函数在编译时生成 8×8 抖动模式。
**存储**: 64 字节的静态常量表。

## 公共 API 函数

### DitherRangeForConfig
```cpp
float DitherRangeForConfig(SkColorType dstColorType)
```
**功能**: 计算指定颜色格式的抖动范围。

**参数**: `dstColorType` - 目标颜色格式。

**返回值**: 抖动范围浮点数,表示最小可感知的颜色差异。

**计算公式**: `1 / (2^bitdepth - 1)`

**支持的格式与返回值**:

| 颜色格式 | 位深 | 抖动范围 | 说明 |
|---------|------|---------|------|
| `kARGB_4444_SkColorType` | 4 bit | `1/15.0` | 每通道4位 |
| `kRGB_565_SkColorType` | 6 bit | `1/63.0` | 绿色通道6位 |
| `kAlpha_8_SkColorType` | 8 bit | `1/255.0` | Alpha 8位 |
| `kGray_8_SkColorType` | 8 bit | `1/255.0` | 灰度 8位 |
| `kR8_unorm_SkColorType` | 8 bit | `1/255.0` | 单通道红色 |
| `kR8G8_unorm_SkColorType` | 8 bit | `1/255.0` | 双通道 |
| `kRGB_888x_SkColorType` | 8 bit | `1/255.0` | RGB各8位 |
| `kRGBA_8888_SkColorType` | 8 bit | `1/255.0` | RGBA各8位 |
| `kSRGBA_8888_SkColorType` | 8 bit | `1/255.0` | sRGB RGBA |
| `kBGRA_8888_SkColorType` | 8 bit | `1/255.0` | BGRA各8位 |
| `kRGBA_1010102_SkColorType` | 10 bit | `1/1023.0` | RGB各10位 |
| `kBGRA_1010102_SkColorType` | 10 bit | `1/1023.0` | BGR各10位 |
| `kRGB_101010x_SkColorType` | 10 bit | `1/1023.0` | RGB各10位 |
| `kBGR_101010x_SkColorType` | 10 bit | `1/1023.0` | BGR各10位 |
| `kBGR_101010x_XR_SkColorType` | 10 bit | `1/1023.0` | 扩展范围 |
| `kBGRA_10101010_XR_SkColorType` | 10 bit | `1/1023.0` | 扩展范围 |
| `kRGBA_10x6_SkColorType` | 10 bit | `1/1023.0` | 10位打包格式 |
| `kA16_unorm_SkColorType` | 16 bit | `1/32767.0` | 16位 Alpha |
| `kR16_unorm_SkColorType` | 16 bit | `1/32767.0` | 16位红色 |
| `kR16G16_unorm_SkColorType` | 16 bit | `1/32767.0` | 双通道16位 |
| `kR16G16B16A16_unorm_SkColorType` | 16 bit | `1/32767.0` | RGBA各16位 |
| 浮点格式 | N/A | `0.0` | 无需抖动 |

**特殊处理**:
- **半精度浮点** (`kRGBA_F16_SkColorType` 等): 返回 0,无需抖动
- **单精度浮点** (`kRGBA_F32_SkColorType`): 返回 0,无需抖动
- **未知格式**: 触发 `SkUNREACHABLE`

### MakeDitherLUT
```cpp
SkBitmap MakeDitherLUT()
```
**功能**: 创建 8×8 的抖动查找表位图。

**返回值**: 包含抖动模式的 `SkBitmap`,格式为 A8,尺寸为 8×8。

**生成算法**: 与 Skia CPU 后端一致的 Bayer 矩阵变体。

**用途**: 上传到 GPU 作为纹理,在片段着色器中采样以获取抖动值。

## 内部实现细节

### 抖动矩阵生成

#### 计算公式
```cpp
unsigned int m = (y & 1) << 5 | (x & 1) << 4 |
                 (y & 2) << 2 | (x & 2) << 1 |
                 (y & 4) >> 1 | (x & 4) >> 2;
float value = static_cast<float>(m) * (1.0f / 64.0f) - (63.0f / 128.0f);
uint8_t byte = (uint8_t)((value + 0.5f) * 255.f + 0.5f);
```

**步骤解析**:
1. **位交错**: 将 X 和 Y 坐标的位交错排列,生成 0-63 的索引 `m`
2. **归一化**: `m / 64.0` 映射到 [0, 1)
3. **中心化**: 减去 `63/128` 得到 [-0.4921875, 0.4921875]
4. **偏移**: 加 0.5 映射到 [0, 1]
5. **量化**: 乘 255 并四舍五入转换为 uint8_t

**结果**: 生成的 8×8 矩阵是无序的(非单调),提供良好的视觉效果。

### 编译时初始化
`DitherTable` 使用 `constexpr` 构造函数,所有计算在编译时完成:
- 无运行时初始化开销
- 存储在只读数据段
- 线程安全(无需同步)

### 位图创建
```cpp
SkBitmap bmp;
bmp.installPixels(SkImageInfo::MakeA8(8, 8), const_cast<uint8_t*>(gTable.data), 8);
bmp.setImmutable();
```
**特点**:
- 使用 `installPixels` 避免内存拷贝
- 设置为不可变以启用共享和缓存优化
- 行字节数为 8(无填充)

### 着色器集成
抖动表的使用流程:
1. CPU 调用 `MakeDitherLUT()` 获取位图
2. 上传位图到 GPU 纹理(通常在初始化时一次性完成)
3. 着色器使用片段坐标 `frag_coord.xy % 8` 采样纹理
4. 将采样值缩放到 `[-ditherRange, +ditherRange]`
5. 加到最终颜色上再量化

### 条件编译
整个模块包裹在 `#ifndef SK_IGNORE_GPU_DITHER` 中,允许在特定平台禁用抖动:
- 节省纹理资源
- 减少着色器复杂度
- 适用于高位深目标或性能受限场景

## 依赖关系

### 依赖的模块

| 模块 | 依赖内容 | 用途 |
|------|----------|------|
| `include/core/SkColorType.h` | `SkColorType` 枚举 | 颜色格式定义 |
| `include/core/SkBitmap.h` | `SkBitmap` | 位图存储 |
| `include/core/SkImageInfo.h` | `SkImageInfo` | 图像信息 |

### 被依赖的模块

| 模块 | 使用内容 | 用途 |
|------|----------|------|
| Ganesh 着色器生成 | `DitherRangeForConfig` | 着色器代码生成 |
| Graphite 管线构建 | `MakeDitherLUT` | 纹理资源创建 |
| GPU 效果处理器 | 抖动范围 | 梯度渲染 |
| 单元测试 | 所有函数 | 抖动算法验证 |

## 设计模式与设计决策

### 1. 编译时计算模式
抖动表在编译时生成,是典型的 `constexpr` 优化应用,消除了运行时初始化开销。

### 2. 单例模式变体
`gTable` 是隐式的单例,通过静态常量实现,无需显式的单例管理代码。

### 3. 不可变对象模式
返回的 `SkBitmap` 设置为不可变,支持安全的多线程共享和内部缓存。

### 4. 空对象模式
浮点格式返回 0.0,避免了调用者的特殊处理逻辑:
```cpp
if (ditherRange > 0) {
    // 应用抖动
}
```

### 5. 策略模式
不同颜色格式使用统一的接口但不同的抖动范围,是策略模式的简单应用。

### 6. 与 CPU 后端一致性
抖动算法与 `SkDraw.cpp` 中的 CPU 实现保持一致,确保跨平台的视觉一致性。

## 性能考量

### 1. 零运行时开销
- 抖动表编译时生成
- 无动态内存分配
- 无初始化逻辑

### 2. 内存占用
- 抖动表: 64 字节
- 位图对象: 约 32 字节(仅元数据,共享数据指针)
- GPU 纹理: 64 字节(A8 格式)

### 3. GPU 纹理采样
- 8×8 纹理非常小,常驻 L1 缓存
- 使用最近邻采样(无过滤),性能开销极小
- 纹理坐标计算为模运算,硬件优化

### 4. 着色器成本
抖动通常只增加 2-3 条指令:
```glsl
float dither = texture(ditherLUT, frag_coord.xy / 8.0).a;
color += (dither - 0.5) * ditherRange;
```

### 5. 分支优化
`DitherRangeForConfig` 使用 switch-case,编译器优化为跳转表,O(1) 查询。

### 6. 缓存友好
- 抖动表在只读数据段,永久缓存
- 8×8 尺寸保证单个缓存行可容纳(64字节)

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/DitherUtils.h` | 定义 | 抖动工具接口 |
| `src/gpu/DitherUtils.cpp` | 实现 | 抖动算法实现 |
| `include/core/SkColorType.h` | 依赖 | 颜色格式定义 |
| `src/gpu/ganesh/GrFragmentProcessor.cpp` | 使用者 | Ganesh 片段处理器 |
| `src/gpu/graphite/ShaderCodeDictionary.cpp` | 使用者 | Graphite 着色器字典 |
| `src/core/SkDraw.cpp` | 参考 | CPU 端抖动实现 |
| `resources/sksl/sk_dither_shader.sksl` | 集成 | SkSL 抖动着色器 |

**备注**: 该模块是 GPU 低位深渲染的关键技术,通过简单而高效的实现显著提升了低位深目标的视觉质量。设计充分利用了编译时计算和 GPU 纹理硬件的优势,体现了性能和质量的平衡。
