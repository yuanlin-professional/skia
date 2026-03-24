# SkImageGenerator

> 源文件
> - include/core/SkImageGenerator.h
> - src/core/SkImageGenerator.cpp

## 概述

`SkImageGenerator` 是 Skia 中用于延迟解码图像的抽象基类。它提供了一个统一的接口来从各种来源(文件、内存、网络等)生成像素数据,而不需要立即解码整个图像。这种设计支持按需解码、部分解码和 YUV 平面解码等高级功能,是 Skia 图像加载和解码系统的核心抽象。

该类被 `SkImage` 和 `SkPixelRef` 使用,允许图像在实际需要像素数据之前延迟解码,从而优化内存使用和加载性能。

## 架构位置

`SkImageGenerator` 在 Skia 图像管道中的位置:

```
应用层 (SkImage::MakeFromEncoded())
    ↓
SkImageGenerator (抽象接口)
    ↓ (具体实现)
SkCodecImageGenerator / SkPictureImageGenerator / ...
    ↓
SkCodec / SkPicture / 其他数据源
    ↓
解码后的像素数据
```

它是连接高层图像 API 和底层解码器的关键抽象层。

## 主要类与结构体

### SkImageGenerator

**继承关系:**
- 抽象基类,定义虚函数接口

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fInfo | const SkImageInfo | 图像信息(只读) |
| fUniqueID | const uint32_t | 唯一标识符 |

**关键虚函数:**

| 方法 | 说明 |
|------|------|
| onRefEncodedData() | 返回编码数据(可选) |
| onGetPixels() | 解码为 RGBA 像素 |
| onQueryYUVAInfo() | 查询 YUVA 解码支持 |
| onGetYUVAPlanes() | 解码为 YUVA 平面 |
| onIsValid() | 验证是否可用于特定上下文 |
| onIsProtected() | 是否为受保护内容 |

## 公共 API 函数

### 构造和析构

```cpp
SkImageGenerator(const SkImageInfo& info, uint32_t uniqueId = kNeedNewImageUniqueID);
virtual ~SkImageGenerator();
```

**说明:**
- 构造函数是 protected,只能通过子类创建
- uniqueId 可以指定或自动生成(通过 `SkNextID::ImageID()`)

### uniqueID

```cpp
uint32_t uniqueID() const;
```

**功能:** 返回生成器的唯一标识符。

**用途:** 缓存键、调试标识等。

### refEncodedData

```cpp
sk_sp<const SkData> refEncodedData();
```

**功能:** 获取原始编码数据(如 JPEG、PNG 字节)。

**返回值:**
- 如果可用,返回编码数据的智能指针
- 如果不可用或已解码,返回 nullptr

**用途:** 序列化、保存文件、网络传输等。

### getInfo

```cpp
const SkImageInfo& getInfo() const;
```

**功能:** 返回图像的 SkImageInfo(宽度、高度、颜色类型等)。

### isValid

```cpp
bool isValid(SkRecorder* recorder) const;
```

**功能:** 检查生成器是否可用于特定的 recorder(或 CPU,如果 recorder 为 nullptr)。

**用途:** GPU 资源验证、上下文兼容性检查。

### isProtected

```cpp
bool isProtected() const;
```

**功能:** 检查内容是否受 DRM 保护。

**返回值:** 如果内容受保护,返回 true。

### getPixels

```cpp
bool getPixels(const SkImageInfo& info, void* pixels, size_t rowBytes);
bool getPixels(const SkPixmap& pm);
```

**功能:** 解码图像为指定格式的像素数据。

**参数:**
- `info`: 目标像素格式(可以与 getInfo() 不同,表示请求转换)
- `pixels`: 输出缓冲区
- `rowBytes`: 每行字节数(必须 >= info.minRowBytes())

**返回值:**
- true: 解码成功
- false: 解码失败(不支持的格式、内存不足等)

**特性:**
- 支持格式转换(如 RGBA → BGRA)
- 支持缩放(如果 info.dimensions() 与 getInfo().dimensions() 不同)
- 重复调用应返回相同结果(幂等性)

### queryYUVAInfo

```cpp
bool queryYUVAInfo(const SkYUVAPixmapInfo::SupportedDataTypes& supportedDataTypes,
                   SkYUVAPixmapInfo* yuvaPixmapInfo) const;
```

**功能:** 查询是否支持 YUVA 解码,以及 YUVA 平面配置。

**参数:**
- `supportedDataTypes`: 调用者支持的数据类型(如 uint8, uint16, float)
- `yuvaPixmapInfo`: 输出参数,返回 YUVA 配置

