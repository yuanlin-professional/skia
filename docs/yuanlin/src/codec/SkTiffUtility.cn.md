# SkTiffUtility — TIFF IFD（图像文件目录）解析工具

> 源文件：[src/codec/SkTiffUtility.h](../../src/codec/SkTiffUtility.h)、[src/codec/SkTiffUtility.cpp](../../src/codec/SkTiffUtility.cpp)

## 概述

`SkTiff::ImageFileDirectory` 是一个 TIFF Image File Directory（IFD）解析工具类，位于 `SkTiff` 命名空间中。TIFF IFD 结构被广泛用于 EXIF 标签、多图片格式（MPF）和制造商说明（Maker Note）等元数据中。

该工具提供：
- TIFF 头部解析（字节序检测和 IFD 偏移量读取）
- IFD 条目遍历和数据提取
- 支持多种 TIFF 数据类型（无符号/有符号字节、短整型、长整型、有理数等共 12 种）
- 容错解析（允许截断数据）
- IFD 链式遍历（通过 `nextIfdOffset`）

## 架构位置

```
SkJpegCodec / SkJpegMetadataDecoderImpl
    │
    └── SkTiff::ImageFileDirectory (IFD 解析)
            │
            ├── EXIF 元数据解析
            ├── MPF（多图片格式）解析
            └── Maker Note 解析
```

## 主要类与结构体

### `SkTiff::ImageFileDirectory`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fData` | `sk_sp<SkData>` | IFD 索引的原始数据（共享所有权） |
| `fLittleEndian` | `bool` | 数据字节序是否为小端 |
| `fOffset` | `uint32_t` | IFD 在数据中的起始偏移 |
| `fNumEntries` | `uint16_t` | IFD 条目数 |
| `fNextIfdOffset` | `uint32_t` | 下一个 IFD 的偏移量（0 表示无） |

### 命名空间常量

**字节序签名**：
- `kEndianBig` = `{'M', 'M', 0, 42}` — 大端
- `kEndianLittle` = `{'I', 'I', 42, 0}` — 小端

**数据类型常量**（共 12 种）：
| 常量 | 值 | 类型 | 字节数 |
|------|----|------|--------|
| `kTypeUnsignedByte` | 1 | 无符号字节 | 1 |
| `kTypeAsciiString` | 2 | ASCII 字符串 | 1 |
| `kTypeUnsignedShort` | 3 | 无符号短整型 | 2 |
| `kTypeUnsignedLong` | 4 | 无符号长整型 | 4 |
| `kTypeUnsignedRational` | 5 | 无符号有理数 | 8 |
| `kTypeSignedByte` | 6 | 有符号字节 | 1 |
| `kTypeUndefined` | 7 | 未定义 | 1 |
| `kTypeSignedShort` | 8 | 有符号短整型 | 2 |
| `kTypeSignedLong` | 9 | 有符号长整型 | 4 |
| `kTypeSignedRational` | 10 | 有符号有理数 | 8 |
| `kTypeSingleFloat` | 11 | 单精度浮点 | 4 |
| `kTypeDoubleFloat` | 12 | 双精度浮点 | 8 |

**尺寸常量**：
- `kSizeEntry` = 12（每个 IFD 条目的字节数）
- `kSizeShort` = 2
- `kSizeLong` = 4

## 公共 API 函数

### `ParseHeader(const SkData*, bool* outLittleEndian, uint32_t* outIfdOffset) -> bool`

静态方法。解析 TIFF 头部（至少 8 字节）：前 4 字节为字节序标记，后 4 字节为第一个 IFD 的偏移量。

### `MakeFromOffset(sk_sp<SkData>, bool littleEndian, uint32_t ifdOffset, bool allowTruncated) -> unique_ptr<ImageFileDirectory>`

静态工厂方法。在给定数据和偏移量处构造 IFD 解析器。当 `allowTruncated` 为 `true` 时，数据不完整也会返回尽可能多的条目。

### `getNumEntries() -> uint16_t`

返回 IFD 条目数。

### `nextIfdOffset() -> uint32_t`

返回下一个 IFD 的偏移量（0 表示无后续 IFD）。

