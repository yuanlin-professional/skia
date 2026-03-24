# SkString

> 源文件
> - include/core/SkString.h
> - src/core/SkString.cpp

## 概述

`SkString` 是 Skia 的轻量级字符串类,采用引用计数和写时复制(COW)策略,使字符串赋值和复制操作高效且无额外内存开销。该类假定字符串使用 UTF-8 编码,提供丰富的字符串操作接口,包括插入、追加、格式化、查找和比较等功能。作为 Skia API 的一部分,它在性能和易用性之间取得了良好平衡。

主要特点:
- 引用计数共享数据,减少内存分配
- 写时复制(Copy-on-Write)优化
- 支持移动语义
- 丰富的字符串操作接口
- printf 风格的格式化支持
- 与 std::string 兼容

## 架构位置

`SkString` 在 Skia 中的位置:
- **层级**: 基础工具类,被广泛使用
- **用途**: 字体名称、文件路径、调试信息、序列化等
- **性能**: 平衡易用性和性能的字符串实现
- **接口**: Skia 公共 API 的一部分

## 主要类与结构体

### SkString

**继承关系**: 无基类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRec` | `sk_sp<Rec>` | 指向 Rec 记录的智能指针 |

### SkString::Rec (内部结构体)

字符串数据的实际存储结构。

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fLength` | `uint32_t` | 字符串逻辑长度(限制32位) |
| `fRefCnt` | `std::atomic<int32_t>` | 原子引用计数 |
| `fBeginningOfData` | `char[1]` | 柔性数组成员(实际数据) |

**特殊成员**:
- `gEmptyRec`: 静态空字符串实例,所有空 SkString 共享

## 公共 API 函数

### 构造与赋值

```cpp
SkString();                          // 默认构造(空字符串)
explicit SkString(size_t len);       // 预分配指定长度
explicit SkString(const char text[]);
SkString(const char text[], size_t len);
SkString(const SkString&);           // 拷贝构造(引用计数)
SkString(SkString&&);                // 移动构造
explicit SkString(const std::string&);
explicit SkString(std::string_view);
~SkString();

SkString& operator=(const SkString&);
SkString& operator=(SkString&&);
SkString& operator=(const char text[]);
```

### 查询

```cpp
bool isEmpty() const;
size_t size() const;
const char* data() const;
const char* c_str() const;
char operator[](size_t n) const;
const char* begin() const;
const char* end() const;

// 比较
bool equals(const SkString&) const;
bool equals(const char text[]) const;
bool equals(const char text[], size_t len) const;
friend bool operator==(const SkString& a, const SkString& b);
friend bool operator!=(const SkString& a, const SkString& b);

// 查找
bool startsWith(const char prefixStr[]) const;
bool startsWith(char prefixChar) const;
bool endsWith(const char suffixStr[]) const;
bool endsWith(char suffixChar) const;
bool contains(const char substring[]) const;
bool contains(char subchar) const;
int find(const char substring[]) const;
int findLastOf(char subchar) const;
```

### 修改

```cpp
char* data();  // 写时复制触发点
char& operator[](size_t n);
char* begin();
char* end();

void reset();                        // 清空字符串
void resize(size_t len);             // 调整大小(保留内容)
void set(const char text[]);
void set(const char text[], size_t len);
void set(std::string_view str);

// 插入
void insert(size_t offset, const char text[]);
void insert(size_t offset, const char text[], size_t len);
void insert(size_t offset, const SkString& str);
void insert(size_t offset, std::string_view str);
void insertUnichar(size_t offset, SkUnichar);
void insertS32(size_t offset, int32_t value);
void insertS64(size_t offset, int64_t value, int minDigits = 0);
void insertU32(size_t offset, uint32_t value);
void insertU64(size_t offset, uint64_t value, int minDigits = 0);
void insertHex(size_t offset, uint32_t value, int minDigits = 0);
void insertScalar(size_t offset, SkScalar);

// 追加
void append(const char text[]);
void append(const char text[], size_t len);
void append(const SkString& str);
void append(std::string_view str);
void appendUnichar(SkUnichar uni);
void appendS32(int32_t value);
void appendS64(int64_t value, int minDigits = 0);
void appendU32(uint32_t value);
void appendU64(uint64_t value, int minDigits = 0);
void appendHex(uint32_t value, int minDigits = 0);
void appendScalar(SkScalar value);

// 前置插入
void prepend(const char text[]);
void prepend(const char text[], size_t len);
void prepend(const SkString& str);
void prepend(std::string_view str);
void prependUnichar(SkUnichar uni);
void prependS32(int32_t value);
void prependS64(int32_t value, int minDigits = 0);
void prependHex(uint32_t value, int minDigits = 0);
void prependScalar(SkScalar value);

// 格式化
void printf(const char format[], ...) SK_PRINTF_LIKE(2, 3);
void printVAList(const char format[], va_list);
void appendf(const char format[], ...) SK_PRINTF_LIKE(2, 3);
void appendVAList(const char format[], va_list);
void prependf(const char format[], ...) SK_PRINTF_LIKE(2, 3);
void prependVAList(const char format[], va_list);

// 删除
void remove(size_t offset, size_t length);

// 运算符
SkString& operator+=(const SkString& s);
SkString& operator+=(const char text[]);
SkString& operator+=(char c);

// 交换
void swap(SkString& other);
```

