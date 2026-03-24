# SkBuffer - 内存缓冲区读写工具
> 源文件: `src/base/SkBuffer.h`, `src/base/SkBuffer.cpp`

## 概述
SkBuffer 模块提供了轻量级的内存缓冲区读取（SkRBuffer）和写入（SkWBuffer）工具类。这两个类封装了对内存块的顺序读写操作，支持边界检查、4字节对齐填充、以及类型安全的数据读写接口。它们广泛应用于 Skia 的序列化、反序列化、以及底层数据传输场景。

## 架构位置
SkBuffer 位于 Skia 基础工具模块（src/base）中，是底层数据处理层的重要组件。它为序列化系统、字体数据解析、图片格式编解码、GPU 命令缓冲区等上层模块提供高效的内存读写抽象。

## 主要类与结构体

### SkRBuffer
轻量级内存读取缓冲区类，用于从内存块中顺序读取数据。

**继承关系**: 继承自 `SkNoncopyable`（不可拷贝）

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fData | const char* | 缓冲区起始地址 |
| fPos | const char* | 当前读取位置 |
| fStop | const char* | 缓冲区结束地址 |
| fValid | bool | 读取状态标志（读取失败后置为 false） |

**核心方法**:
```cpp
SkRBuffer(const void* data, size_t size)   // 构造函数
bool read(void* buffer, size_t size)       // 读取数据
const void* skip(size_t bytes)             // 跳过字节
bool skipToAlign4()                        // 对齐到4字节边界
bool readU8/readS32/readU32(...)          // 类型化读取
```

### SkWBuffer
轻量级内存写入缓冲区类，用于向内存块中顺序写入数据。

**继承关系**: 继承自 `SkNoncopyable`（不可拷贝）

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fData | char* | 缓冲区起始地址 |
| fPos | char* | 当前写入位置 |
| fStop | char* | 缓冲区结束地址（nullptr 表示无边界检查） |

**核心方法**:
```cpp
SkWBuffer(void* data, size_t size)         // 构造函数（带边界检查）
void write(const void* buffer, size_t size) // 写入数据
void* skip(size_t size)                    // 跳过（预留空间）
size_t padToAlign4()                       // 填充到4字节对齐
void write8/write16/write32(...)          // 类型化写入
```

## 公共 API 函数

### SkRBuffer 读取接口

#### `SkRBuffer(const void* data, size_t size)`
- **功能**: 构造读取缓冲区，初始化数据指针和边界
- **参数**:
  - data: 数据起始地址（可以为 nullptr 当 size 为 0）
  - size: 缓冲区大小
- **初始化**: 设置 fData/fPos 为起始地址，fStop 为结束地址

#### `bool read(void* buffer, size_t size)`
- **功能**: 从缓冲区读取指定字节数的数据
- **参数**:
  - buffer: 目标缓冲区
  - size: 读取字节数
- **返回值**: 成功返回 true，失败返回 false（剩余空间不足）
- **副作用**: 失败时设置 fValid 为 false

#### `const void* skip(size_t bytes)`
- **功能**: 跳过指定字节数，返回跳过前的位置指针
- **参数**: bytes - 要跳过的字节数
- **返回值**: 跳过前的位置指针，失败返回 nullptr
- **用途**: 用于读取数组或定位到特定位置

#### `template <typename T> const T* skipCount(size_t count)`
- **功能**: 跳过 count 个类型 T 的元素
- **参数**: count - 元素数量
- **返回值**: 指向元素数组起始位置的类型化指针
- **安全性**: 使用 SkSafeMath::Mul 防止整数溢出

#### `bool skipToAlign4()`
- **功能**: 将读取位置对齐到下一个4字节边界
- **返回值**: 成功返回 true，空间不足返回 false
- **对齐计算**: 使用 `SkAlign4(pos) - pos` 计算需要跳过的字节数

### SkWBuffer 写入接口

#### `SkWBuffer(void* data, size_t size)`
- **功能**: 构造写入缓冲区，启用边界检查
- **参数**:
  - data: 缓冲区起始地址
  - size: 缓冲区大小

#### `void write(const void* buffer, size_t size)`
- **功能**: 向缓冲区写入数据
- **参数**:
  - buffer: 源数据指针
  - size: 写入字节数
- **断言**: 写入不会超出边界（fStop）
- **优化**: size 为 0 时直接返回

#### `void* skip(size_t size)`
- **功能**: 跳过指定字节（预留空间），返回跳过前的位置
- **返回值**: 空缓冲区（fData == nullptr）时返回 nullptr
- **用途**: 预分配空间后稍后填充

#### `size_t padToAlign4()`
- **功能**: 用零填充至下一个4字节边界
- **返回值**: 填充的字节数（0-3）
- **实现**: 循环写入零字节直到对齐

#### `void writePtr(const void* x)` / `void write32(int32_t x)` / `void write16(int16_t x)` / `void write8(int8_t x)`
- **功能**: 类型化的写入接口
- **参数**: 对应类型的值
- **实现**: 调用 `writeNoSizeCheck` 写入值的内存表示

