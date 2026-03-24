# TextureInfo

> 源文件: include/gpu/graphite/TextureInfo.h, src/gpu/graphite/TextureInfo.cpp

## 概述

`TextureInfo` 是 Skia Graphite 中的后端无关纹理属性封装类。它将不同 GPU 后端（Metal、Vulkan、Dawn）的纹理属性统一抽象，使得代码可以在不引入特定后端编译依赖的情况下描述纹理特性。该类采用类型擦除技术存储后端特定数据，是 Graphite 跨平台纹理管理的核心抽象之一。

主要特性：
- 后端无关的纹理属性描述（不包含尺寸信息）
- 支持 Metal、Vulkan、Dawn 等多后端
- 使用类型擦除避免虚函数开销
- 提供纹理兼容性验证机制

## 架构位置

`TextureInfo` 在 Graphite 架构中处于底层抽象位置：

```
skgpu::graphite
├── BackendTexture (持有 TextureInfo + 尺寸)
├── TextureInfo (本模块 - 纹理属性描述)
│   ├── MtlTextureInfo (Metal 实现)
│   ├── DawnTextureInfo (Dawn 实现)
│   └── VulkanTextureInfo (Vulkan 实现)
├── TextureProxy (纹理代理)
└── Texture (实际纹理资源)
```

该类作为纹理描述的基础，被 `BackendTexture`、`TextureProxy`、`Image`、`Surface` 等多个上层组件使用。

## 主要类与结构体

### TextureInfo

后端无关的纹理信息封装类。

**继承关系**
- 无继承关系，使用组合和类型擦除实现多态

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBackend` | `BackendApi` | 后端 API 类型（Metal/Vulkan/Dawn） |
| `fData` | `AnyTextureInfoData` | 类型擦除的后端特定数据 |
| `fViewFormat` | `TextureFormat` | 纹理视图格式（缓存值） |
| `fProtected` | `Protected` | 是否为受保护内存 |

### TextureInfo::Data

后端特定数据的抽象基类（内部使用）。

**继承关系**
- 抽象基类
- 子类：`MtlTextureInfo::Data`、`DawnTextureInfo::Data`、`VulkanTextureInfo::Data`

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fSampleCount` | `SampleCount` | 多重采样数量 |
| `fMipmapped` | `Mipmapped` | 是否包含 mipmap |

## 公共 API 函数

**构造与赋值**
```cpp
TextureInfo();
TextureInfo(const TextureInfo&);
TextureInfo& operator=(const TextureInfo&);
~TextureInfo();
```
支持默认构造、拷贝和赋值，拷贝时会深拷贝后端数据。

**查询接口**
```cpp
bool isValid() const;
BackendApi backend() const;
Protected isProtected() const;
SampleCount sampleCount() const;
Mipmapped mipmapped() const;
```
提供纹理基本属性查询能力。

**兼容性检查**
```cpp
bool operator==(const TextureInfo& that) const;
bool operator!=(const TextureInfo& that) const;
bool canBeFulfilledBy(const TextureInfo& that) const;
```
支持精确相等比较和兼容性验证，用于 Promise Image 等场景。

**调试支持**
```cpp
SkString toString() const;
```
生成包含所有属性的调试字符串。

## 内部实现细节

### 类型擦除机制

使用 `SkAnySubclass` 实现类型擦除：
```cpp
inline constexpr static size_t kMaxSubclassSize = 112;
using AnyTextureInfoData = SkAnySubclass<Data, kMaxSubclassSize>;
```
这避免了虚函数表指针开销，同时允许存储不同后端的数据。

### 拷贝构造实现

通过虚函数 `copyTo` 实现深拷贝：
```cpp
TextureInfo::TextureInfo(const TextureInfo& that)
        : fBackend(that.fBackend)
        , fViewFormat(that.fViewFormat)
        , fProtected(that.fProtected) {
    if (that.fData.has_value()) {
        that.fData->copyTo(fData);
    }
}
```

### 放置 new 赋值优化

赋值操作使用就地析构和重新构造：
```cpp
TextureInfo& TextureInfo::operator=(const TextureInfo& that) {
    if (this != &that) {
        this->~TextureInfo();
        new (this) TextureInfo(that);
    }
    return *this;
}
```

### 兼容性验证逻辑

`isCompatible` 方法分两级检查：
1. **基础属性**：后端类型、采样数、mipmap 设置
2. **后端特定**：委托给子类的 `isCompatible` 虚函数

