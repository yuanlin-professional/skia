# GrThreadSafePipelineBuilder

> 源文件: src/gpu/ganesh/GrThreadSafePipelineBuilder.h, src/gpu/ganesh/GrThreadSafePipelineBuilder.cpp

## 概述

`GrThreadSafePipelineBuilder` 是 Skia Ganesh GPU 后端中用于线程安全地构建图形管线的基类。它主要负责收集和管理管线编译相关的统计信息,包括着色器编译次数、程序缓存命中率、编译失败统计等。

该类使用原子操作保证多线程环境下的统计数据一致性,支持在 GPU 测试和性能分析场景中导出详细的编译指标。其设计重点是提供低开销的统计收集机制,在 Release 版本中完全消除统计开销。

## 架构位置

`GrThreadSafePipelineBuilder` 在 Ganesh 管线系统中的位置:

- **上层**: 被各 GPU 后端的 PipelineBuilder 子类继承
- **同层**: 作为基类,定义统计收集的通用接口
- **下层**: 不直接依赖其他 Ganesh 组件,为独立的基础设施

该类是管线构建系统的基础设施层,为上层提供统一的性能监控能力。

## 主要类与结构体

### GrThreadSafePipelineBuilder 类

**继承关系**:
- 继承自 `SkRefCnt`,支持引用计数管理
- 子类包括各平台特定的 PipelineBuilder(Vulkan/Metal/D3D等)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStats` | `Stats` | 统计信息对象 |

**简洁设计**: 基类只包含统计对象,其他实现由子类负责。

### Stats 内部类

嵌套在 `GrThreadSafePipelineBuilder` 中,封装所有统计逻辑。

#### ProgramCacheResult 枚举

```cpp
enum class ProgramCacheResult {
    kHit,       // 程序在缓存中找到
    kMiss,      // 程序不在缓存中(需要编译)
    kPartial,   // 在持久化缓存中找到预编译版本
    kLast = kPartial
};
```

**用途**: 分类程序缓存的查询结果。

#### 统计成员变量 (GR_GPU_STATS 模式)

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fShaderCompilations` | `std::atomic<int>` | 着色器编译总次数 |
| `fNumInlineCompilationFailures` | `std::atomic<int>` | 内联编译失败次数 |
| `fInlineProgramCacheStats[3]` | `std::atomic<int>[]` | 内联编译的缓存统计 |
| `fNumPreCompilationFailures` | `std::atomic<int>` | 预编译失败次数 |
| `fPreProgramCacheStats[3]` | `std::atomic<int>[]` | 预编译的缓存统计 |
| `fNumCompilationFailures` | `std::atomic<int>` | 总编译失败次数 |
| `fNumPartialCompilationSuccesses` | `std::atomic<int>` | 部分编译成功次数 |
| `fNumCompilationSuccesses` | `std::atomic<int>` | 编译完全成功次数 |

**原子性**: 所有计数器使用 `std::atomic` 保证线程安全。

## 公共 API 函数

### 构造函数

```cpp
GrThreadSafePipelineBuilder() = default
```

**特性**: 默认构造函数,统计对象自动初始化为零。

### stats 访问器

```cpp
Stats* stats()
```

**功能**: 获取统计对象指针,供子类更新统计数据。

### Stats 成员函数 (GR_GPU_STATS 模式)

#### 着色器编译统计

```cpp
int shaderCompilations() const
void incShaderCompilations()
```

#### 内联编译统计

```cpp
int numInlineCompilationFailures() const
void incNumInlineCompilationFailures()
int numInlineProgramCacheResult(ProgramCacheResult stat) const
void incNumInlineProgramCacheResult(ProgramCacheResult stat)
```

#### 预编译统计

```cpp
int numPreCompilationFailures() const
void incNumPreCompilationFailures()
int numPreProgramCacheResult(ProgramCacheResult stat) const
void incNumPreProgramCacheResult(ProgramCacheResult stat)
```

#### 总体编译统计

```cpp
int numCompilationFailures() const
void incNumCompilationFailures()
int numPartialCompilationSuccesses() const
void incNumPartialCompilationSuccesses()
int numCompilationSuccesses() const
void incNumCompilationSuccesses()
```

### Debug 导出函数 (GPU_TEST_UTILS)

```cpp
void dump(SkString* out)
void dumpKeyValuePairs(skia_private::TArray<SkString>* keys,
                       skia_private::TArray<double>* values)
```

**功能**:
- `dump`: 格式化输出所有统计信息到字符串
- `dumpKeyValuePairs`: 导出为键值对,便于集成到测试框架

## 内部实现细节

### 条件编译策略

代码使用宏 `GR_GPU_STATS` 控制统计功能的存在:

```cpp
#if GR_GPU_STATS
    // 完整统计实现
#else
    // 空实现(零开销)
    void incShaderCompilations() {}
#endif
```

**优点**:
- Release 版本无性能开销
- 开发和测试版本提供完整统计
- 保持 API 接口一致性

### 原子操作的使用

