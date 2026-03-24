# KeyBuilder

> 源文件: src/gpu/KeyBuilder.h

## 概述

`KeyBuilder` 是 Skia GPU 模块中用于构建缓存键(cache key)的核心工具类。它提供了一套高效的位级操作 API,用于将各种渲染状态、着色器参数和配置信息编码成紧凑的二进制键。这些键主要用于着色器程序缓存、管线状态对象缓存和各种 GPU 资源的查找,是 GPU 性能优化的关键基础设施。

该模块的设计目标是:最小化缓存键的大小(减少内存占用和哈希计算时间)、提供类型安全的接口、支持调试信息注入(通过子类 `StringKeyBuilder`)。核心思想是将多个小于32位的值紧密打包到 `uint32_t` 数组中,避免空间浪费。

## 架构位置

在 Skia 架构中,`KeyBuilder` 位于以下位置:

- **基础设施层**: 为 GPU 渲染管线提供通用的键构建工具
- **上游使用**: 被着色器编译器、管线构建器、资源管理器使用
- **缓存系统**: 与 GPU 缓存系统紧密集成
- **跨后端**: Ganesh 和 Graphite 都使用该工具

该模块是平台无关的,不依赖特定的 GPU API,提供通用的键构建抽象。

## 主要类与结构体

### KeyBuilder 类

核心的键构建器基类。

**继承关系**: 无继承,但可被 `StringKeyBuilder` 继承。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fData` | `TArray<uint32_t>*` | 指向键数据数组的指针 |
| `fCurValue` | `uint32_t` | 当前正在构建的32位值 |
| `fBitsUsed` | `uint32_t` | `fCurValue` 中已使用的位数 |

**设计说明**: 使用外部提供的数组存储键数据,避免内部动态分配,支持栈上分配的优化。

### StringKeyBuilder 类

带调试信息的键构建器子类。

**继承关系**: 继承自 `KeyBuilder`。

**额外成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fDescription` | `SkString` | 累积的键描述字符串 |

**用途**: 在调试模式下记录每个键元素的标签和值,便于问题诊断。

## 公共 API 函数

### 构造与析构

#### KeyBuilder 构造函数
```cpp
KeyBuilder(skia_private::TArray<uint32_t, true>* data)
```
**功能**: 创建键构建器,使用外部数组存储数据。
**参数**: `data` - 指向 `uint32_t` 数组的指针(栈上分配,带小数组优化)。

#### 虚析构函数
```cpp
virtual ~KeyBuilder()
```
**功能**: 确保在销毁前调用了 `flush()`。
**断言**: `fBitsUsed == 0`,确保没有未提交的数据。

### 核心添加函数

#### addBits
```cpp
virtual void addBits(uint32_t numBits, uint32_t val, std::string_view label)
```
**功能**: 添加指定位数的值到键中。
**参数**:
- `numBits`: 要添加的位数 (1-32)
- `val`: 值(必须在 `numBits` 位范围内)
- `label`: 调试标签(调试版本使用)
**算法**:
1. 将 `val` 左移 `fBitsUsed` 位并或入 `fCurValue`
2. 增加 `fBitsUsed`
3. 如果 `fBitsUsed >= 32`,推送 `fCurValue` 到数组,处理溢出

**溢出处理**:
```cpp
if (fBitsUsed >= 32) {
    fData->push_back(fCurValue);
    uint32_t excess = fBitsUsed - 32;
    fCurValue = excess ? (val >> (numBits - excess)) : 0;
    fBitsUsed = excess;
}
```

#### addBytes
```cpp
void addBytes(uint32_t numBytes, const void* data, std::string_view label)
```
**功能**: 添加字节数组到键中。
**实现**: 逐字节调用 `addBits(8, byte, label)`。

#### addBool
```cpp
void addBool(bool b, std::string_view label)
```
**功能**: 添加布尔值(作为1位)。
**实现**: `addBits(1, b, label)`。

#### add32
```cpp
void add32(uint32_t v, std::string_view label = "unknown")
```
**功能**: 添加完整的32位值。
**实现**: `addBits(32, v, label)`。
**默认标签**: "unknown"(鼓励显式标注)。

### 辅助函数

#### appendComment
```cpp
virtual void appendComment(const char* comment)
```
**功能**: 添加注释到键描述(仅 `StringKeyBuilder` 实现)。
**用途**: 在复杂的键构建过程中添加分隔符或说明。

#### flush
```cpp
void flush()
```
**功能**: 将未完成的位推送到数组,对齐到32位边界。
**必须调用**: 在使用缓存键之前或创建后端特定数据段之前调用。
**实现**:
```cpp
if (fBitsUsed) {
    fData->push_back(fCurValue);
    fCurValue = 0;
    fBitsUsed = 0;
}
```

## StringKeyBuilder 特有函数

### addBits 重写
```cpp
void addBits(uint32_t numBits, uint32_t val, std::string_view label) override
```
**功能**: 调用基类 `addBits`,同时记录标签和值到 `fDescription`。
**格式**: `"{label}: {val}\n"`。

### appendComment 重写
```cpp
void appendComment(const char* comment) override
```
**功能**: 添加注释行到描述字符串。
**格式**: `"{comment}\n"`。

### description
```cpp
SkString description() const
```
**功能**: 获取完整的键描述字符串。
**用途**: 调试输出、日志记录、错误报告。

## 内部实现细节

