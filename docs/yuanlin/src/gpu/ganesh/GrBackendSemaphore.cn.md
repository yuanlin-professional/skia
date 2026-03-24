# GrBackendSemaphore

> 源文件
> - include/gpu/ganesh/GrBackendSemaphore.h
> - src/gpu/ganesh/GrBackendSemaphore.cpp

## 概述

`GrBackendSemaphore` 是 Ganesh GPU 后端的信号量封装类,用于在 Skia 与底层图形 API(如 Vulkan、Metal、Direct3D)之间传递同步原语。该类提供了跨平台的信号量抽象,允许 Skia 和客户端代码在 GPU 操作之间进行同步,支持多队列渲染和跨 API 共享纹理等高级场景。

信号量主要用于 GPU 端的同步,而非 CPU 端同步。该类使用类型擦除技术(`SkAnySubclass`)存储后端特定的信号量数据,避免暴露底层 API 细节。

## 架构位置

`GrBackendSemaphore` 位于 Ganesh GPU 后端的同步基础设施层:

```
skia/
  include/gpu/ganesh/
    GrBackendSemaphore.h           # 公共接口
    GrTypes.h                      # 类型定义
  src/gpu/ganesh/
    GrBackendSemaphore.cpp         # 实现
    GrBackendSemaphorePriv.h       # 内部接口
    vk/GrVkSemaphore.h             # Vulkan 信号量
    mtl/GrMtlSemaphore.h           # Metal 信号量
```

该类被 `GrDirectContext` 的 `wait()` 和 `flush()` 方法使用,用于 GPU 同步操作。

## 主要类与结构体

### GrBackendSemaphore

跨平台信号量封装类。

**继承关系:**
- 基类: 无
- 派生类: 无(使用组合模式封装后端数据)

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBackend` | `GrBackendApi` | GPU 后端类型(默认 `kUnsupported`) |
| `fSemaphoreData` | `AnySemaphoreData` | 后端特定信号量数据(使用 `SkAnySubclass`) |

**类型别名:**
```cpp
using AnySemaphoreData = SkAnySubclass<GrBackendSemaphoreData, kMaxSubclassSize>;
```

**常量:**
- `kMaxSubclassSize = 24` - 内联存储大小(字节)

### GrBackendSemaphoreData

抽象基类,由后端特定实现继承。

**方法:**
- `copyTo()` - 复制信号量数据到目标对象
- 虚析构函数

## 公共 API 函数

### 构造与析构

```cpp
GrBackendSemaphore();
```
**功能:** 创建空的信号量对象
**后置条件:** `isInitialized()` 返回 `false`

```cpp
GrBackendSemaphore(const GrBackendSemaphore& that);
```
**功能:** 拷贝构造函数
**实现:** 使用赋值操作符实现

```cpp
~GrBackendSemaphore();
```
**功能:** 析构函数
**特点:** 默认实现,自动清理内联数据

### 操作符重载

```cpp
GrBackendSemaphore& operator=(const GrBackendSemaphore& that);
```
**功能:** 赋值操作符
**实现:**
- 检查后端类型匹配(断言)
- 复制后端类型和信号量数据
- 根据后端类型调用特定的 `copyTo` 方法

### 查询方法

```cpp
GrBackendApi backend() const;
```
**功能:** 获取 GPU 后端类型
**返回:** `GrBackendApi` 枚举值

```cpp
bool isInitialized() const;
```
**功能:** 检查信号量是否已初始化
**返回:** `true` 表示后端类型不是 `kUnsupported`

## 内部实现细节

### 模板构造函数

```cpp
template <typename SemaphoreData>
GrBackendSemaphore(GrBackendApi api, SemaphoreData data);
```
**特点:**
- 私有构造函数,仅供友元类调用
- 使用 `SkAnySubclass` 的 `emplace` 方法就地构造后端数据
- 支持编译期大小检查

**用途:** 由工厂函数(如 `GrBackendSemaphores::MakeVk`)调用

### 赋值操作符实现

```cpp
GrBackendSemaphore& GrBackendSemaphore::operator=(const GrBackendSemaphore& that) {
    SkASSERT(fBackend == GrBackendApi::kUnsupported || fBackend == that.fBackend);
    fBackend = that.fBackend;
    fSemaphoreData.reset();
    switch (that.fBackend) {
        case GrBackendApi::kOpenGL:
            SK_ABORT("Unsupported");
            break;
        case GrBackendApi::kVulkan:
        case GrBackendApi::kMetal:
        case GrBackendApi::kDirect3D:
            that.fSemaphoreData->copyTo(fSemaphoreData);
            break;
        default:
            SK_ABORT("Unknown GrBackend");
    }
    return *this;
}
```

**关键点:**
1. **后端类型检查** - 未初始化对象或相同后端类型才能赋值
2. **重置旧数据** - 调用 `reset()` 清理现有数据
3. **分支复制** - 根据后端类型选择复制策略
4. **OpenGL 不支持** - OpenGL 后端没有信号量概念

### `SkAnySubclass` 存储机制

`SkAnySubclass` 提供以下特性:
- **固定大小内联存储** - 24 字节栈上存储,避免堆分配
- **类型擦除** - 隐藏后端特定类型,提供统一接口
- **编译期大小检查** - 后端数据超出 24 字节会编译失败

### 后端支持情况

| 后端 | 支持状态 | 说明 |
|------|----------|------|
| Vulkan | ✅ 支持 | 使用 `VkSemaphore` |
| Metal | ✅ 支持 | 使用 `id<MTLEvent>` |
| Direct3D | ✅ 支持 | 使用 D3D 同步对象 |
| OpenGL | ❌ 不支持 | 触发 `SK_ABORT` |
| Dawn | 未知 | 代码中未提及 |

### 友元类访问

- `GrBackendSemaphorePriv` - 提供工厂方法和内部访问
- `GrBackendSemaphoreData` - 后端数据基类

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/gpu/ganesh/GrTypes.h` | GPU 类型定义 |
| `include/private/base/SkAPI.h` | 导出宏 |
| `include/private/base/SkAnySubclass.h` | 类型擦除容器 |
| `include/private/base/SkAssert.h` | 断言宏 |
| `include/private/base/SkDebug.h` | 调试工具 |
| `src/gpu/ganesh/GrBackendSemaphorePriv.h` | 内部接口 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `GrDirectContext` | `wait()` 和 `flush()` 方法使用信号量 |
| `GrResourceProvider` | 包装后端信号量为 `GrSemaphore` |
| Vulkan 后端 | 封装 `VkSemaphore` |
| Metal 后端 | 封装 `id<MTLEvent>` |
| 跨队列渲染 | 多队列同步场景 |

