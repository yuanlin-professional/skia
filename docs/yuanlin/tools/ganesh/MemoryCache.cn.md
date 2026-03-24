# MemoryCache

> 源文件：tools/ganesh/MemoryCache.h, tools/ganesh/MemoryCache.cpp

## 概述

MemoryCache 是 Skia Ganesh 测试工具集中的着色器缓存实现，用于在内存中记录和管理 GPU 程序的编译缓存。该类实现了 `GrContextOptions::PersistentCache` 接口，提供了一个完整的持久化缓存解决方案，主要用于测试、调试和性能分析场景。

MemoryCache 的核心功能包括：
- 存储已编译的 GPU 着色器程序
- 提供快速的内存级缓存访问
- 跟踪缓存命中率和存储统计
- 支持将着色器导出到磁盘进行分析
- 记录每个缓存项的访问次数和描述信息

该类特别适合在测试环境中使用，可以在多个 GrContext 之间共享（前提是这些上下文具有相同的配置和能力），从而避免重复编译相同的着色器程序。通过统计缓存命中率和导出着色器代码，开发人员可以优化着色器生成和编译性能。

## 架构位置

MemoryCache 位于 Skia 测试工具层级，作为持久化缓存接口的内存实现：

- **接口层**：实现 `GrContextOptions::PersistentCache` 接口
- **上层调用者**：
  - Ganesh GPU 测试套件
  - 性能基准测试（benchmarks）
  - 着色器编译测试
  - 跨上下文缓存共享测试

- **同级组件**：
  - TestContext - 测试上下文管理
  - TestOps - 测试用绘制操作
  - ProxyUtils - 代理工具函数

- **下层依赖**：
  - `include/gpu/ganesh/GrContextOptions.h` - 上下文配置和持久化缓存接口
  - `src/core/SkData.h` - 不可变数据对象
  - `src/core/SkChecksum.h` - 哈希计算
  - `src/gpu/ganesh/GrPersistentCacheUtils.h` - 缓存工具函数
  - C++ 标准库 `<unordered_map>` - 哈希映射实现

MemoryCache 作为测试专用的缓存实现，不应在生产环境中使用。生产环境应使用文件系统或其他持久化存储实现。

## 主要类与结构体

### MemoryCache

```cpp
class MemoryCache : public GrContextOptions::PersistentCache {
public:
    MemoryCache() = default;
    MemoryCache(const MemoryCache&) = delete;
    MemoryCache& operator=(const MemoryCache&) = delete;

    void reset();

    // 持久化缓存接口
    sk_sp<SkData> load(const SkData& key) override;
    void store(const SkData& key, const SkData& data, const SkString& description) override;

    // 统计信息
    int numCacheMisses() const;
    int numCacheStores() const;
    void resetCacheStats();

    // 调试和分析
    void writeShadersToDisk(const char* path, GrBackendApi backend);

    template <typename Fn>
    void foreach(Fn&& fn);
};
```

MemoryCache 明确禁止拷贝操作，因为缓存对象应该被共享而非复制。

### Key（内部结构）

```cpp
struct Key {
    Key() = default;
    Key(const SkData& key);
    bool operator==(const Key& that) const;

    sk_sp<const SkData> fKey;
};
```

Key 封装了缓存键，使用 SkData 存储任意二进制数据。相等性比较基于数据内容而非指针。

**设计特点**：
- 使用智能指针管理内存
- 深拷贝键数据，确保生命周期独立
- 提供值语义的相等性比较

### Value（内部结构）

```cpp
struct Value {
    Value() = default;
    Value(const SkData& data, const SkString& description);

    sk_sp<SkData> fData;        // 缓存的数据（编译后的着色器）
    SkString fDescription;       // 人类可读的描述
    int fHitCount;               // 命中计数
};
```

Value 存储缓存的数据及其元信息：
- **fData**：实际的缓存数据（如编译后的着色器二进制）
- **fDescription**：描述信息，用于调试和日志
- **fHitCount**：记录该缓存项被访问的次数，用于分析热点

### Hash（内部结构）

```cpp
struct Hash {
    using argument_type = Key;
    using result_type = uint32_t;
    uint32_t operator()(const Key& key) const;
};
```