### 位打包算法
使用小端序位打包:
- 第一个添加的值占据低位
- 后续值依次占据更高的位
- 32位边界自动处理

示例:
```cpp
KeyBuilder kb(&array);
kb.addBits(5, 10, "a");  // 占据位 [0:4]
kb.addBits(8, 255, "b"); // 占据位 [5:12]
kb.addBits(20, 12345, "c"); // 位 [13:32] 和 [0:0] (溢出到下一个 uint32_t)
kb.flush();
```

### 溢出处理
当添加的位跨越32位边界时:
1. 当前32位值的高位部分被填充
2. 该值被推送到数组
3. 溢出的位部分作为新的 `fCurValue` 的低位
4. `fBitsUsed` 更新为溢出的位数

### 字边界对齐
`flush()` 确保键数据对齐到32位边界,这对缓存查找和哈希计算至关重要:
- 方便使用标准哈希函数
- 避免未定义行为(读取未初始化的位)
- 支持后端特定数据的追加

### 断言与验证
代码中包含多个 `SkASSERT`:
- `numBits > 0 && numBits <= 32`: 位数合法性
- `numBits == 32 || (val < (1u << numBits))`: 值在范围内
- `fCurValue < (1u << fBitsUsed)`: 内部状态一致性
- `fBitsUsed == 0` (析构时): 确保 `flush()` 被调用

### 虚函数设计
`addBits` 和 `appendComment` 是虚函数,允许子类(如 `StringKeyBuilder`)注入额外的行为,而不改变核心逻辑。

## 依赖关系

### 依赖的模块

| 模块 | 依赖内容 | 用途 |
|------|----------|------|
| `include/core/SkString.h` | `SkString` | 字符串操作 |
| `include/private/base/SkTArray.h` | `TArray` | 动态数组 |
| `include/private/base/SkAssert.h` | `SkASSERT` | 断言宏 |

### 被依赖的模块

| 模块 | 使用内容 | 用途 |
|------|----------|------|
| Ganesh 着色器缓存 | `KeyBuilder` | 构建着色器键 |
| Graphite 管线缓存 | `KeyBuilder` | 构建管线键 |
| 程序描述符 | `add32`, `addBits` | 编码程序状态 |
| 资源缓存 | 键构建接口 | 纹理/缓冲区查找 |
| 单元测试 | `StringKeyBuilder` | 验证键生成逻辑 |

## 设计模式与设计决策

### 1. 构建器模式 (Builder Pattern)
`KeyBuilder` 是经典的构建器模式实现,提供流式接口逐步构建复杂的键对象。

### 2. 外部存储策略
键数据存储在外部提供的数组中,而非内部成员:
- 避免构造函数中的动态分配
- 支持栈上分配小数组(带 `TArray<T, true>` 优化)
- 调用者控制内存布局

### 3. 虚函数扩展点
通过虚函数提供扩展点,允许调试版本(如 `StringKeyBuilder`)添加额外功能,而不影响生产版本的性能。

### 4. RAII 验证
析构函数中的断言确保资源正确清理(即 `flush()` 被调用),防止遗漏。

### 5. 位级优化
紧密打包位而非字节或字对齐,最小化缓存键大小:
- 布尔值: 1位
- 枚举值: 根据范围选择位数
- 小整数: 紧凑编码

### 6. 标签化接口
所有添加函数都接受 `std::string_view label` 参数,虽然在发布版本中未使用,但为调试提供了宝贵的元数据。

## 性能考量

### 1. 内存效率
- 紧密打包减少键大小,平均节省 30-50% 空间(相比字节对齐)
- 更小的键意味着更快的哈希计算和比较
- 更好的缓存局部性

### 2. 计算效率
- 位操作(移位、或运算)是 CPU 原生指令,极快
- 无分支的位打包逻辑
- 虚函数调用在发布版本中可能被内联(如果编译器能确定类型)

### 3. 缓存友好
- 连续的 `uint32_t` 数组布局
- 小数组优化(`TArray<T, true>`)避免堆分配
- 典型的键大小 4-16 个 uint32_t,适合单个缓存行

### 4. 哈希性能
对齐到32位边界的键可以高效哈希:
```cpp
size_t hash = 0;
for (uint32_t word : keyData) {
    hash = hash * 31 + word;
}
```

### 5. 比较性能
键比较可使用 `memcmp`,硬件优化的函数:
```cpp
bool operator==(const Key& other) const {
    return fData == other.fData;  // TArray 的 operator==
}
```

### 6. 调试开销
`StringKeyBuilder` 的额外开销仅在调试时产生:
- 生产版本使用基类 `KeyBuilder`,无字符串开销
- 虚函数在调试版本中也可接受(IO 和编译占主导)

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/KeyBuilder.h` | 定义 | 键构建器接口 |
| `src/gpu/ganesh/GrProgramDesc.h` | 使用者 | Ganesh 程序描述符 |
| `src/gpu/graphite/PipelineData.h` | 使用者 | Graphite 管线数据 |
| `src/gpu/graphite/UniformManager.cpp` | 使用者 | Uniform 数据键 |
| `tests/KeyTest.cpp` | 测试 | 键构建器单元测试 |
| `include/private/base/SkTArray.h` | 依赖 | 动态数组实现 |

**备注**: 该模块是 Skia GPU 缓存系统的基石,所有需要高效查找和去重的场景都依赖它提供的紧凑键表示。设计充分考虑了性能(位级打包)和可维护性(标签化接口),是系统编程中空间优化的典范。
