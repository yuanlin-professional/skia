# ResourceKey

> 源文件: src/gpu/ResourceKey.h, src/gpu/ResourceKey.cpp

## 概述

`ResourceKey` 是 Skia GPU 资源缓存系统的核心组件,为 GPU 资源提供键值管理机制。该模块定义了三种类型的资源键:基础资源键(`ResourceKey`)、可共享的临时资源键(`ScratchKey`)、以及独占式的唯一资源键(`UniqueKey`)。此外,还提供了编译期固定大小的键类型(`FixedSizeKey`)和消息传递机制用于资源失效通知。

资源键系统采用哈希和域(domain)机制来确保键的唯一性和高效查找。所有键都包含元数据(哈希值、域和大小信息)以及可变长度的数据部分,通过 Builder 模式构建,确保键的不变性和数据完整性。

## 架构位置

`ResourceKey` 位于 Skia GPU 层的基础设施层,是资源管理的核心抽象:

- 命名空间: `skgpu`
- 模块位置: `src/gpu/`
- 依赖层级: GPU 层基础设施
- 服务对象: GPU 资源缓存系统、纹理管理器、渲染资源管理

该模块处于 GPU 资源管理的底层,为上层的资源缓存和资源池提供键值索引能力,是实现资源复用和生命周期管理的基础。

## 主要类与结构体

### 继承关系

```
ResourceKey (基类)
├── ScratchKey (可共享的临时资源键)
└── UniqueKey (独占式唯一资源键)

独立类:
- FixedSizeKey<N> (模板类,编译期固定大小)
- UniqueKeyInvalidatedMessage (消息传递)
- UniqueKeyInvalidatedMsg_Graphite (Graphite 专用消息)
- AutoCallback (回调管理)
- RefCntedCallback (引用计数回调)
```

### 关键成员变量

#### ResourceKey

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fKey` | `skia_private::AutoSTMalloc<kMetaDataCnt + 6, uint32_t>` | 存储键数据,包含元数据和数据部分 |
| `kHash_MetaDataIdx` | `static const uint32_t` | 哈希值在数组中的索引 |
| `kDomainAndSize_MetaDataIdx` | `static const uint32_t` | 域和大小的打包索引 |
| `kMetaDataCnt` | `static const uint32_t` | 元数据项数量(2个) |

#### ScratchKey

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 继承自 `ResourceKey` | - | 无额外成员变量 |

#### UniqueKey

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fData` | `sk_sp<SkData>` | 自定义数据 |
| `fTag` | `const char*` | 调试标签 |

#### FixedSizeKey<SizeInUInt32>

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHash` | `uint32_t` | 哈希值 |
| `fPackedData` | `uint32_t[SizeInUInt32]` | 固定大小的数据数组 |

## 公共 API 函数

### ResourceKey 核心接口

```cpp
// 获取哈希值
uint32_t hash() const;

// 获取键的总大小(字节)
size_t size() const;

// 重置为无效键
void reset();

// 检查键是否有效
bool isValid() const;

// 获取域标识
uint32_t domain() const;

// 获取数据部分大小
size_t dataSize() const;

// 获取数据指针
const uint32_t* data() const;

// 调试输出
void dump() const;  // SK_DEBUG only
```

### ScratchKey 专用接口

```cpp
// 生成唯一的资源类型 ID
static ResourceType GenerateResourceType();

// 获取资源类型
ResourceType resourceType() const;
```

### UniqueKey 专用接口

```cpp
// 生成唯一的域 ID
static Domain GenerateDomain();

// 设置/获取自定义数据
void setCustomData(sk_sp<SkData> data);
SkData* getCustomData() const;
sk_sp<SkData> refCustomData() const;

// 获取调试标签
const char* tag() const;

// 调试输出
void dump(const char* label) const;  // SK_DEBUG only
```

### FixedSizeKey 接口

```cpp
// 获取哈希值
uint32_t hash() const;

// 比较运算符
bool operator==(const FixedSizeKey& that) const;
```

### Builder 模式

所有键类型都提供 Builder 用于构建:

```cpp
// ResourceKey::Builder
ResourceKey::Builder(ResourceKey* key, uint32_t domain, int data32Count);
uint32_t& operator[](int dataIdx);
void finish();

// ScratchKey::Builder
ScratchKey::Builder(ScratchKey* key, ResourceType type, int data32Count);

// UniqueKey::Builder
UniqueKey::Builder(UniqueKey* key, Domain type, int data32Count, const char* tag = nullptr);
UniqueKey::Builder(UniqueKey* key, const UniqueKey& innerKey, Domain domain,
                   int extraData32Cnt, const char* tag = nullptr);

// FixedSizeKey::Builder
FixedSizeKey::Builder(FixedSizeKey* key);
void finish();
uint32_t& operator[](int dataIdx);
```

### 辅助函数

```cpp
// 计算资源键哈希
uint32_t ResourceKeyHash(const uint32_t* data, size_t size);

// 静态唯一键宏
SKGPU_DECLARE_STATIC_UNIQUE_KEY(name);  // 声明
SKGPU_DEFINE_STATIC_UNIQUE_KEY(name);   // 定义
```

## 内部实现细节

### 键的数据结构布局

每个 `ResourceKey` 内部使用 `uint32_t` 数组存储,布局如下:

```
[0]: 哈希值 (kHash_MetaDataIdx)
[1]: 域和大小打包 (kDomainAndSize_MetaDataIdx)
     - 低 16 位: domain
     - 高 16 位: total size in bytes