## 设计模式与设计决策

### 设计模式

1. **桥接模式 (Bridge Pattern)**
   - `GrBackendSemaphore` 是抽象接口
   - `GrBackendSemaphoreData` 是实现接口
   - 后端特定类是具体实现

2. **类型擦除 (Type Erasure)**
   - 使用 `SkAnySubclass` 隐藏后端类型
   - 避免模板导致的代码膨胀
   - 提供编译期类型安全

3. **友元类工厂 (Friend Factory)**
   - 构造函数私有,禁止直接创建
   - 友元类 `GrBackendSemaphorePriv` 提供工厂方法
   - 确保信号量创建的正确性

### 设计决策

1. **OpenGL 排除**
   - OpenGL 没有原生信号量概念
   - 使用栅栏同步(fences)而非信号量
   - 触发 `SK_ABORT` 防止误用

2. **内联存储优化**
   - 24 字节足够存储所有后端的句柄
   - 避免堆分配,提高性能
   - 适合频繁创建和销毁

3. **拷贝语义**
   - 支持拷贝构造和赋值
   - 复制的是句柄,非底层对象
   - 后端数据需实现 `copyTo` 方法

4. **后端类型检查**
   - 赋值时断言后端类型匹配
   - 防止跨后端信号量混用
   - 调试构建中捕获错误

5. **空对象模式**
   - 默认构造函数创建未初始化对象
   - `isInitialized()` 检查有效性
   - 避免使用可选类型(optional)

## 性能考量

1. **内联存储**
   - 24 字节栈上分配,无堆分配开销
   - 拷贝和赋值仅复制句柄,开销小

2. **分支预测**
   - 赋值操作符的 `switch` 语句
   - 实际使用中后端类型固定,分支预测友好

3. **避免虚函数**
   - 使用 `SkAnySubclass` 而非虚函数表
   - 减少间接调用开销

4. **零成本抽象**
   - 编译后的代码与直接使用后端类型相似
   - 类型擦除在编译期完成

5. **GPU 同步**
   - 信号量操作在 GPU 端,CPU 开销极小
   - 主要开销在 GPU 命令提交和等待

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/gpu/ganesh/GrBackendSemaphore.h` | 公共接口 |
| `src/gpu/ganesh/GrBackendSemaphore.cpp` | 实现 |
| `src/gpu/ganesh/GrBackendSemaphorePriv.h` | 内部接口和工厂方法 |
| `src/gpu/ganesh/vk/GrVkSemaphore.h` | Vulkan 信号量封装 |
| `src/gpu/ganesh/mtl/GrMtlSemaphore.h` | Metal 信号量封装 |
| `include/gpu/ganesh/GrDirectContext.h` | 使用信号量的上下文 API |
| `src/gpu/ganesh/GrResourceProvider.h` | 信号量包装器工厂 |
