# SkDescriptor

> 源文件
> - src/core/SkDescriptor.h
> - src/core/SkDescriptor.cpp

## 概述

`SkDescriptor` 是 Skia 字体渲染系统中的关键数据结构,用于唯一标识和查找字体光栅化上下文。它是一个可变长度的二进制数据容器,包含字体缩放参数、字型标识符和其他渲染配置信息。通过哈希和比较 Descriptor,Skia 可以高效缓存和重用昂贵的字形光栅化结果。

Descriptor 采用紧凑的内存布局,支持多个键值对条目,每个条目由标签(tag)、长度和数据组成。它提供了校验和机制确保数据完整性,并支持高效的相等性比较。`SkAutoDescriptor` 辅助类提供了自动内存管理和小对象优化。

## 架构位置

`SkDescriptor` 位于 Skia 文本渲染系统的核心缓存层:

```
Skia Text Rendering System
  ├─ High-Level Text API
  │   └─ SkFont, SkTextBlob
  ├─ Glyph Management
  │   ├─ SkGlyphCache (字形缓存)
  │   ├─ SkStrike (字形渲染缓存池)
  │   └─ SkStrikeCache (全局缓存管理)
  ├─ Font Scaler Context
  │   ├─ SkScalerContext (字体缩放器)
  │   ├─ SkScalerContextRec (缩放参数记录)
  │   └─ SkDescriptor ← 当前模块(上下文标识符)
  └─ Platform Font Backends
      └─ FreeType, DirectWrite, CoreText
```

Descriptor 作为缓存键,连接上层字形请求和底层字体渲染引擎。

## 主要类与结构体

### SkDescriptor

**继承关系**:
- 基类: `SkNoncopyable`(禁止拷贝,使用智能指针管理)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fChecksum | uint32_t | 内容校验和(必须是第一个成员) |
| fLength | uint32_t | Descriptor 总长度(必须是第二个成员) |
| fCount | uint32_t | 条目数量 |

**内存布局**:
```
[fChecksum: 4字节][fLength: 4字节][fCount: 4字节]
[Entry1: tag+len][Entry1 data]
[Entry2: tag+len][Entry2 data]
...
```

**核心职责**:
- 存储字体渲染参数的二进制数据
- 提供高效的相等性比较(通过校验和和逐字节比较)
- 支持条目的添加和查找
- 保证 4 字节对齐,优化比较性能

### Entry

**结构体成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| fTag | uint32_t | 条目类型标签(如 kRec_SkDescriptorTag) |
| fLen | uint32_t | 数据长度(不包括 Entry 头部) |

紧跟在 Entry 之后的是实际数据,长度为 fLen 字节。

### SkAutoDescriptor

RAII 包装类,提供自动内存管理和小对象优化。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fDesc | SkDescriptor* | 指向 Descriptor 的指针 |
| fStorage | char[kStorageSize] | 栈上缓冲区(约 200 字节),避免小对象堆分配 |

**继承关系**: 无(值语义类,支持移动和拷贝)

**优化策略**:
- 小于 `kStorageSize` 的 Descriptor 使用栈内存
- 大对象使用堆分配,自动释放

## 公共 API 函数

### SkDescriptor 核心函数

#### 内存管理

```cpp
static std::unique_ptr<SkDescriptor> Alloc(size_t length)
```
分配指定长度的 Descriptor。长度必须 4 字节对齐。

```cpp
static size_t ComputeOverhead(int entryCount)
```
计算存储 N 个条目所需的额外空间(不含数据)。

#### 条目操作

```cpp
void* addEntry(uint32_t tag, size_t length, const void* data = nullptr)
```
添加新条目。

**参数**:
- `tag`: 条目标签,如 `kRec_SkDescriptorTag`, `kTypeface_SkDescriptorTag`
- `length`: 数据长度,必须 4 字节对齐
- `data`: 可选的初始数据,如果为 nullptr 则返回未初始化的缓冲区

**返回值**: 指向条目数据区域的指针,调用者可写入数据

```cpp
const void* findEntry(uint32_t tag, uint32_t* length) const
```
查找指定标签的条目。

