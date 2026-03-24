# SkBmpDecoder

> 源文件: `include/codec/SkBmpDecoder.h`

## 概述

SkBmpDecoder 提供 Windows BMP(Bitmap)图像格式的解码能力。BMP 是 Windows 系统最早的标准图像格式,结构简单但功能完整,支持多种色深、压缩方式和调色板模式。该模块是 Skia 处理传统图像格式的重要组件,广泛用于解码系统图标、截图、旧版应用资源等场景。

## 架构位置

SkBmpDecoder 位于 Skia Codec 子系统,实现 SkCodec 抽象接口。它直接处理 BMP 文件的二进制结构,无需依赖外部库,是 Skia 自包含解码能力的典型代表。同时,SkBmpDecoder 也被 SkIcoDecoder 用于解码 ICO 文件中嵌入的 BMP 数据。

## 命名空间 API

### `IsBmp`

检测数据是否为 BMP 格式。

```cpp
SK_API bool IsBmp(const void* data, size_t length)
```

**功能**: 通过检查 BMP 文件头魔数识别格式。

**参数**:
- `data`: 待检测数据的指针
- `length`: 数据长度(字节)

**返回值**:
- `true`: 数据以 BMP 魔数 `0x42 0x4D` ("BM") 开头
- `false`: 非 BMP 格式

**检测细节**:
- BMP 文件必须以 "BM" (0x42 0x4D) 开头
- 其他变体如 "BA"(OS/2 Bitmap Array)、"CI"(OS/2 Color Icon)不常见
- 最少需要 2 字节进行检测

**快速检测优势**:
```cpp
// 仅读取前 2 字节,适合网络流
if (stream->read(header, 2) == 2 && SkBmpDecoder::IsBmp(header, 2)) {
    // 确认为 BMP 格式
}
```

### `Decode` (SkStream 版本)

从输入流解码 BMP 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    std::unique_ptr<SkStream> stream,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

**参数**:
- `stream`: 输入数据流,解码器获取所有权
- `result`: 输出参数,返回解码结果状态
- `context`: 解码上下文(当前版本忽略)

**返回值**:
- 成功: 返回 SkCodec 智能指针,`result` 设为 `kSuccess`
- 失败: 返回 `nullptr`,`result` 设为错误码

**支持的 BMP 变体**:
- **BITMAPINFOHEADER**(最常见,40 字节头)
- **BITMAPV4HEADER**(108 字节,Windows 95+)
- **BITMAPV5HEADER**(124 字节,Windows 98+)
- **OS/2 BITMAPCOREHEADER**(12 字节,兼容旧格式)

**压缩类型支持**:
- **BI_RGB**(无压缩)
- **BI_RLE8**(8-bit 行程编码)
- **BI_RLE4**(4-bit 行程编码)
- **BI_BITFIELDS**(位域掩码)

### `Decode` (SkData 版本)

从内存数据块解码 BMP 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    sk_sp<const SkData> data,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

**参数**:
- `data`: 包含完整 BMP 数据的智能指针
- `result`: 输出参数,返回解码状态
- `context`: 解码上下文(当前忽略)

**适用场景**:
- 从资源文件加载嵌入式 BMP
- 解码内存中构造的 BMP 数据
- 处理 ICO 文件中的 BMP 子图像(不含文件头)

### `Decoder`

返回解码器描述符,用于注册到解码器工厂。

```cpp
inline constexpr SkCodecs::Decoder Decoder()
```

**返回值**: 包含以下信息的结构体:
- `name`: 字符串 "bmp"
- `isFormat`: 函数指针 `IsBmp`
- `makeCodec`: 函数指针 `Decode`

## 内部实现细节

