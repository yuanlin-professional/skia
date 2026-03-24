# GrGpuResourceCacheAccess

> 源文件: src/gpu/ganesh/GrGpuResourceCacheAccess.h

## 概述

`GrGpuResourceCacheAccess` 是 `GrGpuResource` 的特权访问器类,为 `GrResourceCache` 提供对资源内部状态的受控访问。它实现了友元类模式,允许缓存管理器执行资源管理操作(如生命周期控制、键值管理、时间戳维护等),同时不向公共 API 暴露这些敏感接口。

该类通过 `GrGpuResource::cacheAccess()` 方法获取,仅允许特定的友元类(主要是 `GrResourceCache`)使用。它是 Ganesh 资源管理体系中实现访问控制的关键组件。

## 架构位置

`GrGpuResourceCacheAccess` 位于 `GrGpuResource` 和 `GrResourceCache` 之间的桥接层:

```
GrResourceCache (缓存管理器)
    └── 通过 CacheAccess 访问 ───> GrGpuResource (资源对象)
                                        └── CacheAccess (特权接口)
```

架构角色:
- **特权访问器**: 提供受控的内部接口
- **访问控制**: 防止公共 API 暴露危险操作
- **缓存协议**: 定义缓存与资源的交互契约

## 主要类与结构体

### 继承关系

```
GrGpuResource::CacheAccess (嵌套类,无继承)
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fResource` | `GrGpuResource*` | 指向拥有的资源对象 |

## 公共 API 函数

### 生命周期管理

```cpp
// 从零引用转为一引用(仅缓存可调用)
void ref();

// 释放资源(删除 GPU 数据)
void release();

// 放弃资源(上下文丢失时)
void abandon();
```

### 引用计数查询

```cpp
// 检查资源是否有引用
bool hasRef() const;

// 检查资源是否有引用或命令缓冲区使用
bool hasRefOrCommandBufferUsage() const;
```

### Scratch 资源管理

```cpp
// 检查是否为可用的 Scratch 资源
// 必须满足: 是 Scratch 资源 && 无外部引用
bool isUsableAsScratch() const;

// 检查是否为 Scratch 资源
// 必须满足: 无 Unique Key && 有 Scratch Key && 可预算
bool isScratch() const;
```

### 键值管理

```cpp
// 设置 Unique Key(直接赋值,不通知缓存)
void setUniqueKey(const skgpu::UniqueKey& key);

// 移除 Unique Key(直接清除,不通知缓存)
void removeUniqueKey();
```

### 时间戳管理

```cpp
// 获取资源的时间戳(LRU 排序依据)
uint32_t timestamp() const;

// 设置时间戳(由缓存维护)
void setTimestamp(uint32_t ts);

// 记录资源变为可清除的时间点
void setTimeWhenResourceBecomePurgeable();

// 获取资源变为可清除的时间点
skgpu::StdSteadyClock::time_point timeWhenResourceBecamePurgeable();
```

### 缓存内部访问

```cpp
// 获取缓存数组索引的指针(供缓存修改)
int* accessCacheIndex() const;
```

## 内部实现细节

### 零引用到一引用转换

```cpp
void ref() {
    fResource->addInitialRef();  // 调用特权方法
}
```

- 仅缓存可以复活零引用资源
- 用于 Scratch 资源复用
- 必须确保资源仍在缓存中

### 资源释放

```cpp
void release() {
    fResource->release();  // 调用内部 release
    if (!fResource->hasRef() && fResource->hasNoCommandBufferUsages()) {
        delete fResource;  // 如果没有引用,直接删除
    }
}
```

- 先释放 GPU 资源
- 如果无引用和命令缓冲区使用,删除对象
- 否则等待引用计数归零

### 资源放弃

```cpp
void abandon() {
    fResource->abandon();  // 放弃 GPU 句柄
    if (!fResource->hasRef() && fResource->hasNoCommandBufferUsages()) {
        delete fResource;
    }
}
```

- 上下文丢失时调用
- 不释放 GPU 资源,仅放弃句柄
- 同样检查引用计数

### Scratch 资源判断

```cpp
bool isScratch() const {
    return !fResource->getUniqueKey().isValid() &&
           fResource->fScratchKey.isValid() &&
           GrBudgetedType::kBudgeted == fResource->resourcePriv().budgetedType();
}

bool isUsableAsScratch() const {
    return this->isScratch() && !fResource->internalHasRef();
}
```

- `isScratch()`: 资源是 Scratch 类型
- `isUsableAsScratch()`: 可以立即复用

### 键值操作

