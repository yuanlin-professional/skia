# GraphiteMemoryPipelineStorage

> 源文件
> - tools/graphite/GraphiteMemoryPipelineStorage.h
> - tools/graphite/GraphiteMemoryPipelineStorage.cpp

## 概述

GraphiteMemoryPipelineStorage 是 Skia Graphite 测试工具中的管线缓存实现,用于在内存中存储和加载后端特定的管线数据。该类实现了 `PersistentPipelineStorage` 接口,提供管线着色器的序列化存储功能,主要用于测试管线缓存机制的正确性和性能。

核心功能:
- 在内存中缓存已编译的管线数据
- 统计加载和存储操作次数
- 支持缓存重置和统计重置
- 可选的调试日志输出(Base64 编码数据)
- 用于测试管线预编译和缓存命中率

## 架构位置

```
skia/
├── include/
│   ├── core/SkData.h                     # 数据容器
│   └── gpu/graphite/
│       └── PersistentPipelineStorage.h   # 管线存储接口
├── src/
│   └── base/SkBase64.h                   # Base64 编码工具
└── tools/graphite/
    ├── GraphiteMemoryPipelineStorage.h   # 本模块头文件
    └── GraphiteMemoryPipelineStorage.cpp # 本模块实现
```

在 Graphite 架构中的位置:
- 实现 `PersistentPipelineStorage` 接口
- 用于测试框架,不用于生产环境
- 与 `Context` 配合使用,缓存管线编译结果
- 替代文件系统或平台特定的缓存实现

## 主要类与结构体

### GraphiteMemoryPipelineStorage
```cpp
class GraphiteMemoryPipelineStorage : public skgpu::graphite::PersistentPipelineStorage
```
内存中的管线缓存实现,用于测试目的。

**主要成员**:
- `fLoadCount`: 加载操作计数器
- `fStoreCount`: 存储操作计数器
- `fData`: 缓存的管线数据(SkData)

**核心方法**:
- `load()`: 从缓存加载数据
- `store(const SkData&)`: 将数据存储到缓存
- `numLoads()`: 获取加载次数
- `numStores()`: 获取存储次数
- `resetCacheStats()`: 重置统计信息
- `reset()`: 完全重置缓存

**特性**:
- 禁止拷贝构造和赋值
- 使用默认构造函数

## 公共 API 函数

### load()
```cpp
sk_sp<SkData> load() override
```
**功能**: 从内存缓存加载管线数据
**返回值**:
- 如果缓存有数据: 返回 `sk_sp<SkData>` 指向缓存数据
- 如果缓存为空: 返回 `nullptr`

**副作用**: 增加 `fLoadCount` 计数器

### store()
```cpp
void store(const SkData& data) override
```
**功能**: 将管线数据存储到内存缓存
**参数**:
- `data`: 要缓存的管线数据

**行为**:
- 创建数据的深拷贝(`SkData::MakeWithCopy`)
- 替换现有缓存数据
- 增加 `fStoreCount` 计数器

### numLoads()
```cpp
int numLoads() const
```
**功能**: 获取 `load()` 被调用的次数
**用途**: 测试缓存命中率

### numStores()
```cpp
int numStores() const
```
**功能**: 获取 `store()` 被调用的次数
**用途**: 测试缓存更新频率

### resetCacheStats()
```cpp
void resetCacheStats()
```
**功能**: 重置加载和存储计数器为 0
**保留**: 缓存的数据本身

### reset()
```cpp
void reset()
```
**功能**: 完全重置缓存
**行为**:
- 调用 `resetCacheStats()` 重置计数器
- 清空 `fData`,释放缓存数据

## 内部实现细节

### 数据加载实现
```cpp
sk_sp<SkData> GraphiteMemoryPipelineStorage::load() {
    if (!fData) {
#if defined(LOG_MEMORY_CACHE)
        SkDebugf("No data to load\n");
#endif
        return nullptr;
    }

#if defined(LOG_MEMORY_CACHE)
    SkDebugf("Loading data: %zu %s\n", fData->size(), data_to_str(*fData).c_str());
#endif

    ++fLoadCount;
    return fData;  // 返回引用计数的指针,不拷贝数据
}
```
**关键点**:
- 返回的是原始 `fData` 的 `sk_sp`,共享底层数据
- 可选的调试日志记录数据大小和内容

### 数据存储实现
```cpp
void GraphiteMemoryPipelineStorage::store(const SkData& data) {
#if defined(LOG_MEMORY_CACHE)
    SkDebugf("Storing data: %zu %s\n", data.size(), data_to_str(data).c_str());
#endif

    ++fStoreCount;
    fData = SkData::MakeWithCopy(data.data(), data.size());
}
```
**关键点**:
- 使用 `MakeWithCopy` 创建数据副本
- 确保数据独立于调用者的生命周期
- 可选的调试日志