```cpp
bool TextureInfo::isCompatible(const TextureInfo& that, bool requireExact) const {
    if (fBackend != that.fBackend) return false;
    return fData->fSampleCount == that.fData->fSampleCount &&
           fData->fMipmapped == that.fData->fMipmapped &&
           fData->isCompatible(that, requireExact);
}
```

### 缓存属性优化

`fViewFormat` 和 `fProtected` 在构造时从后端数据提取并缓存：
```cpp
TextureInfo(const BackendTextureData& data)
        : fBackend(BackendTextureData::kBackend)
        , fViewFormat(data.viewFormat())
        , fProtected(data.isProtected()) {
    fData.emplace<BackendTextureData>(data);
}
```
避免每次查询时的虚函数调用。

### 调试字符串生成

`toString` 方法组合多个信息源：
```cpp
SkStringPrintf("%s(viewFormat=%s,%s,bpp=%d,sampleCount=%u,mipmapped=%d,protected=%d)",
               backendName,
               TextureFormatName(fViewFormat),
               fData->toBackendString().c_str(),
               TextureFormatBytesPerBlock(fViewFormat),
               (unsigned) fData->fSampleCount,
               static_cast<int>(fData->fMipmapped),
               static_cast<int>(fProtected));
```

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `GraphiteTypes` | 基础类型定义（BackendApi、Protected 等） |
| `SkAnySubclass` | 类型擦除实现 |
| `TextureFormat` | 纹理格式枚举和函数 |
| `GpuTypesPriv` | GPU 类型私有工具 |
| `Caps` | 后端能力查询 |

**被依赖的模块**

该模块是多个上层组件的基础：
- `BackendTexture`：纹理资源封装
- `TextureProxy`：纹理代理
- `YUVABackendTextureInfo`：YUVA 纹理描述
- `Image`/`Surface`：图像和表面管理
- `Recorder`：命令记录时的纹理验证

## 设计模式与设计决策

### 类型擦除模式

使用 `SkAnySubclass` 实现类型擦除，避免虚函数表开销和动态内存分配。这是一种性能优化手段，特别适合高频复制的小对象。

### 属性分离设计

纹理尺寸不包含在 `TextureInfo` 中，而是由 `BackendTexture` 等上层类管理。这使得 `TextureInfo` 可以作为纹理"配方"在不同尺寸间复用。

### 缓存常用属性

将 `viewFormat` 和 `isProtected` 从后端数据中提取并缓存，避免频繁的虚函数调用，这是典型的时间换空间优化。

### 两级兼容性验证

`canBeFulfilledBy` 提供宽松的兼容性检查，而 `operator==` 提供严格的相等性检查，满足不同使用场景（如 Promise Image 的延迟实例化）。

### 后端无关抽象

通过纯虚函数接口（`Data` 基类）定义后端必须实现的能力，确保所有后端提供一致的功能。

### PIMPL 模式变体

虽然不是传统 PIMPL，但 `Data` 基类起到了隐藏后端实现细节的作用，头文件中只需要前向声明。

## 性能考量

### 避免动态内存分配

使用固定大小的 `SkAnySubclass` 存储后端数据，避免了 `std::unique_ptr` 的堆分配开销。112 字节的预留空间足够存储所有已知后端的数据。

### 虚函数调用最小化

只在必要时（拷贝、比较、调试输出）调用虚函数，常用属性通过缓存成员直接访问。

### 内联查询函数

简单查询函数（如 `isValid()`、`backend()`）定义在头文件中，允许编译器内联优化。

### 放置 new 优化

赋值操作使用放置 new 避免额外的内存操作，直接在现有对象内存上重新构造。

### 编译时类型检查

`enable_if_t<std::is_base_of_v<Data, BackendTextureData>>` 确保只接受合法的后端数据类型，将错误提前到编译期。

### 无锁设计

类本身是不可变的（除了拷贝赋值），不需要任何同步机制，适合多线程环境。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/gpu/graphite/GraphiteTypes.h` | 依赖 | 基础类型定义 |
| `include/private/base/SkAnySubclass.h` | 依赖 | 类型擦除实现 |
| `src/gpu/graphite/TextureFormat.h` | 依赖 | 纹理格式定义 |
| `src/gpu/graphite/TextureInfoPriv.h` | 相关 | 私有访问接口 |
| `src/gpu/graphite/mtl/MtlTextureInfo.h` | 实现 | Metal 后端实现 |
| `src/gpu/graphite/vk/VulkanTextureInfo.h` | 实现 | Vulkan 后端实现 |
| `src/gpu/graphite/dawn/DawnTextureInfo.h` | 实现 | Dawn 后端实现 |
| `include/gpu/graphite/BackendTexture.h` | 使用 | 纹理资源封装 |
