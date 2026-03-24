# UrlDataManager

> 源文件
> - tools/UrlDataManager.h
> - tools/UrlDataManager.cpp

## 概述

`UrlDataManager` 是一个用于管理和缓存数据资源的工具类，主要用于 Skia 的调试和可视化工具中。它负责将二进制数据（如图像、字体等）映射到唯一的 URL 地址，并提供双向查找功能。该类通过哈希机制确保数据的唯一性，避免重复存储相同的数据。此外，它还提供了专门的图像索引功能，用于支持 WASM 调试器中的 MSKP 动画。

这个类的核心功能包括：数据去重存储、URL 生成与映射、反向 URL 查找，以及针对图像资源的特殊索引管理。它在 Skia 的 Web 调试工具和 SkiaDebugger 等场景中扮演着重要角色。

## 架构位置

`UrlDataManager` 位于 Skia 项目的 `tools/` 目录下，属于工具层的辅助类，而非核心渲染引擎的一部分。它主要服务于以下场景：

1. **SkiaDebugger**：用于调试和可视化 Skia 绘图命令时，将数据资源映射为可访问的 URL
2. **WASM 调试器**：在 WebAssembly 环境中，用于管理 MSKP（Multi-frame SKP）文件中的图像资源
3. **Web 工具**：为基于 Web 的 Skia 工具提供数据服务能力

该类依赖于 Skia 的核心数据结构（`SkData`、`SkImage`、`SkString`）和内部工具（`SkChecksum`、`SkTDynamicHash`），但不参与实际的图形渲染流程。

## 主要类与结构体

### UrlDataManager

主类，负责整体的数据管理和 URL 映射。

**关键成员变量：**
- `SkString fRootUrl`：根 URL 路径，所有生成的 URL 都基于此路径
- `SkTDynamicHash<UrlData, SkData, LookupTrait> fCache`：基于数据内容的哈希表，用于数据去重
- `SkTDynamicHash<UrlData, SkString, ReverseLookupTrait> fUrlLookup`：基于 URL 的反向查找表
- `uint32_t fDataId`：递增的数据 ID 计数器，用于生成唯一 URL
- `std::unordered_map<const SkImage*, int> imageMap`：图像指针到索引的映射表

### UrlData

内部数据结构，继承自 `SkRefCnt`，表示一个被管理的数据资源。

**成员变量：**
- `SkString fUrl`：资源的 URL 地址
- `SkString fContentType`：资源的内容类型（如 "image/png"）
- `sk_sp<SkData> fData`：实际的数据内容

### LookupTrait

用于 `fCache` 的哈希表特征定义，基于 `SkData` 内容计算哈希值。

**关键方法：**
- `GetKey()`：从 `UrlData` 中提取 `SkData` 作为键
- `Hash()`：使用 `SkChecksum::Hash32` 计算数据内容的哈希值

### ReverseLookupTrait

用于 `fUrlLookup` 的哈希表特征定义，基于 URL 字符串计算哈希值。

**关键方法：**
- `GetKey()`：从 `UrlData` 中提取 URL 字符串作为键
- `Hash()`：使用 `SkChecksum::Hash32` 计算 URL 字符串的哈希值

## 公共 API 函数

### 构造函数与析构函数

```cpp
explicit UrlDataManager(SkString rootUrl);
~UrlDataManager() { this->reset(); }
```

构造函数接受一个根 URL 路径，初始化 `fDataId` 为 0。析构函数调用 `reset()` 清理所有缓存数据。

### addData

```cpp
SkString addData(SkData* data, const char* contentType);
```

添加数据到缓存，并返回生成的 URL。如果相同内容的数据已存在，则返回已有的 URL，否则创建新的 `UrlData` 对象并生成唯一 URL。

**参数：**
- `data`：要添加的数据内容
- `contentType`：数据的 MIME 类型

**返回值：** 数据对应的 URL 字符串

### getDataFromUrl

```cpp
UrlData* getDataFromUrl(const SkString& url);
```

根据 URL 查找对应的 `UrlData` 对象。

**参数：**
- `url`：要查询的 URL 字符串

**返回值：** 对应的 `UrlData` 指针，如果未找到则返回 `nullptr`

### reset

```cpp
void reset();
```

清空所有缓存数据，释放 `UrlData` 对象的引用计数，并重置哈希表。

### indexImages

```cpp
void indexImages(const std::vector<sk_sp<SkImage>>& images);
```

从图像列表构建索引，主要用于 WASM 调试器中 MSKP 动画的场景。该方法只应调用一次。

**参数：**
- `images`：图像对象的向量，通常来自 MSKP 文件

### hasImageIndex

```cpp
bool hasImageIndex();
```

检查是否已初始化图像索引。

**返回值：** 如果 `imageMap` 非空则返回 `true`

### lookupImage

```cpp
int lookupImage(const SkImage* im);
```

查找图像在原始列表中的索引位置。

**参数：**
- `im`：要查找的图像指针

**返回值：** 图像的索引值，如果未找到则返回 -1

## 内部实现细节

### 数据去重机制

`UrlDataManager` 使用双哈希表结构实现高效的数据管理：

1. **fCache**：以数据内容的哈希值为键，用于检测重复数据
2. **fUrlLookup**：以 URL 字符串的哈希值为键，用于反向查找

