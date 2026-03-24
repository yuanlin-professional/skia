# SkPixelRefPriv

> 源文件
> - src/core/SkPixelRefPriv.h

## 概述

`SkPixelRefPriv.h` 是 `SkPixelRef` 的私有辅助头文件，提供创建带自定义释放回调的 `SkPixelRef` 的工厂函数。这个文件虽然简短，但定义了创建灵活像素引用的关键接口，支持将任意内存（包括栈分配内存）包装为 `SkPixelRef`。

该文件仅包含一个工厂函数声明，实际实现位于 `SkPixelRef.cpp` 中。

## 架构位置

`SkPixelRefPriv` 位于 Skia 的内部辅助层：

- 不是公共 API（位于 `src/core` 而非 `include/core`）
- 被内部模块使用来创建自定义 `SkPixelRef`
- 支持栈分配像素的特殊用例
- 提供比公共构造函数更灵活的创建方式

## 主要类与结构体

本文件不定义类或结构体，仅声明工厂函数。

## 公共 API 函数

### SkMakePixelRefWithProc

```cpp
/**
 * 创建新的 SkPixelRef，使用提供的像素存储和行字节数。
 * 析构时调用 ReleaseProc。
 *
 * 如果 ReleaseProc 为 NULL，像素永不释放。这适用于栈分配的
 * 像素，但这样的 SkPixelRef 不能超过其像素的生命周期（例如
 * 通过拷贝指向它的 SkBitmap 或绘制到 SkPicture）。
 *
 * 失败时返回 NULL。
 *
 * @param w         宽度
 * @param h         高度
 * @param rowBytes  行字节数
 * @param addr      像素地址
 * @param releaseProc 释放回调函数
 * @param ctx       释放回调上下文
 * @return          SkPixelRef 智能指针
 */
sk_sp<SkPixelRef> SkMakePixelRefWithProc(int w, int h, size_t rowBytes,
                                         void* addr,
                                         void (*releaseProc)(void* addr, void* ctx),
                                         void* ctx);
```

## 内部实现细节

### 实现位置

虽然声明在 `SkPixelRefPriv.h`，实际实现在 `SkPixelRef.cpp`：

```cpp
sk_sp<SkPixelRef> SkMakePixelRefWithProc(int width, int height,
                                         size_t rowBytes, void* addr,
                                         void (*releaseProc)(void*, void*),
                                         void* ctx)
{
    SkASSERT(width >= 0 && height >= 0);

    // 无释放回调：使用标准 SkPixelRef
    if (nullptr == releaseProc) {
        return sk_make_sp<SkPixelRef>(width, height, addr, rowBytes);
    }

    // 有释放回调：创建自定义子类
    struct PixelRef final : public SkPixelRef {
        void (*fReleaseProc)(void*, void*);
        void* fReleaseProcContext;

        PixelRef(int w, int h, void* s, size_t r,
                 void (*proc)(void*, void*), void* ctx)
            : SkPixelRef(w, h, s, r)
            , fReleaseProc(proc)
            , fReleaseProcContext(ctx) {}

        ~PixelRef() override {
            // 析构时调用释放回调
            fReleaseProc(this->pixels(), fReleaseProcContext);
        }
    };

    return sk_sp<SkPixelRef>(new PixelRef(width, height, addr, rowBytes,
                                          releaseProc, ctx));
}
```

### 使用场景

#### 场景1：堆分配内存

```cpp
void* pixels = malloc(width * height * 4);
auto pixelRef = SkMakePixelRefWithProc(
    width, height, width * 4, pixels,
    [](void* addr, void* ctx) { free(addr); },
    nullptr
);
// pixelRef 析构时自动 free(pixels)
```

#### 场景2：栈分配内存

```cpp
uint32_t pixels[100 * 100];
auto pixelRef = SkMakePixelRefWithProc(
    100, 100, 100 * sizeof(uint32_t), pixels,
    nullptr,  // 不释放
    nullptr
);
// 注意：pixelRef 不能超过 pixels 的作用域
```

#### 场景3：自定义分配器

```cpp
void* pixels = customAllocator.alloc(size);
auto pixelRef = SkMakePixelRefWithProc(
    width, height, rowBytes, pixels,
    [](void* addr, void* ctx) {
        auto* allocator = static_cast<CustomAllocator*>(ctx);
        allocator->free(addr);
    },
    &customAllocator
);
```

### 安全性考虑

**栈分配风险**：
```cpp
sk_sp<SkPixelRef> dangerousFunction() {
    uint32_t pixels[100 * 100];  // 栈分配
    auto pixelRef = SkMakePixelRefWithProc(
        100, 100, 100 * 4, pixels,
        nullptr, nullptr
    );
    return pixelRef;  // 危险！pixels 已销毁
}
```

此函数返回的 `SkPixelRef` 指向已销毁的栈内存。

**正确用法**：
```cpp
void safeFunction() {
    uint32_t pixels[100 * 100];  // 栈分配
    auto pixelRef = SkMakePixelRefWithProc(
        100, 100, 100 * 4, pixels,
        nullptr, nullptr
    );
    // 使用 pixelRef...
    // pixelRef 在 pixels 作用域内销毁：安全
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkPixelRef | 基类 |
| SkRefCnt | 智能指针类型 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| Skia 内部模块 | 创建自定义 SkPixelRef |
| 测试代码 | 测试栈分配像素 |
| 性能基准 | 避免堆分配的快速路径 |

## 设计模式与设计决策

### 工厂函数

使用工厂函数而非构造函数：
- 支持条件创建（有/无释放回调）
- 返回智能指针
- 隐藏实现细节

### 回调机制

使用函数指针回调：
- 灵活的释放逻辑
- 支持 lambda 和函数对象
- 轻量级（无虚函数开销）

### 局部子类

在工厂函数内定义子类：
- 封装实现细节
- 避免头文件污染
- 类型安全

### 可选释放

`nullptr` 释放回调表示不释放：
- 支持栈分配和静态内存
- 避免不必要的回调
- 明确意图

## 性能考量

### 避免虚函数

释放回调使用函数指针而非虚函数：
- 减少 vtable 开销
- 更小的对象尺寸
- 更好的内联机会

### 栈分配优化

支持栈分配像素避免堆分配：
- 零分配开销
- 无内存碎片
- 更好的缓存局部性

### 零释放开销

`nullptr` 回调避免不必要的释放逻辑：
- 适用于栈和静态内存
- 运行时零开销
- 清晰的语义

### 条件子类创建

仅在需要时创建子类：
- 标准情况使用基类
- 减少代码膨胀
- 优化常见路径

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| include/core/SkPixelRef.h | SkPixelRef 公共接口 |
| src/core/SkPixelRef.cpp | 包含工厂函数实现 |
| include/core/SkBitmap.h | 使用 SkPixelRef |
| include/core/SkRefCnt.h | 智能指针定义 |
