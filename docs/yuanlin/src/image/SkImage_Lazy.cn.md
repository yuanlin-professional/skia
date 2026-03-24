# SkImage_Lazy

> 源文件：src/image/SkImage_Lazy.h, src/image/SkImage_Lazy.cpp

## 概述

`SkImage_Lazy` 是 Skia 图像系统中的延迟加载图像实现。它通过 `SkImageGenerator` 按需生成像素数据，而非立即解码整个图像。这种设计在处理大型图像或编码图像时可以显著减少内存占用和初始化时间。该类是 `SkImage_Base` 的派生类，提供了延迟解码、缓存管理、颜色空间转换和 YUVA 平面支持等核心功能。

`SharedGenerator` 类作为辅助结构，通过引用计数和互斥锁实现了多个 `SkImage_Lazy` 实例共享同一个 `SkImageGenerator` 的能力，这对于从同一源创建多个图像变体（如不同颜色空间）时尤为重要。

## 架构位置

`SkImage_Lazy` 位于 Skia 图像层次结构的核心位置：

- **继承关系**：继承自 `SkImage_Base`，后者是所有内部图像实现的基类
- **所属模块**：`src/image/` 模块，与 `SkImage_Raster`、`SkImage_Picture` 等其他图像实现平级
- **生成器层**：依赖 `SkImageGenerator` 接口作为像素数据源
- **缓存层**：通过 `SkBitmapCache` 和 `SkYUVPlanesCache` 与资源缓存系统集成
- **API 接口**：通过 `SkImages::DeferredFromGenerator()` 工厂函数对外暴露

在图像生命周期中，`SkImage_Lazy` 负责管理从编码数据到解码像素的转换过程，采用延迟策略以优化性能。

## 主要类与结构体

### SkImage_Lazy

延迟加载图像的主体实现类。

**关键成员**：
- `fSharedGenerator`：共享的图像生成器智能指针
- `fOnMakeColorTypeAndSpaceMutex`：保护颜色空间转换缓存的互斥锁
- `fOnMakeColorTypeAndSpaceResult`：缓存上次颜色空间转换结果
- `fUniqueIDListeners`：唯一 ID 变化监听器列表，用于通知纹理缓存失效

**核心方法**：
- `getROPixels()`：获取只读像素数据，支持缓存策略
- `onReadPixels()`：实现像素读取接口
- `onRefEncoded()`：返回原始编码数据
- `makeColorTypeAndColorSpace()`：创建不同颜色类型/空间的图像变体
- `getPlanes()`：获取 YUVA 平面数据

### Validator

嵌套结构体，用于验证和配置 `SkImage_Lazy` 构造参数。

**成员**：
- `fSharedGenerator`：验证后的生成器
- `fInfo`：最终的图像信息（可能经过颜色空间调整）
- `fColorSpace`：目标颜色空间
- `fUniqueID`：图像唯一标识符

构造函数处理颜色类型和颜色空间的转换逻辑，如果需要转换则生成新的唯一 ID。

### SharedGenerator

引用计数的生成器共享包装类。

**成员**：
- `fGenerator`：包装的 `SkImageGenerator` 实例
- `fMutex`：保护生成器访问的互斥锁

**方法**：
- `Make()`：静态工厂函数
- `getInfo()`：线程安全地获取图像信息
- `isTextureGenerator()`：检查是否为纹理生成器

通过互斥锁确保多线程环境下生成器的安全访问。

### ScopedGenerator

私有内部类，提供 RAII 风格的生成器访问。

自动获取和释放 `SharedGenerator` 的互斥锁，通过 `operator->()` 和转换操作符提供透明访问。

## 公共 API 函数

### SkImages::DeferredFromGenerator

```cpp
sk_sp<SkImage> DeferredFromGenerator(std::unique_ptr<SkImageGenerator> generator)
```

工厂函数，从 `SkImageGenerator` 创建延迟加载图像。这是创建 `SkImage_Lazy` 的标准方式。

### 核心图像操作

**isValid()**
```cpp
bool isValid(SkRecorder* recorder) const override
```
检查图像是否有效，委托给底层生成器。

**onReadPixels()**
```cpp
bool onReadPixels(GrDirectContext* dContext, const SkImageInfo& dstInfo,
                  void* dstPixels, size_t dstRB, int srcX, int srcY,
                  CachingHint chint) const override
```
读取像素数据到目标缓冲区，支持缓存提示。

**makeColorTypeAndColorSpace()**
```cpp
sk_sp<SkImage> makeColorTypeAndColorSpace(SkRecorder*, SkColorType targetColorType,
                                          sk_sp<SkColorSpace> targetColorSpace,
                                          RequiredProperties) const override
```
创建具有不同颜色类型和颜色空间的新图像，结果会被缓存以避免重复创建。

### 子集和表面操作

**onMakeSubset()**
```cpp
sk_sp<SkImage> onMakeSubset(SkRecorder*, const SkIRect& subset,
                            RequiredProperties) const override
```
创建图像子集，通过先转换为栅格图像再裁剪实现。

