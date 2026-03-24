# GraphiteToolUtils

> 源文件
> - tools/graphite/GraphiteToolUtils.h
> - tools/graphite/GraphiteToolUtils.cpp

## 概述

GraphiteToolUtils 是 Skia Graphite 测试工具模块,提供用于测试的 Recorder 配置和图像管理功能。该模块的核心是 `TestingImageProvider`,一个基于 LRU 缓存的图像提供器,用于在测试环境中高效管理 GPU 纹理图像的创建和复用。

核心功能:
- 创建配置好的测试用 RecorderOptions
- 提供带缓存的 ImageProvider 实现
- 自动管理 CPU 图像到 GPU 纹理的转换
- 支持 mipmap 图像的智能缓存策略
- 使用 LRU 算法管理缓存容量

## 架构位置

```
skia/
├── include/
│   ├── core/
│   │   ├── SkImage.h              # 图像基类
│   │   ├── SkCanvas.h             # 画布接口
│   │   └── SkTiledImageUtils.h    # 图像键值生成工具
│   └── gpu/graphite/
│       ├── ImageProvider.h        # 图像提供器接口
│       ├── Recorder.h             # 记录器接口
│       └── Image.h                # Graphite 图像工具
├── src/core/
│   └── SkLRUCache.h               # LRU 缓存实现
└── tools/graphite/
    ├── GraphiteToolUtils.h        # 本模块头文件
    └── GraphiteToolUtils.cpp      # 本模块实现
```

在 Graphite 架构中:
- 实现 `ImageProvider` 接口,管理图像上传
- 配合 `Recorder` 使用,提供纹理图像
- 用于测试框架,不用于生产环境
- 每个 Recorder 通常拥有独立的 ImageProvider 实例

## 主要类与结构体

### TestingImageProvider
```cpp
class TestingImageProvider : public skgpu::graphite::ImageProvider
```
测试用的图像提供器,使用 LRU 缓存管理 GPU 纹理图像。

**主要成员**:
- `fCache`: LRU 缓存,存储 (ImageKey -> sk_sp<SkImage>) 映射
- `kDefaultNumCachedImages = 256`: 默认缓存容量

**核心方法**:
- `findOrCreate()`: 查找或创建 GPU 纹理图像

**特性**:
- 私有类,仅通过 `CreateTestingRecorderOptions()` 创建
- 线程隔离设计,每个 Recorder 使用独立实例

### ImageKey
```cpp
class ImageKey
```
图像缓存键,基于图像内容和属性生成唯一标识。

**主要成员**:
- `fValues[kNumValues]`: 键值数组
  - `fValues[0]`: 哈希值
  - `fValues[1..(n-2)]`: 图像内容键值
  - `fValues[n-1]`: mipmap 标志

**核心方法**:
- 构造函数: 生成键值
- `hash()`: 返回预计算的哈希值
- `operator==`: 比较键是否相等

### ImageHash
```cpp
struct ImageHash {
    size_t operator()(const ImageKey& key) const { return key.hash(); }
};
```
哈希函数对象,用于 LRU 缓存。

## 公共 API 函数

### CreateTestingRecorderOptions()
```cpp
skgpu::graphite::RecorderOptions CreateTestingRecorderOptions()
```
**功能**: 创建用于测试的 RecorderOptions 配置
**返回值**: 配置好的 RecorderOptions 对象

**行为**:
- 创建新的 `TestingImageProvider` 实例
- 将其设置为 RecorderOptions 的图像提供器
- 返回完整的选项对象

**用途**: 测试代码中创建 Recorder 时使用

## 内部实现细节

### 图像查找与创建流程
```cpp
sk_sp<SkImage> findOrCreate(
    skgpu::graphite::Recorder* recorder,
    const SkImage* image,
    SkImage::RequiredProperties requiredProps) {

    // 策略 1: 如果不要求 mipmap,先查找 mipmap 版本
    if (!requiredProps.fMipmapped) {
        ImageKey mipMappedKey(image, true);
        auto result = fCache.find(mipMappedKey);
        if (result) {
            return *result;  // 复用 mipmap 版本
        }
    }

    // 策略 2: 查找精确匹配的缓存
    ImageKey key(image, requiredProps.fMipmapped);
    auto result = fCache.find(key);
    if (result) {
        return *result;  // 缓存命中
    }

    // 策略 3: 创建新的 GPU 纹理
    sk_sp<SkImage> newImage = SkImages::TextureFromImage(
        recorder, image, requiredProps);
    if (!newImage) {
        return nullptr;  // 创建失败
    }

    // 策略 4: 插入缓存并返回
    result = fCache.insert(key, std::move(newImage));
    SkASSERT(result);
    return *result;
}
```

**智能 mipmap 策略**:
- 如果请求非 mipmap 图像,优先返回 mipmap 版本(如果存在)
- 理由: mipmap 图像可以用于非 mipmap 场景,反之不行
- 优势: 提高缓存利用率

### ImageKey 生成算法
```cpp
ImageKey(const SkImage* image, bool mipmapped) {
    uint32_t flags = mipmapped ? 0x1 : 0x0;

    // 获取图像内容相关的键值
    SkTiledImageUtils::GetImageKeyValues(image, &fValues[1]);

    // 存储 mipmap 标志
    fValues[kNumValues - 1] = flags;

    // 计算所有数据的哈希值
    fValues[0] = SkChecksum::Hash32(
        &fValues[1],
        (kNumValues - 1) * sizeof(uint32_t));
}
```

**设计特点**:
- 位置 0: 存储哈希值,支持快速比较
- 位置 1..(n-2): 图像内容键值
- 位置 n-1: 属性标志(mipmap)

**哈希预计算**:
- 构造时计算一次,多次查找时无需重新计算
- 减少哈希计算开销

