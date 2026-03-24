# SkMallocPixelRef

> 源文件: include/core/SkMallocPixelRef.h, src/core/SkMallocPixelRef.cpp

## 概述

`SkMallocPixelRef` 是 Skia 中用于管理堆分配像素数据的工具命名空间,提供创建 `SkPixelRef` 的工厂方法。它与 `SkMask` 使用相同的内存分配器,确保不同组件之间可以安全地共享像素内存。支持自动分配和使用已有 `SkData` 两种方式。

## 架构位置

`SkMallocPixelRef` 位于 Skia 像素数据管理层:
- 为 `SkBitmap` 提供像素存储后端
- 与 `SkMask` 共享内存分配器
- 支持 `SkData` 的引用计数管理
- 作为 `SkPixelRef` 的具体实现之一

## 主要类与结构体

### 命名空间函数

| 函数 | 说明 |
|------|------|
| MakeAllocate | 自动分配像素内存 |
| MakeWithData | 使用已有 SkData 作为像素存储 |

### 内部实现类

**匿名 PixelRef** (MakeAllocate 版本):
| 特性 | 说明 |
|------|------|
| 继承 | SkPixelRef |
| 内存管理 | 析构时调用 `sk_free()` |
| 初始化 | 零初始化 (`sk_calloc_canfail`) |

**匿名 PixelRef** (MakeWithData 版本):
| 特性 | 说明 |
|------|------|
| 继承 | SkPixelRef |
| 数据引用 | 持有 `sk_sp<SkData>` |
| 不可变性 | 自动标记为 immutable |

## 公共 API 函数

### 自动分配方式

```cpp
SK_API sk_sp<SkPixelRef> MakeAllocate(const SkImageInfo& info,
                                      size_t rowBytes);
```

**参数**:
- `info`: 图像信息 (宽度、高度、颜色类型、alpha 类型)
- `rowBytes`: 每行字节数,传入 0 则自动计算最小值

**返回值**:
- 成功: `sk_sp<SkPixelRef>` 指向新分配的像素数据 (零初始化)
- 失败: `nullptr` (参数无效或内存分配失败)

**失败条件**:
- 图像信息无效 (宽高为负、颜色类型非法等)
- rowBytes 不符合要求 (`!info.validRowBytes(rowBytes)`)
- 计算的总大小溢出
- 内存分配失败

### 使用已有数据

```cpp
SK_API sk_sp<SkPixelRef> MakeWithData(const SkImageInfo& info,
                                      size_t rowBytes,
                                      sk_sp<SkData> data);
```

**参数**:
- `info`: 图像信息
- `rowBytes`: 每行字节数
- `data`: 包含像素数据的 `SkData` 对象

**返回值**:
- 成功: `sk_sp<SkPixelRef>`,像素引用 `data` 的内存
- 失败: `nullptr`

**失败条件**:
- 图像信息无效
- `rowBytes < info.minRowBytes()`
- `data->size() < info.computeByteSize(rowBytes)`

**特性**:
- 返回的 `SkPixelRef` 被标记为 immutable
- `data` 的引用计数增加,确保内存不被提前释放

## 内部实现细节

### 参数验证

```cpp
static bool is_valid(const SkImageInfo& info) {
    if (info.width() < 0 || info.height() < 0 ||
        (unsigned)info.colorType() > (unsigned)kLastEnum_SkColorType ||
        (unsigned)info.alphaType() > (unsigned)kLastEnum_SkAlphaType)
    {
        return false;
    }
    return true;
}
```

### MakeAllocate 实现

```cpp
sk_sp<SkPixelRef> SkMallocPixelRef::MakeAllocate(const SkImageInfo& info,
                                                 size_t rowBytes) {
    if (rowBytes == 0) {
        rowBytes = info.minRowBytes();  // 自动计算
    }
    if (!is_valid(info) || !info.validRowBytes(rowBytes)) {
        return nullptr;
    }

    size_t size = info.computeByteSize(rowBytes);
    if (SkImageInfo::ByteSizeOverflowed(size)) {
        return nullptr;  // 溢出检测
    }

#if defined(SK_BUILD_FOR_FUZZER)
    if (size > 10000000) {  // Fuzzer 限制
        return nullptr;
    }
#endif

    void* addr = sk_calloc_canfail(size);  // 零初始化
    if (nullptr == addr) {
        return nullptr;
    }

    struct PixelRef final : public SkPixelRef {
        PixelRef(int w, int h, void* s, size_t r)
            : SkPixelRef(w, h, s, r) {}
        ~PixelRef() override {
            sk_free(this->pixels());  // 自动释放
        }
    };
    return sk_sp<SkPixelRef>(new PixelRef(info.width(), info.height(),
                                          addr, rowBytes));
}
```