当调用 `addData()` 时，首先在 `fCache` 中查找是否已存在相同内容的数据：
- 如果存在，直接返回已有的 URL
- 如果不存在，创建新的 `UrlData` 对象，生成形式为 `{rootUrl}/{dataId}` 的 URL，并同时添加到两个哈希表中

### URL 生成策略

URL 采用简单的递增 ID 方式生成：
```cpp
urlData->fUrl.appendf("%s/%u", fRootUrl.c_str(), fDataId++);
```

这种方式确保每个 URL 都是唯一的，但相同内容的数据会共享同一个 URL。

### 图像索引机制

图像索引功能使用 `std::unordered_map` 将图像指针映射到其在原始列表中的位置：

```cpp
void UrlDataManager::indexImages(const std::vector<sk_sp<SkImage>>& images) {
    SkASSERT(imageMap.empty());  // 确保只初始化一次
    for (size_t i = 0; i < images.size(); ++i) {
        imageMap.insert({images[i].get(), i});
    }
}
```

这个索引主要用于 WASM 环境中的 MSKP 播放，允许通过图像指针快速获取其文件 ID，避免在序列化命令时重复传输图像数据。

### 内存管理

`UrlData` 继承自 `SkRefCnt`，使用引用计数管理内存。在 `reset()` 方法中，遍历 `fCache` 并调用 `unref()` 释放所有 `UrlData` 对象：

```cpp
void UrlDataManager::reset() {
    fCache.foreach([&](UrlData* urlData) {
        urlData->unref();
    });
    fCache.rewind();
}
```

注意 `fUrlLookup` 不需要单独清理，因为它引用的是 `fCache` 中相同的 `UrlData` 对象。

## 依赖关系

### 直接依赖

- **SkData**：Skia 的二进制数据容器，用于存储资源内容
- **SkImage**：Skia 的图像对象，用于图像索引功能
- **SkString**：Skia 的字符串类，用于 URL 和内容类型的存储
- **SkChecksum**：Skia 的校验和工具，用于计算哈希值
- **SkTDynamicHash**：Skia 的动态哈希表模板，用于高效的键值查找

### 标准库依赖

- **std::unordered_map**：用于图像指针到索引的映射
- **std::vector**：用于接受图像列表参数

### 被依赖

该类主要被以下工具使用：
- SkiaDebugger 相关工具
- WASM 调试器
- SkPicture 可视化工具
- 命令行调试工具（如 skiaserve）

## 设计模式与设计决策

### 双向映射模式

通过维护两个哈希表（`fCache` 和 `fUrlLookup`）实现数据内容到 URL 的双向映射，支持：
- 正向查询：根据数据内容查找 URL（数据去重）
- 反向查询：根据 URL 获取数据内容（服务请求）

这种设计在增加少量内存开销的前提下，大幅提升了查询效率。

### 哈希去重策略

使用数据内容的哈希值作为唯一性判断依据，避免存储重复数据。这在处理大量相同资源（如重复使用的图像）时能显著节省内存和传输带宽。

### 引用计数内存管理

`UrlData` 使用 Skia 的引用计数机制（`SkRefCnt`），确保对象在被多个地方引用时不会提前释放，避免悬空指针问题。

### 特殊化图像处理

针对 WASM 调试器的特殊需求，提供了专门的图像索引功能。这个设计体现了"接口隔离原则"——将通用的数据管理与特定场景的图像管理分离，但在同一个类中统一提供。

### URL 生成的简单性

采用简单的递增 ID 生成 URL，而不是基于内容的哈希或复杂的命名规则。这种设计牺牲了 URL 的可读性，但换来了：
- 实现简单，性能高
- URL 长度固定且较短
- 避免哈希冲突的处理复杂性

## 性能考量

### 哈希查找效率

使用 `SkTDynamicHash` 提供 O(1) 的平均查找时间复杂度，适合需要频繁查询的场景。`SkChecksum::Hash32` 是一个高效的哈希函数，能够快速计算数据内容的哈希值。

### 内存开销

每个 `UrlData` 对象需要存储：
- 数据内容的智能指针（`sk_sp<SkData>`）
- URL 字符串
- 内容类型字符串
- 引用计数

双哈希表设计会导致每个数据在两个表中各有一个指针，但相对于数据去重带来的收益，这个开销是可以接受的。

### 数据去重收益

通过哈希去重，避免存储重复数据，在典型的调试场景中（如多次绘制相同图像），能显著降低内存占用和网络传输量。

### 图像索引性能

使用 `std::unordered_map` 实现图像指针到索引的映射，提供 O(1) 的查找性能。由于只在初始化时构建一次索引，构建开销不是性能瓶颈。

### 适用场景限制

该类主要设计用于调试工具，而非高并发的生产环境。其线程安全性未明确保证，不适合多线程并发访问。

## 相关文件

### 核心依赖

- `include/core/SkData.h` - 二进制数据容器
- `include/core/SkImage.h` - 图像对象定义
- `include/core/SkString.h` - 字符串类
- `src/core/SkChecksum.h` - 哈希计算工具
- `src/core/SkTDynamicHash.h` - 动态哈希表模板

### 使用场景

- `tools/debugger/` - 调试器相关工具
- `tools/skiaserve/` - Web 服务工具
- `tools/viewer/` - 可视化查看器工具

### 相关工具类

- `SkPicture` - SKP 文件格式支持
- `SkMultiPictureDocument` - 多帧图片文档支持
- 各类调试命令序列化工具
