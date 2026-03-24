# SkIcoDecoder

> 源文件: `include/codec/SkIcoDecoder.h`

## 概述

SkIcoDecoder 提供 Windows ICO(Icon)图像格式的解码能力。ICO 格式是 Windows 系统图标的标准容器格式,可包含多个不同尺寸和色深的图像,支持 BMP 和 PNG 两种内嵌格式。该模块是 Skia 跨平台图标显示能力的重要组成部分,广泛用于桌面应用、浏览器收藏夹图标等场景。

## 架构位置

SkIcoDecoder 位于 Skia Codec 子系统,实现 SkCodec 抽象接口。它通过委托机制调用 SkBmpDecoder 或 SkPngDecoder 解码内嵌图像,为上层提供统一的多尺寸图标访问接口,是图像格式支持层的重要模块。

## 命名空间 API

### `IsIco`

检测数据是否为 ICO 格式。

```cpp
SK_API bool IsIco(const void* data, size_t length)
```

**功能**: 通过检查 ICO 文件头识别格式。

**参数**:
- `data`: 待检测数据的指针
- `length`: 数据长度(字节)

**返回值**:
- `true`: 数据符合 ICO 文件头规范
- `false`: 非 ICO 格式

**检测逻辑**:
- ICO 文件头: `00 00 01 00` (前 2 字节为保留字 0,接下来 2 字节为类型 1)
- CUR 文件(光标): `00 00 02 00` (类型为 2,Skia 通常也支持)
- 最少需要 4 字节进行检测

**与 BMP 的区别**:
- BMP 文件头: `42 4D` ("BM")
- ICO 可包含 BMP 数据,但外层有 ICO 容器结构

### `Decode` (SkStream 版本)

从输入流解码 ICO 图像。

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

**ICO 特性支持**:
- 自动选择最高质量的内嵌图像
- 支持透明通道(PNG 子图像或 32-bit BMP 的 Alpha 通道)
- 处理多图标尺寸(通常包含 16x16、32x32、48x48 等)

### `Decode` (SkData 版本)

从内存数据块解码 ICO 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    sk_sp<const SkData> data,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

**参数**:
- `data`: 包含完整 ICO 数据的智能指针
- `result`: 输出参数,返回解码状态
- `context`: 解码上下文(当前忽略)

**适用场景**:
- 从资源文件加载嵌入式图标
- 网络下载的 favicon.ico
- Windows PE 文件中提取的图标资源

### `Decoder`

返回解码器描述符,用于注册到解码器工厂。

```cpp
inline constexpr SkCodecs::Decoder Decoder()
```

**返回值**: 包含以下信息的结构体:
- `name`: 字符串 "ico"
- `isFormat`: 函数指针 `IsIco`
- `makeCodec`: 函数指针 `Decode`

## 内部实现细节

### ICO 文件结构
```
ICONDIR {
    WORD idReserved; // 必须为 0
    WORD idType;     // 1=ICO, 2=CUR
    WORD idCount;    // 图像数量
}
ICONDIRENTRY[idCount] {
    BYTE bWidth;     // 宽度(0 表示 256)
    BYTE bHeight;    // 高度(0 表示 256)
    BYTE bColorCount;// 颜色数(0 表示 >256 色)
    BYTE bReserved;  // 保留
    WORD wPlanes;    // 色彩平面数
    WORD wBitCount;  // 每像素位数
    DWORD dwBytesInRes; // 图像数据大小
    DWORD dwImageOffset;// 图像数据偏移
}
图像数据 (BMP 或 PNG)
```

### 图像选择策略
当 ICO 包含多个图像时,SkCodec 通常选择:
1. **最高分辨率**: 优先选择尺寸最大的图像
2. **PNG 优先**: 如果有 PNG 格式,优先于 BMP(PNG 压缩更好,支持真正的 Alpha)
3. **色深优先**: 相同尺寸下选择 32-bit > 24-bit > 8-bit

### 委托解码
SkIcoDecoder 本身不实现具体解码逻辑:
- 检测内嵌图像格式(通过魔数)
- 创建子流(SkMemoryStream)指向选定图像数据
- 调用对应解码器(SkBmpDecoder 或 SkPngDecoder)

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/codec/SkCodec.h | SkCodec 基类定义 |
| include/core/SkRefCnt.h | 智能指针支持 |
| include/private/base/SkAPI.h | 导出宏 SK_API |
| SkBmpDecoder | 解码 BMP 格式的内嵌图像 |
| SkPngDecoder | 解码 PNG 格式的内嵌图像 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkCodec | 通过工厂方法创建 ICO 解码器 |
| SkImage | 从 ICO 数据创建图像 |
| 桌面应用 | 加载应用程序图标 |
| 浏览器 | 显示网站 favicon |

## 设计模式与设计决策

### 代理模式(Proxy Pattern)
SkIcoDecoder 作为代理,将实际解码工作委托给 BMP/PNG 解码器:
- **优点**: 避免重复实现解码逻辑,代码复用率高
- **缺点**: 增加一层间接调用,但开销可忽略

### 延迟解码(Lazy Decoding)
仅在调用 `getPixels()` 时才解码选定的子图像:
- 节省内存(不需要解码所有尺寸版本)
- 加快初始化速度(仅解析文件头)

