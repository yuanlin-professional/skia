# SkScopeExit

> 源文件: src/base/SkScopeExit.h

## 概述

`SkScopeExit` 是 Skia 中实现的 RAII（Resource Acquisition Is Initialization）辅助类，用于在作用域结束时自动执行清理代码。它封装了一个 `std::function<void()>`，并在析构时调用该函数。这个轻量级工具简化了异常安全的资源管理和清理逻辑，是现代 C++ 中常见的"作用域守卫"（scope guard）模式的实现。

该类特别适用于需要在函数退出时（无论正常返回还是异常退出）执行清理操作的场景，如释放锁、恢复状态、记录日志等。

## 架构位置

`SkScopeExit` 位于 Skia 基础设施层的工具模块中：

- **层级**: src/base（基础工具层）
- **用途**: 提供作用域退出时的自动清理机制
- **应用场景**: 资源清理、状态恢复、异常安全代码

在 Skia 架构中，它是一个通用的 RAII 工具，被各种需要清理逻辑的模块使用。

## 主要类与结构体

### SkScopeExit

作用域退出执行器类。

**继承关系**:
- 无继承关系

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFn` | `std::function<void()>` | 存储待执行的清理函数 |

## 公共 API 函数

### 构造函数

```cpp
SkScopeExit() = default;                       // 默认构造，无清理函数
explicit SkScopeExit(std::function<void()> f); // 指定清理函数
SkScopeExit(SkScopeExit&& that);               // 移动构造
```

### 析构函数

```cpp
~SkScopeExit();  // 若 fFn 非空，则调用清理函数
```

### 操作方法

```cpp
void clear();                                   // 清除清理函数，不再执行
SkScopeExit& operator=(SkScopeExit&& that);    // 移动赋值
```

### 禁用的操作

```cpp
SkScopeExit(const SkScopeExit&) = delete;             // 禁用拷贝构造
SkScopeExit& operator=(const SkScopeExit&) = delete;  // 禁用拷贝赋值
```

## 内部实现细节

### 构造函数实现

```cpp
SkScopeExit() = default;

explicit SkScopeExit(std::function<void()> f) : fFn(std::move(f)) {}

SkScopeExit(SkScopeExit&& that) : fFn(std::move(that.fFn)) {}
```

**要点**:
- 默认构造函数创建空的清理函数
- 显式构造函数接受任何可转换为 `std::function<void()>` 的对象（lambda、函数指针、函数对象等）
- 使用 `std::move` 避免不必要的拷贝

### 析构函数实现

```cpp
~SkScopeExit() {
    if (fFn) {
        fFn();
    }
}
```

**关键特性**:
- 检查 `fFn` 是否为空（默认构造或已 `clear()` 的情况）
- 仅在非空时调用清理函数
- 异常安全：即使构造过程中抛异常，已构造的对象会正常析构

### clear 方法

```cpp
void clear() { fFn = {}; }
```

- 将 `fFn` 重置为空函数对象
- 用于取消预定的清理操作（如提前完成资源释放）

### 移动赋值

```cpp
SkScopeExit& operator=(SkScopeExit&& that) {
    fFn = std::move(that.fFn);
    return *this;
}
```

- 移动语义支持在容器中存储 `SkScopeExit`
- 被移动的对象变为空状态

### 禁用拷贝

```cpp
SkScopeExit(const SkScopeExit&) = delete;
SkScopeExit& operator=(const SkScopeExit&) = delete;
```

**原因**:
- 拷贝会导致多次执行同一清理函数（未定义行为）
- 强制使用移动语义或引用

## 宏 - SK_AT_SCOPE_EXIT

### 定义

```cpp
#define SK_AT_SCOPE_EXIT(stmt) \
    SkScopeExit SK_MACRO_APPEND_LINE(at_scope_exit_)([&]() { stmt; })
