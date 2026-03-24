# SkDataTable

> 源文件
> - include/core/SkDataTable.h
> - src/core/SkDataTable.cpp

## 概述

`SkDataTable` 是 Skia 图形库中用于存储表格结构化数据的引用计数容器。与 `SkData` 类似,它提供不可变的数据缓冲区,但组织形式为多个条目的集合,每个条目可以有不同的大小。这使得它特别适合存储字符串数组、变长记录或其他非统一大小的数据集合。

SkDataTable 支持两种模式:定长元素数组(所有元素大小相同)和变长元素数组(每个元素大小不同)。它提供高效的索引访问,零拷贝的数据共享,以及可自定义的内存释放策略。

## 架构位置

`SkDataTable` 位于 Skia 核心数据结构层,作为特殊化的数据容器:

```
Skia Core Data Structures
  ├─ Basic Containers
  │   ├─ SkData (单一数据块)
  │   └─ SkDataTable ← 当前模块(表格化数据)
  ├─ String Handling
  │   └─ Font Name Tables (使用 SkDataTable)
  └─ Serialization
      └─ Structured Data Encoding
```

主要用于字体系统中的名称表、语言标签列表等结构化数据。

## 主要类与结构体

### SkDataTable

**继承关系**:
- 基类: `SkRefCnt` (引用计数)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fCount | int | 条目数量 |
| fElemSize | size_t | 元素大小(定长模式),0 表示变长模式 |
| fU.fDir | const Dir* | 变长模式:指向目录数组 |
| fU.fElems | const char* | 定长模式:指向连续元素数组 |
| fFreeProc | FreeProc | 内存释放回调函数 |
| fFreeProcContext | void* | 释放回调的上下文 |

**核心职责**:
- 存储和管理多个数据条目
- 提供高效的随机访问接口
- 支持定长和变长两种存储模式
- 管理底层内存的生命周期

### Dir (内部结构)

用于变长模式的目录项:

| 成员 | 类型 | 说明 |
|------|------|------|
| fPtr | const void* | 指向条目数据的指针 |
| fSize | uintptr_t | 条目的字节大小 |

**内存布局(变长模式)**:
```
[Dir数组: count个Dir项][数据区: 紧凑排列的各条目数据]
```

### FreeProc

```cpp
typedef void (*FreeProc)(void* context);
```

内存释放回调类型,当 SkDataTable 销毁时调用。

## 公共 API 函数

### 属性查询

```cpp
bool isEmpty() const
int count() const
```

检查表是否为空,获取条目数量。

### 数据访问

```cpp
size_t atSize(int index) const
```
获取指定索引条目的大小。

**前提**: `index` 必须有效(0 <= index < count)

```cpp
const void* at(int index, size_t* size = nullptr) const
```
获取指定索引条目的数据指针。

**参数**:
- `index`: 条目索引
- `size`: 可选输出参数,返回条目大小

**返回值**: 指向条目数据的指针

```cpp
template <typename T>
const T* atT(int index, size_t* size = nullptr) const
```
类型安全的访问函数,返回指定类型的指针。

```cpp
const char* atStr(int index) const
```
将条目作为 C 字符串访问。

**假设**: 条目数据包含终止符 `\0`,大小等于 `strlen(str) + 1`

### 静态工厂函数

```cpp
static sk_sp<SkDataTable> MakeEmpty()
```
返回共享的空表单例。

```cpp
static sk_sp<SkDataTable> MakeCopyArrays(
    const void * const * ptrs,
    const size_t sizes[],
    int count)
```
从多个独立缓冲区拷贝创建变长表。

**参数**:
- `ptrs`: 指向各条目数据的指针数组
- `sizes`: 各条目的大小数组
- `count`: 条目数量

**实现**:
1. 计算总数据大小
2. 分配单块内存:Dir 数组 + 数据区
3. 拷贝所有数据到连续内存
4. 构造 Dir 数组指向对应数据

```cpp
static sk_sp<SkDataTable> MakeCopyArray(
    const void* array,
    size_t elemSize,
    int count)
```
从连续数组拷贝创建定长表。

**参数**:
- `array`: 连续元素数组
- `elemSize`: 单个元素大小
- `count`: 元素数量

**实现**: 直接拷贝整个数组,设置 `fElemSize` 标记定长模式。

```cpp
static sk_sp<SkDataTable> MakeArrayProc(
    const void* array,
    size_t elemSize,
    int count,
    FreeProc proc,
    void* context)
```
包装现有定长数组,使用自定义释放回调。

**用途**: 零拷贝接管现有内存,在表销毁时调用 `proc(context)` 释放。

## 内部实现细节

### 存储模式区分

通过 `fElemSize` 区分两种模式:

**定长模式** (`fElemSize != 0`):
- `fU.fElems` 指向连续数组
- 所有元素大小相同,快速索引:`fElems + index * fElemSize`
- 节省内存:无需 Dir 数组

**变长模式** (`fElemSize == 0`):
- `fU.fDir` 指向 Dir 数组
- 每个元素独立大小,通过 Dir 索引
- 灵活性高,适合字符串等变长数据

### 内存布局优化

变长表的内存布局紧凑:

```cpp
size_t bufferSize = count * sizeof(Dir) + dataSize;
void* buffer = sk_malloc_throw(bufferSize);

Dir* dir = (Dir*)buffer;
char* elem = (char*)(dir + count);  // 数据区紧跟 Dir 数组
for (int i = 0; i < count; ++i) {
    dir[i].fPtr = elem;
    dir[i].fSize = sizes[i];
    memcpy(elem, ptrs[i], sizes[i]);
    elem += sizes[i];
}
```

