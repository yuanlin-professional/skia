# PipelineCallbackHandler

> 源文件
> - tools/graphite/PipelineCallbackHandler.h
> - tools/graphite/PipelineCallbackHandler.cpp

## 概述

PipelineCallbackHandler 是 Skia Graphite 测试工具中的管线回调处理器,用于跟踪和分析管线预编译的效果。该类作为 `ContextOptions::PipelineCacheCallback` 的实现示例,收集管线缓存操作的统计信息,支持两种测试模式:

1. **预编译测试模式** (gr*testprecompile): 收集 Android 风格的管线键,用于重建管线
2. **跟踪模式** (gr*testtracking): 收集管线标签,统计使用频率并生成报告

核心功能:
- 跟踪管线的添加和查找操作
- 统计管线使用次数
- 识别未使用的预编译管线
- 生成按使用频率排序的报告
- 线程安全的数据收集

## 架构位置

```
skia/
├── include/
│   ├── core/
│   │   ├── SkData.h               # 数据容器
│   │   └── SkRefCnt.h             # 引用计数
│   └── gpu/graphite/
│       └── ContextOptions.h       # 上下文选项(回调接口)
├── src/
│   ├── base/SkSpinlock.h          # 自旋锁
│   ├── core/
│   │   ├── SkChecksum.h           # 哈希工具
│   │   └── SkTHash.h              # 哈希表
└── tools/graphite/
    ├── PipelineCallbackHandler.h  # 本模块头文件
    └── PipelineCallbackHandler.cpp # 本模块实现
```

在 Graphite 测试架构中:
- 实现 `ContextOptions::PipelineCacheCallback` 回调
- 配合 `Context` 使用,监控管线缓存
- 用于 DM/GM 测试框架
- 分析预编译策略的有效性

## 主要类与结构体

### PipelineCallBackHandler
```cpp
class PipelineCallBackHandler
```
管线回调处理器,收集和分析管线缓存操作。

**主要成员**:
- `fMap`: 哈希表,存储管线数据
- `fSpinLock`: 自旋锁,保护并发访问

**核心方法**:
- `CallBack()`: 静态回调函数,桥接到成员方法
- `add()`: 添加管线操作记录
- `retrieveKeys()`: 提取所有 Android 风格的键
- `reset()`: 清空收集的数据
- `report()`: 生成统计报告

### PipelineData
```cpp
struct PipelineData {
    std::string   fLabel;           // 管线标签
    sk_sp<SkData> fAndroidStyleKey; // Android 风格序列化键
    uint32_t      fUniqueKeyHash;   // 唯一键哈希
    uint32_t      fUses;            // 使用次数
    bool          fFromPrecompile;  // 是否来自预编译
};
```
存储单个管线的追踪信息。

**字段说明**:
- `fLabel`: 人类可读的管线描述
- `fAndroidStyleKey`: 用于 Android 平台的序列化键(可为空)
- `fUniqueKeyHash`: 快速查找的哈希值
- `fUses`: 计数器,0 表示仅预编译但未使用
- `fFromPrecompile`: 区分预编译管线和运行时编译管线

### PipelineKey
```cpp
struct PipelineKey {
    const std::string* fLabel;  // 标签指针
    uint32_t fUniqueKeyHash;    // 哈希值

    static PipelineKey GetKey(const std::unique_ptr<PipelineData>& v);
    static uint32_t Hash(const PipelineKey& k);
    bool operator==(const PipelineKey& other) const;
};
```
哈希表的键类型,基于标签和哈希值。

**设计要点**:
- 使用指针引用标签,避免拷贝字符串
- 哈希值作为主键,标签作为冲突解决

## 公共 API 函数

### CallBack() (静态)
```cpp
static void CallBack(void* context,
                     skgpu::graphite::ContextOptions::PipelineCacheOp op,
                     const std::string& label,
                     uint32_t uniqueKeyHash,
                     bool fromPrecompile,
                     sk_sp<SkData> androidStyleKey)
```
**功能**: 静态回调函数,转发到实例方法
**参数**:
- `context`: `PipelineCallBackHandler*` 的 void 指针
- `op`: 操作类型(kAddingPipeline 或 kPipelineFound)
- `label`: 管线标签
- `uniqueKeyHash`: 唯一键哈希
- `fromPrecompile`: 是否预编译管线
- `androidStyleKey`: Android 风格的序列化键

**用途**: 注册为 `ContextOptions::fPipelineCacheCallback`