### 调试日志功能
```cpp
#if defined(LOG_MEMORY_CACHE)
static SkString data_to_str(const SkData& data) {
    size_t encodeLength = SkBase64::EncodedSize(data.size());
    SkString str;
    str.resize(encodeLength);
    SkBase64::Encode(data.data(), data.size(), str.data());

    static constexpr size_t kMaxLength = 60;
    static constexpr char kTail[] = "...";
    bool overlength = encodeLength > kMaxLength;
    if (overlength) {
        str = SkString(str.c_str(), kMaxLength - kTailLen);
        str.append(kTail);
    }
    return str;
}
#endif
```
**特性**:
- 将二进制数据编码为 Base64 字符串
- 限制输出长度为 60 字符,超出部分截断并添加 "..."
- 仅在定义 `LOG_MEMORY_CACHE` 时编译

**用途**: 调试管线缓存问题,查看缓存内容

## 依赖关系

### Skia 核心
- `SkData`: 不可变数据容器,使用引用计数
- `sk_sp`: Skia 的智能指针

### Graphite 接口
- `skgpu::graphite::PersistentPipelineStorage`: 持久化存储抽象接口

### 工具依赖
- `SkBase64`: Base64 编码工具(仅调试日志使用)
- `SkString`: Skia 字符串类(仅调试日志使用)

## 设计模式与设计决策

### 策略模式
`GraphiteMemoryPipelineStorage` 是 `PersistentPipelineStorage` 接口的一个具体实现:
- **接口**: `PersistentPipelineStorage`
- **实现策略**:
  - 生产环境: 文件系统缓存
  - 测试环境: 本类(内存缓存)
  - 平台特定: iOS/Android 的平台缓存

### 单例数据模式
缓存只保存一份数据(`fData`):
```cpp
sk_sp<SkData> fData;
```
后续的 `store()` 调用会替换整个缓存。

**理由**: 管线缓存通常序列化为单个二进制块。

### 防御式拷贝
```cpp
fData = SkData::MakeWithCopy(data.data(), data.size());
```
存储时创建深拷贝,而非引用原始数据。

**优点**:
- 避免悬空指针问题
- 调用者可以安全释放原始数据

**缺点**:
- 额外的内存分配和拷贝开销

**权衡**: 测试场景下性能不是首要考虑。

### 统计注入设计
```cpp
int numLoads() const { return fLoadCount; }
int numStores() const { return fStoreCount; }
```
提供统计接口,方便测试验证:
- 缓存是否被正确使用
- 预编译是否生效
- 缓存命中率

### 可选日志设计
```cpp
// #define LOG_MEMORY_CACHE
#if defined(LOG_MEMORY_CACHE)
    SkDebugf("Loading data: ...");
#endif
```
通过编译时宏控制日志输出:
- **优点**: 零运行时开销(未定义时)
- **用途**: 调试缓存问题

### 接口隔离
不拥有所有权的接口设计:
```cpp
void store(const SkData& data)  // 接受引用,内部拷贝
sk_sp<SkData> load()            // 返回智能指针,共享所有权
```

## 性能考量

### 内存占用
```cpp
sk_sp<SkData> fData;
```
**占用量**: 取决于管线数据大小
- 典型: 几 KB 到几 MB
- 极端: 复杂管线可能达到数十 MB

**优化**: 仅缓存单个版本,不保留历史数据

### 拷贝开销
```cpp
fData = SkData::MakeWithCopy(data.data(), data.size());
```
`store()` 操作涉及完整的内存拷贝。

**缓解因素**:
- 通常只在首次编译时调用一次
- 后续加载直接返回缓存,无拷贝

### 引用计数开销
```cpp
return fData;  // sk_sp 的引用计数增加
```
返回 `sk_sp` 时增加引用计数,开销极小(原子操作)。

### 无锁设计
当前实现无线程同步:
- **假设**: 测试代码单线程访问
- **风险**: 多线程使用可能导致竞态条件

**生产环境**: 需要添加互斥锁保护。

### 统计计数器开销
```cpp
++fLoadCount;
++fStoreCount;
```
简单的整数递增,开销可忽略不计。

## 相关文件

### 接口定义
- `include/gpu/graphite/PersistentPipelineStorage.h`: 持久化存储抽象接口

### 数据容器
- `include/core/SkData.h`: 不可变数据容器
- `include/core/SkRefCnt.h`: 引用计数智能指针

### 工具依赖
- `src/base/SkBase64.h`: Base64 编码/解码
- `include/core/SkString.h`: Skia 字符串类

### Graphite 相关
- `include/gpu/graphite/Context.h`: 使用管线存储的上下文
- `src/gpu/graphite/PipelineCache.h`: 管线缓存管理器

### 测试用途
- `tests/GraphiteTest.cpp`: 使用本类测试管线缓存
- `tests/PrecompileTest.cpp`: 测试预编译功能
- `tools/graphite/GraphiteTestContext.h`: 测试上下文集成
