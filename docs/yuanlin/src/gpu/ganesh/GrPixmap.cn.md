# GrPixmap

> 源文件: [src/gpu/ganesh/GrPixmap.h](../../../../src/gpu/ganesh/GrPixmap.h)

## 概述

`GrPixmap.h` 定义了 Ganesh GPU 后端的像素图（pixmap）抽象层，提供了比 Skia 核心 `SkPixmap` 更丰富的颜色类型支持。该文件包含三个类：基类模板 `GrPixmapBase<T, DERIVED>`，以及两个派生类 `GrPixmap`（可变像素）和 `GrCPixmap`（不可变像素）。这些类封装了像素数据的内存地址、行字节数、图像信息以及可选的像素存储所有权，是 Ganesh 内部进行像素数据读写传输的核心数据结构。

## 架构位置

`GrPixmap` 类族位于 Ganesh 后端的像素数据管理层：

```
SkPixmap (Skia 公共 API 像素图)
  |
  v (隐式转换)
GrPixmapBase<T, DERIVED> (Ganesh 像素图基类模板)
  |
  +-- GrPixmap  (可变像素图，T = void)
  +-- GrCPixmap (不可变像素图，T = const void)
  |
  v
GrSurfaceContext / GrSurfaceProxy (GPU 表面读写操作)
  |
  v
GPU 驱动层 (像素数据上传/下载)
```

`GrPixmap` 和 `GrCPixmap` 在 Ganesh 内部被广泛使用，用于 CPU 与 GPU 之间的像素数据传输、纹理上传、渲染目标读回等场景。

## 主要类与结构体

### `GrPixmapBase<T, DERIVED>` — 基类模板

使用 CRTP（Curiously Recurring Template Pattern）的模板基类，`T` 为像素数据指针的类型（`void` 或 `const void`），`DERIVED` 为派生类类型。