### add()
```cpp
void add(skgpu::graphite::ContextOptions::PipelineCacheOp op,
         const std::string& label,
         uint32_t uniqueKeyHash,
         bool fromPrecompile,
         sk_sp<SkData> androidStyleKey)
```
**功能**: 记录管线缓存操作
**行为**:
- `kAddingPipeline`: 添加新管线到映射表
- `kPipelineFound`: 增加已有管线的使用计数

**线程安全**: 使用自旋锁保护

### retrieveKeys()
```cpp
void retrieveKeys(std::vector<sk_sp<SkData>>* result)
```
**功能**: 提取所有可序列化的管线键
**参数**:
- `result`: 输出参数,存储键列表

**用途**: 预编译测试模式中重建管线

### reset()
```cpp
void reset()
```
**功能**: 清空所有收集的数据
**用途**: 测试不同场景时重置状态

### report()
```cpp
void report()
```
**功能**: 生成并打印管线使用统计报告
**输出格式**:
```
!! 0 UnusedPrecompiledPipeline
5 HighlyUsedPipeline
2 ModeratelyUsedPipeline
1 RarelyUsedPipeline
```
- `!!` 前缀: 预编译但未使用的管线
- 数字: 使用次数
- 标签: 管线描述

**排序**: 按使用次数降序,次要按标签字母序

## 内部实现细节

### 添加操作实现
```cpp
void PipelineCallBackHandler::add(...) {
    SkAutoSpinlock lock{ fSpinLock };

    std::unique_ptr<PipelineData>* foundData = fMap.find({ &label, uniqueKeyHash });
    if (foundData) {
        // 已存在的管线
        if (op == PipelineCacheOp::kPipelineFound) {
            (*foundData)->fUses++;  // 增加使用计数
        }
    } else {
        // 新管线
        SkASSERT(op == PipelineCacheOp::kAddingPipeline);

        auto newData = std::make_unique<PipelineData>(
            label, uniqueKeyHash, fromPrecompile, std::move(androidStyleKey));

        fMap.set(std::move(newData));
    }
}
```

**关键逻辑**:
1. 使用复合键 `{label, hash}` 查找
2. 找到则增加计数(仅 kPipelineFound 操作)
3. 未找到则插入新条目
4. 断言新管线必须是 kAddingPipeline 操作

**初始使用计数**:
```cpp
fUses(fromPrecompile ? 0 : 1)
```
- 预编译管线: 初始为 0
- 运行时编译管线: 初始为 1(编译即使用)

### 报告生成实现
```cpp
void PipelineCallBackHandler::report() {
    SkAutoSpinlock lock{ fSpinLock };

    // 1. 收集所有管线指针
    std::vector<const PipelineData*> tmp;
    tmp.reserve(fMap.count());
    fMap.foreach([&tmp](std::unique_ptr<PipelineData>* data) {
        tmp.push_back((*data).get());
    });

    // 2. 排序: 使用次数降序,标签升序
    std::sort(tmp.begin(), tmp.end(), [](const PipelineData* a, const PipelineData* b) {
        if (a->fUses != b->fUses) {
            return a->fUses > b->fUses;
        }
        return a->fLabel < b->fLabel;
    });

    // 3. 打印报告
    for (const PipelineData* data : tmp) {
        if (data->fFromPrecompile && !data->fUses) {
            SkDebugf("!! ");   // 标记未使用的预编译管线
        }
        SkDebugf("%u %s\n", data->fUses, data->fLabel.c_str());
    }
}
```

**"!!" 标记意义**:
- 预编译了但从未使用的管线
- 表示预编译策略可能过于激进
- 帮助优化预编译列表

### 键提取实现
```cpp
void retrieveKeys(std::vector<sk_sp<SkData>>* result) {
    SkAutoSpinlock lock{ fSpinLock };

    result->reserve(fMap.count());

    fMap.foreach([result](std::unique_ptr<PipelineData>* data) {
        // 跳过不可序列化的管线
        if ((*data)->fAndroidStyleKey) {
            result->push_back((*data)->fAndroidStyleKey);
        }
    });
}
```

**过滤逻辑**: 仅包含可序列化的管线(非空 `androidStyleKey`)

### 复合键查找
```cpp
PipelineKey key = { &label, uniqueKeyHash };
std::unique_ptr<PipelineData>* foundData = fMap.find(key);
```

**查找过程**:
1. 计算哈希: `PipelineKey::Hash(key)` 返回 `uniqueKeyHash`
2. 哈希桶查找
3. 冲突解决: 比较 `uniqueKeyHash` 和 `label`

**效率**: O(1) 平均时间

## 依赖关系

### Graphite 核心
- `skgpu::graphite::ContextOptions::PipelineCacheCallback`: 回调接口
- `skgpu::graphite::ContextOptions::PipelineCacheOp`: 操作枚举