### 键值比较优化
```cpp
bool operator==(const ImageKey& other) const {
    for (int i = 0; i < kNumValues; ++i) {
        if (fValues[i] != other.fValues[i]) {
            return false;  // 早期退出
        }
    }
    return true;
}
```
**优化点**:
- 首先比较哈希值(`fValues[0]`),不同则快速失败
- 然后逐个比较其他字段

### LRU 缓存特性
```cpp
SkLRUCache<ImageKey, sk_sp<SkImage>, ImageHash> fCache;
```
**容量**: 256 个图像

**淘汰策略**: 最近最少使用(LRU)
- 缓存满时,移除最久未访问的图像
- 自动释放 GPU 纹理内存

**查找复杂度**: O(1) 平均情况
**插入复杂度**: O(1) 平均情况

## 依赖关系

### Graphite 核心
- `skgpu::graphite::ImageProvider`: 图像提供器接口
- `skgpu::graphite::Recorder`: 记录器,用于创建 GPU 资源
- `skgpu::graphite::RecorderOptions`: 记录器配置选项

### Skia 核心
- `SkImage`: 图像基类
- `SkImages::TextureFromImage()`: CPU 图像转 GPU 纹理
- `SkTiledImageUtils::GetImageKeyValues()`: 图像键值生成

### 工具组件
- `SkLRUCache`: LRU 缓存容器
- `SkChecksum::Hash32()`: 哈希计算
- `sk_sp`: Skia 智能指针

## 设计模式与设计决策

### 策略模式
`TestingImageProvider` 是 `ImageProvider` 接口的一个测试实现:
- **接口**: `ImageProvider`
- **测试实现**: `TestingImageProvider`(本类)
- **其他实现**: 可能有应用特定的图像提供器

### 代理模式
`ImageProvider` 作为图像创建的代理:
- 隔离 CPU 图像和 GPU 纹理的创建细节
- 提供缓存层,避免重复上传

### 工厂方法模式
```cpp
skgpu::graphite::RecorderOptions CreateTestingRecorderOptions()
```
工厂函数,隐藏 `TestingImageProvider` 的创建细节。

### 缓存穿透保护
```cpp
if (!newImage) {
    return nullptr;  // 不缓存失败结果
}
```
**设计**: 仅缓存成功创建的图像
**理由**: 避免缓存 `nullptr`,下次请求时可以重试

### 键值预计算设计
```cpp
fValues[0] = SkChecksum::Hash32(...);  // 构造时计算
uint32_t hash() const { return fValues[0]; }  // 直接返回
```
**权衡**:
- **优势**: 查找时无需重新计算哈希
- **劣势**: 每个键多占用 4 字节

**适用场景**: 图像键会被多次查找。

### 线程隔离设计
```cpp
// 注释: Currently, we give each new Recorder its own ImageProvider.
// This means we don't have to deal w/ any threading issues.
```
**设计决策**: 每个 Recorder 独立的 ImageProvider
**优势**:
- 避免多线程同步开销
- 简化实现
**劣势**:
- 不同 Recorder 无法共享缓存
- 可能重复上传相同图像

**未来方向**: 注释提到可能测试单个 ImageProvider 多 Recorder 共享。

### Mipmap 优先级设计
非常巧妙的缓存策略:
```cpp
if (!requiredProps.fMipmapped) {
    // 优先查找 mipmap 版本
    auto result = fCache.find(mipMappedKey);
    if (result) {
        return *result;
    }
}
```
**原理**: mipmap 图像是非 mipmap 图像的超集
**收益**: 提高缓存命中率

## 性能考量

### 缓存容量选择
```cpp
static constexpr int kDefaultNumCachedImages = 256;
```
**256 的理由**:
- 中等大小,平衡内存和命中率
- 典型测试场景的图像数量 < 256

**内存估算**:
- 假设平均每个纹理 1MB
- 总内存占用约 256MB
- 测试环境可接受

### 哈希查找开销
```cpp
SkLRUCache<ImageKey, sk_sp<SkImage>, ImageHash> fCache;
```
**时间复杂度**: O(1) 平均,O(n) 最坏
**实际性能**: 哈希表负载因子低时接近 O(1)

### 键值比较优化
预计算哈希值的收益:
- **场景**: 哈希冲突时需要完整比较键
- **频率**: 低(好的哈希函数冲突率 < 1%)
- **收益**: 减少每次查找的计算

### GPU 上传开销
```cpp
sk_sp<SkImage> newImage = SkImages::TextureFromImage(recorder, image, requiredProps);
```
这是最昂贵的操作:
- 数据从 CPU 传输到 GPU
- GPU 端内存分配
- 可能的格式转换

**缓存的价值**: 避免这个开销。

### LRU 算法开销
`SkLRUCache` 维护访问顺序:
- 查找: 更新访问时间
- 插入: 可能淘汰最旧项
- 开销: 链表操作 O(1)

## 相关文件

### Graphite 接口
- `include/gpu/graphite/ImageProvider.h`: 图像提供器接口
- `include/gpu/graphite/Recorder.h`: 记录器接口
- `include/gpu/graphite/RecorderOptions.h`: 记录器选项
- `include/gpu/graphite/Image.h`: Graphite 图像工具

### Skia 核心
- `include/core/SkImage.h`: 图像基类
- `include/core/SkTiledImageUtils.h`: 图像键值生成
- `src/core/SkLRUCache.h`: LRU 缓存实现
- `src/core/SkChecksum.h`: 哈希工具

### 测试相关
- `tools/graphite/GraphiteTestContext.h`: 测试上下文
- `tests/`: 使用本模块的测试代码
- `gm/`: GM 测试可能使用本模块