**返回值:**
- true: 支持 YUVA 解码,且与 supportedDataTypes 兼容
- false: 不支持或不兼容

**用途:** 视频解码、YUV 纹理上传等。

### getYUVAPlanes

```cpp
bool getYUVAPlanes(const SkYUVAPixmaps& yuvaPixmaps);
```

**功能:** 解码为 YUVA 平面数据。

**参数:**
- `yuvaPixmaps`: 预分配的 YUVA 平面缓冲区(配置必须与 queryYUVAInfo() 返回的一致)

**返回值:**
- true: 解码成功
- false: 解码失败

**注意:** 这是完整解码,不是部分解码。要获取配置而不解码,使用 queryYUVAInfo()。

### isTextureGenerator

```cpp
virtual bool isTextureGenerator() const;
```

**功能:** 检查是否为纹理生成器(直接生成 GPU 纹理而不是 CPU 像素)。

**默认实现:** 返回 false。

**用途:** GPU 路径优化。

## 内部实现细节

### 构造函数实现

```cpp
SkImageGenerator::SkImageGenerator(const SkImageInfo& info, uint32_t uniqueID)
    : fInfo(info)
    , fUniqueID(kNeedNewImageUniqueID == uniqueID ? SkNextID::ImageID() : uniqueID)
{}
```

**uniqueID 生成逻辑:**
- 如果传入 `kNeedNewImageUniqueID`(值为 0),自动生成新 ID
- 否则使用传入的 ID

### getPixels 实现

```cpp
bool SkImageGenerator::getPixels(const SkImageInfo& info, void* pixels, size_t rowBytes) {
    if (kUnknown_SkColorType == info.colorType()) {
        return false;  // 不支持未知颜色类型
    }
    if (nullptr == pixels) {
        return false;  // 无效缓冲区
    }
    if (rowBytes < info.minRowBytes()) {
        return false;  // rowBytes 太小
    }

    Options defaultOpts;
    return this->onGetPixels(info, pixels, rowBytes, defaultOpts);
}
```

**验证步骤:**
1. 颜色类型检查
2. 缓冲区指针检查
3. rowBytes 大小检查
4. 委托给虚函数 `onGetPixels()`

### queryYUVAInfo 实现

```cpp
bool SkImageGenerator::queryYUVAInfo(
        const SkYUVAPixmapInfo::SupportedDataTypes& supportedDataTypes,
        SkYUVAPixmapInfo* yuvaPixmapInfo) const {
    SkASSERT(yuvaPixmapInfo);

    return this->onQueryYUVAInfo(supportedDataTypes, yuvaPixmapInfo) &&
           yuvaPixmapInfo->isSupported(supportedDataTypes);
}
```

**双重验证:**
1. 调用虚函数 `onQueryYUVAInfo()`
2. 再次验证返回的配置是否被 supportedDataTypes 支持

**原因:** 防止子类返回无效或不兼容的配置。

### getYUVAPlanes 实现

```cpp
bool SkImageGenerator::getYUVAPlanes(const SkYUVAPixmaps& yuvaPixmaps) {
    return this->onGetYUVAPlanes(yuvaPixmaps);
}
```

简单委托给虚函数。

### 默认虚函数实现

所有虚函数都有默认实现:

```cpp
virtual sk_sp<const SkData> onRefEncodedData() { return nullptr; }
virtual bool onGetPixels(const SkImageInfo&, void*, size_t, const Options&) { return false; }
virtual bool onIsValid(SkRecorder*) const { return true; }
virtual bool onIsProtected() const { return false; }
virtual bool onQueryYUVAInfo(const SkYUVAPixmapInfo::SupportedDataTypes&,
                             SkYUVAPixmapInfo*) const { return false; }
virtual bool onGetYUVAPlanes(const SkYUVAPixmaps&) { return false; }
```

**设计理由:** 允许子类只实现需要的功能。

### Options 结构体

```cpp
struct Options {};
```

**当前状态:** 空结构体,预留用于未来扩展。

**历史:** 可能曾经包含解码选项(如采样率、区域解码等)。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkImageInfo | 图像格式描述 |
| SkData | 编码数据存储 |
| SkPixmap | 像素映射 |
| SkYUVAPixmaps | YUVA 平面数据 |
| SkRefCnt | 引用计数 |
| SkNextID | 唯一 ID 生成 |
| SkRecorder | 上下文验证 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkImage | 延迟解码实现 |
| SkPixelRef | 位图后端 |
| SkCodecImageGenerator | 编解码器适配器 |
| SkPictureImageGenerator | Picture 渲染生成器 |
| SkBitmap | 延迟位图 |

