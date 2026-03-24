# GrGpuResourcePriv

> 源文件: src/gpu/ganesh/GrGpuResourcePriv.h

## 概述

`GrGpuResourcePriv` 是 `GrGpuResource` 的特权访问器类,为 Skia 内部代码提供对 GPU 资源的缓存键、预算状态等内部属性的管理能力。与 `GrGpuResourceCacheAccess` 相比,`ResourcePriv` 提供更广泛的内部访问,不仅限于缓存管理器,还包括其他内部模块。

该类允许内部代码设置唯一键、修改预算状态、访问 Scratch Key、检查资源的可清除性等操作,这些都是实现高效资源管理所必需的内部接口。

## 架构位置

`GrGpuResourcePriv` 位于资源访问控制层,与 `CacheAccess` 并行:

```
GrGpuResource
    ├── CacheAccess (专为缓存设计)
    └── ResourcePriv (更广泛的内部访问)
```

使用场景:
- `GrSurfaceProxy` 设置资源的唯一键
- 内部代码检查资源预算状态
- 资源提供器修改预算类型
- 调试和测试代码访问内部状态

## 主要类与结构体

### 继承关系

```
GrGpuResource::ResourcePriv (嵌套类,无继承)
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fResource` | `GrGpuResource*` | 指向拥有的资源对象 |

## 公共 API 函数

### 唯一键管理

```cpp
// 设置资源的唯一键
// 如果键无效,等同于 removeUniqueKey()
// 如果其他资源使用该键,会移除其键并转移给当前资源
void setUniqueKey(const skgpu::UniqueKey& key);

// 移除唯一键
// 如果资源有 Scratch Key,可能保留以供回收
void removeUniqueKey();
```

### 预算管理

```cpp
// 将未预算资源转为可预算
// 对包装资源或已预算资源无效
void makeBudgeted();

// 将可预算资源转为未预算
// 对包装资源、未预算资源或有唯一键的资源无效
void makeUnbudgeted();

// 获取资源的预算类型
GrBudgetedType budgetedType() const;
```

### 资源属性查询

```cpp
// 检查资源是否包装外部 GPU 对象
bool refsWrappedObjects() const;

// 获取 Scratch Key
// 如果资源可作为 Scratch 使用,返回有效键
// 否则返回空键
const skgpu::ScratchKey& getScratchKey() const;

// 检查资源是否可清除
// 可清除条件: 无引用 && 无命令缓冲区使用 && (无唯一键或可预算)
bool isPurgeable() const;

// 检查资源是否有引用或命令缓冲区使用
bool hasRefOrCommandBufferUsage() const;
```

### Scratch Key 管理

```cpp
// 移除 Scratch Key
// 移除后资源永远不能再作为 Scratch 使用
void removeScratchKey() const;
```

## 内部实现细节

### setUniqueKey 实现

```cpp
void setUniqueKey(const skgpu::UniqueKey& key) {
    fResource->setUniqueKey(key);  // 调用私有方法
}
```

- 调用 `GrGpuResource` 的私有 `setUniqueKey()`
- 私有方法处理缓存通知和键值冲突
- 如果键无效,内部会移除现有键

### removeUniqueKey 实现

```cpp
void removeUniqueKey() {
    fResource->removeUniqueKey();
}
```

- 移除资源的唯一键
- 如果有 Scratch Key,资源变为 Scratch 资源
- 通知缓存更新索引

### makeBudgeted 实现

```cpp
void makeBudgeted() {
    fResource->makeBudgeted();
}
```

- 调用私有方法转为可预算
- 检查约束条件(非包装资源)
- 通知缓存更新预算统计

### makeUnbudgeted 实现

```cpp
void makeUnbudgeted() {
    fResource->makeUnbudgeted();
}
```

- 转为未预算资源
- 要求无唯一键(有唯一键的资源必须可预算)
- 通知缓存更新

### budgetedType 实现

```cpp
GrBudgetedType budgetedType() const {
    SkASSERT(GrBudgetedType::kBudgeted == fResource->fBudgetedType ||
             !fResource->getUniqueKey().isValid() ||
             fResource->fRefsWrappedObjects);
    return fResource->fBudgetedType;
}
```

- 直接访问私有成员
- 断言检查不变量:可预算资源或无唯一键或包装对象

### refsWrappedObjects 实现

```cpp
bool refsWrappedObjects() const {
    return fResource->fRefsWrappedObjects;
}
```

- 检查是否包装外部 GPU 对象
- 包装资源永远不可预算

### getScratchKey 实现

