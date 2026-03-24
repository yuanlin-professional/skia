# SkRawDecoder

> 源文件: `include/codec/SkRawDecoder.h`

## 概述

SkRawDecoder 命名空间提供了 RAW 相机图像格式的解码功能。RAW 格式是专业相机输出的未经处理的传感器数据,包含最大的图像信息。该模块支持多种厂商的 RAW 格式(如 Canon CR2、Nikon NEF、Sony ARW 等),是 Skia 模块化图像解码架构中处理专业摄影格式的组件。

## 架构位置

SkRawDecoder 位于 Skia 图像编解码子系统的格式特定层,属于 RAW 图像解码模块。它依赖 Google 的 PIEX(Preview Image Extractor)和 DNG SDK 进行 RAW 格式识别和解码。由于 RAW 格式的复杂性和多样性,该模块在解码器链中通常被最后检查,以避免误识别。

## 主要函数

### 格式检测

#### `inline bool IsRaw(const void*, size_t)`

**功能**: 检查给定的字节序列是否可能为 RAW 图像

**参数**:
- 第一个参数: 指向数据缓冲区的指针
- 第二个参数: 缓冲区大小(字节)

**返回值**: 始终返回 `true`

**特殊设计**:
```cpp
inline bool IsRaw(const void*, size_t) {
    // 始终返回 true,假定一切可能是 RAW
    return true;
}
```

**设计原因**:
RAW 格式难以仅通过前几个字节识别:
- **多样性**: 不同厂商使用不同的文件结构
- **嵌入式数据**: 文件头可能在深层位置
- **PIEX 需求**: 某些格式(如 Sony ARW)可能需要读取 10KB+ 才能识别

**使用策略**:
- 将 RAW 解码器注册为**最后检查**的解码器
- 其他格式检测失败后才尝试 RAW 解码
- 实际格式验证在 Decode 函数中进行

**性能影响**:
由于始终返回 true,IsRaw 不会过滤任何输入,但通过注册顺序控制避免性能问题。

### 解码器创建

#### `SK_API std::unique_ptr<SkCodec> Decode(std::unique_ptr<SkStream>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从流中解码 RAW 图像

**参数**:
- `stream`: 唯一指针,指向包含 RAW 数据的输入流
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 被忽略(RAW 解码不使用上下文)

**返回值**:
- 成功: 返回 SkCodec 智能指针
- 失败: 返回 nullptr,同时设置 result 参数

**支持的 RAW 格式**:
- **Canon**: CR2, CRW
- **Nikon**: NEF, NRW
- **Sony**: ARW, SRF, SR2
- **Olympus**: ORF
- **Pentax**: PEF, DNG
- **Panasonic**: RW2
- **Fujifilm**: RAF
- **Adobe**: DNG(通用格式)
- 其他: 基于 TIFF 的 RAW 格式

**解码流程**:
1. 使用 PIEX 识别 RAW 格式类型
2. 提取预览图像或缩略图
3. 如果可用,解码全分辨率图像
4. 应用基本颜色校正(可选)

**DecodeContext 说明**:
```cpp
// DecodeContext 在 RAW 解码中被忽略
std::unique_ptr<SkCodec> codec = SkRawDecoder::Decode(
    std::move(stream),
    &result,
    nullptr  // 无需传递上下文
);
```

#### `SK_API std::unique_ptr<SkCodec> Decode(sk_sp<const SkData>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从内存数据中解码 RAW 图像

**参数**: 同流版本

**返回值**: 同流版本

**使用场景**:
- RAW 文件已完全加载到内存
- 从相机直接获取的内存数据
- 网络传输的 RAW 图像

**性能**: RAW 文件通常较大(10-50 MB),内存版本需要足够的可用内存

### 解码器描述符

#### `inline constexpr SkCodecs::Decoder Decoder()`

**功能**: 返回 RAW 解码器的描述符,用于注册到解码器系统

**返回值**: SkCodecs::Decoder 结构体,包含:
- `name`: "raw"(格式名称)
- `probe`: IsRaw(格式检测函数)
- `decode`: Decode(解码函数)

**特殊注释**:
```cpp
// This decoder will always be checked last, no matter when it is registered.
// 该解码器总是最后检查,无论何时注册
```