### MakeWithData 实现

```cpp
sk_sp<SkPixelRef> SkMallocPixelRef::MakeWithData(const SkImageInfo& info,
                                                 size_t rowBytes,
                                                 sk_sp<SkData> data) {
    SkASSERT(data != nullptr);
    if (!is_valid(info)) {
        return nullptr;
    }

    // 检查 data 大小是否足够
    if ((rowBytes < info.minRowBytes()) ||
        (data->size() < info.computeByteSize(rowBytes))) {
        return nullptr;
    }

    struct PixelRef final : public SkPixelRef {
        sk_sp<SkData> fData;  // 持有数据引用
        PixelRef(int w, int h, void* s, size_t r, sk_sp<SkData> d)
            : SkPixelRef(w, h, s, r), fData(std::move(d)) {}
    };

    void* pixels = const_cast<void*>(data->data());
    sk_sp<SkPixelRef> pr(new PixelRef(info.width(), info.height(),
                                      pixels, rowBytes, std::move(data)));
    pr->setImmutable();  // 标记为不可变
    return pr;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPixelRef | 基类 |
| SkImageInfo | 图像元数据 |
| SkData | 数据封装 |
| SkMalloc | 内存分配 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkBitmap | 使用 PixelRef 存储像素 |
| SkImage | 图像数据管理 |
| SkMask | 共享内存分配器 |

## 设计模式与设计决策

### 1. 工厂方法模式
通过静态工厂方法隐藏具体实现:
```cpp
namespace SkMallocPixelRef {
    sk_sp<SkPixelRef> MakeAllocate(...);
    sk_sp<SkPixelRef> MakeWithData(...);
}
```

### 2. 匿名内部类
使用局部结构体实现 `SkPixelRef`:
```cpp
struct PixelRef final : public SkPixelRef {
    PixelRef(...) : SkPixelRef(...) {}
    ~PixelRef() override { sk_free(this->pixels()); }
};
return sk_sp<SkPixelRef>(new PixelRef(...));
```

优点:
- 隐藏实现细节
- 每个工厂方法可定制析构行为

### 3. RAII 资源管理
利用智能指针自动管理生命周期:
```cpp
sk_sp<SkPixelRef> pr = SkMallocPixelRef::MakeAllocate(...);
// 离开作用域自动释放
```

### 4. 内存分配器统一
与 `SkMask::AllocImage()` 使用相同的分配器:
```cpp
void* addr = sk_calloc_canfail(size);  // 相同的分配函数
```

允许跨类型内存共享。

### 5. 不可变性标记
`MakeWithData` 创建的对象自动标记为 immutable:
```cpp
pr->setImmutable();
```
优化缓存和并发访问。

## 性能考量

### 1. 零初始化优化
```cpp
void* addr = sk_calloc_canfail(size);
```
使用 `calloc` 而非 `malloc + memset`,某些平台可优化。

### 2. 失败快速返回
按失败概率排序检查:
```cpp
if (!is_valid(info)) return nullptr;           // 最常见
if (!info.validRowBytes(rowBytes)) return nullptr;
if (ByteSizeOverflowed(size)) return nullptr;  // 少见
if (!sk_calloc_canfail(...)) return nullptr;   // 极少见
```

### 3. 自动 rowBytes 计算
```cpp
if (rowBytes == 0) {
    rowBytes = info.minRowBytes();
}
```
避免用户手动计算错误。

### 4. Fuzzer 保护
```cpp
#if defined(SK_BUILD_FOR_FUZZER)
if (size > 10000000) {
    return nullptr;
}
#endif
```
防止模糊测试时的 OOM。

### 5. 移动语义
```cpp
fData(std::move(d))
```
避免引用计数的原子操作开销。

### 6. const_cast 零开销
```cpp
void* pixels = const_cast<void*>(data->data());
```
`SkData::data()` 返回 `const void*`,但 `SkPixelRef` 需要 `void*`,通过 const_cast 避免拷贝。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkPixelRef.h | 基类 | 像素引用基类 |
| include/core/SkImageInfo.h | 依赖 | 图像元数据 |
| include/core/SkData.h | 依赖 | 数据封装 |
| include/core/SkBitmap.h | 使用者 | 位图类 |
| src/core/SkMask.h | 相关 | 共享分配器 |
| include/private/base/SkMalloc.h | 依赖 | 内存分配 |
