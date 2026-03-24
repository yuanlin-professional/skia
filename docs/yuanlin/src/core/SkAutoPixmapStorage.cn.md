# SkAutoPixmapStorage

> 源文件
> - src/core/SkAutoPixmapStorage.h
> - src/core/SkAutoPixmapStorage.cpp

## 概述

`SkAutoPixmapStorage` 是 Skia 图形库中用于自动管理像素内存的 RAII 包装类。它继承自 `SkPixmap`，在提供像素数据访问的同时，自动处理内存的分配和释放，是栈上使用临时像素缓冲区的理想选择。

## 架构位置

`SkAutoPixmapStorage` 位于 Skia 的图像数据管理层，是 `SkPixmap` 的扩展，提供自动内存管理功能。它在图像处理、格式转换、临时缓冲等场景中广泛使用。

```
Skia Core
  └── Image Data Management
      ├── SkImageInfo (像素格式描述)
      ├── SkPixmap (只读像素访问)
      │   └── SkAutoPixmapStorage (带自动内存管理)
      └── SkBitmap (可变像素容器)
```

## 主要类与结构体

### SkAutoPixmapStorage

**继承关系**
- 继承自 `SkPixmap`
- 不可复制（移动语义支持）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStorage` | `void*` | 内部管理的像素内存指针 |
| `INHERITED` | `typedef SkPixmap` | 基类类型别名 |

**设计特点**
- 使用 `[[nodiscard]]` 属性标记，防止意外丢弃返回值
- 支持移动构造和移动赋值
- 析构时自动释放内存

## 公共 API 函数

### 构造与析构

**SkAutoPixmapStorage()**
- **功能**: 默认构造函数，创建空对象
- **初始状态**: `fStorage = nullptr`，无像素数据

**~SkAutoPixmapStorage()**
- **功能**: 析构函数，自动释放内部存储
- **行为**: 调用 `freeStorage()` 释放 `fStorage`

**SkAutoPixmapStorage(SkAutoPixmapStorage&& other)**
- **功能**: 移动构造函数
- **行为**: 转移 `other` 的内存所有权，`other` 被置为空状态

**operator=(SkAutoPixmapStorage&& other)**
- **功能**: 移动赋值操作符
- **行为**: 释放当前内存，转移 `other` 的所有权
- **返回**: `*this` 引用

### 内存分配

**tryAlloc(const SkImageInfo&)**
- **功能**: 尝试分配像素内存以匹配指定的图像信息
- **成功**: 返回 true，设置 pixmap 指向新内存
- **失败**: 返回 false，重置 pixmap 为空
- **内存安全**: 检测溢出，使用 `sk_malloc_canfail`
- **行为**: 自动释放旧内存（如果存在）

**alloc(const SkImageInfo&)**
- **功能**: 分配像素内存，失败时中止程序
- **实现**: 调用 `tryAlloc()`，如果失败则 `SK_ABORT()`
- **用途**: 确保分配成功的场景

### 静态工具方法

**AllocSize(const SkImageInfo& info, size_t* rowBytes)**
- **功能**: 计算给定图像信息需要的内存大小
- **参数**: `rowBytes` - 可选输出参数，返回计算的行字节数
- **返回**: 总字节数
- **实现**: `info.computeByteSize(info.minRowBytes())`

### 内存分离

**detachPixels()**
- **功能**: 分离像素内存所有权，返回原始指针
- **返回**: `void*` 指向像素内存（如果未分配则返回 nullptr）
- **后果**: 调用者负责使用 `sk_free()` 释放内存
- **状态**: 对象被重置为空状态
- **标记**: `[[nodiscard]]` 强制使用返回值

**detachPixelsAsData()**
- **功能**: 分离像素内存为 `SkData` 对象
- **返回**: `sk_sp<SkData>` 智能指针（如果未分配则返回 nullptr）
- **优势**: 自动管理内存生命周期
- **状态**: 对象被重置为空状态
- **标记**: `[[nodiscard]]` 强制使用返回值

### 重置方法

**reset()**
- **功能**: 释放内部存储，重置为空状态
- **实现**: 调用 `freeStorage()` 和基类的 `reset()`

**reset(const SkImageInfo& info, const void* addr, size_t rb)**
- **功能**: 设置为外部管理的像素数据（不拥有所有权）
- **行为**: 释放内部存储，调用基类 `reset()`

**reset(const SkMask& mask)**
- **功能**: 从 `SkMask` 重置 pixmap
- **返回**: 成功返回 true
- **行为**: 释放内部存储

## 内部实现细节

### 内存分配流程

```cpp
tryAlloc(info):
  1. freeStorage()              // 释放旧内存
  2. size = AllocSize(info, &rb)  // 计算需要的大小
  3. 检查溢出 (ByteSizeOverflowed)
  4. pixels = sk_malloc_canfail(size)  // 尝试分配
  5. 如果成功:
       reset(info, pixels, rb)   // 设置 Pixmap
       fStorage = pixels          // 保存指针
  6. 如果失败: 返回 false
