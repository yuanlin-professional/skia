# DDLPromiseImageHelper

> 源文件: tools/ganesh/DDLPromiseImageHelper.h, tools/ganesh/DDLPromiseImageHelper.cpp

## 概述

`DDLPromiseImageHelper` 是一个用于支持延迟显示列表(Deferred Display List, DDL)中图像处理的辅助类。它负责将 SkPicture 中的常规图像转换为 Promise Image,管理图像数据从 CPU 到 GPU 的上传过程,并协调多线程环境下的图像纹理生命周期管理。该类是 Skia 在 DDL 模式下实现高效图形渲染的关键组件,支持将绘制命令的记录与实际 GPU 执行分离。

Promise Image 是一种特殊的图像类型,它承诺在未来某个时刻提供实际的纹理数据。这种机制允许在多线程环境中提前记录绘制命令,而将实际的纹理创建和数据上传延迟到合适的时机执行。`DDLPromiseImageHelper` 封装了整个流程,包括图像数据的提取、去重、GPU 纹理的创建和生命周期管理。

## 架构位置

该类位于 Skia 工具层的 Ganesh 后端支持模块中:

```
skia/
  tools/
    ganesh/
      DDLPromiseImageHelper.h        # 类声明和内部结构定义
      DDLPromiseImageHelper.cpp      # 实现文件
```