## 设计模式与设计决策

### 模板方法模式

`SkImageGenerator` 使用模板方法模式:
- **公共方法:** 提供统一接口和验证逻辑
- **虚函数:** 子类实现具体行为

**示例:**
```cpp
// 公共方法(模板)
bool getPixels(...) {
    // 验证参数
    if (...) return false;
    // 调用虚函数
    return onGetPixels(...);
}

// 虚函数(待实现)
virtual bool onGetPixels(...) = 0;
```

### 策略模式

不同的 SkImageGenerator 子类提供不同的解码策略:
- **SkCodecImageGenerator:** 从编码数据(JPEG, PNG 等)解码
- **SkPictureImageGenerator:** 从 SkPicture 渲染
- **SkTextureImageGenerator:** 直接提供 GPU 纹理

**优势:** 高层代码(如 SkImage)不需要知道具体解码策略。

### 延迟加载设计

核心设计理念:
- **构造时:** 只存储 SkImageInfo,不解码像素
- **使用时:** 调用 getPixels() 时才解码
- **缓存:** 由调用者(如 SkImage)决定是否缓存解码结果

**优势:**
- 减少内存占用
- 加快图像对象创建
- 支持按需解码

### 不可拷贝设计

```cpp
SkImageGenerator(SkImageGenerator&&) = delete;
SkImageGenerator(const SkImageGenerator&) = delete;
SkImageGenerator& operator=(SkImageGenerator&&) = delete;
SkImageGenerator& operator=(const SkImageGenerator&) = delete;
```

**原因:**
- 生成器通常包含状态(如文件句柄、解码器状态)
- 拷贝语义不明确(深拷贝还是共享状态?)
- 通过智能指针管理生命周期更合适

### YUVA 支持设计

提供单独的 YUVA 接口:
- **queryYUVAInfo():** 查询能力,无开销
- **getYUVAPlanes():** 实际解码

**设计理由:**
1. YUVA 解码比 RGBA 复杂(多个平面、不同采样率)
2. 需要预先分配缓冲区
3. 分离查询和解码,允许调用者做更好的资源规划

## 性能考量

### 延迟解码

最大的性能优势:
- **内存:** 未使用的图像不占用解码后的内存
- **加载速度:** 图像列表加载更快(只读取元数据)
- **选择性解码:** 只解码可见的图像

### 重复调用开销

getPixels() 应该是幂等的:
```cpp
// 重复调用应返回相同结果
generator->getPixels(info, pixels1, rowBytes);
generator->getPixels(info, pixels2, rowBytes);
// pixels1 和 pixels2 应该相同
```

**实现策略:**
- **每次解码:** 简单但慢(如 SkCodecImageGenerator)
- **内部缓存:** 快但占内存
- **无状态:** 从不可变的编码数据解码(最常见)

### YUVA 解码优化

对于视频和某些图像格式,YUVA 解码更高效:
- **带宽:** YUV 占用更少内存(色度子采样)
- **GPU 上传:** 现代 GPU 原生支持 YUV 纹理
- **解码速度:** 某些解码器直接输出 YUV

### uniqueID 用于缓存

uniqueID 可以作为缓存键:
```cpp
std::unordered_map<uint32_t, sk_sp<SkImage>> cache;
uint32_t id = generator->uniqueID();
if (cache.find(id) != cache.end()) {
    return cache[id];  // 命中缓存
}
```

避免重复解码相同的图像。

### 编码数据引用

refEncodedData() 返回 sk_sp,使用引用计数:
- **优势:** 多个对象可以共享编码数据
- **开销:** 原子操作增减引用计数

**权衡:** 编码数据通常较大,共享优于拷贝。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkImageInfo.h | 依赖 | 图像格式描述 |
| include/core/SkData.h | 依赖 | 编码数据 |
| include/core/SkPixmap.h | 依赖 | 像素映射 |
| include/core/SkYUVAPixmaps.h | 依赖 | YUVA 平面 |
| src/core/SkNextID.h | 依赖 | 唯一 ID 生成 |
| include/core/SkImage.h | 使用者 | 延迟图像 |
| src/core/SkPixelRef.h | 使用者 | 位图后端 |
| src/codec/SkCodecImageGenerator.h | 子类 | 编解码器适配器 |
| src/core/SkPictureImageGenerator.h | 子类 | Picture 渲染 |
