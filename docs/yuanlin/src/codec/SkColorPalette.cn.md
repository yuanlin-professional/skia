# SkColorPalette

> 源文件: src/codec/SkColorPalette.h, src/codec/SkColorPalette.cpp

## 概述

`SkColorPalette` 是 Skia 中用于存储调色板的线程安全类，主要用于 8 位索引色位图。它持有最多 256 个预乘的 32 位颜色（SkPMColor），位图字节被解释为调色板索引。该类继承自 `SkRefCnt`，支持引用计数和智能指针管理。

## 架构位置

在 Skia 图像解码体系中：
```
SkCodec → 调色板图片解码器 → SkColorPalette
```
主要被 BMP、GIF、PNG (索引色) 等格式的解码器使用。

## 主要成员

**私有成员**:
- `SkPMColor* fColors`: 颜色数组指针
- `int fCount`: 颜色数量 (0-256)

## 公共 API

### 构造与析构
```cpp
SkColorPalette(const SkPMColor colors[], int count)
```
拷贝最多 256 个颜色创建调色板，使用 `sk_malloc_throw` 分配内存并 `memcpy` 拷贝数据。

```cpp
~SkColorPalette() override
```
释放颜色数组内存（`sk_free(fColors)`）。

### 访问方法
```cpp
int count() const
```
返回颜色数量。

```cpp
SkPMColor operator[](int index) const
```
通过索引访问颜色，调试模式下断言索引有效性。

```cpp
const SkPMColor* readColors() const
```
返回颜色数组指针供批量读取。

## 设计特点

**线程安全**: 不可变对象，构造后颜色不可修改。

**引用计数**: 继承 `SkRefCnt`，多个解码器可共享同一调色板。

**拷贝语义**: 构造时深拷贝颜色数据，避免生命周期依赖。

**预乘颜色**: 存储 `SkPMColor` (预乘 Alpha)，解码时可直接使用。

## 性能考量

**内存**: 每个调色板最多 1KB (256 × 4 字节)。

**拷贝开销**: 构造时一次性拷贝，后续访问零开销。

**缓存友好**: 连续内存布局，访问性能佳。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkRefCnt.h` | 基类 | 引用计数基类 |
| `include/core/SkColor.h` | 依赖 | SkPMColor 定义 |
| `include/private/base/SkMalloc.h` | 工具 | 内存分配 |
