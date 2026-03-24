# SkBmpBaseCodec

> 源文件: src/codec/SkBmpBaseCodec.h, src/codec/SkBmpBaseCodec.cpp

## 概述

`SkBmpBaseCodec` 是 Skia BMP 图片解码器的抽象基类，为 `SkBmpStandardCodec` 和 `SkBmpMaskCodec` 提供共同的基础设施。该类主要负责管理源数据缓冲区的分配和访问，简化了子类的实现。

作为中间层抽象，`SkBmpBaseCodec` 封装了源行缓冲区的生命周期管理，使得具体的解码器子类可以专注于解码算法本身，而无需处理缓冲区的内存管理细节。

## 架构位置

在 Skia BMP 解码器的继承层次中：

```
SkCodec (基类)
    ↓
SkBmpCodec (BMP 通用基类)
    ↓
SkBmpBaseCodec (缓冲区管理层)
    ↓        ↓
SkBmpStandardCodec  SkBmpMaskCodec
```

- **父类**: `SkBmpCodec` - 提供 BMP 格式的通用功能
- **子类**: `SkBmpStandardCodec` (标准 BMP)、`SkBmpMaskCodec` (位掩码 BMP)
- **职责**: 源数据缓冲区的分配和访问管理
- **排除**: `SkBmpRLECodec` 不继承此类（RLE 压缩需要不同的缓冲策略）

## 主要类与结构体

### SkBmpBaseCodec 类

**继承关系**:
```
SkBmpBaseCodec → SkBmpCodec → SkCodec → SkRefCnt
```

**主要成员变量**:
- `skia_private::UniqueVoidPtr fSrcBuffer`: 源行缓冲区的智能指针

**设计特点**:
- 使用 `UniqueVoidPtr` 管理非类型化内存
- 缓冲区大小由父类 `SkBmpCodec::srcRowBytes()` 确定
- 失败时缓冲区可能为 `nullptr`（需要检查）

## 公共 API 函数

### 生命周期管理

**析构函数**
```cpp
~SkBmpBaseCodec() override
```
虚析构函数，使用默认实现。智能指针 `fSrcBuffer` 会自动释放内存。

**构造函数** (protected)
```cpp
SkBmpBaseCodec(SkEncodedInfo&& info, std::unique_ptr<SkStream>,
               uint16_t bitsPerPixel, SkCodec::SkScanlineOrder rowOrder)
```
初始化基类并分配源缓冲区：
1. 调用父类 `SkBmpCodec` 构造函数传递参数
2. 使用 `sk_malloc_canfail` 分配 `srcRowBytes()` 字节的缓冲区
3. 分配失败时 `fSrcBuffer` 为 `nullptr`

**参数说明**:
- `info`: 编码信息（尺寸、颜色类型等）
- `stream`: 图片数据流
- `bitsPerPixel`: 每像素位数
- `rowOrder`: 行扫描顺序（自顶向下或自底向上）

### 缓冲区访问

**didCreateSrcBuffer**
```cpp
bool didCreateSrcBuffer() const
```
检查源缓冲区是否成功分配。返回 `false` 表示内存分配失败，解码器不可用。

**用途**: 在创建解码器后验证其有效性。

**srcBuffer** (protected)
```cpp
uint8_t* srcBuffer()
```
返回源缓冲区的指针，转换为 `uint8_t*` 类型。子类使用此方法访问缓冲区进行解码操作。

## 内部实现细节

### 缓冲区分配策略

使用 `sk_malloc_canfail` 而非 `sk_malloc`：
- **失败安全**: 分配失败返回 `nullptr`，不会终止程序
- **大图片处理**: BMP 文件可能很大，允许优雅地处理内存不足
- **验证机制**: 通过 `didCreateSrcBuffer()` 让调用者检查分配结果

### 缓冲区大小计算

缓冲区大小由父类 `SkBmpCodec::srcRowBytes()` 计算：
```cpp
fSrcRowBytes = SkAlign4(SkCodecPriv::ComputeRowBytes(width, bitsPerPixel))
```