**返回值**: 条目数据指针,如果未找到返回 nullptr。`length` 输出参数返回数据长度。

#### 校验和与验证

```cpp
void computeChecksum()
```
计算并存储 Descriptor 的校验和。必须在添加所有条目后调用。

```cpp
bool isValid() const
```
验证 Descriptor 的结构完整性:
- 检查总长度和对齐
- 验证条目数量与实际条目匹配
- 检查每个条目的长度合法性

```cpp
#ifdef SK_DEBUG
void assertChecksum() const
#endif
```
调试模式下断言校验和正确。

#### 比较与拷贝

```cpp
bool operator==(const SkDescriptor& other) const
bool operator!=(const SkDescriptor& other) const
```
逐字节比较两个 Descriptor(优先比较校验和快速拒绝)。

```cpp
std::unique_ptr<SkDescriptor> copy() const
```
创建深拷贝。

#### 调试

```cpp
SkString dumpRec() const
```
转储 Descriptor 内容为字符串(包括校验和和 SkScalerContextRec 信息)。

### SkAutoDescriptor 函数

#### 构造与初始化

```cpp
SkAutoDescriptor()
explicit SkAutoDescriptor(size_t size)
explicit SkAutoDescriptor(const SkDescriptor& desc)
```
默认构造、预分配大小、或从已有 Descriptor 拷贝。

```cpp
void reset(size_t size)
void reset(const SkDescriptor& desc)
```
重新分配或拷贝 Descriptor。

#### 访问

```cpp
SkDescriptor* getDesc() const
```
获取底层 Descriptor 指针。

#### 序列化

```cpp
static std::optional<SkAutoDescriptor> MakeFromBuffer(SkReadBuffer& buffer)
```
从序列化缓冲区反序列化 Descriptor。

**安全性**:
- 验证长度合法性,防止缓冲区溢出
- 检查校验和(非 Fuzzer 模式)
- 验证结构完整性

**返回值**: 成功返回 `SkAutoDescriptor`,失败返回 `std::nullopt`

## 内部实现细节

### 内存布局设计

SkDescriptor 使用自定义布局,直接在堆内存上构造:

```cpp
void* allocation = ::operator new(length);
return std::unique_ptr<SkDescriptor>(new (allocation) SkDescriptor{});
```

这是 placement new 的应用,允许可变大小的对象。

### 校验和计算

```cpp
uint32_t SkDescriptor::ComputeChecksum(const SkDescriptor* desc) {
    const uint32_t* ptr = (const uint32_t*)desc + 1;  // 跳过校验和字段
    size_t len = desc->fLength - sizeof(uint32_t);
    return SkChecksum::Hash32(ptr, len);
}
```

使用 Murmur3 哈希算法,快速且分布均匀。

### 相等性比较优化

```cpp
bool SkDescriptor::operator==(const SkDescriptor& other) const {
    const uint32_t* aa = (const uint32_t*)this;
    const uint32_t* bb = (const uint32_t*)&other;
    const uint32_t* stop = (const uint32_t*)((const char*)aa + fLength);
    do {
        if (*aa++ != *bb++)  // 首先比较校验和
            return false;
    } while (aa < stop);
    return true;
}
```

**优化点**:
1. 校验和是第一个字段,不相等时立即返回
2. 按 4 字节对齐比较,比逐字节快
3. 假定所有数据都已 4 字节对齐(addEntry 强制要求)

### SkAutoDescriptor 小对象优化

```cpp
static constexpr size_t kStorageSize
    = sizeof(SkDescriptor)
      + sizeof(SkDescriptor::Entry) + sizeof(SkScalerContextRec)
      + sizeof(SkDescriptor::Entry) + sizeof(void*)
      + 32;  // 额外缓冲
```

大多数 Descriptor 包含:
- 1 个 SkScalerContextRec 条目(约 80 字节)
- 1 个 Typeface 指针条目(8 字节)
- 少量其他数据

总计约 200 字节,栈分配避免了堆分配开销。

### 条目遍历算法

```cpp
const Entry* entry = (const Entry*)(this + 1);  // 跳过头部
int count = fCount;
while (--count >= 0) {
    if (entry->fTag == tag) {
        return entry + 1;  // 返回数据指针
    }
    entry = (const Entry*)((const char*)(entry + 1) + entry->fLen);
}
```

