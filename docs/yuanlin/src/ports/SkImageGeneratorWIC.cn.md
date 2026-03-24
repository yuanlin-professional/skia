# SkImageGeneratorWIC

> 源文件: include/ports/SkImageGeneratorWIC.h, src/ports/SkImageGeneratorWIC.cpp

## 概述

SkImageGeneratorWIC 是 Skia 图形库为 Windows 平台提供的图像解码器实现，基于 Windows Imaging Component (WIC) API。WIC 是 Windows Vista 引入的系统级图像编解码框架，支持广泛的图像格式和硬件加速。该模块将 WIC 集成到 Skia 的 SkImageGenerator 框架中，支持 JPEG、PNG、GIF、BMP、TIFF、HEIF 等格式的解码，以及 EXIF 方向元数据处理。该实现要求客户端负责 COM 库初始化。

## 架构位置

该模块位于 Skia 的平台适配层（ports），专门为 Windows 提供图像生成功能：

```
skia/
├── include/ports/
│   └── SkImageGeneratorWIC.h          # 公共接口
└── src/ports/
    ├── SkImageGeneratorWIC.cpp        # 实现（286 行）
    └── utils/win/
        ├── SkIStream.h                # IStream 适配器
        └── SkTScopedComPtr.h          # COM 智能指针
```

该模块仅在定义 `SK_BUILD_FOR_WIN` 宏时可用。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `ImageGeneratorWIC` | `SkImageGenerator` | 封装 WIC 解码器的图像生成器 |

### 关键成员变量

**ImageGeneratorWIC:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fImagingFactory` | `SkTScopedComPtr<IWICImagingFactory>` | WIC 成像工厂实例 |
| `fImageSource` | `SkTScopedComPtr<IWICBitmapSource>` | WIC 位图源（解码后的帧）|
| `fData` | `sk_sp<const SkData>` | 编码图像的原始数据 |
| `fOrigin` | `SkEncodedOrigin` | EXIF 方向标签 |

## 公共 API 函数

### 工厂函数

```cpp
namespace SkImageGeneratorWIC {
    SK_API std::unique_ptr<SkImageGenerator> MakeFromEncodedWIC(sk_sp<const SkData>);
}
```

从编码的图像数据创建 WIC 图像生成器。支持 Windows 系统安装的所有图像编解码器。

**COM 初始化要求**:

客户端必须在调用此函数前初始化 COM 库：

```cpp
// 每个使用 COM 的线程必须调用
CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);

// 使用完成后
CoUninitialize();
```

详见 [MSDN 文档](https://msdn.microsoft.com/en-us/library/windows/desktop/ff485844.aspx)。

### SkImageGenerator 接口实现

```cpp
protected:
    sk_sp<const SkData> onRefEncodedData() override;
    bool onGetPixels(const SkImageInfo& info, void* pixels,
                     size_t rowBytes, const Options&) override;
```

## 内部实现细节

### 解码器初始化

`MakeFromEncodedWIC` 执行以下初始化流程：

#### 1. 创建 WIC 成像工厂

```cpp
SkTScopedComPtr<IWICImagingFactory> imagingFactory;
HRESULT hr = CoCreateInstance(
    CLSID_WICImagingFactory,        // WIC 工厂 CLSID
    nullptr,                         // 不使用聚合
    CLSCTX_INPROC_SERVER,           // 进程内服务器
    IID_PPV_ARGS(&imagingFactory)   // 接口 IID 和输出指针
);
```

注意：代码显式使用 `CLSID_WICImagingFactory`（Windows 7/Vista 版本），而非 Windows 8+ 的 `CLSID_WICImagingFactory2`，以兼容旧版本。

#### 2. 创建 IStream 适配器

```cpp
SkTScopedComPtr<IStream> iStream;
hr = SkIStream::CreateFromSkStream(
    std::make_unique<SkMemoryStream>(data),
    &iStream
);
```

`SkIStream` 将 Skia 的 `SkStream` 适配为 COM `IStream` 接口。

#### 3. 创建解码器

```cpp
SkTScopedComPtr<IWICBitmapDecoder> decoder;
hr = imagingFactory->CreateDecoderFromStream(
    iStream.get(),
    nullptr,                          // 不指定供应商
    WICDecodeMetadataCacheOnDemand,  // 按需加载元数据
    &decoder
);
```

#### 4. 提取第一帧

```cpp
SkTScopedComPtr<IWICBitmapFrameDecode> imageFrame;
hr = decoder->GetFrame(0, &imageFrame);  // 总是使用第一帧
```

#### 5. 查询 EXIF 方向

```cpp
SkEncodedOrigin origin = kDefault_SkEncodedOrigin;
SkTScopedComPtr<IWICMetadataQueryReader> queryReader;
hr = imageFrame->GetMetadataQueryReader(&queryReader);