单次分配减少内存碎片,提高缓存局部性。

### 定长表访问

```cpp
const void* SkDataTable::at(int index, size_t* size) const {
    if (fElemSize) {
        if (size) *size = fElemSize;
        return fU.fElems + index * fElemSize;  // 直接计算偏移
    } else {
        if (size) *size = fU.fDir[index].fSize;
        return fU.fDir[index].fPtr;  // 通过目录查找
    }
}
```

定长模式下无需间接访问,性能更优。

### 空表单例

```cpp
sk_sp<SkDataTable> SkDataTable::MakeEmpty() {
    static SkDataTable* singleton = new SkDataTable();
    return sk_ref_sp(singleton);
}
```

全局共享的空表,避免重复分配。构造函数设置 `fCount=0`, `fElemSize=0`, `fU.fDir=nullptr`。

### 释放机制

析构函数调用自定义释放回调:

```cpp
SkDataTable::~SkDataTable() {
    if (fFreeProc) {
        fFreeProc(fFreeProcContext);
    }
}
```

**典型释放回调**:
- `malloc_freeproc`: 调用 `sk_free(context)`
- 自定义回调:如引用计数递减、资源解锁等

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 引用计数基类 |
| include/private/base/SkMalloc.h | 内存分配 |
| include/private/base/SkAssert.h | 断言检查 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| src/core/SkTypeface.h | 字体名称表(family, style, etc.) |
| src/ports/SkFontMgr_*.cpp | 字体管理器存储字体列表 |
| src/sfnt/ | TrueType/OpenType 表数据 |
| 测试和工具 | 存储测试数据集 |

## 设计模式与设计决策

### 设计模式

1. **不可变对象模式**: 创建后内容不变,线程安全
2. **策略模式**: 通过 FreeProc 支持不同内存管理策略
3. **单例模式**: 空表全局共享
4. **模板方法模式**: `at()` 统一接口,内部根据模式分发

### 设计决策

**为何区分定长和变长模式**:
- **性能**: 定长模式无需 Dir 数组,节省内存和间接访问开销
- **通用性**: 变长模式支持任意大小组合,灵活性高
- **自动优化**: 调用者选择合适的工厂函数,自动获得最优实现

**为何使用单块内存**:
- 减少分配次数:一次 malloc 同时获得目录和数据
- 提高缓存局部性:相关数据相邻存储
- 简化内存管理:单个 free 即可释放所有资源

**为何提供 atStr() 便捷函数**:
- 常见用例:字体名称、语言标签等字符串列表
- 类型安全:明确表达字符串语义
- 调试友好:断言检查终止符存在

**FreeProc 的设计**:
- 灵活性:支持 malloc、引用计数、自定义资源等多种来源
- 简单性:仅一个上下文参数,足够表达常见场景
- 性能:函数指针调用开销可忽略(析构时仅执行一次)

**为何不支持修改操作**:
- 不可变性保证线程安全
- 简化实现,无需考虑容量增长、重分配等
- 符合 Skia 的不可变数据模型

## 性能考量

### 优化策略

1. **定长模式优化**: 直接索引,无间接访问开销
2. **单块内存分配**: 减少分配次数和内存碎片
3. **紧凑布局**: 目录和数据相邻,提高缓存命中率
4. **空表单例**: 零拷贝共享
5. **引用计数共享**: 避免数据拷贝

### 性能特征

| 操作 | 定长模式 | 变长模式 |
|------|---------|---------|
| at() 访问 | O(1),~2ns | O(1),~3ns(额外一次间接访问) |
| atSize() | O(1),~1ns | O(1),~2ns |
| MakeCopyArray | O(N),内存拷贝 | - |
| MakeCopyArrays | - | O(N),内存拷贝+目录构建 |
| 内存占用 | 数据大小 | 数据大小 + count * 16 字节(Dir) |

### 内存效率

**定长表**:
- 对象:48 字节
- 数据:count * elemSize

**变长表**:
- 对象:48 字节
- 目录:count * 16 字节
- 数据:所有条目大小之和

**示例**(100 个字符串,平均 20 字节):
- 变长表:48 + 1600 + 2000 = 3648 字节
- 相比独立 SkData 数组:100 * (32 + 20) = 5200 字节
- 节省约 30% 内存

### 典型使用场景

**字体名称表**:
```cpp
std::vector<const char*> names = {"Arial", "Helvetica", "Times New Roman"};
std::vector<size_t> sizes = {6, 10, 17};  // 包含 \0
auto table = SkDataTable::MakeCopyArrays(names.data(), sizes.data(), 3);
for (int i = 0; i < table->count(); ++i) {
    printf("%s\n", table->atStr(i));
}
```

**定长记录**:
```cpp
struct Record { int id; float value; };
Record records[100];
auto table = SkDataTable::MakeCopyArray(records, sizeof(Record), 100);
for (int i = 0; i < table->count(); ++i) {
    const Record* rec = table->atT<Record>(i);
    // 处理记录
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkRefCnt.h | 基类 | 引用计数实现 |
| include/core/SkData.h | 相关 | 单一数据块容器 |
| src/core/SkTypeface.cpp | 使用者 | 字体名称和属性表 |
| src/ports/SkFontMgr_fontconfig.cpp | 使用者 | 字体列表管理 |
| src/sfnt/SkOTTable_name.cpp | 使用者 | TrueType 名称表解析 |
| tests/DataTableTest.cpp | 测试 | 单元测试 |