```cpp
const skgpu::ScratchKey& getScratchKey() const {
    return fResource->fScratchKey;
}
```

- 返回 Scratch Key 的引用
- 如果无效,返回空键

### removeScratchKey 实现

```cpp
void removeScratchKey() const {
    fResource->removeScratchKey();
}
```

- 调用私有方法移除 Scratch Key
- 通知缓存更新 Scratch 索引
- 资源不再可回收

### isPurgeable 实现

```cpp
bool isPurgeable() const {
    return fResource->isPurgeable();
}
```

- 调用资源的私有 `isPurgeable()` 方法
- 检查无引用、无命令缓冲区使用、预算状态

### hasRefOrCommandBufferUsage 实现

```cpp
bool hasRefOrCommandBufferUsage() const {
    return fResource->hasRef() ||
           !fResource->hasNoCommandBufferUsages();
}
```

- 检查是否有任何形式的使用
- 用于判断是否可以清除

### 构造函数

```cpp
protected:
    ResourcePriv(GrGpuResource* resource) : fResource(resource) {}
    ResourcePriv(const ResourcePriv& that) : fResource(that.fResource) {}
```

- 受保护构造函数
- 支持拷贝构造
- 不支持赋值

### 禁止赋值和取地址

```cpp
ResourcePriv& operator=(const CacheAccess&) = delete;

const ResourcePriv* operator&() const;
ResourcePriv* operator&();
```

- 禁止赋值操作
- 声明但不定义 `operator&`
- 防止指针逃逸

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGpuResource` | 被访问的资源类 |
| `skgpu::UniqueKey` | 唯一键类型 |
| `skgpu::ScratchKey` | 临时键类型 |
| `GrTypesPriv.h` | `GrBudgetedType` 定义 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `GrSurfaceProxy` | 设置资源的唯一键 |
| `GrResourceProvider` | 修改资源预算状态 |
| `GrDirectContextPriv` | 内部资源操作 |
| 测试代码 | 访问资源内部状态 |

## 设计模式与设计决策

### 设计模式

1. **特权访问器模式 (Privileged Accessor)**
   - 为内部代码提供受控访问
   - 通过友元关系访问私有成员
   - 限制公共 API 的暴露

2. **代理模式 (Proxy)**
   - 代理对资源内部状态的访问
   - 提供简化的接口
   - 封装实现细节

3. **不可取地址模式 (Non-Addressable)**
   - 防止指针泄露
   - 强制通过 `resourcePriv()` 获取
   - 维护访问控制

### 关键设计决策

1. **ResourcePriv 与 CacheAccess 的区别**
   - `CacheAccess`: 专为 `GrResourceCache` 设计,更底层
   - `ResourcePriv`: 更广泛的内部访问,多个模块可用
   - 分离关注点,明确访问权限

2. **为何 makeBudgeted/makeUnbudgeted?**
   - 某些资源初始为未预算,后来需要加入预算
   - 支持动态调整资源管理策略
   - 例如: 包装资源可能后来转为非包装

3. **为何唯一键资源不能 makeUnbudgeted?**
   - 唯一键意味着资源是重要的,应该被跟踪
   - 未预算资源可能随时被清除
   - 保持语义一致性

4. **removeScratchKey 的永久性**
   - Scratch Key 在创建时计算
   - 移除后无法恢复
   - 用于将临时资源"升级"为持久资源

5. **isPurgeable 的复杂逻辑**
   - 考虑多种条件: 引用、命令缓冲区、预算、键
   - 包装资源的特殊规则
   - 封装复杂性,简化调用者代码

6. **refsWrappedObjects 的重要性**
   - 包装资源有特殊的生命周期规则
   - 永远不可预算
   - 支持外部 GPU 对象的集成

## 性能考量

### 零开销抽象

- 内联方法调用
- 编译器优化后等同于直接访问
- 无额外的运行时开销

### 直接成员访问

```cpp
return fResource->fBudgetedType;
```

- 避免虚函数调用
- 无 getter 函数开销
- 快速的状态查询

### 断言检查

```cpp
SkASSERT(条件);
```

- 仅在 Debug 模式执行
- Release 版本完全移除
- 无运行时开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuResource.h` | 宿主 | 定义被访问的资源类 |
| `src/gpu/ganesh/GrGpuResourceCacheAccess.h` | 兄弟 | 缓存特权访问器 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 使用 | 设置唯一键 |
| `src/gpu/ganesh/GrResourceProvider.h` | 使用 | 资源分配和管理 |
| `src/gpu/ResourceKey.h` | 依赖 | 键值系统 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | 类型定义 |