`DDLPromiseImageHelper` 是测试和基准测试工具的一部分,主要用于验证 DDL 功能。它与以下模块协同工作:
- **src/gpu/ganesh/**: Ganesh GPU 后端核心实现
- **include/gpu/ganesh/**: Ganesh 公共 API
- **include/private/chromium/**: Chromium 特定的 Promise Image 接口
- **src/core/SkTaskGroup**: 任务并行化支持

## 主要类与结构体

### PromiseImageCallbackContext

```cpp
class PromiseImageCallbackContext : public SkRefCnt {
public:
    PromiseImageCallbackContext(GrDirectContext* direct, GrBackendFormat backendFormat);
    sk_sp<GrPromiseImageTexture> fulfill();
    void release();
    void wasAddedToImage();
    static sk_sp<GrPromiseImageTexture> PromiseImageFulfillProc(void* textureContext);
    static void PromiseImageReleaseProc(void* textureContext);

private:
    GrDirectContext* fContext;
    GrBackendFormat fBackendFormat;
    sk_sp<GrPromiseImageTexture> fPromiseImageTexture;
    int fNumImages;      // 使用此上下文的图像数量
    int fTotalFulfills;  // fulfill 调用总次数
    int fDoneCnt;        // 完成的图像数量
};
```

这是 Promise Image 的回调上下文,负责:
- 保存后端纹理引用
- 跟踪图像使用和完成状态
- 提供标准的 fulfill 和 release 回调函数
- 在所有图像完成时自动清理 GPU 纹理

### PromiseImageInfo

```cpp
class PromiseImageInfo {
public:
    PromiseImageInfo(int index, uint32_t originalUniqueID, const SkImageInfo& ii);

    bool isYUV() const;
    SkISize overallDimensions() const;
    const SkBitmap& baseLevel() const;
    std::unique_ptr<SkPixmap[]> normalMipLevels() const;
    int numMipLevels() const;

    void setMipLevels(const SkBitmap& baseLevel, std::unique_ptr<SkMipmap> mipLevels);
    void setYUVPlanes(SkYUVAPixmaps yuvaPixmaps);

private:
    const int fIndex;                      // 在数组中的索引
    const uint32_t fOriginalUniqueID;      // 原始图像 ID(用于去重)
    const SkImageInfo fImageInfo;          // 图像信息
    SkBitmap fBaseLevel;                   // 基础 mipmap 层级
    std::unique_ptr<SkMipmap> fMipLevels;  // mipmap 数据
    SkYUVAPixmaps fYUVAPixmaps;            // YUV 图像数据
    sk_sp<PromiseImageCallbackContext> fCallbackContexts[SkYUVAInfo::kMaxPlanes];
};
```

存储单个图像的所有相关信息:
- 支持普通 RGBA 图像和 YUV 格式图像
- 缓存 mipmap 层级数据
- 管理多个纹理平面(YUV 最多 4 个平面)
- 关联回调上下文以管理 GPU 资源

### DDLPromiseImageHelper

```cpp
class DDLPromiseImageHelper {
public:
    explicit DDLPromiseImageHelper(
        const SkYUVAPixmapInfo::SupportedDataTypes& supportedYUVADataTypes);

    sk_sp<SkPicture> recreateSKP(GrDirectContext*, SkPicture*);
    void uploadAllToGPU(SkTaskGroup*, GrDirectContext*);
    void deleteAllFromGPU(SkTaskGroup*, GrDirectContext*);
    void reset();

private:
    int findImage(SkImage* image) const;
    int addImage(SkImage* image);
    int findOrDefineImage(SkImage* image);
    void createCallbackContexts(GrDirectContext*);
    sk_sp<SkPicture> reinflateSKP(sk_sp<GrContextThreadSafeProxy>, const SkData*);
    static sk_sp<SkImage> CreatePromiseImages(const void*, size_t, void*);

    SkYUVAPixmapInfo::SupportedDataTypes fSupportedYUVADataTypes;
    skia_private::TArray<PromiseImageInfo> fImageInfo;
    skia_private::TArray<sk_sp<SkImage>> fPromiseImages;
};
```

## 公共 API 函数

### recreateSKP()

```cpp
sk_sp<SkPicture> recreateSKP(GrDirectContext* dContext, SkPicture* inputPicture);
```

将输入的 SkPicture 转换为使用 Promise Image 的新 SkPicture:
1. 序列化原始 SkPicture,提取所有图像并替换为索引
2. 创建每个图像的 PromiseImageCallbackContext
3. 反序列化时将索引替换为 Promise Image

**使用场景**: 在开始 DDL 记录之前调用,准备可以在多线程中使用的 picture

### uploadAllToGPU()

```cpp
void uploadAllToGPU(SkTaskGroup* taskGroup, GrDirectContext* direct);
```

将所有图像数据上传到 GPU:
- 支持可选的 `SkTaskGroup` 进行并行上传
- 为每个图像创建后端纹理
- 支持 mipmap 和 YUV 格式
- 可以在任务组中异步执行以提高性能

**注意**: 必须在 DDL 回放前调用,确保纹理资源就绪

### deleteAllFromGPU()

```cpp
void deleteAllFromGPU(SkTaskGroup* taskGroup, GrDirectContext* direct);
```

从 GPU 删除所有纹理资源:
- 销毁所有后端纹理
- 可以并行执行清理操作
- 通常在所有 DDL 回放完成后调用

### reset()

```cpp
void reset();
```

释放所有 CPU 端的图像引用:
- 清空 `fImageInfo` 和 `fPromiseImages` 数组
- 允许 `PromiseImageCallbackContext` 的引用计数归零
- 在 DDL 回放完成且不再需要重复回放时调用

## 内部实现细节

### 图像序列化与反序列化流程

**序列化阶段** (`recreateSKP`):
```cpp
SkSerialProcs procs;
procs.fImageProc = [](SkImage* image, void* ctx) -> SkSerialReturnType {
    auto helper = static_cast<DDLPromiseImageHelper*>(ctx);
    int id = helper->findOrDefineImage(image);
    return SkData::MakeWithCopy(&id, sizeof(id));
};
auto compressedPictureData = inputPicture->serialize(&procs);
```

将每个 `SkImage` 替换为其在 `fImageInfo` 数组中的整数索引。

**反序列化阶段** (`reinflateSKP`):
```cpp
SkDeserialProcs procs;
procs.fImageProc = CreatePromiseImages;
return SkPicture::MakeFromData(compressedPictureData, &procs);
```

将索引转换回 Promise Image,使用之前创建的回调上下文。

### 图像去重机制

```cpp
int DDLPromiseImageHelper::findImage(SkImage* image) const {
    for (int i = 0; i < fImageInfo.size(); ++i) {
        if (fImageInfo[i].originalUniqueID() == image->uniqueID()) {
            return i;
        }
    }
    return -1;
}
```

使用图像的 `uniqueID()` 进行去重,避免重复上传相同的图像数据。

### YUV 图像处理

对于 YUV 格式的图像:
```cpp
if (codec && codec->queryYUVAInfo(fSupportedYUVADataTypes, &yuvaInfo)) {
    auto yuvaPixmaps = SkYUVAPixmaps::Allocate(yuvaInfo);
    codec->getYUVAPlanes(yuvaPixmaps);
    newImageInfo.setYUVPlanes(std::move(yuvaPixmaps));
}
```

- 查询 codec 以获取 YUV 平面信息
- 分配并解码 YUV 平面数据
- 为每个平面创建独立的后端纹理
- 最多支持 4 个平面(Y, U, V, A)

### GPU 纹理创建

```cpp
static GrBackendTexture create_yuva_texture(GrDirectContext* direct,
                                            const SkPixmap& pm,
                                            int texIndex) {
    bool finishedBECreate = false;
    auto beTex = direct->createBackendTexture(
        pm, kTopLeft_GrSurfaceOrigin, GrRenderable::kNo, GrProtected::kNo,
        markFinished, &finishedBECreate, "CreateYuvaTexture");
    if (beTex.isValid()) {
        direct->submit();
        while (!finishedBECreate) {
            direct->checkAsyncWorkCompletion();
        }
    }
    return beTex;
}
```

使用异步创建机制,然后轮询等待完成。这种方式允许 GPU 在后台处理纹理上传。

### Mipmap 支持

```cpp
std::unique_ptr<SkPixmap[]> DDLPromiseImageHelper::PromiseImageInfo::normalMipLevels() const {
    std::unique_ptr<SkPixmap[]> pixmaps(new SkPixmap[this->numMipLevels()]);
    pixmaps[0] = fBaseLevel.pixmap();
    if (fMipLevels) {
        for (int i = 0; i < fMipLevels->countLevels(); ++i) {
            SkMipmap::Level mipLevel;
            fMipLevels->getLevel(i, &mipLevel);
            pixmaps[i+1] = mipLevel.fPixmap;
        }
    }
    return pixmaps;
}
```

构建完整的 mipmap 链,包括基础层级和所有 mip 层级,用于创建支持 mipmap 的纹理。

### 生命周期管理

```cpp
PromiseImageCallbackContext::~PromiseImageCallbackContext() {
    SkASSERT(fDoneCnt == fNumImages);
    SkASSERT(!fTotalFulfills || fDoneCnt);
    if (fPromiseImageTexture) {
        fContext->deleteBackendTexture(fPromiseImageTexture->backendTexture());
    }
}
```

当所有使用该纹理的 Promise Image 都调用了 release 回调后,引用计数归零,析构函数自动删除后端纹理。

## 依赖关系

**内部依赖**:
- `include/core/SkPicture.h`: Picture 序列化/反序列化
- `include/gpu/ganesh/GrDirectContext.h`: GPU 上下文管理
- `include/gpu/ganesh/GrYUVABackendTextures.h`: YUV 后端纹理支持
- `include/private/chromium/GrPromiseImageTexture.h`: Promise 纹理封装
- `src/core/SkMipmap.h`: Mipmap 生成和访问
- `src/core/SkTaskGroup.h`: 任务并行化

**外部依赖**:
- `SkCodecImageGenerator`: 图像解码和 YUV 查询
- `SkImage_GaneshYUVA`: YUV 图像的 Ganesh 实现
- `GrCaps`: GPU 能力查询

**数据流**:
```
原始 SkPicture
    ↓ (serialize)
SkData (图像 → 索引)
    ↓ (createCallbackContexts)
PromiseImageCallbackContext 创建
    ↓ (uploadAllToGPU)
GPU 后端纹理创建
    ↓ (reinflateSKP)
新 SkPicture (Promise Images)
    ↓ (DDL recording & playback)
图像使用
    ↓ (release callbacks)
资源清理
```

## 设计模式与设计决策

### 1. Promise Pattern

Promise Image 模式允许延迟纹理提供:
- **fulfill 回调**: 返回纹理引用,支持延迟创建
- **release 回调**: 通知图像不再使用,配合引用计数管理生命周期

**优势**: 解耦纹理创建与使用,支持多线程 DDL 记录

### 2. Resource Management Pattern

使用引用计数自动管理 GPU 资源:
```cpp
void PromiseImageCallbackContext::release() {
    ++fDoneCnt;
    SkASSERT(fDoneCnt <= fNumImages);
}
```

当 `fDoneCnt` 达到 `fNumImages` 且引用计数归零时,自动清理纹理。

### 3. Builder Pattern

分阶段构建 Promise Image 系统:
1. **收集阶段**: `recreateSKP` 提取图像信息
2. **准备阶段**: `createCallbackContexts` 创建上下文
3. **上传阶段**: `uploadAllToGPU` 创建纹理
4. **使用阶段**: DDL 记录和回放

### 4. Visitor Pattern

```cpp
procs.fImageProc = [](SkImage* image, void* ctx) -> SkSerialReturnType {
    // 访问每个图像并转换
};
```

使用 `SkSerialProcs` 在序列化过程中访问和转换所有图像。

### 5. 设计决策

**为何支持多平面纹理**:
YUV 格式需要多个纹理平面,每个平面独立上传和管理,提供更好的压缩比和性能。

**为何使用同步等待**:
```cpp
while (!finishedBECreate) {
    direct->checkAsyncWorkCompletion();
}
```
确保纹理在使用前完全就绪,避免竞态条件。

**为何分离上传和重置**:
允许多次回放 DDL 而无需重新上传纹理,提高性能。调用 `reset()` 释放 CPU 内存,但保留 GPU 纹理。

## 性能考量

### 1. 图像去重

```cpp
int findOrDefineImage(SkImage* image) {
    int preExistingID = this->findImage(image);
    if (preExistingID >= 0) {
        return preExistingID;
    }
    return this->addImage(image);
}
```

避免重复解码和上传相同图像,节省 CPU 和 GPU 内存。

### 2. 并行上传

```cpp
void uploadAllToGPU(SkTaskGroup* taskGroup, GrDirectContext* direct) {
    if (taskGroup) {
        for (int i = 0; i < fImageInfo.size(); ++i) {
            taskGroup->add([direct, info]() {
                CreateBETexturesForPromiseImage(direct, info);
            });
        }
    }
}
```

使用任务组并行化纹理创建,充分利用多核 CPU。

### 3. Mipmap 优化

```cpp
std::unique_ptr<SkMipmap> mipmaps(SkMipmap::Build(tmp.pixmap(), nullptr));
newImageInfo.setMipLevels(tmp, std::move(mipmaps));
```

预先生成 mipmap,避免运行时生成的开销,提高渲染质量和性能。

### 4. YUV 优化

优先使用 YUV 格式:
- 减少内存占用(色度采样)
- 避免 CPU 端的 YUV 到 RGB 转换
- 让 GPU 在采样时执行转换

### 5. 内存管理

```cpp
void reset() {
    fImageInfo.clear();
    fPromiseImages.clear();
}
```

及时释放 CPU 端缓存,在保留 GPU 纹理的同时减少内存压力。

### 6. 大图像处理

```cpp
if (maxDimension < std::max(baseLevel.width(), baseLevel.height())) {
    // 这将超出 GPU 限制,回退到 raster 图像
    continue;
}
```

检测超大图像并回退到 CPU 渲染,避免 GPU 限制导致的失败。

## 相关文件

**头文件**:
- `tools/ganesh/DDLPromiseImageHelper.h`: 类声明

**实现文件**:
- `tools/ganesh/DDLPromiseImageHelper.cpp`: 完整实现

**依赖的核心文件**:
- `include/gpu/ganesh/GrDirectContext.h`: GPU 上下文
- `include/gpu/ganesh/GrYUVABackendTextures.h`: YUV 纹理
- `include/private/chromium/GrPromiseImageTexture.h`: Promise 纹理
- `src/core/SkMipmap.h`: Mipmap 支持
- `src/core/SkTaskGroup.h`: 并行任务

**相关工具**:
- `tools/ganesh/DDLTileHelper.h/cpp`: 使用本类实现 DDL 分块渲染
- `tools/ganesh/TestContext.h/cpp`: 测试上下文基础设施

**测试文件**:
- `tests/DDLPromiseImageTest.cpp`: Promise Image 功能测试
- `tests/DDLSerializationTest.cpp`: 序列化测试
