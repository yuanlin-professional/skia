# GrMippedBitmap

> 源文件
> - src/gpu/ganesh/image/GrMippedBitmap.h
> - src/gpu/ganesh/image/GrMippedBitmap.cpp

## 概述

`GrMippedBitmap` 是 Skia Ganesh GPU 后端中用于封装不可变位图及其相关 mipmap 数据的轻量级包装类。它将 `SkBitmap` 与可选的 `SkMipmap` 结合在一起，为 Ganesh 的纹理上传系统提供了统一的数据源接口。该类的主要目的是在将位图数据上传到 GPU 时，能够同时提供基础纹理和预生成的 mipmap 层级，避免 GPU 端的 mipmap 重新生成。

这是一个简单的值类型包装器，不涉及复杂的资源管理逻辑，但在 Ganesh 的纹理创建流程中扮演着关键的数据传输角色。

## 架构位置

```
SkBitmap (CPU 像素数据)
    ↓
SkMipmap (预生成的 mipmap)
    ↓
GrMippedBitmap (组合封装)
    ↓
GrMakeUncachedBitmapProxyView() / GrMakeCachedBitmapProxyView()
    ↓
GrTextureProxy (GPU 纹理代理)
```

位于 CPU 像素数据层和 GPU 纹理代理层之间，作为数据转换的中间表示。

## 主要类与结构体

### GrMippedBitmap

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBitmap` | `SkBitmap` | 不可变的位图数据 |
| `fMips` | `sk_sp<const SkMipmap>` | 可选的 mipmap 数据 |

**访问器方法**:

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `alphaType()` | `SkAlphaType` | 获取 alpha 类型 |
| `bitmap()` | `SkBitmap` | 获取位图副本 |
| `colorType()` | `SkColorType` | 获取颜色类型 |
| `mips()` | `sk_sp<const SkMipmap>` | 获取 mipmap 数据 |

## 公共 API 函数

### 构造函数

```cpp
explicit GrMippedBitmap(SkBitmap b);
```
从单个位图创建，不包含 mipmap 数据。

```cpp
explicit GrMippedBitmap(SkBitmap b, sk_sp<const SkMipmap> mipmaps);
```
从位图和预生成的 mipmap 创建完整的 mipmap 位图。

### 工厂方法

```cpp
static std::optional<GrMippedBitmap> Make(
    SkImageInfo ii,
    const void* pixels,
    size_t rowBytes,
    ReleaseProc proc,
    void* context);
```
从原始像素数据创建 `GrMippedBitmap`，支持自定义释放回调。

**参数说明**:
- `ii`: 图像信息（尺寸、颜色类型等）
- `pixels`: 像素数据指针
- `rowBytes`: 行字节数
- `proc`: 可选的释放回调函数
- `context`: 释放回调的上下文数据

**重载版本**:

```cpp
static std::optional<GrMippedBitmap> Make(
    SkImageInfo ii,
    const void* pixels,
    size_t rowBytes);