```

### 移动语义实现

```cpp
operator=(SkAutoPixmapStorage&& other):
  1. this->fStorage = other.fStorage        // 窃取指针
  2. this->INHERITED::reset(other.info(), ...)  // 更新 Pixmap
  3. other.fStorage = nullptr               // 清空源对象
  4. other.INHERITED::reset()               // 重置源对象
  5. return *this
```

### 内存释放机制

```cpp
freeStorage():
  sk_free(fStorage)    // 使用 Skia 的内存分配器
  fStorage = nullptr   // 防止悬空指针
```

### 溢出检查

使用 `SkImageInfo::ByteSizeOverflowed(size)` 检测：
- 计算的大小是否超过 `size_t` 最大值
- 防止整数溢出导致的小分配

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkPixmap.h` | 基类，像素访问接口 |
| `include/core/SkImageInfo.h` | 图像格式描述 |
| `include/core/SkData.h` | 数据容器 |
| `include/private/base/SkMalloc.h` | 内存分配函数 |
| `include/private/base/SkAssert.h` | 断言宏 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| 图像解码器 | 临时解码缓冲区 |
| 图像编码器 | 格式转换缓冲区 |
| 滤镜效果 | 中间结果存储 |
| 测试代码 | 单元测试像素数据 |
| `SkImage` 实现 | 临时像素拷贝 |

## 设计模式与设计决策

### RAII 模式（Resource Acquisition Is Initialization）
- **核心**: 构造时可分配资源，析构时自动释放
- **优势**: 异常安全，无需手动释放
- **实现**: 析构函数调用 `freeStorage()`

### 移动语义（Move Semantics）
- **动机**: 支持高效的所有权转移
- **实现**: 移动构造和移动赋值
- **效果**: 避免不必要的内存拷贝
- **禁止拷贝**: 删除拷贝构造和拷贝赋值

### 继承扩展模式
- **基类**: `SkPixmap` 提供只读访问
- **扩展**: `SkAutoPixmapStorage` 添加内存管理
- **优势**: 可以传递给接受 `SkPixmap` 的函数

### 智能分离机制
- **方法**: `detachPixels()` 和 `detachPixelsAsData()`
- **目的**: 转移所有权给调用者
- **安全**: `[[nodiscard]]` 防止内存泄漏

### 双重分配策略
- **tryAlloc**: 软失败，返回错误码
- **alloc**: 硬失败，程序中止
- **适用**: 不同的错误处理需求

## 性能考量

### 优化点

1. **栈上对象**
   - 固定大小（仅一个指针）
   - 无额外堆分配（像素数据除外）
   - 析构自动调用，无 GC 压力

2. **移动优化**
   - O(1) 所有权转移
   - 避免像素数据拷贝
   - 适合作为返回值

3. **延迟分配**
   - 默认构造不分配内存
   - 按需调用 `tryAlloc` 或 `alloc`
   - 减少不必要的分配

4. **内存对齐**
   - `sk_malloc` 保证适当对齐
   - 优化 CPU 缓存访问

### 性能特征

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| 默认构造 | O(1) | 只初始化指针 |
| 移动构造 | O(1) | 指针赋值 |
| tryAlloc | O(n) | n 为像素数量，内存分配 |
| detach | O(1) | 指针转移 |
| 析构 | O(1) | 内存释放（内部可能 O(n)） |

### 内存使用

| 场景 | 占用 | 说明 |
|------|------|------|
| 对象本身 | ~40 字节 | SkPixmap(32) + fStorage(8) |
| 像素数据 | width * height * bpp | 按图像大小分配 |
| 空对象 | ~40 字节 | 无像素数据开销 |

### 典型使用模式

```cpp
// 模式 1: 局部临时缓冲
SkAutoPixmapStorage tmp;
tmp.alloc(SkImageInfo::MakeN32Premul(width, height));
// ... 使用 tmp ...
// 自动析构释放

// 模式 2: 所有权转移
SkAutoPixmapStorage createPixmap() {
    SkAutoPixmapStorage pmap;
    pmap.alloc(info);
    return pmap;  // 移动，无拷贝
}

// 模式 3: 分离所有权
sk_sp<SkData> data = pmap.detachPixelsAsData();
// pmap 现在为空，data 拥有像素
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkPixmap.h` | 基类 | 只读像素访问 |
| `include/core/SkBitmap.h` | 相关类 | 可变像素容器 |
| `include/core/SkImageInfo.h` | 依赖 | 图像格式描述 |
| `include/core/SkData.h` | 协作 | 字节数据容器 |
| `include/private/base/SkMalloc.h` | 依赖 | 内存分配 |
| `src/codec/SkCodec.cpp` | 使用者 | 图像解码 |
| `src/core/SkImage_Raster.cpp` | 使用者 | 光栅图像实现 |