**注册机制**:
解码器系统特殊处理 RAW 解码器:
- 自动放置在检查列表末尾
- 避免误识别其他格式
- 保证性能最优

**使用场景**:
```cpp
// 注册 RAW 解码器(会自动排在最后)
SkCodecs::Register(SkRawDecoder::Decoder());

// 即使先注册 RAW,也会在 PNG、JPEG 等之后检查
SkCodecs::Register(SkRawDecoder::Decoder());
SkCodecs::Register(SkPngDecoder::Decoder());
// 实际顺序: PNG, JPEG, ..., RAW
```

## 使用示例

### 示例 1: 基础 RAW 解码

```cpp
#include "include/codec/SkRawDecoder.h"
#include "include/core/SkBitmap.h"
#include "include/core/SkStream.h"

bool decodeRawFile(const char* path, SkBitmap* bitmap) {
    // 打开 RAW 文件
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    // 尝试解码为 RAW
    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkRawDecoder::Decode(std::move(stream), &result);

    if (!codec) {
        // 不是有效的 RAW 文件或不支持的格式
        printf("Failed to decode RAW: %d\n", result);
        return false;
    }

    // 获取图像信息
    SkImageInfo info = codec->getInfo();
    printf("RAW image: %dx%d, color type: %d\n",
           info.width(), info.height(), info.colorType());

    // 分配位图
    if (!bitmap->tryAllocPixels(info)) {
        return false;
    }

    // 解码像素
    result = codec->getPixels(info, bitmap->getPixels(),
                              bitmap->rowBytes());
    return result == SkCodec::kSuccess;
}
```

### 示例 2: 提取缩略图

```cpp
bool extractRawThumbnail(const char* path, SkBitmap* thumbnail,
                         int maxDimension) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkRawDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        return false;
    }

    // 获取原始尺寸
    SkImageInfo fullInfo = codec->getInfo();

    // 计算缩放比例
    float scale = std::min(
        (float)maxDimension / fullInfo.width(),
        (float)maxDimension / fullInfo.height()
    );

    if (scale >= 1.0f) {
        scale = 1.0f; // 不放大
    }

    // 计算目标尺寸
    int dstWidth = (int)(fullInfo.width() * scale);
    int dstHeight = (int)(fullInfo.height() * scale);
    SkImageInfo dstInfo = fullInfo.makeWH(dstWidth, dstHeight);

    // 分配缩略图
    if (!thumbnail->tryAllocPixels(dstInfo)) {
        return false;
    }

    // 解码为缩略图尺寸
    SkCodec::Options options;
    result = codec->getPixels(dstInfo, thumbnail->getPixels(),
                              thumbnail->rowBytes(), &options);

    return result == SkCodec::kSuccess;
}
```

### 示例 3: 检测 RAW 格式类型

```cpp
std::string getRawFormatName(const char* path) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return "Unknown";
    }

    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkRawDecoder::Decode(std::move(stream), &result);

    if (!codec) {
        return "Not RAW";
    }

    // 可以从编解码器元数据获取格式信息
    // 实际实现依赖于 SkCodec 的扩展接口
    return "RAW"; // 简化示例
}
```

### 示例 4: 批量 RAW 处理

```cpp
#include <filesystem>
#include <vector>

std::vector<SkBitmap> batchProcessRaw(const std::string& directory) {
    std::vector<SkBitmap> results;

    for (const auto& entry :
         std::filesystem::directory_iterator(directory)) {
        if (!entry.is_regular_file()) {
            continue;
        }

        // 尝试解码
        SkBitmap bitmap;
        if (decodeRawFile(entry.path().c_str(), &bitmap)) {
            results.push_back(std::move(bitmap));
        }
    }

    return results;
}
```

## 内部实现细节

### PIEX 集成

PIEX (Preview Image Extractor) 职责:
- 快速识别 RAW 格式类型
- 提取嵌入的 JPEG 预览图
- 读取 EXIF 元数据
- 定位图像数据块

工作流程:
1. 读取文件头(可能需要数千字节)
2. 解析 TIFF/EXIF 结构
3. 识别相机制造商和型号
4. 定位预览图像偏移

### DNG SDK 集成

DNG SDK 职责:
- 解码 Adobe DNG 格式
- 处理线性化和颜色校正
- Demosaicing(去马赛克)
- 白平衡调整