**onMakeSurface()**
```cpp
sk_sp<SkSurface> onMakeSurface(SkRecorder* recorder, const SkImageInfo& info) const override
```
创建兼容的绘制表面。

### YUVA 支持

**getPlanes()**
```cpp
sk_sp<SkCachedData> getPlanes(const SkYUVAPixmapInfo::SupportedDataTypes& supportedDataTypes,
                              SkYUVAPixmaps* pixmaps) const
```
获取 YUVA 平面数据，结果会缓存以提高性能。

## 内部实现细节

### 延迟加载机制

`SkImage_Lazy` 的核心设计是延迟像素生成。在构造时只保存 `SharedGenerator`，真正的像素解码发生在以下时机：

1. **首次像素访问**：调用 `getROPixels()` 或 `onReadPixels()` 时
2. **纹理上传**：GPU 渲染需要像素数据时
3. **YUVA 平面请求**：调用 `getPlanes()` 时

### 缓存策略

实现了两层缓存机制：

**位图缓存**（`SkBitmapCache`）：
```cpp
auto desc = SkBitmapCacheDesc::Make(this);
if (SkBitmapCache::Find(desc, bitmap)) {
    return true;  // 缓存命中
}
```

根据 `CachingHint` 参数决定是否缓存：
- `kAllow_CachingHint`：分配缓存记录并存储解码结果
- 其他：直接分配临时位图，不缓存

**YUVA 平面缓存**（`SkYUVPlanesCache`）：
```cpp
sk_sp<SkCachedData> data(SkYUVPlanesCache::FindAndRef(generator->uniqueID(), yuvaPixmaps));
```

使用生成器的唯一 ID 作为缓存键。

### 线程安全设计

多处使用互斥锁保证线程安全：

1. **生成器访问**：通过 `ScopedGenerator` 自动加锁
2. **颜色空间转换缓存**：`fOnMakeColorTypeAndSpaceMutex` 保护缓存结果
3. **共享生成器**：`SharedGenerator::fMutex` 保护生成器状态

### 像素读取流程

`getROPixels()` 实现了完整的像素获取逻辑：

```cpp
bool SkImage_Lazy::getROPixels(GrDirectContext* ctx, SkBitmap* bitmap,
                               SkImage::CachingHint chint) const {
    // 1. 检查缓存
    if (SkBitmapCache::Find(desc, bitmap)) {
        return true;
    }

    // 2. 根据缓存策略分配内存
    if (SkImage::kAllow_CachingHint == chint) {
        SkBitmapCache::RecPtr cacheRec = SkBitmapCache::Alloc(...);
        // 3. 尝试从生成器获取像素
        success = ScopedGenerator(fSharedGenerator)->getPixels(pmap);
        // 4. 失败则尝试代理读取（子类可重写）
        if (!success) success = this->readPixelsProxy(ctx, pmap);
        // 5. 添加到缓存
        SkBitmapCache::Add(std::move(cacheRec), bitmap);
    }
    // ...
}
```

### 唯一 ID 管理

`Validator` 构造函数中的逻辑确定图像唯一 ID：

```cpp
fUniqueID = fSharedGenerator->fGenerator->uniqueID();

if (colorType || colorSpace) {
    // 颜色类型或空间变化时生成新 ID
    fUniqueID = SkNextID::ImageID();
}
```

这保证了颜色空间转换后的图像拥有独立的缓存键。

### 颜色空间重解释

`onReinterpretColorSpace()` 采用非零拷贝策略：

```cpp
SkBitmap bitmap;
if (bitmap.tryAllocPixels(this->imageInfo().makeColorSpace(std::move(newCS)))) {
    SkPixmap pixmap = bitmap.pixmap();
    pixmap.setColorSpace(this->refColorSpace());  // 临时设置原始颜色空间
    if (ScopedGenerator(fSharedGenerator)->getPixels(pixmap)) {
        bitmap.setImmutable();
        return SkImages::RasterFromBitmap(bitmap);  // 转为栅格图像
    }
}
```

注释说明了理想实现应该克隆生成器并修改其颜色空间，但由于 API 限制采用了这种降级方案。

## 依赖关系

### 核心依赖

| 依赖项 | 用途 |
|--------|------|
| `SkImageGenerator` | 像素生成的抽象接口 |
| `SkImage_Base` | 基类，提供图像基础功能 |
| `SkBitmapCache` | 解码像素的缓存系统 |
| `SkYUVPlanesCache` | YUVA 平面数据缓存 |
| `SkResourceCache` | 底层资源缓存框架 |

### 次要依赖

| 依赖项 | 用途 |
|--------|------|
| `SkIDChangeListener` | 监听图像 ID 变化以失效缓存 |
| `SkNextID` | 生成唯一图像标识符 |
| `SkCachedData` | 缓存数据的包装类 |
| `SkRecorder` | 图形命令记录器 |
| `GrDirectContext` | GPU 上下文（可选） |

### 反向依赖

以下组件依赖 `SkImage_Lazy`：

