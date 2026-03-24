# SkAutoMalloc

> 源文件: `src/base/SkAutoMalloc.h`

## 概述

SkAutoMalloc 提供堆内存的 RAII 包装,自动管理内存块的生命周期。它支持动态调整大小、可选的栈内联存储(SkAutoSMalloc),并在析构时自动释放内存。该类是 Skia 内存管理的基础工具,确保异常安全和资源正确释放。

## 架构位置

- **所属子系统**: 基础设施层 (Base Infrastructure)
- **层级**: 内存管理 - RAII 包装器
- **作用域**: 为 Skia 各模块提供安全的动态内存管理

## 主要类与结构体

### SkAutoMalloc

堆内存块的 RAII 管理器,独占所有权。

**继承关系**: SkNoncopyable → SkAutoMalloc

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fPtr | std::unique_ptr<void, WrapFree> | 内存块指针,带自定义删除器 |
| fSize | size_t | 当前分配的大小 |

**OnShrink 枚举**:
| 值 | 说明 |
|----|------|
| kAlloc_OnShrink | 缩小时释放旧块,分配新的更小块 |
| kReuse_OnShrink | 缩小时重用现有块,不重新分配 |

### SkAutoSMalloc<kSizeRequested>

带栈内联存储的智能内存管理器模板。

**继承关系**: SkNoncopyable → SkAutoSMalloc

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fPtr | void* | 指向当前使用的内存(栈或堆) |
| fSize | size_t | 当前分配大小 |
| fStorage | uint32_t[kSize >> 2] | 栈内联存储数组 |

**编译时常量**:
| 常量 | 值 | 说明 |
|------|------|------|
| kSizeAlign4 | SkAlign4(kSizeRequested) | 4 字节对齐的请求大小 |
| kSize | kSizeAlign4 或 kMaxBytes | 实际栈存储大小 |
| kMaxBytes | 4096 (Google3) | Google3 构建的栈限制 |

## 公共 API 函数

### SkAutoMalloc 方法

#### `explicit SkAutoMalloc(size_t size = 0)`
- **功能**: 构造函数,分配指定大小的内存
- **参数**: `size` - 字节数,0 表示不分配
- **返回值**: 无
- **异常**: 分配失败抛出异常(sk_malloc_throw)

#### `void* reset(size_t size = 0, OnShrink shrink = kAlloc_OnShrink)`
- **功能**: 调整内存块大小
- **参数**:
  - `size`: 新的字节数
  - `shrink`: 缩小时的行为策略
- **返回值**: 新内存块指针
- **行为**:
  - size > fSize: 总是重新分配
  - size < fSize && shrink == kAlloc_OnShrink: 重新分配
  - size < fSize && shrink == kReuse_OnShrink: 重用现有块

#### `void* get()` / `const void* get() const`
- **功能**: 获取内存块指针
- **返回值**: 内存指针,可能为 nullptr

#### `void* release()`
- **功能**: 释放所有权,返回指针
- **返回值**: 内存指针
- **副作用**: fPtr 和 fSize 重置为 0
- **责任转移**: 调用者必须调用 sk_free()

### SkAutoSMalloc 方法

#### `SkAutoSMalloc()`
- **功能**: 默认构造函数,初始化为栈存储
- **返回值**: 无
- **说明**: get() 返回栈指针,但大小为 0

#### `explicit SkAutoSMalloc(size_t size)`
- **功能**: 构造并分配指定大小
- **参数**: `size` - 字节数
- **返回值**: 无
- **行为**: size ≤ kSize 使用栈,否则堆分配

#### `~SkAutoSMalloc()`
- **功能**: 析构函数,释放堆内存(如有)
- **返回值**: 无
- **行为**: 仅释放非栈内存

#### `void* get() const`
- **功能**: 获取内存指针(栈或堆)
- **返回值**: 内存指针,永不为 nullptr

#### `void* reset(size_t size, OnShrink = kAlloc_OnShrink, bool* didChangeAlloc = nullptr)`
- **功能**: 调整内存块大小
- **参数**:
  - `size`: 新的字节数
  - `shrink`: 缩小时的行为
  - `didChangeAlloc`: 输出参数,指示是否重新分配