### BMP 文件结构
```
BITMAPFILEHEADER (14 字节)
    WORD  bfType;      // "BM" (0x4D42)
    DWORD bfSize;      // 文件大小
    WORD  bfReserved1; // 保留
    WORD  bfReserved2; // 保留
    DWORD bfOffBits;   // 像素数据偏移

BITMAPINFOHEADER (40 字节)
    DWORD biSize;        // 头大小
    LONG  biWidth;       // 宽度
    LONG  biHeight;      // 高度(负值表示自顶向下)
    WORD  biPlanes;      // 必须为 1
    WORD  biBitCount;    // 每像素位数(1/4/8/16/24/32)
    DWORD biCompression; // 压缩类型
    DWORD biSizeImage;   // 图像大小
    LONG  biXPelsPerMeter; // 水平分辨率
    LONG  biYPelsPerMeter; // 垂直分辨率
    DWORD biClrUsed;     // 使用的颜色数
    DWORD biClrImportant;// 重要颜色数

调色板(可选,取决于 biBitCount)
像素数据(自底向上存储,每行 4 字节对齐)
```

### 色深处理
| 位深 | 颜色模式 | 调色板 | 说明 |
|------|----------|--------|------|
| 1-bit | 单色 | 必需(2 色) | 黑白图像 |
| 4-bit | 16 色 | 必需(≤16 色) | 旧 Windows 图标 |
| 8-bit | 256 色 | 必需(≤256 色) | 索引色图像 |
| 16-bit | 高彩色 | 可选(位域) | RGB555 或 RGB565 |
| 24-bit | 真彩色 | 无 | RGB888(BGR 顺序) |
| 32-bit | 真彩色+Alpha | 无 | RGBA8888(BGRA 顺序) |

### 像素顺序特殊性
- **自底向上**: 默认从图像最后一行开始存储(biHeight > 0)
- **自顶向下**: biHeight 为负值时,从第一行开始
- **行对齐**: 每行字节数必须是 4 的倍数,不足补 0

### RLE 压缩算法
BMP 的 RLE4/RLE8 压缩非常简单:
- **重复模式**: `[count][value]` 表示重复 count 次值 value
- **绝对模式**: `[0][count][data...]` 表示接下来 count 个像素为原始数据
- **特殊标记**: `[0][0]` 行结束, `[0][1]` 图像结束, `[0][2]` 位移

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/codec/SkCodec.h | SkCodec 基类定义 |
| include/core/SkRefCnt.h | 智能指针支持 |
| include/private/base/SkAPI.h | 导出宏 SK_API |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkIcoDecoder | 解码 ICO 文件中的 BMP 子图像 |
| SkCodec | 通过工厂方法创建 BMP 解码器 |
| 桌面应用 | 加载截图、旧版应用资源 |

## 设计模式与设计决策

### 自包含实现
SkBmpDecoder 不依赖外部库,所有解码逻辑自行实现:
- **优点**: 无外部依赖,代码可控,易于调试
- **权衡**: BMP 格式简单,重新实现成本低

### 流式解析
解码器支持从 SkStream 读取,无需一次性加载整个文件:
- 头部解析: 仅读取前 54 字节(文件头+信息头)
- 调色板缓存: 按需读取
- 像素数据: 逐行解码,内存占用小

### 格式容错
对损坏或非标准 BMP 的处理:
- 宽松的头部验证(允许某些字段为 0)
- 自动修正非法的调色板大小
- 处理不规范的行对齐

## 性能考量

### 解码速度
BMP 解码速度极快,因为压缩简单:
- **无压缩 24-bit**: 几乎是内存拷贝速度(~5ms for 1920x1080)
- **RLE 压缩**: 稍慢,但仍比 JPEG 快(~10-20ms)
- **索引色转换**: 需要查表,略有额外开销

### 内存占用
- 解码器对象: ~200 字节
- 调色板缓存: 最多 1024 字节(256 色 * 4 字节)
- 像素缓冲区: width * height * 4 字节(RGBA)

### 文件大小
BMP 文件通常较大,因为压缩率低:
- 1920x1080 的 24-bit BMP: ~6.2 MB
- 同尺寸 PNG: ~1-3 MB
- 同尺寸 JPEG: ~200-500 KB

## 典型使用场景

### 场景 1: 解码截图文件
```cpp
std::unique_ptr<SkStream> stream = SkFILEStream::Make("screenshot.bmp");
SkCodec::Result result;
auto codec = SkBmpDecoder::Decode(std::move(stream), &result);
if (codec && result == SkCodec::kSuccess) {
    SkImageInfo info = codec->getInfo();
    SkBitmap bitmap;
    bitmap.allocPixels(info);
    codec->getPixels(info, bitmap.getPixels(), bitmap.rowBytes());
}
```

