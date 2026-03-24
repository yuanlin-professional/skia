# SkPixelStorage

> 源文件
> - src/core/SkPixelStorage.cpp

## 概述

`SkPixelStorage.cpp` 实现了 `SkPixelStorage` 基类的核心功能。`SkPixelStorage` 是 Skia 中像素存储的抽象基类，为 `SkPixelRef` 和其他像素存储类型提供统一的接口。该文件虽然只有20行代码，但定义了关键的 ID 生成机制，为像素存储提供唯一标识。

`SkPixelStorage` 是 Skia 最近引入的抽象层，用于统一管理不同类型的像素存储（如 `SkPixelRef` 和新的 GPU 纹理代理）。

## 架构位置

`SkPixelStorage` 位于 Skia 像素管理架构的基础层：

- 是 `SkPixelRef` 的基类
- 提供唯一 ID 生成机制
- 定义存储类型接口
- 统一像素存储抽象

## 主要类与结构体

### SkPixelStorage

像素存储基类（声明在头文件中）。

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fID | uint32_t | 唯一标识符 |

**类型枚举**（在头文件中）

```cpp
enum class Type {
    kPixelRef,      // 传统像素引用
    kTextureProxy,  // GPU 纹理代理（新增）
};
```

## 公共 API 函数

### 静态工厂方法

```cpp
// 生成下一个唯一 ID
static uint32_t NextId();
```

### 构造函数

```cpp
// 构造函数（分配唯一 ID）
SkPixelStorage();
```

## 内部实现细节

### ID 生成机制

```cpp
uint32_t SkPixelStorage::NextId() {
    static std::atomic<uint32_t> gNextID{1};  // 从1开始
    uint32_t id;
    do {
        id = gNextID.fetch_add(1, std::memory_order_relaxed);
    } while (id == 0);  // 跳过0（保留为无效ID）
    return id;
}
```

**关键设计**：
- 使用原子计数器保证线程安全
- 从1开始，跳过0（0表示无效）
- 使用 `memory_order_relaxed` 优化性能
- 循环跳过溢出到0的情况

### 构造函数实现

```cpp
SkPixelStorage::SkPixelStorage() : fID(NextId()) {}
```

每个 `SkPixelStorage` 实例在构造时自动分配唯一 ID。

### ID 用途

唯一 ID 用于：
1. **资源缓存**：作为缓存键的一部分
2. **失效追踪**：检测像素数据变更
3. **引用比较**：快速判断是否引用相同存储
4. **调试追踪**：追踪存储对象的生命周期

### 与 SkPixelRef 的关系

`SkPixelRef` 继承 `SkPixelStorage`：

```cpp
class SkPixelRef : public SkPixelStorage, public SkRefCnt {
    // SkPixelRef 使用继承的 fID
    // 但也有自己的 generation ID 机制（追踪内容变更）
};
```

**两种 ID 的区别**：
- `SkPixelStorage::fID`：标识存储对象本身（不变）
- `SkPixelRef::getGenerationID()`：标识像素内容版本（可变）

### 线程安全

ID 生成是线程安全的：
- 使用 `std::atomic` 原子操作
- `fetch_add` 保证原子递增
- 无需额外的锁
- 多线程并发创建安全

### ID 溢出处理

虽然使用32位 ID，溢出处理确保不返回0：

```cpp
do {
    id = gNextID.fetch_add(1, std::memory_order_relaxed);
} while (id == 0);
```

理论上可能溢出（约40亿个对象后），但实际应用中不太可能。

### 内存顺序优化

使用 `memory_order_relaxed`：
- 不保证与其他操作的顺序
- 仅保证原子性
- 适用于 ID 生成（不需要同步）
- 最小化性能开销

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| atomic | 原子操作 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| SkPixelRef | 继承 SkPixelStorage |
| 未来的 TextureProxy | 可能继承 SkPixelStorage |
| 资源缓存 | 使用 ID 作为键 |

## 设计模式与设计决策

### 抽象基类

`SkPixelStorage` 提供统一抽象：
- 不同存储类型的共同接口
- 便于扩展新的存储类型
- 统一的 ID 管理

### 单例模式（ID 生成器）

静态原子计数器是单例：
- 全局唯一的 ID 序列
- 无需显式单例类
- 简单高效

### 值对象语义

ID 是值类型：
- 不可变（构造后）
- 可拷贝
- 轻量级

### 零值无效

ID 0 保留为无效：
- 便于初始化检查
- 明确的"无效"语义
- 与指针 NULL 类似

## 性能考量

### 原子操作开销

虽然使用原子操作，开销已最小化：
- `fetch_add` 是最快的原子操作之一
- `memory_order_relaxed` 无内存栅栏
- 构造时仅执行一次

### 无锁设计

避免使用互斥锁：
- 减少上下文切换
- 更好的并发性能
- 适合高频创建场景

### 内联优化

简单的内联函数：
- 构造函数可内联
- `NextId()` 可内联
- 零调用开销

### 缓存行竞争

静态原子变量可能导致缓存行竞争：
- 多线程同时递增可能竞争
- 对于频繁创建场景可能成为瓶颈
- 实际应用中通常不是问题

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| include/private/SkPixelStorage.h | 基类声明 |
| include/core/SkPixelRef.h | 主要子类 |
| src/core/SkPixelRef.cpp | SkPixelRef 实现 |
| src/core/SkBitmapCache.cpp | 使用 ID 进行缓存 |