关键点：
- **4 字节对齐**: BMP 格式要求行边界对齐到 4 字节
- **位深度处理**: 根据 `bitsPerPixel` 计算原始字节数
- **填充字节**: 对齐可能引入额外的填充字节

### 智能指针的使用

`UniqueVoidPtr` 的特性：
- 自动管理 `void*` 类型内存
- 析构时自动调用 `sk_free`
- 移动语义支持（可转移所有权）
- 避免类型安全问题（需要手动转换）

## 依赖关系

### 直接依赖
- **SkBmpCodec**: 父类，提供 BMP 解码的通用功能
- **SkEncodedInfo**: 描述编码图片的元信息
- **SkStream**: 图片数据流接口
- **SkTemplates (UniqueVoidPtr)**: 智能指针模板
- **SkMalloc**: 内存分配工具

### 被依赖
- **SkBmpStandardCodec**: 标准 BMP 格式解码器
- **SkBmpMaskCodec**: 位掩码 BMP 格式解码器

## 设计模式与设计决策

### 模板方法模式（Template Method Pattern）

`SkBmpBaseCodec` 提供缓冲区基础设施，子类实现具体的解码逻辑：
- **基类**: 分配和管理缓冲区
- **子类**: 使用 `srcBuffer()` 进行解码操作
- **好处**: 避免重复的缓冲区管理代码

### 资源获取即初始化（RAII）

缓冲区在构造函数中分配，在析构函数中释放：
- **自动化**: 无需显式释放内存
- **异常安全**: 即使发生异常也能正确清理
- **智能指针**: `UniqueVoidPtr` 封装了 RAII 语义

### 失败安全设计

使用 `sk_malloc_canfail` + 验证方法：
```cpp
auto codec = std::make_unique<SkBmpStandardCodec>(...);
if (!codec->didCreateSrcBuffer()) {
    return kInvalidInput;  // 失败处理
}
```

**优势**:
- 不抛出异常（符合 Skia 的无异常策略）
- 显式检查（强制调用者处理失败）
- 可区分的错误（内存不足 vs 格式错误）

### 为何不继承到 RLE 解码器

`SkBmpRLECodec` 不继承 `SkBmpBaseCodec` 的原因：
- **缓冲需求不同**: RLE 压缩数据是变长的，不需要固定大小的行缓冲
- **解码方式不同**: RLE 解码器直接从流中读取并解压，而标准解码器先读取完整行
- **内存优化**: RLE 避免分配未使用的缓冲区

## 性能考量

### 内存分配

**一次性分配**:
- 在构造时分配，整个解码过程重用
- 避免每行解码时重复分配
- 减少内存分配器的开销

**缓冲区大小**:
- 仅分配一行的数据（而非整个图片）
- 对于大图片，显著减少内存占用
- 支持逐行解码（扫描线模式）

### 对齐优化

4 字节对齐的好处：
- **CPU 访问效率**: 现代 CPU 偏好对齐的内存访问
- **SIMD 优化**: 向量化指令通常要求对齐
- **BMP 格式要求**: 符合格式规范，避免额外的数据移动

### 类型转换开销

`srcBuffer()` 返回 `uint8_t*`：
- **零开销**: 转换是编译时的类型重解释
- **灵活性**: 子类可根据需要解释缓冲区内容
- **风险**: 缺少类型安全检查，依赖子类正确使用

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/codec/SkBmpCodec.h` | 父类 | BMP 解码器的通用基类 |
| `src/codec/SkBmpStandardCodec.h` | 子类 | 标准 BMP 格式解码器 |
| `src/codec/SkBmpMaskCodec.h` | 子类 | 位掩码 BMP 格式解码器 |
| `include/codec/SkCodec.h` | 基类 | 所有解码器的基类 |
| `include/private/SkEncodedInfo.h` | 依赖 | 编码信息结构 |
| `include/core/SkStream.h` | 依赖 | 数据流接口 |
| `include/private/base/SkTemplates.h` | 依赖 | 智能指针模板 |
| `include/private/base/SkMalloc.h` | 依赖 | 内存分配工具 |
