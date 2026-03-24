# SkFontStream

> 源文件：src/core/SkFontStream.h, src/core/SkFontStream.cpp

## 概述

SkFontStream 是 Skia 字体系统中的底层流解析工具类,专门用于解析 TrueType/OpenType 字体文件格式。它提供从字节流中提取字体表(font tables)、处理 TrueType Collection (TTC) 文件、以及访问字体元数据的功能。该类是 Skia 字体加载管道的基础组件。

## 架构位置

```
Skia 字体系统
└── src/core
    ├── SkFontStream (字体流解析器)
    ├── SkTypeface (字体面抽象)
    ├── SkFontMgr (字体管理器)
    └── SkStream (通用流接口)
        └── 字体数据源(文件/内存/网络)
```

该类位于字体加载流程的最底层,直接处理二进制字体数据。

## 主要类与结构体

### SkFontStream (主类)

**继承关系**
- 无继承,纯静态工具类

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无 | - | 纯静态工具类,无实例成员 |

### 内部数据结构

#### SkSFNTHeader

SFNT (Scalable Font) 头部结构:

| 字段 | 类型 | 说明 |
|------|------|------|
| fVersion | uint32_t | 字体版本标识符 |
| fNumTables | uint16_t | 表数量 |
| fSearchRange | uint16_t | 搜索范围优化参数 |
| fEntrySelector | uint16_t | 入口选择器 |
| fRangeShift | uint16_t | 范围偏移 |

#### SkTTCFHeader

TrueType Collection 文件头:

| 字段 | 类型 | 说明 |
|------|------|------|
| fTag | uint32_t | 'ttcf' 魔数标识 |
| fVersion | uint32_t | TTC 版本 |
| fNumOffsets | uint32_t | 字体数量 |
| fOffset0 | uint32_t | 首个字体偏移(后续为数组) |

#### SkSFNTDirEntry

字体表目录项:

| 字段 | 类型 | 说明 |
|------|------|------|
| fTag | uint32_t | 表标签(如 'head', 'name') |
| fChecksum | uint32_t | 校验和 |
| fOffset | uint32_t | 表在文件中的偏移 |
| fLength | uint32_t | 表数据长度 |

## 公共 API 函数

### CountTTCEntries

```cpp
static int CountTTCEntries(SkStream* stream)
```

计算 TTC 文件中包含的字体数量,普通字体返回 1。

**参数**
- stream: 输入流(会被 rewind)

**返回值**
- TTC 文件返回字体数量
- 单字体文件返回 1
- 错误时返回 0

**流操作**
- 自动 rewind 流到起始位置
- 返回时流位置未定义

### GetTableTags

```cpp
static int GetTableTags(SkStream* stream, int ttcIndex,
                        SkSpan<SkFontTableTag> tags)
```

获取指定字体的所有表标签。

**参数**
- stream: 输入流
- ttcIndex: TTC 索引(普通字体使用 0)
- tags: 输出缓冲区

**返回值**
- 实际表数量
- 如果 tags 太小,仅填充 min(count, tags.size()) 个

**流操作**
- 自动 rewind
- 读取表目录
- 返回时流位置未定义

### GetTableData

```cpp
static size_t GetTableData(SkStream* stream, int ttcIndex,
                           SkFontTableTag tag,
                           size_t offset, size_t length, void* data)
```

读取指定表的数据。

**参数**
- stream: 输入流
- ttcIndex: TTC 索引
- tag: 表标签(如 SkSetFourByteTag('h','e','a','d'))
- offset: 表内偏移
- length: 读取长度(~0U 表示全部)
- data: 输出缓冲(nullptr 表示仅查询大小)

**返回值**
- 实际读取/可读取的字节数
- 0 表示表不存在或错误

**安全特性**
- 溢出检查: offset + length < offset
- 范围验证: offset >= realLength
- 自动截断超出表大小的请求

### GetTableSize

```cpp
static size_t GetTableSize(SkStream* stream, int ttcIndex,
                           SkFontTableTag tag)
```

获取表的大小(便捷方法)。

**实现**
```cpp
return GetTableData(stream, ttcIndex, tag, 0, ~0U, nullptr);
```

## 内部实现细节

### 字节序处理

所有多字节值使用大端序(Big Endian):

```cpp
uint32_t tag = SkEndian_SwapBE32(header->fCollection.fTag);
uint16_t numTables = SkEndian_SwapBE16(header->fSingle.fNumTables);
```

### TTC 检测逻辑