### 辅助函数

```cpp
// 全局函数
SkString SkStringPrintf(const char* format, ...) SK_PRINTF_LIKE(1, 2);
static inline SkString SkStringPrintf();
static inline void swap(SkString& a, SkString& b);
```

### C 字符串辅助

```cpp
// 内联函数
static inline bool SkStrStartsWith(const char string[], const char prefixStr[]);
static inline bool SkStrStartsWith(const char string[], char prefixChar);
bool SkStrEndsWith(const char string[], const char suffixStr[]);
bool SkStrEndsWith(const char string[], char suffixChar);
int SkStrStartsWithOneOf(const char string[], const char prefixes[]);
static inline int SkStrFind(const char string[], const char substring[]);
static inline int SkStrFindLastOf(const char string[], char subchar);
static inline bool SkStrContains(const char string[], const char substring[]);
static inline bool SkStrContains(const char string[], char subchar);

// 数值追加到缓冲区
char* SkStrAppendU32(char buffer[], uint32_t);
char* SkStrAppendS32(char buffer[], int32_t);
char* SkStrAppendU64(char buffer[], uint64_t, int minDigits);
char* SkStrAppendS64(char buffer[], int64_t, int minDigits);
char* SkStrAppendScalar(char buffer[], SkScalar);
```

## 内部实现细节

### 引用计数机制

```cpp
void SkString::Rec::ref() const {
    if (this == &SkString::gEmptyRec) {
        return;  // 空字符串不需要引用计数
    }
    fRefCnt.fetch_add(+1, std::memory_order_relaxed);
}

void SkString::Rec::unref() const {
    if (this == &SkString::gEmptyRec) {
        return;
    }
    int32_t oldRefCnt = fRefCnt.fetch_add(-1, std::memory_order_acq_rel);
    if (1 == oldRefCnt) {
        delete this;  // 最后一个引用,释放内存
    }
}

bool SkString::Rec::unique() const {
    return fRefCnt.load(std::memory_order_acquire) == 1;
}
```

### 写时复制(COW)

```cpp
char* SkString::data() {
    if (fRec->fLength) {
        if (!fRec->unique()) {
            // 多个引用,需要复制
            fRec = Rec::Make(fRec->data(), fRec->fLength);
        }
    }
    return fRec->data();
}
```

### 内存分配策略

```cpp
sk_sp<SkString::Rec> SkString::Rec::Make(const char text[], size_t len) {
    if (0 == len) {
        return sk_sp<Rec>(const_cast<Rec*>(&gEmptyRec));
    }

    SkSafeMath safe;
    uint32_t stringLen = safe.castTo<uint32_t>(len);
    // 计算总大小:头部 + 数据 + null 终止符
    size_t allocationSize = safe.add(len, SizeOfRec() + sizeof(char));
    // 对齐到 4 字节
    allocationSize = safe.alignUp(allocationSize, 4);

    void* storage = ::operator new (allocationSize);
    sk_sp<Rec> rec(new (storage) Rec(stringLen, 1));
    if (text) {
        memcpy(rec->data(), text, len);
    }
    rec->data()[len] = 0;
    return rec;
}
```

**设计特点**:
- 空字符串共享全局单例
- 4 字节对齐优化缓存行
- 柔性数组成员减少内存碎片
- placement new 自定义内存布局

### resize 优化

```cpp
void SkString::resize(size_t len) {
    len = trim_size_t_to_u32(len);
    if (0 == len) {
        this->reset();
    } else if (fRec->unique() && ((len >> 2) <= (fRec->fLength >> 2))) {
        // 如果新长度在同一个 4 字节对齐块内,原地调整
        char* p = this->data();
        p[len] = '\0';
        fRec->fLength = SkToU32(len);
    } else {
        // 否则分配新内存
        SkString newString(len);
        char* dest = newString.data();
        int copyLen = std::min<uint32_t>(len, this->size());
        memcpy(dest, this->c_str(), copyLen);
        dest[copyLen] = '\0';
        this->swap(newString);
    }
}
```

