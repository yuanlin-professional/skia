# SkJpegxlCodec

> 源文件: src/codec/SkJpegxlCodec.h, src/codec/SkJpegxlCodec.cpp

## 概述

`SkJpegxlCodec` 是 Skia 图像解码库中用于处理 JPEG XL（JXL）格式图像的解码器实现。JPEG XL 是新一代高效图像格式，支持有损和无损压缩、HDR、动画等高级特性。该类继承自 `SkScalingCodec`，通过封装 libjxl 解码库提供完整的 JXL 图像解码能力，支持静态图像和动画帧解码、色彩空间管理、ICC 配置文件处理等功能。

## 架构位置

该模块位于 Skia 编解码器子系统的核心位置：

```
src/codec/
  ├── SkJpegxlCodec.h           # 解码器声明
  ├── SkJpegxlCodec.cpp         # 解码器实现
  ├── SkScalingCodec.h          # 基类（支持缩放的解码器）
  ├── SkCodec.h                 # 顶层解码器抽象
  └── SkFrameHolder.h           # 动画帧管理器
include/codec/
  └── SkJpegxlDecoder.h         # 公共解码器 API
```

作为格式特定解码器，它是 Skia 图像解码管线的重要组成部分，与其他格式解码器（PNG、JPEG、WebP 等）并列。

## 主要类与结构体

### SkJpegxlCodec

继承自 `SkScalingCodec` 的主解码器类。

**核心成员变量：**

```cpp
std::unique_ptr<SkJpegxlCodecPriv> fCodec;  // 不透明的解码器实现（PIMPL 模式）
sk_sp<const SkData> fData;                  // 图像数据（整体内存）
```

**公共静态方法：**

```cpp
static bool IsJpegxl(const void*, size_t);  // 检测 JXL 签名
static std::unique_ptr<SkCodec> MakeFromStream(
    std::unique_ptr<SkStream>, Result*);    // 从流创建解码器
```

**虚函数覆盖：**

```cpp
Result onGetPixels(...) override;           // 解码像素数据
bool onRewind() override;                   // 重置解码器状态
bool conversionSupported(...) override;     // 检查颜色格式转换支持
int onGetFrameCount() override;             // 获取动画帧数
bool onGetFrameInfo(int, FrameInfo*) const override;  // 获取帧信息
int onGetRepetitionCount() override;        // 获取动画循环次数
IsAnimated onIsAnimated() override;         // 判断是否为动画
```

### SkJpegxlCodecPriv

私有实现类（PIMPL 模式），继承自 `SkFrameHolder`。

**成员变量：**

```cpp
JxlDecoderPtr fDecoder;                     // libjxl 解码器智能指针
JxlBasicInfo fInfo;                         // 基本图像信息
bool fSeenAllFrames = false;                // 是否已扫描所有帧
std::vector<Frame> fFrames;                 // 帧信息列表
int fLastProcessedFrame = SkCodec::kNoFrame; // 最后处理的帧索引
void* fDst;                                 // 目标缓冲区指针
size_t fPixelShift;                         // 像素位移（用于地址计算）
size_t fRowBytes;                           // 行字节数
SkColorType fDstColorType;                  // 目标颜色类型
```

**覆盖方法：**

```cpp
const SkFrame* onGetFrame(int i) const override;  // 获取指定帧
```

### Frame

匿名命名空间内的帧信息类，继承自 `SkFrame`。

```cpp
class Frame : public SkFrame {
public:
    explicit Frame(int i, SkEncodedInfo::Alpha alpha);
    SkEncodedInfo::Alpha onReportedAlpha() const override;
private:
    const SkEncodedInfo::Alpha fReportedAlpha;  // 透明度类型
};
```

## 公共 API 函数

### IsJpegxl (静态方法)

```cpp
bool SkJpegxlCodec::IsJpegxl(const void* buffer, size_t bytesRead);
```

检测数据是否为有效的 JPEG XL 格式。通过 `JxlSignatureCheck` 验证签名：
- `JXL_SIG_CODESTREAM`：裸码流
- `JXL_SIG_CONTAINER`：容器格式

### MakeFromStream (静态工厂方法)

```cpp
std::unique_ptr<SkCodec> MakeFromStream(
    std::unique_ptr<SkStream> stream, Result* result);
```

从流创建 JXL 解码器实例。实现流程：