**核心成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fAddr` | `T*` | 像素数据首地址，默认 `nullptr` |
| `fRowBytes` | `size_t` | 每行像素的字节数，默认 0 |
| `fInfo` | `GrImageInfo` | 图像元信息（颜色类型、alpha 类型、颜色空间、尺寸） |
| `fPixelStorage` | `sk_sp<SkData>` | 可选的像素数据所有权持有者 |

### `GrPixmap` — 可变像素图

继承自 `GrPixmapBase<void, GrPixmap>`。表示一个具有可写像素数据的像素图。支持从 `SkPixmap` 隐式转换，可以通过静态方法 `Allocate` 分配自有内存。

### `GrCPixmap` — 不可变像素图

继承自 `GrPixmapBase<const void, GrCPixmap>`。表示一个具有只读像素数据的像素图。支持从 `GrPixmap` 和 `SkPixmap` 的隐式转换（只读视图）。

## 公共 API 函数

### `GrPixmapBase` 基类公共接口

#### 查询方法

- **`const GrImageInfo& info() const`**：返回完整的图像元信息。
- **`const GrColorInfo& colorInfo() const`**：返回颜色信息（颜色类型、alpha 类型、颜色空间）。
- **`T* addr() const`**：返回像素数据首地址。
- **`size_t rowBytes() const`**：返回每行字节数。
- **`bool hasPixels() const`**：是否有有效的像素数据地址。
- **`bool ownsPixels() const`**：是否拥有像素数据的所有权（即 `fPixelStorage` 非空）。
- **`sk_sp<SkData> pixelStorage() const`**：返回像素存储的引用。
- **`int width() const`**：图像宽度（像素）。
- **`int height() const`**：图像高度（像素）。
- **`SkISize dimensions() const`**：图像尺寸。
- **`GrColorType colorType() const`**：Ganesh 颜色类型。
- **`SkAlphaType alphaType() const`**：Alpha 类型。
- **`SkColorSpace* colorSpace() const`**：颜色空间裸指针。
- **`sk_sp<SkColorSpace> refColorSpace() const`**：颜色空间智能指针。

#### 操作方法

- **`DERIVED clip(SkISize surfaceDims, SkIPoint* surfacePt)`**：将像素图裁剪到指定表面的边界内。更新 `surfacePt` 为裁剪后的左上角坐标，返回裁剪后的子像素图。如果不相交则返回默认（空）像素图。

### `GrPixmap` 特有接口

- **构造函数 `GrPixmap(GrImageInfo info, void* addr, size_t rowBytes)`**：从图像信息和外部内存构造。
- **隐式转换 `GrPixmap(const SkPixmap& pixmap)`**：从 `SkPixmap` 隐式构造（使用可写地址）。
- **`static GrPixmap Allocate(const GrImageInfo& info)`**：分配一块自有的未初始化像素内存，返回拥有该内存所有权的 `GrPixmap`。

### `GrCPixmap` 特有接口

- **构造函数 `GrCPixmap(GrImageInfo info, const void* addr, size_t rowBytes)`**：从图像信息和只读内存构造。
- **隐式转换 `GrCPixmap(const GrPixmap& pixmap)`**：从可变像素图隐式构造只读视图。
- **隐式转换 `GrCPixmap(const SkPixmap& pixmap)`**：从 `SkPixmap` 隐式构造（使用只读地址）。

## 内部实现细节

1. **CRTP 模式**：`GrPixmapBase<T, DERIVED>` 使用 CRTP 使基类的 `clip()` 方法能够返回正确的派生类类型，避免了虚函数调用的开销。

2. **构造函数验证**：基类构造函数会检查 `rowBytes` 是否满足最小行字节要求（`fInfo.minRowBytes()`），以及地址是否非空。若不满足则将对象重置为默认空状态，这是一种安全的失败处理策略。

3. **像素所有权模型**：
   - `fAddr` 存储像素数据的地址，可以指向外部管理的内存。
   - `fPixelStorage`（`sk_sp<SkData>`）可选地持有像素数据的所有权。
   - 通过 `ownsPixels()` 可以判断该像素图是否拥有内存。
   - 拷贝像素图会共享像素存储的所有权（引用计数）。

4. **`clip()` 方法的地址计算**：使用 `sknonstd::copy_const_t<char, T>*` 进行字节级指针运算，保持 `const` 正确性。偏移量基于行字节数和每像素字节数计算。

5. **`GrCPixmap` 从 `GrPixmap` 的转换**：转换时会检查源像素图是否持有像素存储所有权，如有则共享所有权；否则仅创建只读视图。

6. **`GrPixmap::Allocate` 的实现**：使用 `SkData::MakeUninitialized` 分配内存（未初始化以提高性能），采用最小行字节数避免浪费。

## 依赖关系

- **`include/core/SkData.h`**：`SkData` 类，用于像素数据的所有权管理
- **`include/core/SkPixmap.h`**：`SkPixmap` 类，公共 API 层的像素图
- **`include/core/SkPoint.h`**：`SkIPoint` 类型
- **`include/core/SkRect.h`**：`SkIRect` 类型，用于裁剪计算
- **`include/core/SkRefCnt.h`**：`sk_sp` 智能指针
- **`include/core/SkSize.h`**：`SkISize` 类型
- **`include/private/base/SkTLogic.h`**：`sknonstd::copy_const_t` 模板工具
- **`include/private/base/SkTo.h`**：`SkToBool` 转换工具
- **`src/gpu/ganesh/GrImageInfo.h`**：`GrImageInfo` 类，Ganesh 图像元信息

## 设计模式与设计决策

1. **CRTP（奇异递归模板模式）**：通过 `GrPixmapBase<T, DERIVED>` 实现编译期多态，使 `clip()` 返回正确的派生类型，同时避免虚函数开销。这在 Skia 代码库中是常见模式。

2. **const 正确性分离**：通过模板参数 `T`（`void` vs `const void`）将可变和不可变像素图分离为不同的类型，在编译期强制只读语义，防止意外修改。

3. **隐式转换设计**：
   - `SkPixmap -> GrPixmap/GrCPixmap`：便于在 Ganesh 内部直接使用公共 API 的像素图。
   - `GrPixmap -> GrCPixmap`：允许将可变像素图安全地传递给只需只读访问的函数。
   - 这些隐式转换简化了 API 调用，但也意味着使用者需要注意生命周期管理。

4. **值语义与共享所有权**：像素图对象本身是值类型（可复制、可移动），但像素数据的所有权通过 `sk_sp<SkData>` 共享。这种设计允许轻量级地创建子视图或只读视图。

## 性能考量

- **零开销抽象**：CRTP 模式确保无虚函数调用开销，所有方法均可内联。
- **避免不必要的拷贝**：像素数据通过指针引用而非拷贝，`sk_sp` 共享所有权避免数据复制。
- **`Allocate` 使用未初始化内存**：`SkData::MakeUninitialized` 跳过零初始化，减少大缓冲区分配的开销。
- **最小行字节数**：`Allocate` 使用 `minRowBytes()` 而非更大的对齐值，节省内存。但这可能在某些 GPU 上不是最优对齐。
- **`clip()` 方法**：返回子视图而非拷贝数据，是零拷贝操作（仅调整指针和元数据）。

## 相关文件

- `src/gpu/ganesh/GrImageInfo.h`：`GrImageInfo` 图像元信息类，存储颜色类型、alpha 类型、颜色空间和尺寸
- `src/gpu/ganesh/GrColorInfo.h`：`GrColorInfo` 颜色信息类，`GrImageInfo` 内部使用的颜色描述
- `include/core/SkPixmap.h`：Skia 公共 API 像素图，`GrPixmap` 提供与其的隐式转换
- `include/core/SkData.h`：`SkData` 数据持有类，用于管理像素数据的所有权
- `include/private/gpu/ganesh/GrTypesPriv.h`：`GrColorType` 枚举，Ganesh 内部颜色类型定义
- `src/gpu/ganesh/SurfaceContext.h`：GPU 表面上下文，使用 `GrPixmap` 进行 CPU-GPU 数据传输
- `include/private/base/SkTLogic.h`：`sknonstd::copy_const_t` 模板工具，用于 `clip()` 方法的 const 正确指针运算