Hash 为 unordered_map 提供自定义哈希函数，使用 `SkChecksum::Hash32` 计算键的哈希值。

## 公共 API 函数

### load

```cpp
sk_sp<SkData> load(const SkData& key) override;
```

从缓存中加载数据。这是持久化缓存接口的核心方法。

**参数**：
- `key` - 缓存键，通常由 Ganesh 根据着色器配置生成

**返回值**：
- 成功时返回指向缓存数据的智能指针
- 未命中时返回 `nullptr`

**副作用**：
- 缓存未命中时递增 `fCacheMissCnt`
- 缓存命中时递增对应 Value 的 `fHitCount`
- 如果启用 `LOG_MEMORY_CACHE`，输出调试日志

**实现细节**：
```cpp
auto result = fMap.find(key);
if (result == fMap.end()) {
    ++fCacheMissCnt;
    return nullptr;
}
result->second.fHitCount++;
return result->second.fData;
```

### store

```cpp
void store(const SkData& key, const SkData& data, const SkString& description) override;
```

将数据存储到缓存中。当 Ganesh 编译新的着色器时会调用此方法。

**参数**：
- `key` - 缓存键
- `data` - 要缓存的数据（编译后的着色器）
- `description` - 描述信息，用于调试

**副作用**：
- 递增 `fCacheStoreCnt`
- 如果键已存在，覆盖旧值并重置 `fHitCount` 为 1
- 如果启用 `LOG_MEMORY_CACHE`，输出调试日志

**实现细节**：
```cpp
++fCacheStoreCnt;
fMap[Key(key)] = Value(data, description);
```

### reset

```cpp
void reset();
```

清空整个缓存，包括所有数据和统计信息。

**用途**：
- 测试间清理
- 测量特定场景的缓存行为
- 内存管理

### 统计信息查询

```cpp
int numCacheMisses() const { return fCacheMissCnt; }
int numCacheStores() const { return fCacheStoreCnt; }
void resetCacheStats();
```

这些函数用于分析缓存效率：
- **numCacheMisses**：返回缓存未命中次数
- **numCacheStores**：返回缓存存储次数
- **resetCacheStats**：重置统计计数器但保留缓存数据

**命中率计算**：
```cpp
float hitRate = 1.0f - (float)numCacheMisses() / (numCacheMisses() + numHits);
```

### writeShadersToDisk

```cpp
void writeShadersToDisk(const char* path, GrBackendApi backend);
```

将缓存中的着色器导出到磁盘，用于离线分析和调试。

**参数**：
- `path` - 输出目录路径
- `backend` - 后端 API（OpenGL 或 Vulkan）

**导出格式**：
- OpenGL：文本格式 GLSL（`.vert` 和 `.frag` 文件）
- Vulkan：SPIR-V 二进制格式（`.vert.spv` 和 `.frag.spv` 文件）
- 键描述：文本文件（`.key` 文件）

**文件命名**：
使用 MD5 哈希作为文件名，确保唯一性：
```cpp
SkMD5 hash;
hash.write(key->bytes(), bytesToHash);
SkString md5 = hash.finish().toLowercaseHexString();
// 输出文件如：a3f2b8e1c4d5.vert.spv
```

**Vulkan 特殊处理**：
Vulkan 缓存包含两种类型（着色器和管线），仅导出着色器：
```cpp
GrVkGpu::PersistentCacheKeyType vkKeyType;
memcpy(&vkKeyType, keyBytes + bytesToHash - sizeof(vkKeyType), sizeof(vkKeyType));
if (vkKeyType != GrVkGpu::kShader_PersistentCacheKeyType) {
    continue;  // 跳过管线缓存
}
```

### foreach

```cpp
template <typename Fn>
void foreach(Fn&& fn);
```

遍历所有缓存项，对每项调用提供的函数。

**函数签名**：
```cpp
fn(const SkData& key, const SkData& data, const SkString& description, int hitCount)
```

**使用示例**：
```cpp
cache.foreach([](const auto& key, const auto& data,
                 const auto& desc, int hits) {
    printf("Key: %s, Hits: %d, Desc: %s\n",
           keyToString(key).c_str(), hits, desc.c_str());
});
```