### Skia 核心
- `SkData`: 不可变数据容器
- `sk_sp`: Skia 智能指针

### 并发工具
- `SkSpinlock`: 轻量级自旋锁
- `SK_GUARDED_BY`: 线程安全注解
- `SK_EXCLUDES`: 锁排除注解
- `SkAutoSpinlock`: RAII 锁管理

### 数据结构
- `skia_private::THashTable`: Skia 哈希表
- `std::vector`: 标准动态数组
- `std::unique_ptr`: 智能指针
- `std::string`: 标准字符串

### 工具
- `SkChecksum::Hash32()`: 哈希计算(未直接使用但相关)

## 设计模式与设计决策

### 回调模式
```cpp
static void CallBack(void* context, ...) {
    PipelineCallBackHandler* handler = reinterpret_cast<PipelineCallBackHandler*>(context);
    handler->add(...);
}
```
**设计**: 静态函数桥接到成员方法
**理由**: C 风格回调接口要求静态函数

### 观察者模式
`PipelineCallBackHandler` 作为观察者,监控管线缓存事件。

### 策略模式
两种测试模式使用相同的收集逻辑,不同的分析策略:
- 预编译测试: `retrieveKeys()` 提取键
- 跟踪模式: `report()` 生成报告

### 线程安全设计
```cpp
void add(...) SK_EXCLUDES(fSpinLock) {
    SkAutoSpinlock lock{ fSpinLock };
    // 临界区
}
```
**注解**:
- `SK_EXCLUDES`: 文档化锁排除(Clang 线程安全分析)
- `SK_GUARDED_BY`: 标记被锁保护的成员

### 自旋锁的选择
使用 `SkSpinlock` 而非 `std::mutex`:
- **优势**: 极短临界区,自旋比睡眠快
- **劣势**: 长时间持锁会浪费 CPU

**适用性**: 管线回调操作极快(哈希查找+计数)。

### 延迟排序设计
```cpp
report() {
    std::vector<const PipelineData*> tmp;
    fMap.foreach([&tmp](...) { tmp.push_back(...); });
    std::sort(tmp.begin(), tmp.end(), ...);
}
```
**设计**: 仅在报告时排序,收集时无序
**理由**: 收集频繁,报告罕见

### 智能指针所有权
```cpp
using Map = THashTable<std::unique_ptr<PipelineData>, ...>;
```
哈希表拥有 `PipelineData` 的所有权,自动释放。

### 防御式空指针检查
```cpp
if ((*data)->fAndroidStyleKey) {
    result->push_back((*data)->fAndroidStyleKey);
}
```
**理由**: 注释说明"not all Pipelines are serializable"

## 性能考量

### 自旋锁开销
```cpp
SkAutoSpinlock lock{ fSpinLock };
```
**场景分析**:
- **低竞争**: 接近无锁性能
- **高竞争**: 可能自旋等待,浪费 CPU

**实际情况**: 管线回调通常在渲染线程,竞争低。

### 哈希表性能
```cpp
std::unique_ptr<PipelineData>* foundData = fMap.find(key);
```
**时间复杂度**: O(1) 平均,O(n) 最坏
**空间复杂度**: O(n),n 为管线数量

### 内存占用
每个管线条目:
- `std::string`: 标签长度 + 约 24 字节
- `sk_sp<SkData>`: 8 字节指针 + 数据大小
- `uint32_t * 2`: 8 字节
- `bool`: 1 字节
- 总计: 约 50 字节 + 标签 + 序列化数据

**典型场景**: 100-1000 个管线,总内存 < 1MB。

### 排序开销
```cpp
std::sort(tmp.begin(), tmp.end(), ...);
```
**时间复杂度**: O(n log n)
**频率**: 仅报告时(通常测试结束时一次)
**影响**: 可忽略

### 容量预留优化
```cpp
result->reserve(fMap.count());
tmp.reserve(fMap.count());
```
避免动态数组重分配,提升性能。

## 相关文件

### Graphite 接口
- `include/gpu/graphite/ContextOptions.h`: 回调接口定义
- `src/gpu/graphite/Context.h`: 上下文实现(调用回调)

### 并发工具
- `src/base/SkSpinlock.h`: 自旋锁实现
- `include/private/base/SkThreadAnnotations.h`: 线程安全注解

### 数据结构
- `src/core/SkTHash.h`: 哈希表实现
- `include/core/SkData.h`: 数据容器

### 测试框架
- `tools/graphite/ContextFactory.h`: 创建带回调的上下文
- `dm/`: DM 测试框架使用本类
- `gm/`: GM 测试可能使用本类