- **返回值**: 新内存指针
- **行为**:
  - size ≤ kSize: 使用栈存储
  - size > kSize: 堆分配

## 内部实现细节

### SkAutoMalloc 实现

**自定义删除器**:
```cpp
struct WrapFree {
    void operator()(void* p) { sk_free(p); }
};
std::unique_ptr<void, WrapFree> fPtr;
```

使用 unique_ptr 确保异常安全和自动释放。

**reset 逻辑**:
```cpp
void* reset(size_t size, OnShrink shrink) {
    if (size != fSize && (size > fSize || shrink != kReuse_OnShrink)) {
        fPtr.reset(size ? sk_malloc_throw(size) : nullptr);
        fSize = size;
    }
    return fPtr.get();
}
```

### SkAutoSMalloc 实现

**栈/堆切换逻辑**:
```cpp
void* reset(size_t size, OnShrink shrink, bool* didChangeAlloc) {
    size = (size < kSize) ? kSize : size;  // 最小为 kSize
    bool alloc = size != fSize &&
                 (shrink == kAlloc_OnShrink || size > fSize);

    if (alloc) {
        if (fPtr != (void*)fStorage) {
            sk_free(fPtr);  // 释放旧堆内存
        }

        if (size == kSize) {
            fPtr = fStorage;  // 切换到栈
        } else {
            fPtr = sk_malloc_throw(size);  // 分配堆
        }
        fSize = size;
    }

    if (didChangeAlloc) {
        *didChangeAlloc = alloc;
    }
    return fPtr;
}
```

**析构函数**:
```cpp
~SkAutoSMalloc() {
    if (fPtr != (void*)fStorage) {
        sk_free(fPtr);
    }
}
```

仅释放堆内存,栈存储自动清理。

### Google3 栈限制

```cpp
#if defined(SK_BUILD_FOR_GOOGLE3)
static const size_t kMaxBytes = 4 * 1024;
static const size_t kSize = kSizeRequested > kMaxBytes ? kMaxBytes : kSizeAlign4;
#else
static const size_t kSize = kSizeAlign4;
#endif
```

Google3 构建限制栈帧大小,避免栈溢出。

### 对齐处理

```cpp
static const size_t kSizeAlign4 = SkAlign4(kSizeRequested);
```

存储数组类型为 uint32_t,确保 4 字节对齐。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkAlign.h | 对齐计算(SkAlign4) |
| SkMalloc.h | 底层分配(sk_malloc_throw, sk_free) |
| SkNoncopyable | 禁止拷贝的基类 |
| std::unique_ptr | 智能指针管理 |

### 被依赖的模块
- **SkPath**: 临时路径数据分配
- **SkString**: 字符串缓冲区
- **SkBitmap**: 像素数据临时缓冲
- **各种解码器**: 解码缓冲区管理

## 设计模式与设计决策

### 设计模式
1. **RAII 模式**: 构造时分配,析构时释放
2. **策略模式**: OnShrink 枚举控制缩小行为
3. **模板方法模式**: SkAutoSMalloc 扩展基本功能

### 设计决策

**为什么禁止拷贝?**
- 内存所有权唯一,避免双重释放
- 移动语义未实现,确保语义明确
- 使用指针或引用传递

**为什么 SkAutoSMalloc 使用栈存储?**
- 小分配避免堆开销
- 提高缓存局部性
- 对于临时缓冲区性能显著

**为什么支持 kReuse_OnShrink?**
- 避免频繁分配/释放
- 适用于大小波动的场景
- 减少内存碎片

**为什么使用 sk_malloc_throw 而不是 new?**
- 与 Skia 内存跟踪系统集成
- 允许自定义内存分配策略
- 兼容 C 风格内存管理

**为什么 SkAutoSMalloc 的栈大小限制到 4KB?**
- 避免栈溢出(特别在递归场景)
- Google3 构建环境的安全要求
- 大对象应使用 SkAutoMalloc

## 性能考量

