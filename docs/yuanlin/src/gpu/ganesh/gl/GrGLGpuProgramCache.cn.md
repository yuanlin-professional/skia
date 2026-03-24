# GrGLGpuProgramCache

> 源文件
> - src/gpu/ganesh/gl/GrGLGpuProgramCache.cpp

## 概述

`GrGLGpuProgramCache.cpp` 实现了 `GrGLGpu::ProgramCache` 类，负责管理已编译的 OpenGL 着色器程序缓存。该缓存使用 LRU（Least Recently Used）策略，避免重复编译相同的着色器程序，显著提升渲染性能。它还支持预编译程序（precompiled programs），允许在后台线程中预先编译着色器并存储在缓存中。

该缓存是 Skia GPU 渲染管线的关键性能优化组件，通过缓存 `GrGLProgram` 对象来减少昂贵的着色器编译和链接操作。缓存以 `GrProgramDesc`（程序描述符）为键，程序对象为值。

## 架构位置

```
GrGLGpu
    └── ProgramCache
        ├── SkLRUCache<GrProgramDesc, Entry>
        └── Stats (统计信息)

调用链:
GrGLGpu::getProgram() -> ProgramCache::findOrCreateProgram() -> GrGLProgramBuilder
```

该类是 `GrGLGpu` 的内部组件，负责程序对象的生命周期管理和性能优化。

## 主要类与结构体

### GrGLGpu::ProgramCache

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fMap` | `SkLRUCache<GrProgramDesc, std::unique_ptr<Entry>>` | LRU 缓存映射 |
| `fStats` | `Stats` | 缓存统计信息 |

### Entry 结构体

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProgram` | `sk_sp<GrGLProgram>` | 完整的 GL 程序对象 |
| `fPrecompiledProgram` | `GrGLPrecompiledProgram` | 预编译的程序（仅 GL 对象） |

**构造函数:**
```cpp
Entry(sk_sp<GrGLProgram> program)
    : fProgram(std::move(program)) {}

Entry(const GrGLPrecompiledProgram& precompiledProgram)
    : fPrecompiledProgram(precompiledProgram) {}
```

## 公共 API 函数

### 构造与析构
- `ProgramCache(int runtimeProgramCacheSize)` - 构造函数，设置缓存大小
- `~ProgramCache()` - 析构函数

### 缓存管理
- `void abandon()` - 放弃所有 GL 对象（上下文丢失时调用）
- `void reset()` - 重置缓存，清空所有条目

### 程序查找/创建
- `sk_sp<GrGLProgram> findOrCreateProgram(GrDirectContext*, const GrProgramInfo&)` - 查找或创建程序（内联编译）
- `sk_sp<GrGLProgram> findOrCreateProgram(GrDirectContext*, const GrProgramDesc&, const GrProgramInfo&, Stats::ProgramCacheResult*)` - 查找或创建程序（预编译）

### 预编译
- `bool precompileShader(GrDirectContext*, const SkData& key, const SkData& data)` - 预编译着色器

## 内部实现细节

### 缓存查找与创建流程

`findOrCreateProgramImpl` 实现了三级查找策略：

```cpp
sk_sp<GrGLProgram> ProgramCache::findOrCreateProgramImpl(
        GrDirectContext* dContext,
        const GrProgramDesc& desc,
        const GrProgramInfo& programInfo,
        Stats::ProgramCacheResult* stat) {

    *stat = Stats::ProgramCacheResult::kHit;
    std::unique_ptr<Entry>* entry = fMap.find(desc);

    // 情况 1: 缓存命中，但仅有预编译程序
    if (entry && !(*entry)->fProgram) {
        const GrGLPrecompiledProgram* precompiledProgram = &((*entry)->fPrecompiledProgram);
        SkASSERT(precompiledProgram->fProgramID != 0);

        // 从预编译程序创建完整的 GrGLProgram
        (*entry)->fProgram = GrGLProgramBuilder::CreateProgram(
            dContext, desc, programInfo, precompiledProgram);

        if (!(*entry)->fProgram) {
            SkDEBUGFAIL("Couldn't create program from precompiled program");
            fStats.incNumCompilationFailures();
            return nullptr;
        }

        fStats.incNumPartialCompilationSuccesses();
        *stat = Stats::ProgramCacheResult::kPartial;
    }
    // 情况 2: 缓存未命中，需要完整编译
    else if (!entry) {
        sk_sp<GrGLProgram> program = GrGLProgramBuilder::CreateProgram(
            dContext, desc, programInfo);

        if (!program) {
            fStats.incNumCompilationFailures();
            return nullptr;
        }

        fStats.incNumCompilationSuccesses();
        entry = fMap.insert(desc, std::make_unique<Entry>(std::move(program)));
        *stat = Stats::ProgramCacheResult::kMiss;
    }
    // 情况 3: 缓存命中，完整程序
    // (*stat 已经设置为 kHit)

    return (*entry)->fProgram;
}
```

### 预编译着色器

```cpp
bool ProgramCache::precompileShader(GrDirectContext* dContext,
                                    const SkData& key,
                                    const SkData& data) {
    GrProgramDesc desc;
    if (!GrProgramDesc::BuildFromData(&desc, key.data(), key.size())) {
        return false;
    }

    std::unique_ptr<Entry>* entry = fMap.find(desc);
    if (entry) {
        // 已经存在，跳过
        return true;
    }

    // 预编译 GL 程序（不创建 GrGLProgram 包装）
    GrGLPrecompiledProgram precompiledProgram;
    if (!GrGLProgramBuilder::PrecompileProgram(dContext, &precompiledProgram, data)) {
        return false;
    }

    // 插入缓存
    fMap.insert(desc, std::make_unique<Entry>(precompiledProgram));
    return true;
}
```