if (SUCCEEDED(hr)) {
    // JPEG EXIF 策略路径
    PROPVARIANT propValue;
    PropVariantInit(&propValue);
    hr = queryReader->GetMetadataByName(L"/app1/ifd/{ushort=274}", &propValue);

    if (SUCCEEDED(hr) && propValue.vt == VT_UI2) {
        SkEncodedOrigin originValue = static_cast<SkEncodedOrigin>(propValue.uiVal);
        if (originValue >= kTopLeft_SkEncodedOrigin && originValue <= kLast_SkEncodedOrigin) {
            origin = originValue;
        }
    }
}
```

注意：
- BMP 和 ICO 不支持元数据，`GetMetadataQueryReader` 会失败（不影响解码）
- 查询路径 `/app1/ifd/{ushort=274}` 是 JPEG EXIF 方向标签的标准位置（TIFF Tag 274）

#### 6. 查询图像属性

```cpp
UINT width, height;
hr = imageSource->GetSize(&width, &height);

WICPixelFormatGUID format;
hr = imageSource->GetPixelFormat(&format);
```

#### 7. 确定透明度类型

根据 WIC 像素格式确定 `SkAlphaType`：

```cpp
SkAlphaType alphaType = kPremul_SkAlphaType;  // 默认预乘

// 不透明格式列表
if (GUID_WICPixelFormat16bppBGR555 == format ||
    GUID_WICPixelFormat16bppBGR565 == format ||
    GUID_WICPixelFormat24bppRGB == format ||
    GUID_WICPixelFormat24bppBGR == format ||
    GUID_WICPixelFormat32bppBGR == format ||
    GUID_WICPixelFormat8bppGray == format ||
    ... // 其他不透明格式
) {
    alphaType = kOpaque_SkAlphaType;
}
```

注意：索引格式（如 `GUID_WICPixelFormat8bppIndexed`）无法提前判断是否有透明度，保守返回 `kPremul`。

#### 8. 应用方向变换

```cpp
SkImageInfo info = SkImageInfo::MakeS32(width, height, alphaType);
if (SkEncodedOriginSwapsWidthHeight(origin)) {
    info = SkPixmapUtils::SwapWidthHeight(info);  // 旋转 90/270 度时交换宽高
}
```

### 像素格式转换

`onGetPixels` 方法执行实际解码和格式转换：

#### 1. 创建格式转换器

```cpp
SkTScopedComPtr<IWICFormatConverter> formatConverter;
HRESULT hr = fImagingFactory->CreateFormatConverter(&formatConverter);

// 选择目标格式
GUID format = GUID_WICPixelFormat32bppPBGRA;  // 预乘 BGRA（默认）
if (kUnpremul_SkAlphaType == info.alphaType()) {
    format = GUID_WICPixelFormat32bppBGRA;     // 非预乘 BGRA
}

// 初始化转换器
hr = formatConverter->Initialize(
    fImageSource.get(),           // 源位图
    format,                        // 目标格式
    WICBitmapDitherTypeNone,      // 不抖动
    nullptr,                       // 不使用调色板
    0.0,                          // Alpha 阈值（未使用）
    WICBitmapPaletteTypeCustom    // 自定义调色板类型
);
```

#### 2. 查询转换器接口

```cpp
SkTScopedComPtr<IWICBitmapSource> formatConverterSrc;
hr = formatConverter->QueryInterface(IID_PPV_ARGS(&formatConverterSrc));
```

#### 3. 解码并应用方向

```cpp
SkPixmap dst(info, pixels, rowBytes);

auto decode = [&formatConverterSrc](const SkPixmap& pm) {
    void* pixelsAddr = pm.writable_addr();
    size_t rowBytes = pm.rowBytes();
    const SkImageInfo& info = pm.info();

    // 拷贝像素数据
    HRESULT hr = formatConverterSrc->CopyPixels(
        nullptr,                              // 完整矩形
        (UINT)rowBytes,                       // 行字节数
        (UINT)(rowBytes * info.height()),    // 总字节数
        (BYTE*)pixelsAddr                     // 目标缓冲区
    );
    return SUCCEEDED(hr);
};

// 应用 EXIF 方向变换
return SkPixmapUtils::Orient(dst, fOrigin, decode);
```

`SkPixmapUtils::Orient` 处理以下情况：
- **kTopLeft_SkEncodedOrigin (1)**: 无变换
- **kTopRight_SkEncodedOrigin (2)**: 水平翻转
- **kBottomRight_SkEncodedOrigin (3)**: 旋转 180 度
- **kBottomLeft_SkEncodedOrigin (4)**: 垂直翻转
- **kLeftTop_SkEncodedOrigin (5)**: 旋转 90 度顺时针 + 垂直翻转
- **kRightTop_SkEncodedOrigin (6)**: 旋转 90 度顺时针
- **kRightBottom_SkEncodedOrigin (7)**: 旋转 90 度顺时针 + 水平翻转
- **kLeftBottom_SkEncodedOrigin (8)**: 旋转 90 度逆时针

### COM 兼容性处理

#### Windows 8 SDK 兼容

```cpp
// Windows 8 SDK 将 CLSID_WICImagingFactory #define 为 CLSID_WICImagingFactory2
// 撤销此定义以确保链接到预期的符号
#if defined(CLSID_WICImagingFactory)
    #undef CLSID_WICImagingFactory