1. **数据包装**：根据流类型选择策略
   - 内存映射流：使用 `MakeWithoutCopy` 零拷贝包装
   - 普通流：拷贝数据到 `SkData`

2. **解码器初始化**：
   - 订阅 `JXL_DEC_BASIC_INFO` 和 `JXL_DEC_COLOR_ENCODING` 事件
   - 设置输入数据

3. **元数据提取**：
   - 获取基本信息（尺寸、通道数、位深度）
   - 验证尺寸是否在 `int32_t` 范围内
   - 确定颜色类型（RGB/RGBA/Gray/GrayAlpha）

4. **ICC 配置文件处理**：
   - 查询 ICC 配置文件大小
   - 提取并封装为 `SkCodecs::ColorProfile`

5. **创建编码信息**：
   - 固定使用 16 位通道
   - 构造 `SkEncodedInfo` 对象

## 内部实现细节

### onGetPixels 解码流程

```cpp
Result onGetPixels(const SkImageInfo& dstInfo, void* dst,
                   size_t rowBytes, const Options& options,
                   int* rowsDecodedPtr);
```

**核心流程：**

1. **帧索引处理**：
   - 如果请求帧在当前位置之前，执行 `JxlDecoderRewind` 重置
   - 如果在之后，使用 `JxlDecoderSkipFrames` 跳过中间帧

2. **解码器配置**：
   - 订阅 `JXL_DEC_FRAME` 和 `JXL_DEC_FULL_IMAGE` 事件
   - 确定输出格式（`JXL_TYPE_UINT8` 或 `JXL_TYPE_FLOAT16`）
   - 设置像素格式：`{通道数, 数据类型, 小端序, 对齐}`

3. **输出格式选择**：
   - **F16 条件**：目标为 F16 或需要色彩转换
   - **U8 条件**：其他情况（节省内存）

4. **回调注册**：
   - 注册 `imageOutCallback` 用于接收解码数据
   - 传递 `this` 指针作为 opaque 参数

5. **解码执行**：
   - 调用 `JxlDecoderProcessInput` 直到 `JXL_DEC_FULL_IMAGE`
   - 回调函数逐行/逐块写入目标缓冲区

### imageOutCallback 实现

```cpp
void imageOutCallback(void* opaque, size_t x, size_t y,
                     size_t num_pixels, const void* pixels);
```

**处理逻辑：**

1. **地址计算**：
   ```cpp
   size_t offset = y * codec.fRowBytes + (x << codec.fPixelShift);
   void* dst = SkTAddOffset<void>(codec.fDst, offset);
   ```

2. **色彩转换路径**（如果需要）：
   ```cpp
   if (instance->colorXform()) {
       instance->applyColorXform(dst, pixels, num_pixels);
       return;
   }
   ```

3. **直接拷贝路径**：
   - `kRGBA_8888_SkColorType`：4 字节/像素，直接 `memcpy`
   - `kBGRA_8888_SkColorType`：使用 `SkOpts::RGBA_to_bgrA` 交换红蓝通道
   - `kRGBA_F16_SkColorType`：8 字节/像素，直接 `memcpy`

### scanFrames 动画帧扫描

```cpp
bool scanFrames();
```

用于延迟扫描动画的所有帧信息。流程：

1. 创建独立的解码器实例
2. 订阅 `JXL_DEC_FRAME` 事件
3. 循环处理直到 `JXL_DEC_SUCCESS`
4. 对每个帧：
   - 提取 `JxlFrameHeader`
   - 计算帧持续时间（毫秒）：
     ```cpp
     int duration = (1000 * frameHeader.duration *
                     info.animation.tps_denominator) /
                     info.animation.tps_numerator;
     ```
   - 创建 `Frame` 对象并设置依赖关系

### conversionSupported 格式支持检测

支持的目标格式：
- `kRGBA_8888_SkColorType`：直接拷贝或色彩转换
- `kBGRA_8888_SkColorType`：红蓝通道交换
- `kRGBA_F16_SkColorType`：F16 输出

不支持的格式（返回 `false`）：
- `kRGB_565_SkColorType`
- `kGray_8_SkColorType`
- `kAlpha_8_SkColorType`

## 依赖关系