支持的 DNG 特性:
- 线性 RAW 数据
- 压缩 RAW (lossless JPEG)
- 浮点 RAW
- 颜色配置文件

### 颜色处理

RAW 解码的颜色流程:
1. **传感器数据**: 单通道 Bayer 阵列
2. **Demosaicing**: 插值生成 RGB
3. **白平衡**: 应用色温校正
4. **色彩空间**: 转换到 sRGB 或其他空间
5. **Gamma**: 应用伽马曲线

Skia 的处理:
- 通常使用相机嵌入的 JPEG 预览
- 或应用基本的线性转换
- 专业应用应使用 RawTherapee/Darktable 等工具

### 性能优化

**预览图优先**:
优先提取嵌入的 JPEG 预览而非解码完整 RAW:
- 预览图通常 1-5 MB
- 完整解码需要 10-30 秒
- 预览解码 < 1 秒

**渐进式解码**:
支持逐行解码以减少内存峰值

**缓存策略**:
缓存解码结果避免重复处理大文件

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkCodec.h | 解码器基类和接口 |
| SkRefCnt.h | 智能指针和引用计数 |
| SkAPI.h | API 导出宏 |
| PIEX | RAW 格式识别和预览提取(外部) |
| DNG SDK | DNG 格式解码(外部) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkCodecs | 解码器注册和查找系统 |
| SkImage | 从 RAW 数据创建图像 |
| 照片应用 | 相机 RAW 文件处理 |

## 设计模式与设计决策

### "接受一切"的格式检测

IsRaw 返回 true 的设计:
- **简化**: 避免复杂的多格式检测逻辑
- **推迟验证**: 在 Decode 阶段进行完整验证
- **依赖排序**: 通过注册顺序保证正确性

### 最后检查策略

自动放置在检查列表末尾:
- **避免误判**: 不会将其他格式误识为 RAW
- **性能优化**: 常见格式先检查
- **兜底处理**: 作为最后尝试的格式

### 可选依赖

RAW 解码作为可选模块:
- 减小核心库体积
- 避免强制依赖大型 SDK
- 按需编译和链接

## 性能考量

### 文件大小

典型 RAW 文件大小:
- **入门相机**: 10-20 MB
- **中端相机**: 20-40 MB
- **专业相机**: 40-80 MB
- **中画幅**: 80-150 MB

### 解码时间

影响因素:
- **文件大小**: 线性关系
- **解码模式**: 预览 vs 完整解码
- **压缩**: 无损压缩需要额外时间
- **颜色处理**: 完整处理耗时

典型性能:
- 预览提取: 0.5-2 秒
- 完整解码: 5-30 秒(取决于文件大小和处理器)

### 内存使用

内存需求:
- 输入缓冲: 文件大小
- 输出位图: 宽 × 高 × 4 字节(RGBA)
- 临时缓冲: 额外 50-100 MB(DNG SDK)

优化建议:
- 对于预览,使用流式解码
- 大文件使用缩略图提取
- 限制并发解码数量

## 平台相关说明

### 外部依赖

不同平台的依赖管理:
- **PIEX**: 通常静态链接或作为子模块
- **DNG SDK**: 可能需要单独构建
- **libjpeg/libpng**: 用于解码预览图

### 编译选项

可选编译:
```gn
# BUILD.gn
skia_enable_raw_codec = true
skia_use_piex = true
skia_use_dng_sdk = true
```

条件编译:
```cpp
#if defined(SK_CODEC_DECODES_RAW)
    // RAW 解码代码
#endif
```

### 移动平台限制

移动设备注意事项:
- 内存限制: 避免解码超大 RAW
- 电池消耗: RAW 解码 CPU 密集
- 存储空间: RAW 文件占用大量空间

建议:
- 仅提取预览图
- 使用云端处理
- 提供用户选项(质量 vs 速度)

## 相关文件

| 文件 | 关系 |
|------|------|
| include/codec/SkCodec.h | 解码器基类 |
| src/codec/SkRawCodec.h | RAW 解码器实现类 |
| src/codec/SkRawCodec.cpp | RAW 解码器实现 |
| third_party/piex | PIEX 库(格式识别) |
| third_party/dng_sdk | Adobe DNG SDK |
| include/core/SkData.h | 内存数据容器 |
| include/core/SkStream.h | 流接口 |