#endif
```

#### COM 智能指针

`SkTScopedComPtr` 实现 RAII 风格的 COM 接口管理：

```cpp
template<typename T>
class SkTScopedComPtr {
    T* fPtr;
public:
    SkTScopedComPtr() : fPtr(nullptr) {}
    ~SkTScopedComPtr() {
        if (fPtr) {
            fPtr->Release();  // 自动释放引用
        }
    }
    T** operator&() { return &fPtr; }
    T* get() const { return fPtr; }
    T* release() {
        T* ptr = fPtr;
        fPtr = nullptr;
        return ptr;
    }
};
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| Windows Imaging Component (`<wincodec.h>`) | 图像解码和格式转换 |
| COM (Component Object Model) | Windows 对象模型基础 |
| `SkIStream` | SkStream 到 IStream 适配器 |
| `SkTScopedComPtr` | COM 智能指针 |
| `SkPixmapUtils` | 像素操作和方向变换 |
| `SkEncodedOrigin` | EXIF 方向枚举 |

### 被依赖的模块

该模块通过 SkCodec 框架被 SkImage、SkBitmap 等高层 API 使用，作为 Windows 平台优先的图像解码路径。

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `MakeFromEncodedWIC` 静态工厂方法
2. **适配器模式**: `SkIStream` 适配 SkStream 到 IStream
3. **RAII**: `SkTScopedComPtr` 自动管理 COM 对象生命周期
4. **策略模式**: 根据 SkAlphaType 选择不同的 WIC 像素格式

### 设计决策

1. **客户端 COM 初始化**: 将 COM 生命周期管理责任留给应用，避免与其他 COM 使用冲突
2. **第一帧解码**: 仅解码多帧图像的第一帧，简化实现
3. **按需元数据**: 使用 `WICDecodeMetadataCacheOnDemand` 减少内存占用
4. **格式转换器**: 利用 WIC 的格式转换器处理所有像素格式，无需手动实现
5. **EXIF 方向**: 在 Skia 层处理方向变换，而非在 WIC 层
6. **错误容忍**: 元数据查询失败不影响解码（BMP/ICO 兼容性）
7. **保守透明度**: 索引格式默认 `kPremul`，避免错误假设

### Windows 版本兼容

- **Windows Vista+**: 使用 `CLSID_WICImagingFactory`（WIC 1.0）
- **Windows 8+**: 避免自动升级到 `CLSID_WICImagingFactory2`，确保旧系统兼容
- **Windows 10+**: 自动利用新增的编解码器（如 HEIF）

## 性能考量

### 性能优势

1. **硬件加速**: WIC 可利用 GPU 和专用图像处理单元
2. **系统优化**: Windows 针对 WIC 进行了深度优化
3. **格式转换器**: WIC 的格式转换器比软件实现更快
4. **按需元数据**: 避免解析不需要的元数据
5. **零拷贝路径**: 某些格式可直接解码到目标缓冲区

### 内存优化

- **IStream 适配**: 避免复制编码数据到 Windows 内存
- **懒解码**: 仅在调用 `getPixels` 时执行解码
- **引用计数**: COM 自动管理对象生命周期

### 潜在瓶颈

1. **COM 开销**: 跨接口调用有一定开销
2. **格式转换**: 某些像素格式转换可能在 CPU 上执行
3. **元数据查询**: EXIF 解析需要额外时间
4. **首次解码**: 创建 WIC 对象和解码器有初始化成本

### 优化建议

- 复用 `IWICImagingFactory` 实例（线程安全）
- 缓存常用图像的解码结果
- 对于大图像考虑使用 WIC 的渐进式解码

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkImageGeneratorWIC.h` | 公共接口定义 |
| `src/ports/SkImageGeneratorWIC.cpp` | 实现文件（286 行）|
| `src/utils/win/SkIStream.h` | SkStream 到 IStream 适配器 |
| `src/utils/win/SkTScopedComPtr.h` | COM 智能指针 |
| `src/codec/SkPixmapUtilsPriv.h` | 像素操作工具 |
| `include/codec/SkEncodedOrigin.h` | EXIF 方向枚举 |
| `include/core/SkImageGenerator.h` | 图像生成器抽象基类 |
| Windows SDK `<wincodec.h>` | WIC API 定义 |