**外部库依赖：**
- `jxl/decode.h`：libjxl 解码 API
- `jxl/decode_cxx.h`：C++ 封装（智能指针等）
- `jxl/codestream_header.h`：码流头信息
- `jxl/types.h`：类型定义

**内部依赖：**
- `SkScalingCodec`：基类，提供缩放支持框架
- `SkFrameHolder`：动画帧管理
- `SkCodecPriv.h`：编解码器通用私有工具
- `SkSwizzlePriv.h`：像素格式转换（`RGBA_to_bgrA`）
- `skcms`：色彩管理系统

**依赖方：**
- `SkJpegxlDecoder`：公共 API 命名空间
- `SkCodec` 工厂系统：通过注册机制自动选择解码器

## 设计模式与设计决策

### 1. PIMPL（Pointer to Implementation）模式

将 `SkJpegxlCodecPriv` 作为不透明实现，优点：
- **编译隔离**：头文件不暴露 libjxl 类型
- **二进制兼容性**：实现变化不影响 ABI
- **减少编译依赖**：客户端不需要包含 libjxl 头文件

### 2. 回调函数机制

使用 `imageOutCallback` 而非轮询：
- **流式处理**：支持增量解码（虽然当前未启用）
- **零拷贝潜力**：未来可以直接写入目标缓冲区
- **灵活性**：支持部分区域解码

### 3. 延迟帧扫描

`scanFrames()` 仅在需要时执行：
- 静态图像无需扫描
- 动画第一次访问帧信息时触发
- 避免不必要的解码开销

### 4. 数据所有权策略

- **内存映射流**：零拷贝包装，保持流活跃
- **普通流**：拷贝后释放流，简化生命周期管理

### 5. 输出格式自适应

根据目标格式和是否需要色彩转换自动选择：
- **U8 路径**：内存友好，适合显示
- **F16 路径**：精度优先，避免色彩转换中的量化损失

## 性能考量

### 1. 内存使用优化

**零拷贝策略**：
- 内存映射流使用 `MakeWithoutCopy`，避免冗余拷贝
- 数据在 `fData` 中保持，供解码器直接访问

**格式选择**：
- 默认使用 U8（4 字节/像素）而非 F16（8 字节/像素）
- 仅在必要时使用高精度格式

### 2. 解码器状态管理

**帧跳过优化**：
- 使用 `JxlDecoderSkipFrames` 快速跳过不需要的帧
- 避免完整解码中间帧

**重置开销**：
- `JxlDecoderRewind` 是轻量级操作
- 但需要重新订阅事件和设置输入

### 3. 像素拷贝优化

**SIMD 加速**：
- `SkOpts::RGBA_to_bgrA` 使用平台优化的 SIMD 指令
- 在 x86 上使用 SSE/AVX，ARM 上使用 NEON

**直接内存拷贝**：
- RGBA 和 F16 格式直接 `memcpy`
- 避免逐像素循环

### 4. 色彩转换策略

**条件启用 F16**：
```cpp
if (fCodec->fDstColorType == kRGBA_F16_SkColorType) halfFloatOutput = true;
if (colorXform()) halfFloatOutput = true;
```

这避免了两次精度损失（JXL F32 → U8 → 色彩转换 → 目标格式）。

### 5. 未实现的优化机会

注释中标记的待实现特性：
- **扫描线解码**：允许逐行处理，减少内存峰值
- **增量解码**：支持流式输入
- **裁剪输出**：仅解码感兴趣区域
- **缩放支持**：利用 JXL 的多分辨率特性

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `include/codec/SkJpegxlDecoder.h` | 公共解码器 API | 提供工厂函数和命名空间 |
| `src/codec/SkScalingCodec.h` | 缩放解码器基类 | 父类，提供缩放框架 |
| `src/codec/SkCodec.h` | 解码器抽象基类 | 定义解码器接口 |
| `src/codec/SkFrameHolder.h` | 动画帧管理 | 管理帧序列和依赖 |
| `include/private/SkEncodedInfo.h` | 编码信息结构 | 描述图像格式和元数据 |
| `src/core/SkSwizzlePriv.h` | 像素格式转换 | 提供 RGBA↔BGRA 转换 |
| `modules/skcms/skcms.h` | 色彩管理系统 | ICC 配置文件处理 |
| `jxl/decode.h` | libjxl 解码库 | 外部依赖，核心解码功能 |

---

*本文档由 Claude Code 自动生成*