### `getEntryTag(uint16_t entryIndex) -> uint16_t`

返回指定条目的标签（Tag）值。

### `getEntryUnsignedShort(entryIndex, count, values) -> bool`

读取类型为无符号短整型（3）的条目数据，填充到 `values` 数组中。

### `getEntryUnsignedLong(entryIndex, count, values) -> bool`

读取类型为无符号长整型（4）的条目数据。

### `getEntrySignedRational(entryIndex, count, values) -> bool`

读取类型为有符号有理数（10）的条目数据，转换为 `float` 值。

### `getEntryUnsignedRational(entryIndex, count, values) -> bool`

读取类型为无符号有理数（5）的条目数据，转换为 `float` 值。

### `getEntryUndefinedData(uint16_t entryIndex) -> sk_sp<SkData>`

读取类型为 undefined（7）的条目，返回其字节数据的子集。

## 内部实现细节

### IFD 验证

`validate_ifd()` 函数执行完整的边界检查：
1. 验证 IFD 偏移量不超出数据范围
2. 读取条目数（2 字节）
3. 验证所有条目（每个 12 字节）不超出数据范围
4. 读取下一个 IFD 偏移量（4 字节）
5. 在 `allowTruncated` 模式下，截断条目数到可用空间，下一个 IFD 偏移设为 0

### 条目数据读取

每个 IFD 条目 12 字节布局：
- 字节 0-1：标签（Tag）
- 字节 2-3：类型（Type）
- 字节 4-7：计数（Count）
- 字节 8-11：值或偏移量

当数据大小 <= 4 字节时，值直接存储在字节 8-11 中。否则字节 8-11 为数据在文件中的偏移量。`getEntryRawData()` 透明处理这两种情况。

### 有理数转换

有理数（Rational）类型由分子和分母两个 32 位整数组成。转换为 float 时，当分母为 0 返回 0.0（遵循现有行为约定，TIFF 规范未定义此情况）。

### 字节序处理

所有多字节值读取都通过 `SkCodecPriv::GetEndianShort()` 和 `SkCodecPriv::GetEndianInt()` 函数，根据 `fLittleEndian` 标志进行适当的字节序转换。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkData` | 不可变数据块，持有 IFD 原始数据 |
| `SkCodecPriv` | 编解码私有工具（字节序读取、有效性检查） |

## 设计模式与设计决策

1. **不可变设计**：`ImageFileDirectory` 一旦构造，所有数据成员均为 `const`。解析在构造时完成，后续只读访问。

2. **共享数据所有权**：通过 `sk_sp<SkData>` 持有原始数据的共享引用，避免数据复制。`getEntryUndefinedData()` 返回数据子集也是通过 `SkData::MakeSubset` 实现零拷贝。

3. **容错解析**：`allowTruncated` 参数允许解析不完整的 IFD 数据，这在处理损坏或截断的 EXIF 数据时非常有用。

4. **类型安全的访问器**：提供独立的类型化访问方法（`getEntryUnsignedShort`、`getEntryUnsignedLong` 等），内部通过 `getEntryValuesGeneric` 统一实现，在访问时严格验证类型和计数匹配。

5. **私有构造函数**：只能通过 `MakeFromOffset` 工厂方法创建实例，确保构造前完成所有验证。

## 性能考量

- **零拷贝数据访问**：IFD 解析直接在原始数据上操作，不复制数据。通过 `sk_sp<SkData>` 共享所有权避免数据生命周期问题。
- **按需读取**：条目数据在调用 `getEntry*` 方法时才解析，而非在构造时解析所有条目。
- **O(1) 条目访问**：由于 IFD 条目大小固定（12 字节），通过索引直接计算偏移量实现常数时间访问。
- **简单的类型验证**：`IsValidType` 仅检查范围 1-12，`BytesForType` 通过 switch 语句实现 O(1) 查找。

## 相关文件

- `src/codec/SkCodecPriv.h` — 编解码器私有工具（字节序工具函数）
- `src/codec/SkJpegMetadataDecoderImpl.h` — 使用 IFD 解析 JPEG 元数据
- `include/core/SkData.h` — 不可变数据块
