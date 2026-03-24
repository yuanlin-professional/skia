# SkTextBlob

> 源文件: include/core/SkTextBlob.h, src/core/SkTextBlob.cpp

## 概述

`SkTextBlob` 是 Skia 中用于高效文本渲染的不可变容器类,它将多个文本运行 (text run) 组合成一个单一对象。每个文本运行包含字形 (glyphs)、字体信息 (`SkFont`) 和位置数据。文本 blob 一旦创建即不可修改,这使得它可以被缓存和重复使用。`SkTextBlob` 通过引用计数管理生命周期,并支持序列化/反序列化以及边界计算等功能。配合 `SkTextBlobBuilder` 构造器类,可以灵活地构建包含多种定位方式的复杂文本布局。

## 架构位置

`SkTextBlob` 位于 Skia 文本渲染管道的高层接口:
- **位置**: `include/core/` (公共 API), `src/core/` (实现)
- **层次**: 核心文本抽象,位于字形运行 (GlyphRun) 之上,Canvas 绘制接口之下
- **用途**: 提供高性能的文本批量渲染能力,支持复杂文本布局和缓存优化

## 主要类与结构体

### SkTextBlob

不可变文本 blob 类,存储多个文本运行。

**继承关系**:
- 继承自 `SkNVRefCnt<SkTextBlob>` - 非虚析构函数引用计数基类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBounds` | `const SkRect` | 保守边界框,包含所有字形 |
| `fUniqueID` | `const uint32_t` | 全局唯一标识符 |
| `fCacheID` | `mutable std::atomic<uint32_t>` | 缓存条目 ID |
| `fPurgeDelegate` | `mutable std::atomic<PurgeDelegate>` | 缓存清理回调 |
| `fStorageSize` | `size_t` (DEBUG) | 存储大小,仅调试模式 |

### SkTextBlob::RunRecord

内部运行记录结构 (私有),存储单个文本运行的数据。

**内存布局**:
```
RunRecord | 字形数组 (对齐到 4) | 位置数组 | [扩展数据: 文本大小 | 簇索引 | UTF-8 文本]
```

### SkTextBlob::Iter

迭代器类,用于遍历 blob 中的所有运行。

**嵌套结构**:
- `Run`: 包含字体、字形数量、字形索引指针

### SkTextBlobBuilder

文本 blob 构造器,用于增量构建 `SkTextBlob`。

**继承关系**:
- 无继承

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStorage` | `AutoTMalloc<uint8_t>` | 动态内存存储 |
| `fStorageSize` | `size_t` | 已分配存储大小 |
| `fStorageUsed` | `size_t` | 已使用存储大小 |
| `fBounds` | `SkRect` | 累积边界框 |
| `fRunCount` | `int` | 运行数量 |
| `fDeferredBounds` | `bool` | 是否延迟边界计算 |
| `fLastRun` | `size_t` | 最后一个运行的存储索引 |
| `fCurrentRunBuffer` | `RunBuffer` | 当前运行缓冲区 |

### SkTextBlobBuilder::RunBuffer

运行缓冲区,提供对字形和位置数据的可写访问。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `glyphs` | `SkGlyphID*` | 字形 ID 数组 |
| `pos` | `SkScalar*` | 位置数组 (可能是 x, (x,y), 或 xform) |
| `utf8text` | `char*` | UTF-8 文本数据 (可选) |
| `clusters` | `uint32_t*` | 簇索引数组 (可选) |

## 公共 API 函数

### SkTextBlob 核心接口

```cpp
const SkRect& bounds() const
```
返回保守边界框。

```cpp
uint32_t uniqueID() const
```
返回全局唯一标识符。

```cpp
int getIntercepts(const SkScalar bounds[2], SkScalar intervals[], const SkPaint* paint = nullptr) const
```
计算文本与水平线段的交点。

### 静态工厂方法

```cpp
static sk_sp<SkTextBlob> MakeFromText(const void* text, size_t byteLength, const SkFont& font, SkTextEncoding encoding = SkTextEncoding::kUTF8)
```
从文本创建单运行 blob,使用完全定位 (full positioning)。