### 状态查询接口

#### `size_t pos() const`
- **功能**: 返回当前读写位置的偏移量（相对于起始地址）
- **计算**: `fPos - fData`

#### `size_t size() const` (SkRBuffer)
- **功能**: 返回缓冲区总大小
- **计算**: `fStop - fData`

#### `bool eof() const` (SkRBuffer)
- **功能**: 检查是否已读取到缓冲区末尾
- **返回值**: `fPos >= fStop`

#### `size_t available() const` (SkRBuffer)
- **功能**: 返回剩余可读字节数
- **计算**: `fStop - fPos`

#### `bool isValid() const` (SkRBuffer)
- **功能**: 检查缓冲区是否仍处于有效状态
- **返回值**: 任何读取失败后返回 false

## 内部实现细节

### 内存安全机制
1. **边界检查**: 读取前检查 `size <= available()`
2. **失败传播**: 一次失败后 `fValid` 置为 false，后续操作被禁止
3. **断言保护**: 写入时使用断言确保不超出边界
4. **空指针处理**: 允许 data 为 nullptr 当 size 为 0

### 内存拷贝优化
使用 `sk_careful_memcpy` 而非标准 `memcpy`：
- 该函数会检查源和目标重叠情况
- 在小数据时可能内联优化
- 提供更好的调试信息

### 对齐填充实现
```cpp
size_t SkWBuffer::padToAlign4() {
    size_t pos = this->pos();
    size_t n = SkAlign4(pos) - pos;
    if (n && fData) {
        char* p = fPos;
        char* stop = p + n;
        do {
            *p++ = 0;
        } while (p < stop);
    }
    fPos += n;
    return n;
}
```
逐字节填充零，而非使用 memset，可能是为了：
- 避免函数调用开销（通常只填充 1-3 字节）
- 更好的内联和编译器优化

### SkScalar 类型兼容
头文件中定义 `typedef float SkScalar`，保证 `writeScalar` 写入 4 字节。这是为了兼容历史代码和跨平台一致性。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 边界检查断言 |
| include/private/base/SkNoncopyable.h | 不可拷贝基类 |
| src/base/SkSafeMath.h | 防止整数溢出的安全运算 |
| include/private/base/SkAlign.h | 对齐计算工具 |
| include/private/base/SkMalloc.h | sk_careful_memcpy |

### 被依赖的模块
- 序列化系统（SkFlattenable）
- 字体文件解析（TrueType/OpenType）
- 图片编解码器（PNG, JPEG 等）
- 路径数据序列化
- GPU 命令缓冲区构建
- 网络传输数据打包

## 设计模式与设计决策

### 非拥有型设计
SkRBuffer 和 SkWBuffer 都不拥有内存：
- 不负责分配和释放内存
- 仅持有指针，不管理生命周期
- 使用者负责确保缓冲区在使用期间有效

这种设计带来：
- **优点**: 零额外内存开销，灵活性高
- **缺点**: 需要调用者管理内存生命周期

### 失败状态记录（SkRBuffer）
SkRBuffer 使用 `fValid` 标志记录失败状态：
- 一次失败后所有后续操作都返回失败
- 避免部分读取的未定义行为
- 简化错误处理逻辑

### 写入无返回值（SkWBuffer）
SkWBuffer 的 write 方法返回 void：
- 使用断言而非运行时检查
- 假设调用者已预先验证缓冲区大小
- 适用于性能关键路径

### 类型安全的便利接口
提供 `readU8`, `write32` 等类型化方法：
- 避免手动计算字节大小
- 提高代码可读性
- 减少类型转换错误

## 性能考量

### 轻量级设计
- **结构体大小**:
  - SkRBuffer: 32 字节（3 指针 + 1 bool + 填充）
  - SkWBuffer: 24 字节（3 指针）
- **无虚函数**: 避免虚函数表开销
- **内联友好**: 简单方法易于被编译器内联

### 对齐的性能影响
4字节对齐的必要性：
- 某些架构（如 ARM）要求整数必须对齐访问
- 对齐访问通常更快（单次总线事务）
- 避免触发硬件陷阱或软件模拟

### 空缓冲区优化
允许 fData 为 nullptr 的设计：
- 可以"空运行"计算所需空间（write 不实际写入）
- 通过 pos() 获取所需的缓冲区大小
- 适用于两阶段序列化（先计算大小，再分配并写入）

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkAlign.h | 提供 SkAlign4 对齐计算 |
| src/base/SkSafeMath.h | 安全的乘法运算（防溢出） |
| src/core/SkReadBuffer.h | 更高级的反序列化缓冲区 |
| src/core/SkWriteBuffer.h | 更高级的序列化缓冲区 |
| src/core/SkPictureData.cpp | 使用 SkRBuffer 读取图片数据 |
| src/core/SkTypeface.cpp | 字体序列化使用 SkWBuffer |
| src/ports/SkFontHost_*.cpp | 字体文件解析 |