### 统一接口
通过 SkCodec 接口暴露,上层无需关心 ICO 的特殊性:
```cpp
// 用户代码无需区分格式
auto codec = SkCodec::MakeFromStream(stream);
codec->getPixels(...); // 自动处理 ICO 内部结构
```

## 性能考量

### 解码速度
ICO 解码速度取决于内嵌格式:
- **PNG 子图像**: 解码速度与 PNG 相当(~10-50ms)
- **BMP 子图像**: 通常更快(~1-5ms),因为压缩简单
- **多图标解析**: 文件头解析耗时 <1ms

### 内存占用
- 解码器对象: ~100 字节
- 文件头缓存: ~数百字节(取决于图标数量)
- 实际图像数据: 仅解码选定的一个尺寸,内存 = width * height * 4 字节

### 文件大小
典型 favicon.ico 文件:
- 单尺寸(16x16): ~1-4 KB
- 多尺寸(16/32/48): ~10-30 KB
- 高清图标(包含 256x256): ~50-200 KB

## 典型使用场景

### 场景 1: 加载网站图标
```cpp
// 下载 favicon.ico
sk_sp<SkData> data = downloadFavicon("https://example.com/favicon.ico");
SkCodec::Result result;
auto codec = SkIcoDecoder::Decode(data, &result);
if (codec) {
    // 获取推荐尺寸(通常是最大尺寸)
    SkImageInfo info = codec->getInfo();
    SkBitmap bitmap;
    bitmap.allocPixels(info);
    codec->getPixels(info, bitmap.getPixels(), bitmap.rowBytes());
}
```

### 场景 2: 选择特定尺寸
```cpp
// ICO 包含多个尺寸,但 SkCodec API 仅暴露一个
// 如需访问其他尺寸,需手动解析 ICO 结构或使用更底层 API
auto codec = SkIcoDecoder::Decode(stream, &result);
// 默认获取最大尺寸
```

### 场景 3: 格式检测
```cpp
// 区分 ICO 和 BMP(头部相似)
if (SkIcoDecoder::IsIco(data->data(), data->size())) {
    // ICO 格式,可能包含多尺寸
} else if (SkBmpDecoder::IsBmp(data->data(), data->size())) {
    // 单一 BMP 图像
}
```

## 边界情况处理

### 空 ICO 文件
如果 `idCount = 0`,返回 `kInvalidInput` 错误。

### 损坏的图像数据
如果选定的子图像数据损坏,返回对应格式的错误码(如 PNG 的 `kInvalidInput`)。

### 超大尺寸
ICO 规范理论上支持 256x256,但某些文件可能包含更大尺寸(如 512x512):
- Skia 会尝试解码,但可能受内存限制
- 建议在移动设备上限制最大尺寸

## 平台相关说明

### Windows
- 系统原生支持 ICO 格式
- 可通过 WIC(Windows Imaging Component)解码,性能更优
- Skia 的实现保证跨平台一致性

### macOS/iOS
- 系统不直接支持 ICO 格式
- 依赖 Skia 的实现
- .icns 格式(Apple 图标)需要不同的解码器

### Web/浏览器
- favicon.ico 是最常见的使用场景
- 现代浏览器也支持 PNG/SVG 格式图标
- ICO 仍然是兼容性最好的选择

## 限制与注意事项

### API 限制
当前 SkCodec API 不直接暴露多尺寸访问:
- `getInfo()` 仅返回选定图像的信息
- 如需枚举所有尺寸,需要使用内部 API 或手动解析

### 光标文件(CUR)
虽然格式相似,但 CUR 文件包含热点坐标:
- SkIcoDecoder 可能能解码,但会忽略热点信息
- 应用程序需要自行解析热点数据

### 压缩 BMP
ICO 中的 BMP 数据可能使用特殊格式:
- 不包含 BITMAPFILEHEADER(前 14 字节)
- 直接从 BITMAPINFOHEADER 开始
- SkBmpDecoder 需要处理这种变体

## 相关文件

| 文件 | 关系 |
|------|------|
| src/codec/SkIcoCodec.cpp | ICO 解码器实现 |
| include/codec/SkBmpDecoder.h | 解码 BMP 格式子图像 |
| include/codec/SkPngDecoder.h | 解码 PNG 格式子图像 |
| include/codec/SkCodec.h | 解码器基类接口 |
| src/codec/SkCodecPriv.h | 内部辅助函数 |

## 扩展阅读

### ICO 格式规范
- Microsoft ICO 格式官方文档
- MSDN: Icon Resources 章节
- ICO 与 CUR 的区别

### 替代格式
- **ICNS**: macOS/iOS 图标格式
- **SVG**: 矢量图标,可伸缩
- **WebP**: 现代网页图标格式

## 最佳实践

### 选择合适的格式
- **网站图标**: 优先使用 PNG 或 SVG,ICO 作为兼容性回退
- **Windows 应用**: 使用 ICO 包含多尺寸(16/32/48/256)
- **跨平台应用**: 准备 ICO(Windows)和 ICNS(macOS)两种格式

### 优化文件大小
- 仅包含常用尺寸(16/32/48)
- 大尺寸使用 PNG 而非 BMP(更小)
- 避免包含不必要的 8-bit 或 4-bit 版本

### 线程安全
- `IsIco` 函数线程安全
- 单个解码器实例不可跨线程使用
- 可在不同线程创建多个解码器