### 时间复杂度
- 构造/析构: O(1)
- `reset()`: O(1) (不考虑系统分配器)
- `get()`: O(1)
- `release()`: O(1)

### 空间开销
- **SkAutoMalloc**: sizeof(unique_ptr) + sizeof(size_t) ≈ 16 字节
- **SkAutoSMalloc<N>**: N + sizeof(void*) + sizeof(size_t) ≈ N + 16 字节

### 性能优化
1. **栈分配**: SkAutoSMalloc 小对象零堆开销
2. **重用策略**: kReuse_OnShrink 避免不必要的分配
3. **对齐优化**: 4 字节对齐减少内存浪费

### 性能对比
| 场景 | SkAutoMalloc | SkAutoSMalloc<512> |
|------|--------------|---------------------|
| 100 字节分配 | 堆分配 | 栈内联(更快) |
| 1000 字节分配 | 堆分配 | 堆分配(相同) |
| 构造/析构 | 1 次堆操作 | 0-1 次堆操作 |

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkMalloc.h | 底层内存分配 |
| include/private/base/SkAlign.h | 对齐工具 |
| src/base/SkArenaAlloc.h | 竞技场分配器 |

## 使用示例

### 示例 1: 基本 SkAutoMalloc
```cpp
{
    SkAutoMalloc buffer(1024);
    void* ptr = buffer.get();
    // 使用 ptr...
} // 自动释放
```

### 示例 2: 动态调整大小
```cpp
SkAutoMalloc buffer(100);
// ... 发现需要更多空间 ...
buffer.reset(500);  // 重新分配
```

### 示例 3: 重用策略
```cpp
SkAutoMalloc buffer(1000);
// ... 只需要 800 字节 ...
buffer.reset(800, SkAutoMalloc::kReuse_OnShrink);
// 仍使用 1000 字节块,避免重新分配
```

### 示例 4: 栈内联分配
```cpp
{
    SkAutoSMalloc<512> buffer(256);
    // 使用栈存储,无堆分配
    memcpy(buffer.get(), src, 256);
} // 无堆释放开销
```

### 示例 5: 转移所有权
```cpp
SkAutoMalloc buffer(1024);
void* ptr = buffer.release();
// 现在调用者负责 sk_free(ptr)
sk_free(ptr);
```

### 示例 6: 检测重新分配
```cpp
SkAutoSMalloc<512> buffer;
bool didAlloc;
buffer.reset(1024, SkAutoMalloc::kAlloc_OnShrink, &didAlloc);
if (didAlloc) {
    // 发生了堆分配
}
```

## 注意事项

1. **线程安全**: 对象本身不是线程安全的
2. **所有权**: 使用 release() 后,调用者负责释放
3. **对齐**: 默认对齐到 4 字节,特殊需求使用其他分配器
4. **栈大小**: SkAutoSMalloc 大模板参数可能导致栈溢出
5. **移动语义**: 当前不支持,使用 std::move 是未定义行为
6. **异常**: sk_malloc_throw 分配失败抛出异常
7. **零大小**: reset(0) 或构造 SkAutoMalloc(0) 是合法的
8. **Google3**: 栈存储限制为 4KB,注意模板参数

## 最佳实践

### 何时使用 SkAutoMalloc
- 需要动态大小的临时缓冲区
- 大小在运行时确定
- 需要频繁调整大小

### 何时使用 SkAutoSMalloc
- 大多数情况下大小 ≤ 512 字节
- 希望避免小分配的堆开销
- 在性能关键路径上

### 何时使用其他分配器
- **std::vector**: 需要自动增长和元素管理
- **SkArenaAlloc**: 批量分配多个对象
- **SkData**: 需要引用计数和共享

### 模板参数选择
```cpp
SkAutoSMalloc<256>  // 小缓冲区(字符串,小数组)
SkAutoSMalloc<512>  // 中等缓冲区(路径数据)
SkAutoSMalloc<1024> // 大缓冲区(像素行)
SkAutoSMalloc<4096> // 最大推荐(Google3 限制)
```

避免超过 4KB 的模板参数。