```cpp
static sk_sp<SkTextBlob> MakeFromPosTextH(const void* text, size_t byteLength, SkSpan<const SkScalar> xpos, SkScalar constY, const SkFont& font, SkTextEncoding encoding = SkTextEncoding::kUTF8)
```
创建水平定位 blob,共享 y 坐标。

```cpp
static sk_sp<SkTextBlob> MakeFromPosText(const void* text, size_t byteLength, SkSpan<const SkPoint> pos, const SkFont& font, SkTextEncoding encoding = SkTextEncoding::kUTF8)
```
创建完全定位 blob,每个字形独立位置。

```cpp
static sk_sp<SkTextBlob> MakeFromRSXform(const void* text, size_t byteLength, SkSpan<const SkRSXform> xform, const SkFont& font, SkTextEncoding encoding = SkTextEncoding::kUTF8)
```
创建 RSXform 定位 blob,支持旋转缩放。

### 序列化

```cpp
sk_sp<SkData> serialize(const SkSerialProcs& procs) const
size_t serialize(const SkSerialProcs& procs, void* memory, size_t memory_size) const
```
序列化 blob 数据。

```cpp
static sk_sp<SkTextBlob> Deserialize(const void* data, size_t size, const SkDeserialProcs& procs)
```
反序列化 blob。

### SkTextBlobBuilder 接口

```cpp
const RunBuffer& allocRun(const SkFont& font, int count, SkScalar x, SkScalar y, const SkRect* bounds = nullptr)
```
分配默认定位运行,字形从 (x,y) 开始,使用字体度量推进。

```cpp
const RunBuffer& allocRunPosH(const SkFont& font, int count, SkScalar y, const SkRect* bounds = nullptr)
```
分配水平定位运行,共享 y 坐标。

```cpp
const RunBuffer& allocRunPos(const SkFont& font, int count, const SkRect* bounds = nullptr)
```
分配完全定位运行,每个字形独立 (x,y) 坐标。

```cpp
const RunBuffer& allocRunRSXform(const SkFont& font, int count)
```
分配 RSXform 定位运行。

```cpp
sk_sp<SkTextBlob> make()
```
构建最终的 `SkTextBlob`,重置构造器状态。

## 内部实现细节

### GlyphPositioning 枚举

定义了四种字形定位方式:
- `kDefault_Positioning` (0): 默认推进,0 个标量/字形
- `kHorizontal_Positioning` (1): 水平定位,1 个标量/字形
- `kFull_Positioning` (2): 完全定位,2 个标量/字形
- `kRSXform_Positioning` (3): RSXform 定位,4 个标量/字形

### 内存管理

`SkTextBlob` 使用自定义内存分配:
- 对象内存通过 `sk_malloc` 分配,placement new 构造
- 运行数据紧跟对象存储,对齐到指针边界
- 析构时手动调用运行记录的析构函数

### 运行合并优化

`SkTextBlobBuilder::mergeRun()` 在满足条件时合并相邻运行:
- 相同字体和定位方式
- 无文本扩展数据
- 完全定位或相同 y 偏移的水平定位

### 延迟边界计算

构造器使用 `fDeferredBounds` 标志延迟边界计算:
- 未提供显式边界时设置延迟标志
- 在 `make()` 或添加下一个运行前计算
- 保守边界使用字体度量,精确边界遍历所有字形

### 边界计算策略

```cpp
SkRect ConservativeRunBounds(const RunRecord& run)
```
- 使用字形位置范围 + 字体边界框
- 快速但可能较宽松

```cpp
SkRect TightRunBounds(const RunRecord& run)
```
- 查询每个字形的实际边界
- 精确但开销较大

### 序列化格式

Flatten 流程:
1. 写入整体边界
2. 遍历每个运行:
   - 字形数量
   - 定位方式和扩展标志
   - 可选的文本大小
   - 偏移量
   - 字体数据 (通过 `SkFontPriv::Flatten`)
   - 字形数组
   - 位置数组
   - 可选的簇索引和 UTF-8 文本
3. 结束标记 (0)

### 缓存集成