## 内部实现细节

### 数据结构选择

MemoryCache 使用 `std::unordered_map` 作为核心数据结构：

```cpp
std::unordered_map<Key, Value, Hash> fMap;
```

**选择理由**：
- **O(1) 平均查找时间**：满足高频缓存访问需求
- **任意键类型**：支持二进制数据作为键
- **自动扩容**：无需手动管理容量

### 键的深拷贝策略

Key 构造函数执行深拷贝：

```cpp
Key(const SkData& key) : fKey(SkData::MakeWithCopy(key.data(), key.size())) {}
```

这确保：
- 缓存键的生命周期独立于调用者
- Ganesh 可以在调用后立即释放临时键
- 避免悬空指针问题

同样，Value 也深拷贝数据：
```cpp
Value(const SkData& data, const SkString& description)
    : fData(SkData::MakeWithCopy(data.data(), data.size()))
    , fDescription(description)
    , fHitCount(1) {}
```

### 哈希函数实现

使用 `SkChecksum::Hash32` 提供快速、高质量的哈希：

```cpp
uint32_t operator()(const Key& key) const {
    return key.fKey ? SkChecksum::Hash32(key.fKey->data(), key.fKey->size()) : 0;
}
```

这个哈希函数：
- 针对二进制数据优化
- 具有良好的分布特性
- 处理空键的边界情况

### 日志系统

条件编译日志系统用于调试：

```cpp
#define LOG_MEMORY_CACHE 0

if (LOG_MEMORY_CACHE) {
    SkDebugf("Load Key: %s\n\tFound Data: %s\n\n",
             data_to_str(key).c_str(),
             data_to_str(*result->second.fData).c_str());
}
```

`data_to_str` 函数将二进制数据转换为 Base64 编码的字符串，截断长数据：
```cpp
static SkString data_to_str(const SkData& data) {
    size_t encodeLength = SkBase64::EncodedSize(data.size());
    SkString str;
    str.resize(encodeLength);
    SkBase64::Encode(data.data(), data.size(), str.data());
    static constexpr size_t kMaxLength = 60;
    if (encodeLength > kMaxLength) {
        str = SkString(str.c_str(), kMaxLength - 3);
        str.append("...");
    }
    return str;
}
```

### 着色器解包和导出

`writeShadersToDisk` 使用 `GrPersistentCacheUtils` 解包着色器：

```cpp
SkReadBuffer reader(data->data(), data->size());
const SkFourByteTag shaderType = GrPersistentCacheUtils::GetType(&reader);
const bool isBinaryShader =
    (GrBackendApi::kVulkan == api && shaderType == SkSetFourByteTag('S', 'P', 'R', 'V'));

SkSL::NativeShader shaders[kGrShaderTypeCount];
GrPersistentCacheUtils::UnpackCachedShaders(
    &reader, shaders, isBinaryShader, interfacesIgnored, kGrShaderTypeCount);
```

然后根据类型写入不同格式：
- **文本着色器（OpenGL）**：直接写入字符串
- **二进制着色器（Vulkan）**：写入 uint32_t 数组

## 依赖关系

### 核心依赖

- **SkData**：不可变数据容器，用于存储键和值
- **GrContextOptions::PersistentCache**：持久化缓存接口
- **std::unordered_map**：哈希映射数据结构

### 哈希和校验

- **SkChecksum**：快速哈希计算
- **SkMD5**：MD5 哈希，用于生成文件名

### 序列化和编码

- **SkReadBuffer**：读取序列化数据
- **SkBase64**：Base64 编码（用于日志）
- **GrPersistentCacheUtils**：缓存数据打包/解包

### 着色器相关

- **SkSL::NativeShader**：本地着色器表示
- **GrVkGpu**：Vulkan 特定类型（条件编译）

### 文件 I/O

- **SkFILEWStream**：文件写入流

## 设计模式与设计决策

### 接口实现模式

MemoryCache 实现 `PersistentCache` 接口，提供可插拔的缓存后端：