所有计数器修改使用原子递增:

```cpp
void incShaderCompilations() { fShaderCompilations++; }
```

C++11 保证 `std::atomic<int>` 的 `++` 操作是线程安全的。

### 缓存统计数组索引

```cpp
int numInlineProgramCacheResult(ProgramCacheResult stat) const {
    return fInlineProgramCacheStats[(int)stat];
}
```

使用枚举值作为数组索引,编译时类型安全。

### dump 方法的实现

仅在 `GPU_TEST_UTILS` 和 `GR_GPU_STATS` 同时开启时实现:

```cpp
#if GR_GPU_STATS
#if defined(GPU_TEST_UTILS)
void GrThreadSafePipelineBuilder::Stats::dump(SkString* out) {
    out->appendf("Shader Compilations: %d\n", fShaderCompilations.load());
    // ... 更多统计输出
}
#endif
#endif
```

**输出格式**:
- 清晰的标签和数值
- 使用 `SkASSERT` 验证预期(如失败次数应为 0)
- 区分内联编译和预编译的统计

### cache_result_to_str 辅助函数

```cpp
static const char* cache_result_to_str(int i) {
    const char* kCacheResultStrings[] = {"hits", "misses", "partials"};
    return kCacheResultStrings[i];
}
```

**静态断言验证枚举顺序**:
```cpp
static_assert(0 == (int)Stats::ProgramCacheResult::kHit);
static_assert(1 == (int)Stats::ProgramCacheResult::kMiss);
static_assert(2 == (int)Stats::ProgramCacheResult::kPartial);
```

确保数组索引与枚举值匹配。

### dumpKeyValuePairs 的简化实现

当前只导出着色器编译次数:

```cpp
void GrThreadSafePipelineBuilder::Stats::dumpKeyValuePairs(
        TArray<SkString>* keys, TArray<double>* values) {
    keys->push_back(SkString("shader_compilations"));
    values->push_back(fShaderCompilations);
}
```

**设计**: 可扩展以支持更多指标。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRefCnt` | 提供引用计数基类 |
| `SkString` | 字符串格式化(仅测试模式) |
| `skia_private::TArray` | 动态数组(仅测试模式) |
| `<atomic>` | 原子操作支持 |

### 被依赖的模块

该类被以下模块继承和使用:
- Vulkan PipelineBuilder
- Metal PipelineBuilder
- D3D12 PipelineBuilder
- Dawn PipelineBuilder
- Mock PipelineBuilder (测试)

## 设计模式与设计决策

### Template Method 模式

基类提供统计框架,子类在管线构建过程中调用统计方法:

**流程**:
1. 子类尝试从缓存获取程序
2. 调用 `incNumInlineProgramCacheResult(kHit/kMiss)`
3. 如果需要编译,调用 `incShaderCompilations()`
4. 根据结果调用成功/失败统计方法

### Facade 模式

`Stats` 类隐藏复杂的统计逻辑,提供简单的增量接口。

### 零开销抽象

非 `GR_GPU_STATS` 模式下,统计方法为空函数:

```cpp
void incShaderCompilations() {}  // 编译器会内联并消除
```

**效果**: Release 版本无任何开销,调用点代码被完全优化掉。

### 引用计数生命周期

继承 `SkRefCnt` 允许多个渲染上下文共享同一个 builder:
- 减少重复编译
- 统计数据全局聚合

### 防御性编程

`dump` 方法中的断言:

```cpp
SkASSERT(fNumInlineCompilationFailures == 0);
```

在测试中验证系统行为的正确性。

## 性能考量

### 原子操作开销

原子递增比普通递增慢:
- 需要内存屏障
- 可能导致缓存失效

**权衡**: 统计仅在开发版本启用,生产环境无影响。

### 缓存行竞争

多个原子变量可能在同一缓存行:

**影响**: 多线程写入可能导致伪共享(false sharing)。

**当前设计**: 统计更新频率相对较低(编译事件),影响有限。

### 条件编译的优势

```cpp
#if GR_GPU_STATS
    // 统计代码
#else
    // 空实现
#endif
```

**好处**:
- Release 版本二进制大小不增加
- 无运行时分支判断
- 编译器完全消除死代码

### load 操作的成本

```cpp
fShaderCompilations.load()
```

原子 load 在 x86/ARM 上通常是零成本的(普通内存读取)。

### 字符串格式化开销

`dump` 方法仅在测试环境调用:
- 不在热路径
- 格式化开销可接受

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/core/SkString.h` | 字符串工具(测试) |
| `include/private/base/SkTArray.h` | 动态数组(测试) |
| `include/core/SkTypes.h` | 基础类型定义 |
| `src/gpu/ganesh/vk/GrVkPipelineBuilder.h` | Vulkan 实现(子类) |
| `src/gpu/ganesh/mtl/GrMtlPipelineBuilder.h` | Metal 实现(子类) |
| `src/gpu/ganesh/d3d/GrD3DPipelineBuilder.h` | D3D12 实现(子类) |