`SkTextBlob` 支持缓存通知:
```cpp
void notifyAddedToCache(uint32_t cacheID, PurgeDelegate purgeDelegate) const
```
当 blob 被缓存时,记录缓存 ID 和清理回调,析构时自动触发缓存清理。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkFont.h` | 字体属性 |
| `include/core/SkRSXform.h` | 旋转缩放变换 |
| `include/core/SkRefCnt.h` | 引用计数 |
| `src/text/GlyphRun.h` | 字形运行转换 |
| `src/core/SkReadBuffer.h` / `SkWriteBuffer.h` | 序列化支持 |
| `src/core/SkStrikeSpec.h` | 字形缓存规格 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkCanvas` | 使用 `SkTextBlob` 绘制文本 |
| `SkPicture` | 录制包含文本 blob 的绘制命令 |
| Skia 文本布局引擎 | 生成复杂布局的 blob |
| GPU 后端 | 缓存和光栅化 blob |

## 设计模式与设计决策

### 1. 不可变对象模式 (Immutable Object)
`SkTextBlob` 创建后不可修改,带来多重优势:
- 线程安全,可跨线程共享
- 可安全缓存
- 简化状态管理

### 2. Builder 模式
`SkTextBlobBuilder` 提供灵活的构造接口:
- 增量添加多个运行
- 支持不同定位方式
- 运行合并优化

### 3. 延迟计算 (Lazy Evaluation)
边界计算可延迟到需要时进行,避免不必要的开销。

### 4. Placement New
对象和运行数据使用 placement new 构造,减少内存碎片:
```cpp
new (fStorage.release()) SkTextBlob(fBounds)
```

### 5. 引用计数 (Reference Counting)
使用 `SkNVRefCnt` 管理生命周期,自动释放内存。

### 6. 紧凑内存布局
运行数据紧跟对象存储,提高缓存局部性:
```
[SkTextBlob][RunRecord1][glyphs1][pos1][RunRecord2][glyphs2][pos2]...
```

## 性能考量

### 1. 单次分配
整个 blob 及所有运行数据在单次 `malloc` 中分配,减少堆开销和碎片。

### 2. 运行合并
自动合并兼容的运行,减少迭代开销和状态切换。

### 3. 缓存友好
紧凑的内存布局提高缓存命中率。

### 4. 延迟边界计算
仅在需要时计算边界,避免不必要的字形查询。

### 5. 保守边界优化
对于定位运行,优先使用保守边界避免昂贵的精确计算。

### 6. 预留容量
`reserve()` 方法减少增量构建时的重新分配次数。

### 7. 运行位置验证
调试模式下验证运行数据布局,确保内存安全。

### 8. 原子缓存 ID
使用原子变量避免锁竞争。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkTextBlob.h` | 声明 | 公共 API 接口 |
| `src/core/SkTextBlob.cpp` | 实现 | 核心实现逻辑 |
| `src/core/SkTextBlobPriv.h` | 私有接口 | 内部辅助类 |
| `src/text/GlyphRun.h` | 转换 | 转换为字形运行列表 |
| `include/core/SkFont.h` | 依赖 | 字体属性 |
| `include/core/SkPaint.h` | 依赖 | 绘制属性 |
| `src/core/SkReadBuffer.h` | 序列化 | 反序列化支持 |
| `src/core/SkWriteBuffer.h` | 序列化 | 序列化支持 |

## 使用示例

```cpp
// 使用 Builder 构建复杂文本
SkTextBlobBuilder builder;

// 添加第一个运行 (水平定位)
SkFont font1(typeface, 24);
auto run1 = builder.allocRunPosH(font1, count1, y1);
// 填充 run1.glyphs 和 run1.pos

// 添加第二个运行 (完全定位)
SkFont font2(typeface, 18);
auto run2 = builder.allocRunPos(font2, count2);
// 填充 run2.glyphs 和 run2.points()

// 构建 blob
sk_sp<SkTextBlob> blob = builder.make();

// 使用 blob 绘制
canvas->drawTextBlob(blob, x, y, paint);

// Blob 可被重复使用和缓存
canvas->drawTextBlob(blob, x + 100, y + 50, paint);
```