- **编码图像工厂**：如 `SkImages::DeferredFromEncodedData()`
- **图像解码器**：通过生成器接入延迟加载系统
- **图像效果**：某些效果可能创建基于生成器的延迟图像

## 设计模式与设计决策

### 代理模式（Proxy Pattern）

`SkImage_Lazy` 是 `SkImageGenerator` 的代理，延迟实际的像素生成操作：

- **虚拟代理**：推迟开销大的解码操作直到真正需要
- **保护代理**：通过互斥锁保护生成器访问

### 享元模式（Flyweight Pattern）

`SharedGenerator` 实现了生成器共享：

```cpp
class SharedGenerator final : public SkNVRefCnt<SharedGenerator> {
    std::unique_ptr<SkImageGenerator> fGenerator;
    SkMutex fMutex;
};
```

多个 `SkImage_Lazy` 实例可以共享同一个生成器，减少内存占用。

### RAII 模式

`ScopedGenerator` 使用 RAII 管理互斥锁：

```cpp
class ScopedGenerator {
    const sk_sp<SharedGenerator>& fSharedGenerator;
    SkAutoMutexExclusive fAutoAcquire;  // 自动加锁/解锁
};
```

### 缓存模式

实现了结果缓存以避免重复计算：

1. **位图缓存**：缓存解码后的像素数据
2. **颜色空间转换缓存**：`fOnMakeColorTypeAndSpaceResult` 缓存上次转换结果
3. **YUVA 平面缓存**：缓存解码后的平面数据

### 设计决策

**决策 1：延迟解码而非立即解码**
- **原因**：大型图像或复杂编码格式解码开销大
- **权衡**：增加了代码复杂性，但显著降低内存和启动时间

**决策 2：生成器共享而非复制**
- **原因**：某些生成器（如编码图像）占用大量内存
- **权衡**：需要互斥锁保护，但节省了内存

**决策 3：缓存颜色空间转换结果**
- **原因**：`onMakeColorTypeAndColorSpace()` 可能被重复调用
- **权衡**：缓存单个结果而非多个（简化实现但可能错过某些命中）

**决策 4：子集操作转为栅格图像**
- **原因**：生成器接口不支持子集查询
- **权衡**：失去延迟加载优势，但简化了实现

**决策 5：颜色空间重解释降级为栅格**
- **原因**：生成器 API 是公共的且不支持克隆
- **权衡**：性能次优，但保证了正确性

## 性能考量

### 内存优化

1. **延迟分配**：构造时不分配像素内存，仅在需要时分配
2. **缓存控制**：通过 `CachingHint` 参数让调用者控制内存使用
3. **生成器共享**：避免重复保存编码数据

### 时间优化

1. **缓存查找**：先查找缓存再解码，避免重复工作
2. **结果缓存**：颜色空间转换结果缓存避免重复创建图像对象
3. **YUVA 缓存**：平面数据缓存避免重复解码

### 线程性能

1. **细粒度锁**：`ScopedGenerator` 只在访问生成器时持有锁
2. **分离锁**：颜色空间缓存使用独立互斥锁，减少竞争
3. **锁作用域最小化**：
```cpp
{   // make sure ScopedGenerator goes out of scope before we try readPixelsProxy
    success = ScopedGenerator(fSharedGenerator)->getPixels(pmap);
}
```

### 缓存失效

通过 `SkIDChangeListener` 机制通知依赖方缓存失效：

```cpp
void addUniqueIDListener(sk_sp<SkIDChangeListener> listener) const {
    fUniqueIDListeners.add(std::move(listener));
}
```

当 `SkImage_Lazy` 销毁时，自动通知所有监听器。

### 性能注意事项

1. **首次访问开销**：第一次 `getROPixels()` 会触发完整解码
2. **缓存未命中**：`kDisallow_CachingHint` 时每次都重新解码
3. **颜色空间转换**：`onReinterpretColorSpace()` 总是解码为栅格图像
4. **子集操作**：`onMakeSubset()` 需要完整解码再裁剪

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkImage.h` | 公共接口 | 定义 `SkImage` 公共 API |
| `src/image/SkImage_Base.h` | 基类 | 内部图像实现基类 |
| `include/core/SkImageGenerator.h` | 核心依赖 | 像素生成器接口 |
| `src/core/SkBitmapCache.h` | 缓存系统 | 位图缓存实现 |
| `src/core/SkYUVPlanesCache.h` | 缓存系统 | YUVA 平面缓存实现 |
| `src/image/SkImage_Raster.h` | 兄弟类 | 栅格图像实现 |
| `src/image/SkImage_Picture.h` | 兄弟类 | 基于 Picture 的图像实现 |
| `src/image/SkImage_LazyFactories.cpp` | 工厂函数 | 延迟图像工厂函数 |
| `include/private/SkIDChangeListener.h` | 通知机制 | ID 变化监听器 |
| `src/core/SkNextID.h` | ID 生成 | 唯一 ID 分配器 |
| `src/core/SkResourceCache.h` | 资源管理 | 底层缓存框架 |
| `include/core/SkYUVAPixmaps.h` | YUVA 支持 | YUVA 平面数据结构 |