```
不带释放回调的简化版本。

```cpp
static std::optional<GrMippedBitmap> Make(const SkPixmap& p);
```
从 `SkPixmap` 创建。

### ReleaseProc 类型定义

```cpp
using ReleaseProc = void(void* pixels, void* context);
```
像素释放回调函数类型，用于管理外部像素数据的生命周期。

## 内部实现细节

### 位图安装过程

`Make` 工厂方法的核心逻辑：

```cpp
SkBitmap bm;
if (!bm.installPixels(ii, const_cast<void*>(pixels), rowBytes, proc, context)) {
    return {};
}
bm.setImmutable();
return GrMippedBitmap(bm, /*mipmaps=*/nullptr);
```

1. 创建空白 `SkBitmap`
2. 安装外部像素数据（`installPixels`）
3. 标记为不可变（`setImmutable`）
4. 封装为 `GrMippedBitmap`

### 不可变性保证

所有通过工厂方法创建的位图都会被标记为不可变：

```cpp
bm.setImmutable();
```

这确保了在 GPU 上传过程中，底层像素数据不会被意外修改。

### Mipmap 关联

当前实现中，工厂方法创建的 `GrMippedBitmap` 不自动生成 mipmap：

```cpp
return GrMippedBitmap(bm, /*mipmaps=*/nullptr);
```

Mipmap 需要通过构造函数显式提供，或者在后续的 Ganesh 纹理创建过程中由 GPU 生成。

### 默认成员函数

类使用编译器生成的默认实现：

- 拷贝构造函数
- 移动构造函数
- 拷贝赋值操作符
- 移动赋值操作符
- 析构函数

这意味着 `GrMippedBitmap` 是一个简单的值语义类型，可以高效地复制和移动。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBitmap` | 位图数据容器 |
| `SkMipmap` | Mipmap 层级数据 |
| `SkImageInfo` | 图像元数据描述 |
| `SkPixelRef` | 像素数据引用 |
| `SkPixmap` | 像素图访问器 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrImageUtils` | 通过 `GrMakeUncachedBitmapProxyView` 创建纹理代理 |
| `SkImage_RasterPinnable` | 将光栅图像转换为 GPU 纹理 |
| `SkImage_GaneshFactories` | 跨上下文纹理创建 |

## 设计模式与设计决策

### 值语义设计

`GrMippedBitmap` 设计为值类型而非引用类型：

- **优点**: 简化内存管理，避免堆分配
- **用法**: 通常作为临时对象传递给纹理创建函数
- **性能**: 底层的 `SkBitmap` 和 `SkMipmap` 使用引用计数，复制开销低

### 不可变性原则

所有封装的位图都标记为不可变：

- **线程安全**: 不可变对象天然线程安全
- **GPU 上传**: 确保上传过程中数据不变
- **缓存安全**: 可安全地缓存和重用

### 工厂方法模式

使用静态工厂方法而非构造函数处理可能失败的创建：

```cpp
static std::optional<GrMippedBitmap> Make(...);
```

- **错误处理**: 通过 `std::optional` 表达失败
- **验证**: 在工厂方法中集中验证逻辑
- **灵活性**: 支持多种创建路径（`SkImageInfo`、`SkPixmap`）

### 最小接口原则

类只提供必要的访问器方法：

- `alphaType()`, `colorType()`: 元数据查询
- `bitmap()`, `mips()`: 数据访问
- 没有修改器方法，保持不可变性

### Mipmap 可选设计

将 mipmap 设计为可选项：

- **灵活性**: 支持有/无 mipmap 两种场景
- **性能**: 避免不必要的 mipmap 生成
- **延迟决策**: 可由 Ganesh 根据需要生成 mipmap

## 性能考量

### 轻量级封装

- **零开销抽象**: 仅包含两个成员变量
- **栈分配**: 通常在栈上创建，避免堆分配
- **引用计数**: 底层数据使用智能指针，共享开销低

### Mipmap 优化

- **预生成 mipmap**: 可以在 CPU 上预先生成 mipmap，避免 GPU 生成
- **按需生成**: 如果没有提供 mipmap，GPU 可以按需生成
- **共享数据**: `sk_sp<const SkMipmap>` 允许多个 `GrMippedBitmap` 共享同一份 mipmap 数据

### 释放回调机制

`ReleaseProc` 允许外部管理像素数据的生命周期：

- **零拷贝**: 可以直接使用外部内存，无需复制
- **灵活释放**: 支持自定义释放逻辑（如引用计数、内存池）
- **YUVA 场景**: 特别适用于 YUVA 平面数据的管理

### 不可变性性能

标记位图为不可变带来的性能优势：

- **缓存优化**: 不可变位图可以安全缓存
- **并发访问**: 多线程可安全读取
- **GPU 优化**: GPU 可以假设纹理数据不变

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkBitmap.h` | 位图类定义 |
| `src/core/SkMipmap.h` | Mipmap 实现 |
| `include/core/SkPixmap.h` | 像素图访问器 |
| `src/gpu/ganesh/image/GrImageUtils.h` | 图像到纹理转换工具 |
| `src/gpu/ganesh/image/SkImage_RasterPinnable.h` | 可固定光栅图像 |
| `src/gpu/ganesh/SkGr.h` | Ganesh 工具函数 |
