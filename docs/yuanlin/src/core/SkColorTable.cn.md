# SkColorTable

> 源文件: include/core/SkColorTable.h, src/core/SkColorTable.cpp

## 概述

`SkColorTable` 保存每个颜色通道(ARGB)的查找表,用于定义 `SkColorFilters::Table` 的过滤行为。它提供了在客户端代码和返回的 SkColorFilter 之间共享表格数据的方式。一旦创建,SkColorTable 就是不可变的。内部使用 256x4 的 A8 位图存储四个通道的查找表,每个通道 256 个字节。

## 架构位置

`SkColorTable` 位于 Skia 核心公共 API(include/core),是颜色过滤系统的一部分。它与 `SkColorFilter` 和 `SkTableColorFilter` 紧密配合,提供基于查找表的颜色变换功能。该类使用引用计数管理内存,支持高效的共享和序列化。

## 主要类与结构体

### SkColorTable

| 特性 | 说明 |
|------|------|
| 继承关系 | 继承自 `SkRefCnt` |
| 线程安全 | 不可变对象,线程安全 |
| 内存管理 | 引用计数 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTable` | `SkBitmap` | 256x4 的 A8 位图,存储 ARGB 四个通道的查找表 |

位图布局:
- 行 0: Alpha 通道查找表 (256 字节)
- 行 1: Red 通道查找表 (256 字节)
- 行 2: Green 通道查找表 (256 字节)
- 行 3: Blue 通道查找表 (256 字节)

## 公共 API 函数

### 创建方法

```cpp
static sk_sp<SkColorTable> Make(const uint8_t table[256]);
```
- 为所有四个通道使用相同的查找表
- 表格数据被复制到 SkColorTable 中
- 返回 nullptr 如果表格为全恒等

```cpp
static sk_sp<SkColorTable> Make(const uint8_t tableA[256],
                                const uint8_t tableR[256],
                                const uint8_t tableG[256],
                                const uint8_t tableB[256]);
```
- 为每个通道指定不同的查找表
- null 参数被解释为恒等表(table[i] = i)
- 如果所有参数都是 null,返回 nullptr(完全恒等)
- 表格数据被复制

### 查询方法

```cpp
const uint8_t* alphaTable() const;
const uint8_t* redTable() const;
const uint8_t* greenTable() const;
const uint8_t* blueTable() const;
```
- 返回指向每个通道查找表的常量指针
- 指针指向内部位图数据,不应修改

### 序列化

```cpp
void flatten(SkWriteBuffer& buffer) const;
static sk_sp<SkColorTable> Deserialize(SkReadBuffer& buffer);
```
- 序列化和反序列化查找表
- 序列化格式:4 * 256 字节的连续数据(ARGB 顺序)

## 内部实现细节

### 位图存储

使用 `SkBitmap` 的 A8 格式存储查找表:

```cpp
SkBitmap table;
table.tryAllocPixels(SkImageInfo::MakeA8(256, 4));
```

优点:
- 利用现有的位图基础设施
- 自动处理内存管理
- 可以设置为不可变(`setImmutable()`)
- 易于在 GPU 上传为纹理

### 查找表填充

```cpp
uint8_t *a = table.getAddr8(0,0),
        *r = table.getAddr8(0,1),
        *g = table.getAddr8(0,2),
        *b = table.getAddr8(0,3);
for (int i = 0; i < 256; i++) {
    a[i] = tableA ? tableA[i] : i;  // null -> 恒等
    r[i] = tableR ? tableR[i] : i;
    g[i] = tableG ? tableG[i] : i;
    b[i] = tableB ? tableB[i] : i;
}
```

### 不可变性保证

创建后立即设置位图为不可变:
```cpp
table.setImmutable();
```

尝试修改会在调试版本中触发断言,在发布版本中导致未定义行为。

### 友元访问

`SkTableColorFilter` 通过友元关系访问内部位图:
```cpp
friend class SkTableColorFilter;
const SkBitmap& bitmap() const { return fTable; }
```

这允许颜色过滤器直接访问位图数据,用于 GPU 纹理上传等操作。

### 序列化格式

展平为 1024 字节的连续数据:
```cpp
void SkColorTable::flatten(SkWriteBuffer& buffer) const {
    buffer.writeByteArray(fTable.getAddr8(0, 0), 4 * 256);
}
```

反序列化时重建表格:
```cpp
sk_sp<SkColorTable> SkColorTable::Deserialize(SkReadBuffer& buffer) {
    uint8_t argb[4*256];
    if (buffer.readByteArray(argb, sizeof(argb))) {
        return SkColorTable::Make(argb+0*256, argb+1*256, argb+2*256, argb+3*256);
    }
    return nullptr;
}
```

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkBitmap` | 存储查找表数据 |
| `SkRefCnt` | 引用计数管理 |
| `SkReadBuffer` | 反序列化 |
| `SkWriteBuffer` | 序列化 |
| `SkImageInfo` | 位图格式定义 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkColorFilter` | 使用查找表进行颜色过滤 |
| `SkTableColorFilter` | 实现基于表的过滤器 |
| `SkRasterPipeline` | 在管线中应用查找表 |
| GPU 后端 | 将查找表上传为纹理 |

## 设计模式与设计决策

### 值对象模式

`SkColorTable` 是不可变的值对象:
- 创建后状态不可更改
- 线程安全,可以跨线程共享
- 引用计数管理生命周期

### 工厂模式

使用静态工厂方法创建实例:
- 隐藏构造函数,避免不完整初始化
- 可以返回 nullptr 表示恒等表
- 验证输入并优化创建过程

### 写时复制(概念上)

虽然实际上是不可变的,但设计支持未来可能的写时复制优化:
- 引用计数允许多个所有者
- 内部位图可以共享像素数据(如果未来需要)

### 紧凑存储

使用单个 256x4 位图而不是四个独立数组:
- 内存局部性更好
- 便于序列化
- GPU 纹理上传更高效

## 性能考量

### 内存布局

使用 A8 格式的位图:
- 每个查找表占用 256 字节
- 总共 1024 字节,适合 L1 缓存
- 行优先布局,每个通道的数据连续

### GPU 优化

位图格式便于 GPU 纹理上传:
- 可以作为 1D 纹理数组上传
- 着色器中查找非常快
- 支持硬件纹理缓存

### 引用计数

使用智能指针共享实例:
- 避免复制大量数据
- 多个颜色过滤器可以共享同一表格
- 自动内存管理

### 恒等优化

全恒等表返回 nullptr:
```cpp
if (!tableA && !tableR && !tableG && !tableB) {
    return nullptr;  // 完全恒等
}
```
- 避免创建和存储无用的表格
- 上层可以检测 nullptr 并跳过查找

### 序列化紧凑性

序列化为 1024 字节的连续数据:
- 无额外元数据开销
- 直接内存复制,速度快
- 适合网络传输和磁盘存储

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkBitmap.h` | 依赖 | 存储查找表 |
| `include/core/SkRefCnt.h` | 基类 | 引用计数 |
| `src/core/SkReadBuffer.h` | 依赖 | 反序列化 |
| `src/core/SkWriteBuffer.h` | 依赖 | 序列化 |
| `include/core/SkColorFilter.h` | 使用者 | 颜色过滤器 API |
| `src/effects/colorfilters/SkTableColorFilter.h` | 使用者 | 表格过滤器实现 |
| `include/core/SkImageInfo.h` | 依赖 | 位图格式 |