```

### 功能

在当前作用域结束时执行指定的语句。

### 实现细节

- `SK_MACRO_APPEND_LINE` 生成唯一的变量名（基于行号），避免命名冲突
- `[&]()` 创建捕获所有外部变量的 lambda
- 自动创建一个匿名 `SkScopeExit` 对象

### 使用示例

```cpp
{
    int x = 5;
    {
        SK_AT_SCOPE_EXIT(x--);
        SkASSERT(x == 5);  // 清理还未执行
    }
    SkASSERT(x == 4);      // 清理已执行
}
```

### 典型用例

```cpp
void processData() {
    lock.acquire();
    SK_AT_SCOPE_EXIT(lock.release());  // 自动释放锁

    // ... 处理数据 ...
    // 即使中途 return 或抛异常，锁也会被释放
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<functional>` | `std::function` 类型 |
| `<utility>` | `std::move` 函数 |
| `SkMacros.h` | `SK_MACRO_APPEND_LINE` 宏 |

### 被依赖的模块

`SkScopeExit` 作为通用 RAII 工具，被以下场景使用：

| 使用场景 | 说明 |
|---------|------|
| 资源释放 | 自动关闭文件句柄、释放内存 |
| 状态恢复 | 临时修改状态后自动恢复 |
| 日志记录 | 函数退出时记录日志 |
| 性能测量 | 自动计算函数执行时间 |
| 异常安全 | 确保清理代码在异常时也执行 |

## 设计模式与设计决策

### 设计模式

1. **RAII 模式**:
   - 构造时绑定清理函数
   - 析构时自动执行清理
   - 保证资源管理的异常安全性

2. **类型擦除**:
   - 使用 `std::function` 接受任意可调用对象
   - 隐藏具体类型，提供统一接口

3. **宏辅助模式**:
   - `SK_AT_SCOPE_EXIT` 宏简化常见用法
   - 自动生成 lambda 和变量名

### 设计决策

1. **使用 std::function 而非模板**:
   - 优点: 类型统一，可存储不同类型的可调用对象
   - 缺点: 有一定的间接调用开销（通常可忽略）
   - 原因: 简化实现，避免模板膨胀

2. **explicit 构造函数**:
   - 防止隐式转换导致的意外行为
   - 强制显式创建清理守卫

3. **禁用拷贝，允许移动**:
   - 拷贝语义不明确（是否应该复制清理函数？）
   - 移动语义清晰（转移所有权）

4. **检查函数是否为空**:
   - 支持默认构造和 `clear()` 操作
   - 避免调用空函数对象的未定义行为

5. **宏捕获所有变量**:
   - `[&]` 捕获所有局部变量的引用
   - 优点: 使用方便
   - 风险: 若 lambda 逃逸作用域会导致悬垂引用（但析构时执行不会有此问题）

6. **没有提供条件执行**:
   - 不支持 "仅在成功时执行" 或 "仅在失败时执行"
   - 原因: 保持简单，复杂逻辑由用户在 lambda 中实现

## 性能考量

### 性能开销

1. **构造开销**:
   - `std::function` 构造: 约 10-50 纳秒（取决于可调用对象大小）
   - 小型 lambda（无捕获或少量捕获）: 约 10 纳秒
   - 大型 lambda 或函数对象: 可能涉及堆分配（约 100 纳秒）

2. **析构开销**:
   - 函数调用: 约 5-10 纳秒（虚函数调用开销）
   - 清理函数本身的执行时间

3. **内存占用**:
   - `sizeof(SkScopeExit)` ≈ `sizeof(std::function)` ≈ 32-48 字节（平台相关）

### 优化建议

1. **小型 lambda 优化**:
   - `std::function` 对小型可调用对象有 SBO（Small Buffer Optimization）
   - 捕获少量值可避免堆分配

2. **避免重量级清理函数**:
   - 清理函数应尽量简单快速
   - 复杂逻辑考虑延迟到专门的清理阶段

3. **复用 SkScopeExit 对象**:
   - 移动赋值允许复用对象
   - 避免频繁创建销毁

### 性能权衡

| 方面 | SkScopeExit | 手动清理 | RAII 专用类 |
|------|-------------|----------|-------------|
| 易用性 | 高 | 低 | 中 |
| 性能 | 中（10-50 ns 开销） | 最高 | 高（< 5 ns） |
| 灵活性 | 高 | 高 | 低 |
| 异常安全 | 自动 | 手动 | 自动 |

### 使用建议

1. **适用场景**:
   - 清理逻辑简单但需要异常安全
   - 一次性的临时清理需求
   - 不想为每种资源写专用 RAII 类

2. **不适用场景**:
   - 极端性能敏感的热点路径（考虑专用 RAII 类）
   - 需要复杂的清理逻辑控制（如条件执行）
   - 清理函数需要参数（需外部捕获）

3. **最佳实践**:
   ```cpp
   // 推荐: 使用宏
   SK_AT_SCOPE_EXIT(cleanup());

   // 可行: 显式创建
   SkScopeExit guard([]() { cleanup(); });

   // 避免: 捕获大量变量导致性能下降
   SkScopeExit guard([=]() { /* 拷贝所有变量 */ });
   ```

4. **与专用 RAII 类的选择**:
   - 频繁使用的资源（如锁）→ 专用类（`SkAutoMutexExclusive`）
   - 一次性清理 → `SkScopeExit`
   - 复杂生命周期 → 专用类

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/base/SkMacros.h` | 提供 `SK_MACRO_APPEND_LINE` 等宏工具 |
| `include/private/base/SkMutex.h` | 使用 RAII 管理锁（类似但专用） |
| `src/core/SkAutoPixmapStorage.h` | 使用 RAII 管理像素内存 |
| `src/gpu/ganesh/GrResourceCache.cpp` | 可能使用 SkScopeExit 进行状态恢复 |
| C++17 `<scope_guard>` | 标准提案（未纳入标准），类似功能 |