```cpp
void setUniqueKey(const skgpu::UniqueKey& key) {
    fResource->fUniqueKey = key;  // 直接访问私有成员
}

void removeUniqueKey() {
    fResource->fUniqueKey.reset();
}
```

- 直接修改私有成员
- 不触发缓存通知(调用者负责)

### 时间戳管理

```cpp
uint32_t timestamp() const {
    return fResource->fTimestamp;
}

void setTimestamp(uint32_t ts) {
    fResource->fTimestamp = ts;
}

void setTimeWhenResourceBecomePurgeable() {
    SkASSERT(fResource->isPurgeable());
    fResource->fTimeWhenBecamePurgeable = skgpu::StdSteadyClock::now();
}

skgpu::StdSteadyClock::time_point timeWhenResourceBecamePurgeable() {
    SkASSERT(fResource->isPurgeable());
    return fResource->fTimeWhenBecamePurgeable;
}
```

- 时间戳用于 LRU 缓存策略
- 可清除时间用于老化策略

### 缓存索引访问

```cpp
int* accessCacheIndex() const {
    return &fResource->fCacheArrayIndex;
}
```

- 返回指针允许缓存直接修改
- 用于维护堆/数组中的位置

### 构造函数

```cpp
CacheAccess(GrGpuResource* resource) : fResource(resource) {}
CacheAccess(const CacheAccess& that) : fResource(that.fResource) {}
```

- 私有构造函数
- 仅 `GrGpuResource` 可以创建
- 支持拷贝但不支持赋值

### 禁止取地址

```cpp
const CacheAccess* operator&() const = delete;
CacheAccess* operator&() = delete;
```

- 防止指针逃逸
- 确保只能按值传递

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGpuResource` | 被访问的资源类 |
| `GrGpuResourcePriv` | 访问资源的其他特权接口 |
| `skgpu::UniqueKey` | 唯一键类型 |
| `GrTypesPriv.h` | `GrBudgetedType` 等类型 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `GrResourceCache` | 主要使用者 |
| `GrGpuResource` | 提供 `cacheAccess()` 方法 |

## 设计模式与设计决策

### 设计模式

1. **友元访问器模式 (Friend Accessor)**
   - 通过嵌套类提供特权访问
   - 利用友元关系访问私有成员
   - 限制访问范围到特定类

2. **代理模式 (Proxy)**
   - 代理对 `GrGpuResource` 的访问
   - 提供受控的接口子集
   - 增加一层抽象

3. **不可取地址模式 (Non-Addressable)**
   - 删除 `operator&`
   - 防止指针逃逸
   - 强制按值使用

### 关键设计决策

1. **为何需要 CacheAccess?**
   - 缓存需要修改资源内部状态
   - 不能将这些操作暴露给公共 API
   - 通过友元关系精确控制访问

2. **为何是嵌套类而非友元函数?**
   - 组织相关操作为一组
   - 更清晰的命名空间
   - 避免友元函数污染全局命名空间

3. **为何禁止取地址?**
   - 防止 `CacheAccess*` 指针逃逸
   - 确保只有授权代码可以获取
   - 通过 `cacheAccess()` 控制访问点

4. **为何支持拷贝但禁止赋值?**
   - 允许按值传递和返回
   - 禁止赋值避免混淆资源指针
   - 简化生命周期管理

5. **ref() 的零引用到一引用特权**
   - 普通 `ref()` 断言引用计数 > 0
   - `CacheAccess::ref()` 可以从 0 到 1
   - 实现 Scratch 资源复用

6. **直接修改键值而非通过方法**
   - 避免重复通知缓存
   - 调用者负责维护缓存一致性
   - 减少函数调用层次

## 性能考量

### 零开销抽象

- 内联构造和访问方法
- 编译器优化后等同于直接访问
- Release 版本无运行时开销

### 引用计数检查

- `hasRef()` 和 `hasRefOrCommandBufferUsage()` 是简单的布尔检查
- 无同步开销(调用者确保线程安全)

### 时间戳访问

- 直接读写整数,极低开销
- 用于 LRU 排序的关键路径
- 避免函数调用层次

### 缓存索引指针

- 返回指针避免额外的 setter 调用
- 缓存可以直接修改索引
- 用于堆操作的高频路径

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuResource.h` | 宿主 | 定义被访问的资源类 |
| `src/gpu/ganesh/GrResourceCache.h` | 使用 | 主要使用者 |
| `src/gpu/ganesh/GrGpuResourcePriv.h` | 兄弟 | 另一个特权访问器 |
| `src/gpu/ResourceKey.h` | 依赖 | 键值系统 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | 类型定义 |