```cpp
class MemoryCache : public GrContextOptions::PersistentCache {
    sk_sp<SkData> load(const SkData& key) override;
    void store(const SkData& key, const SkData& data, const SkString& description) override;
};
```

这允许：
- 测试时使用内存缓存
- 生产环境使用文件系统缓存
- 自定义缓存策略（如分布式缓存）

### 不可拷贝设计

明确删除拷贝操作：

```cpp
MemoryCache(const MemoryCache&) = delete;
MemoryCache& operator=(const MemoryCache&) = delete;
```

理由：
- 缓存对象应该被共享（通过指针或引用）
- 拷贝会导致数据重复和不一致
- 明确设计意图，防止误用

### 值语义的键

Key 结构使用值语义而非指针语义：

```cpp
struct Key {
    sk_sp<const SkData> fKey;  // 深拷贝的数据
    bool operator==(const Key& that) const;  // 基于内容的比较
};
```

这简化了哈希表的使用，避免了指针生命周期管理问题。

### 统计分离

统计信息（命中/未命中计数）与实际缓存数据分离：

```cpp
void reset() {  // 清空缓存和统计
    this->resetCacheStats();
    fMap.clear();
}

void resetCacheStats() {  // 仅重置统计
    fCacheMissCnt = 0;
    fCacheStoreCnt = 0;
}
```

这允许在保留缓存数据的同时重置统计，用于测量特定时间窗口的缓存行为。

### 条件编译日志

使用宏控制日志输出：

```cpp
#define LOG_MEMORY_CACHE 0
```

这比运行时开关更高效，因为未启用时代码会被完全优化掉。

### 模板遍历

`foreach` 使用模板实现，支持任意可调用对象：

```cpp
template <typename Fn>
void foreach(Fn&& fn) { ... }
```

这提供了最大的灵活性，支持 lambda、函数指针、函数对象等。

## 性能考量

### 内存 vs 磁盘

MemoryCache 牺牲持久性换取速度：
- **优势**：无磁盘 I/O，极快的访问速度
- **劣势**：进程退出后缓存丢失

适用于：
- 单次运行的测试
- 短期性能测试
- 缓存行为分析

### 哈希表性能

`std::unordered_map` 提供：
- **平均 O(1) 查找**：快速缓存访问
- **O(1) 插入**：快速缓存存储
- **自动负载因子管理**：维持性能

### 深拷贝开销

每次 store 都执行深拷贝：

```cpp
fMap[Key(key)] = Value(data, description);
```

这增加了内存使用和拷贝时间，但：
- 确保数据安全
- 简化生命周期管理
- 对于相对较小的着色器数据是可接受的

如果性能关键，可以考虑使用移动语义或共享所有权。

### 命中计数开销

每次 load 递增命中计数：

```cpp
result->second.fHitCount++;
```

这是轻量级操作，但在高频访问场景下可能导致缓存行争用。如果命中计数不重要，可以考虑移除或使用原子操作。

### 导出性能

`writeShadersToDisk` 是 I/O 密集型操作：
- MD5 计算
- 数据解包
- 文件写入

应仅在调试或分析时调用，不应在性能测量路径上。

## 相关文件

### 接口定义
- `include/gpu/ganesh/GrContextOptions.h` - 持久化缓存接口定义

### 同目录测试工具
- `tools/ganesh/TestContext.h/cpp` - 测试上下文管理
- `tools/ganesh/TestOps.h/cpp` - 测试用绘制操作
- `tools/ganesh/ProxyUtils.h/cpp` - 代理工具函数

### Ganesh 缓存工具
- `src/gpu/ganesh/GrPersistentCacheUtils.h` - 缓存打包/解包工具
- `src/gpu/ganesh/vk/GrVkGpu.h` - Vulkan GPU 实现（包含缓存键类型定义）

### 数据结构
- `include/core/SkData.h` - 不可变数据对象
- `src/core/SkChecksum.h` - 哈希计算
- `src/core/SkMD5.h` - MD5 哈希

### 序列化和编码
- `src/core/SkReadBuffer.h` - 读取序列化数据
- `src/base/SkBase64.h` - Base64 编码

### 着色器处理
- `src/sksl/codegen/SkSLNativeShader.h` - 本地着色器表示