### 场景 2: 处理 ICO 中的 BMP
```cpp
// ICO 中的 BMP 数据不包含 BITMAPFILEHEADER
sk_sp<SkData> bmpData = extractFromIco(icoData, index);
auto codec = SkBmpDecoder::Decode(bmpData, &result);
// SkBmpDecoder 会检测并处理这种情况
```

### 场景 3: 解码 RLE 压缩 BMP
```cpp
// RLE 压缩在旧版 Windows 图标中常见
auto codec = SkBmpDecoder::Decode(stream, &result);
if (codec) {
    // 透明处理 RLE 解压缩
    codec->getPixels(...);
}
```

## 边界情况处理

### 不支持的压缩类型
- **BI_JPEG/BI_PNG**: 某些 BMP 文件内嵌 JPEG/PNG 数据,Skia 不支持
- **解决方案**: 返回 `kUnimplemented` 错误,建议直接使用对应格式解码器

### 超大尺寸
- BMP 规范允许最大 2^31 像素的图像
- Skia 会检查尺寸是否合理,防止内存溢出
- 移动设备上建议限制在 4096x4096 以内

### 损坏的 RLE 数据
- RLE 数据损坏可能导致解码越界
- SkBmpDecoder 会检测异常并提前终止,返回 `kIncompleteInput`

## 平台相关说明

### Windows
- 系统原生支持 BMP 格式(通过 GDI/GDI+)
- Skia 的实现保证跨平台一致性
- 可通过 WIC 硬件加速(可选)

### 非 Windows 平台
- 完全依赖 Skia 实现
- 性能与 Windows 相当(BMP 解码简单,无需硬件加速)

### 移动设备
- BMP 在移动端较少使用(文件太大)
- 建议转换为 PNG/WebP 以节省存储和带宽

## 限制与注意事项

### 颜色空间
- BMP 不支持嵌入 ICC 配置文件
- 默认假设 sRGB 色彩空间
- V4/V5 头部包含色彩空间信息,但很少使用

### Alpha 通道
- 32-bit BMP 理论上支持 Alpha,但标准定义模糊
- 某些软件(如 Photoshop)生成的 32-bit BMP 包含有效 Alpha
- 其他软件可能将 Alpha 通道填充为 0(全透明)或 255(不透明)

### 自顶向下 BMP
- 负高度的 BMP 在某些旧软件中不兼容
- Skia 完全支持,但导出时建议使用标准的自底向上格式

## 相关文件

| 文件 | 关系 |
|------|------|
| src/codec/SkBmpCodec.cpp | BMP 解码器实现 |
| src/codec/SkBmpRLECodec.cpp | RLE 压缩 BMP 的特殊处理 |
| src/codec/SkBmpStandardCodec.cpp | 标准无压缩 BMP 的优化实现 |
| src/codec/SkBmpMaskCodec.cpp | 位域掩码 BMP 的处理 |
| include/codec/SkIcoDecoder.h | ICO 解码器,依赖 BMP 解码器 |
| include/codec/SkCodec.h | 解码器基类接口 |

## 最佳实践

### 选择合适的格式
- **截图保存**: 优先使用 PNG(无损,文件小)
- **临时文件**: BMP 适合快速写入(无压缩开销)
- **长期存储**: 转换为 PNG/JPEG/WebP

### 处理透明度
```cpp
// 检测 32-bit BMP 的 Alpha 通道是否有效
if (codec->getInfo().alphaType() == kUnpremul_SkAlphaType) {
    // 包含有效 Alpha
} else {
    // 假设不透明
}
```

### 性能优化
```cpp
// 对于大 BMP,使用子区域解码
SkCodec::Options options;
options.fSubset = SkIRect::MakeXYWH(100, 100, 500, 500);
codec->getPixels(info, pixels, rowBytes, &options);
```

### 线程安全
- `IsBmp` 函数线程安全
- 单个解码器实例不可跨线程使用
- 可在不同线程创建多个解码器实例