```cpp
if (SkSetFourByteTag('t', 't', 'c', 'f') == tag) {
    // TTC 文件
    读取 fNumOffsets
    根据 ttcIndex 定位到具体字体
} else {
    // 普通 SFNT 文件
}
```

### 表查找算法

```cpp
for (int i = 0; i < header.fCount; i++) {
    if (SkEndian_SwapBE32(header.fDir[i].fTag) == tag) {
        // 找到目标表
        计算偏移和长度
        验证范围
        读取数据
        return length;
    }
}
return 0;  // 未找到
```

线性搜索,复杂度 O(n),n 为表数量(通常 < 20)。

### 安全验证

1. **溢出检查**
```cpp
if (offset + length < offset) {  // 整数溢出
    return 0;
}
```

2. **范围验证**
```cpp
if (offset >= realLength) {  // 起始位置超出范围
    return 0;
}
if (length > realLength - offset) {  // 截断到有效范围
    length = realLength - offset;
}
```

3. **流位置验证**
```cpp
if (!skip(stream, bytesToSkip)) {
    return 0;  // 无法跳转到目标位置
}
```

### 内存管理

```cpp
// SfntHeader 使用智能内存管理
struct SfntHeader {
    ~SfntHeader() { sk_free(fDir); }  // RAII 自动释放

    SkSFNTDirEntry* fDir;  // 动态分配数组
    int fCount;
};
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkStream | 流抽象接口 |
| SkEndian | 字节序转换 |
| SkMalloc | 内存分配 |
| SkAutoMalloc | 智能内存管理 |
| SkFourByteTag | 四字节标签宏 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkTypeface | 创建字体面时读取表数据 |
| SkFontMgr | 检测字体格式和数量 |
| SkScalerContext | 访问字形数据表 |
| SkTestTypeface | 测试用例 |

## 设计模式与设计决策

### 设计模式

1. **门面模式**: 为复杂的字体格式提供简化接口
2. **静态工具类**: 无状态设计,避免对象生命周期管理
3. **RAII**: SfntHeader 使用析构函数自动释放资源

### 设计决策

1. **为何使用静态方法**
   - 无需维护状态
   - 每次操作都 rewind 流,无位置依赖
   - 简化调用方代码

2. **流自动 rewind 的原因**
   - 避免调用方记录位置
   - 支持并发读取(每次从头开始)
   - 简化错误恢复

3. **返回时流位置未定义**
   - 减少额外的 seek 操作
   - 调用方通常不关心最终位置
   - 下次调用会自动 rewind

4. **线性搜索而非二分查找**
   - 表数量通常很小(< 20)
   - 避免复杂的排序假设
   - 代码更简单可靠

5. **安全性优先设计**
   - 全面的溢出检查
   - 范围自动截断而非失败
   - 防御性编程应对恶意字体文件

## 性能考量

### 性能特征

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| CountTTCEntries | O(1) | 仅读取头部 |
| GetTableTags | O(n) | n = 表数量 |
| GetTableData | O(n) | 线性查找表 |

### 内存使用

```cpp
// 临时分配
sizeof(SkSFNTDirEntry) * numTables
// 典型值: 16 字节 * 15 = 240 字节
```

### 优化策略

1. **SkAutoSMalloc**: 小数据用栈,大数据用堆
```cpp
SkAutoSMalloc<1024> storage(sizeof(SkSharedTTHeader));
```

2. **批量读取**: 一次性读取整个表目录
```cpp
size_t size = fCount * sizeof(SkSFNTDirEntry);
fDir = (SkSFNTDirEntry*)sk_malloc_throw(size);
return read(stream, fDir, size);
```

3. **延迟解析**: 仅在需要时读取表内容,不预加载

### 潜在瓶颈

- **磁盘 I/O**: 每次操作都 rewind,可能导致多次 seek
- **线性搜索**: 大量查询时可缓存表位置映射
- **重复解析**: 相同流的多次调用会重复解析头部

### 优化建议

对于频繁访问:
```cpp
// 推荐: 一次性读取所有标签,缓存映射
int count = GetTableTags(stream, ttcIndex, tags);
std::unordered_map<uint32_t, size_t> tableOffsets;
// 后续直接访问映射
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkStream.h | 流抽象接口定义 |
| include/core/SkTypeface.h | 字体面接口(使用表数据) |
| src/core/SkFontDescriptor.cpp | 字体描述符(序列化字体流) |
| src/core/SkScalerContext.cpp | 缩放上下文(访问字形表) |
| src/ports/SkFontHost_*.cpp | 平台字体加载实现 |
| tests/FontHostStreamTest.cpp | 单元测试 |