### 放弃所有程序

```cpp
void ProgramCache::abandon() {
    fMap.foreach([](const GrProgramDesc*, std::unique_ptr<Entry>* e) {
        if ((*e)->fProgram) {
            (*e)->fProgram->abandon();
        }
    });

    this->reset();
}
```

### 统计信息收集

代码中多处调用 `fStats` 的方法记录缓存性能：

```cpp
// 内联编译路径
if (!tmp) {
    fStats.incNumInlineCompilationFailures();
} else {
    fStats.incNumInlineProgramCacheResult(stat);
}

// 预编译路径
if (!tmp) {
    fStats.incNumPreCompilationFailures();
} else {
    fStats.incNumPreProgramCacheResult(*stat);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLProgram` | 缓存的程序对象 |
| `GrGLProgramBuilder` | 创建和编译程序 |
| `GrProgramDesc` | 程序描述符，用作缓存键 |
| `GrProgramInfo` | 程序信息，用于编译 |
| `SkLRUCache` | LRU 缓存实现 |
| `GrDirectContext` | 图形上下文 |
| `GrCaps` | 能力查询 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLGpu` | 使用该缓存管理程序 |

## 设计模式与设计决策

### 1. LRU 缓存策略

使用 `SkLRUCache` 实现最近最少使用策略：

```cpp
SkLRUCache<GrProgramDesc, std::unique_ptr<Entry>> fMap;
```

**优势**:
- 自动淘汰最少使用的程序
- 限制内存使用
- 简化缓存管理

### 2. 两阶段编译

支持预编译（仅 GL 对象）和完整编译（包含 GrGLProgram 包装）：

```cpp
// 预编译阶段: GrGLPrecompiledProgram (仅 GL program ID)
// 完整编译阶段: GrGLProgram (完整对象，包含 uniform 管理等)
```

**优势**:
- 允许后台预编译
- 延迟创建昂贵的 C++ 对象
- 减少主线程阻塞

### 3. 智能指针管理

使用 `std::unique_ptr` 和 `sk_sp` 管理所有权：

```cpp
SkLRUCache<GrProgramDesc, std::unique_ptr<Entry>> fMap;
sk_sp<GrGLProgram> fProgram;
```

**优势**:
- 自动内存管理
- 明确所有权语义

### 4. 统计信息分离

缓存统计独立于核心逻辑：

```cpp
fStats.incNumCompilationSuccesses();
fStats.incNumPartialCompilationSuccesses();
fStats.incNumCompilationFailures();
```

**优势**:
- 便于性能分析
- 不影响核心功能

## 性能考量

### 1. 缓存命中率优化

通过 LRU 策略保留最常用的程序：

```cpp
ProgramCache(int runtimeProgramCacheSize)
    : fMap(runtimeProgramCacheSize) {}
```

**典型缓存大小**: 256-512 个程序

### 2. 预编译减少主线程阻塞

预编译允许在后台线程编译：

```cpp
// 后台线程
bool precompileShader(GrDirectContext*, const SkData& key, const SkData& data);

// 主线程（快速）
auto program = findOrCreateProgram(...);  // 如果预编译了，只需创建包装
```

### 3. 避免重复编译

着色器编译是昂贵操作（通常 10-100ms），缓存可减少 99%+ 的编译：

```cpp
// 首次绘制: 100ms (编译)
// 后续绘制: <1ms (缓存命中)
```

### 4. 内存与速度权衡

通过调整缓存大小平衡内存和性能：

```cpp
// 小缓存: 低内存，但可能需要重新编译
// 大缓存: 高内存，但几乎总是命中
```

## 缓存行为示例

### 场景 1: 冷启动

```cpp
// 第一次绘制
auto program = cache.findOrCreateProgram(ctx, programInfo);
// -> 缓存未命中 (kMiss)
// -> 调用 GrGLProgramBuilder::CreateProgram()
// -> 编译着色器 (耗时)
// -> 插入缓存
// -> 返回程序

// 第二次绘制相同内容
auto program2 = cache.findOrCreateProgram(ctx, programInfo);
// -> 缓存命中 (kHit)
// -> 直接返回缓存的程序
```

### 场景 2: 预编译

```cpp
// 后台线程预编译
cache.precompileShader(ctx, keyData, shaderData);
// -> 编译 GL 程序
// -> 创建 Entry(GrGLPrecompiledProgram)
// -> 插入缓存

// 主线程首次使用
auto program = cache.findOrCreateProgram(ctx, programInfo);
// -> 缓存部分命中 (kPartial)
// -> 从预编译程序创建 GrGLProgram 包装
// -> 更新 Entry
// -> 返回程序
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/gl/GrGLGpu.h` | 所有者 | ProgramCache 是 GrGLGpu 的嵌套类 |
| `src/gpu/ganesh/gl/GrGLProgram.h` | 缓存对象 | 被缓存的程序类型 |
| `src/gpu/ganesh/gl/builders/GrGLProgramBuilder.h` | 构建器 | 创建程序对象 |
| `src/gpu/ganesh/GrProgramDesc.h` | 缓存键 | 程序描述符 |
| `src/core/SkLRUCache.h` | 缓存实现 | LRU 缓存容器 |
| `src/gpu/ganesh/GrProgramInfo.h` | 依赖 | 程序信息 |
| `include/core/SkData.h` | 依赖 | 预编译数据容器 |