[2..n]: 实际键数据
```

### 哈希计算

- 使用 `SkChecksum::Hash32` 计算哈希
- 哈希计算排除哈希值本身,仅对后续数据计算
- Builder 的 `finish()` 方法触发哈希计算

### 域和类型生成

`ScratchKey::GenerateResourceType()` 和 `UniqueKey::GenerateDomain()` 使用原子计数器生成唯一 ID:

```cpp
static std::atomic<int32_t> nextType{ResourceKey::kInvalidDomain + 1};
int32_t type = nextType.fetch_add(1, std::memory_order_relaxed);
```

- 起始值: `kInvalidDomain + 1` (1)
- 上限: `UINT16_MAX` (65535)
- 超限则触发 `SK_ABORT`

### 内存管理

- 使用 `AutoSTMalloc` 进行栈上小对象优化
- 默认栈上容量: `kMetaDataCnt + 6` (8 个 `uint32_t`)
- Ganesh 位图纹理需要 5 个 uint32_t
- Graphite 需要 6 个(额外存储 mipmap 状态)

### 键比较

`operator==` 分两步:

1. 比较元数据(包含大小信息)
2. 如果大小相同,比较数据部分

这种设计避免了比较不同大小的键时访问越界。

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkData | 存储 UniqueKey 的自定义数据 | `include/core/SkData.h` |
| SkRefCnt | 引用计数基础设施 | `include/core/SkRefCnt.h` |
| SkChecksum | 哈希计算 | `src/core/SkChecksum.h` |
| SkAlign | 对齐检查和操作 | `include/private/base/SkAlign.h` |
| SkTemplates | 模板工具(AutoSTMalloc) | `include/private/base/SkTemplates.h` |
| SkDebug | 调试输出 | `include/private/base/SkDebug.h` |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| GrResourceCache | 使用方 | Ganesh 资源缓存系统 |
| GrTexture | 使用方 | 纹理资源管理 |
| GrSurface | 使用方 | 表面资源管理 |
| GraphiteResourceCache | 使用方 | Graphite 资源缓存 |
| TextureProxy | 使用方 | 纹理代理对象 |

## 设计模式与设计决策

### 1. Builder 模式

所有键类型都使用 Builder 模式构建,确保:
- 键的不可变性(构建后)
- 哈希值的延迟计算和一致性
- 类型安全的数据填充

Builder 析构时自动调用 `finish()`,防止忘记完成构建。

### 2. 类型安全的域管理

使用静态方法生成域 ID,避免冲突:
- `ScratchKey::GenerateResourceType()`: 为可共享资源生成类型
- `UniqueKey::GenerateDomain()`: 为独占资源生成域

### 3. 两种键的语义区别

**ScratchKey (临时键)**:
- 多个资源可以共享同一个 ScratchKey
- 资源被引用时不会被缓存返回
- 适用场景: 可互换的临时资源(如临时渲染目标)

**UniqueKey (唯一键)**:
- 一个键只对应一个资源
- 资源被引用时仍可被缓存返回
- 优先级高于 ScratchKey
- 适用场景: 需要精确缓存控制的资源

### 4. 固定大小键优化

`FixedSizeKey` 模板类用于编译期已知大小的键:
- 无需动态分配
- 栈上存储,性能更优
- 适用于专用缓存

### 5. 消息传递机制

`UniqueKeyInvalidatedMessage` 用于跨模块通知资源失效:
- 包含键、上下文 ID 和缓存标识
- 使用消息总线传递
- 支持 Ganesh 和 Graphite 两种架构

## 性能考量

### 1. 内存优化

- **栈上小对象优化**: `AutoSTMalloc` 默认栈上分配 8 个 uint32_t
- **数据对齐**: 所有大小都是 4 字节对齐,便于 SIMD 优化
- **紧凑布局**: 元数据和数据连续存储,缓存友好

### 2. 哈希性能

- 使用 `SkChecksum::Hash32`,基于高效的哈希算法
- 哈希值预计算并缓存
- 键比较时先比较哈希,快速排除不等情况

### 3. 原子操作

域和类型生成使用 `std::atomic` 和 `memory_order_relaxed`:
- 避免锁开销
- 放松内存序减少同步成本
- 安全性足够(仅需唯一性,不需要顺序保证)

### 4. 避免虚函数开销

- `FixedSizeKey` 完全无虚函数
- `ScratchKey` 和 `UniqueKey` 继承自 `ResourceKey`,但实际使用时通常作为具体类型

### 5. 比较优化

`operator==` 先比较元数据(包含大小),大小不同则无需比较数据部分,避免无效内存访问。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/GrResourceCache.h` | 使用方 | Ganesh 资源缓存实现 |
| `src/gpu/GrTexture.h` | 使用方 | 纹理资源定义 |
| `src/gpu/GrSurface.h` | 使用方 | 表面资源基类 |
| `src/core/SkChecksum.h` | 依赖 | 哈希计算实现 |
| `include/gpu/GpuTypes.h` | 相关 | GPU 类型定义 |
| `src/gpu/graphite/ResourceCache.h` | 使用方 | Graphite 资源缓存 |
| `include/core/SkData.h` | 依赖 | 数据容器 |
| `tests/ResourceCacheTest.cpp` | 测试 | 单元测试 |