线性搜索,适合少量条目(通常 2-4 个)。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkString.h | dumpRec 调试输出 |
| include/private/base/SkAlign.h | 4 字节对齐检查 |
| src/core/SkScalerContext.h | SkScalerContextRec 数据结构 |
| src/core/SkChecksum.h | 校验和计算 |
| src/core/SkReadBuffer.h | 反序列化支持 |
| src/core/SkWriteBuffer.h | 序列化支持 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| src/core/SkStrike.h | 字形缓存键 |
| src/core/SkStrikeCache.h | 全局缓存查找 |
| src/core/SkScalerContext.h | 创建字体缩放上下文 |
| src/core/SkGlyphCache.h | 字形查找和缓存 |

## 设计模式与设计决策

### 设计模式

1. **值对象模式**: Descriptor 是不可变的,创建后内容不变
2. **RAII 模式**: SkAutoDescriptor 自动管理内存
3. **小对象优化**: SkAutoDescriptor 内嵌缓冲区避免堆分配
4. **工厂模式**: `Alloc()` 静态工厂函数创建实例

### 设计决策

**为何校验和是第一个字段**:
- 相等性比较时首先检查,不相等立即返回
- 作为哈希表键时直接使用校验和作为哈希值
- 提高缓存命中判断性能

**为何禁止拷贝构造**:
- Descriptor 大小可变,拷贝语义复杂
- 强制使用 `copy()` 显式创建副本,避免意外拷贝
- 通过智能指针管理生命周期

**为何要求 4 字节对齐**:
- 加速相等性比较(按 uint32_t 比较)
- 保证所有平台上的高效访问
- 简化指针运算(无需处理未对齐情况)

**SkAutoDescriptor 的设计权衡**:
- 栈分配快但有大小限制,堆分配慢但无限制
- 大多数场景下字体参数较小,栈优化有效
- 提供移动语义支持高效传递

**为何条目使用 tag 而非顺序**:
- 灵活性:不同 Descriptor 可包含不同条目组合
- 扩展性:未来可添加新条目类型
- 向后兼容:旧代码忽略不认识的 tag

## 性能考量

### 优化策略

1. **校验和快速拒绝**: 不相等的 Descriptor 在首个 4 字节比较时返回
2. **4 字节对齐比较**: 比逐字节比较快 4 倍
3. **小对象优化**: 避免 90%+ 的堆分配
4. **单次校验和计算**: 创建时计算,后续只需比较
5. **紧凑布局**: 无填充字节,最小化内存占用

### 性能特征

- **创建开销**: 约 50-100 纳秒(栈分配)或 500-1000 纳秒(堆分配)
- **比较开销**: 约 10-50 纳秒(典型 200 字节 Descriptor)
- **查找条目**: O(N) 线性搜索,N 通常 ≤ 4,约 5-20 纳秒
- **内存占用**: 典型 150-250 字节

### 缓存效益

Descriptor 的主要性能收益来自避免重复创建 `SkScalerContext`:
- 创建字体缩放上下文开销巨大(毫秒级)
- Descriptor 比较开销微不足道(纳秒级)
- 缓存命中率通常 > 95%

### 潜在瓶颈

- **大量唯一 Descriptor**: 导致缓存未命中和内存增长
- **频繁的 Descriptor 创建**: 即使有缓存,创建本身也有开销
- **长 Descriptor 比较**: 包含大量自定义数据时比较变慢

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkScalerContext.h | 依赖 | SkScalerContextRec 定义,主要条目类型 |
| src/core/SkStrike.h | 使用者 | 字形缓存使用 Descriptor 作为键 |
| src/core/SkStrikeCache.h | 使用者 | 全局缓存管理 |
| include/core/SkTypeface.h | 相关 | 字型对象,存储在 Descriptor 中 |
| src/core/SkChecksum.h | 依赖 | 校验和算法 |
| src/core/SkGlyphCache.h | 使用者 | 字形查找和缓存 |
| tests/SkDescriptorTest.cpp | 测试 | 单元测试 |