### insert 优化

```cpp
void SkString::insert(size_t offset, const char text[], size_t len) {
    if (len) {
        // ... 边界检查和长度限制 ...

        if (fRec->unique() && (length >> 2) == ((length + len) >> 2)) {
            // 原地插入(有足够空间)
            char* dst = this->data();
            if (offset < length) {
                memmove(dst + offset + len, dst + offset, length - offset);
            }
            memcpy(dst + offset, text, len);
            dst[length + len] = 0;
            fRec->fLength = SkToU32(length + len);
        } else {
            // 分配新内存
            SkString tmp(fRec->fLength + len);
            char* dst = tmp.data();
            // 复制前缀、插入内容、后缀
            // ...
            this->swap(tmp);
        }
    }
}
```

### printf 实现

```cpp
template <int SIZE>
static StringBuffer apply_format_string(
    const char* format, va_list args,
    char (&stackBuffer)[SIZE],
    SkString* heapBuffer)
{
    va_list argsCopy;
    va_copy(argsCopy, args);
    int outLength = std::vsnprintf(stackBuffer, SIZE, format, args);

    if (outLength < 0) {
        // 错误处理
        va_end(argsCopy);
        return {stackBuffer, 0};
    }
    if (outLength < SIZE) {
        // 栈缓冲区足够
        va_end(argsCopy);
        return {stackBuffer, outLength};
    }

    // 栈缓冲区不够,使用堆
    heapBuffer->set(nullptr, outLength);
    char* heapBufferDest = heapBuffer->data();
    std::vsnprintf(heapBufferDest, outLength + 1, format, argsCopy);
    va_end(argsCopy);
    return {heapBufferDest, outLength};
}
```

**优化点**:
- 先尝试栈分配(1024字节)
- 不够时动态分配
- 避免大多数情况的堆分配

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRefCnt` | 引用计数智能指针 |
| `SkMalloc` | 内存分配 |
| `SkSafeMath` | 安全算术运算 |
| `SkUTF` | UTF-8 编码支持 |
| `SkFloatingPoint` | 浮点数处理 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| 整个 Skia | 作为基础字符串类 |
| API 层 | 字体名称、文件路径等 |
| 调试工具 | 格式化输出 |
| 序列化 | 文本数据存储 |

## 设计模式与设计决策

### 设计模式

1. **写时复制(COW)**: 延迟复制直到修改
2. **智能指针**: `sk_sp<Rec>` 自动管理生命周期
3. **享元模式**: 空字符串共享全局实例
4. **策略模式**: 不同大小字符串使用不同分配策略

### 设计决策

1. **32位长度限制**:
   - `fLength` 使用 `uint32_t`
   - 即使在 64 位平台也限制为 4GB
   - 实践中足够,节省内存

2. **引用计数 vs 移动**:
   - 拷贝构造仅增加引用计数(极快)
   - 移动构造转移所有权
   - 自动选择最优策略

3. **4字节对齐**:
   - `allocationSize = safe.alignUp(allocationSize, 4)`
   - 提高缓存行利用率
   - 简化内存管理

4. **原地修改优化**:
   - 检查是否 `unique()` 且空间足够
   - 避免不必要的分配
   - resize/insert/set 都有原地优化

5. **特殊值处理**:
   - 空字符串不分配内存
   - 单字节字符串也完整分配
   - 平衡复杂度和内存效率

6. **printf 栈优化**:
   - 1024 字节栈缓冲区
   - 覆盖绝大多数格式化场景
   - 避免堆分配

## 性能考量

1. **拷贝开销**:
   - 拷贝仅增加引用计数(原子操作)
   - 赋值不分配内存
   - 大字符串高效共享

2. **写时复制开销**:
   - 修改时检查 `unique()`
   - 多引用时才复制
   - 只读操作零开销

3. **内存局部性**:
   - Rec 头部和数据连续
   - 减少指针追踪
   - 缓存友好

4. **小字符串优化**:
   - 空字符串零分配
   - 对齐减少碎片
   - 快速路径优化

5. **批量操作**:
   - `insert` 一次性移动数据
   - `resize` 尽量原地调整
   - 减少内存拷贝

6. **原子操作**:
   - `fRefCnt` 使用 `std::atomic`
   - `memory_order_relaxed` 优化性能
   - 仅在必要时使用强序

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkRefCnt.h` | 智能指针 |
| `include/private/base/SkMalloc.h` | 内存分配 |
| `src/base/SkSafeMath.h` | 安全算术 |
| `src/base/SkUTF.h` | UTF-8 支持 |
| `include/private/base/SkTypeTraits.h` | 类型特征 |
