# SkJpegXmp

> 源文件: src/codec/SkJpegXmp.h, src/codec/SkJpegXmp.cpp

## 概述

`SkJpegXmp` 是 Skia 图像解码库中专门用于从 JPEG 文件中提取和解析 XMP（Extensible Metadata Platform）元数据的模块。XMP 是 Adobe 开发的一种标准化元数据格式，广泛用于存储图像的创作信息、版权、相机参数、增益映射（HDR）等高级元数据。该模块完整实现了 XMP 规范中关于 JPEG 存储的要求，支持标准 XMP 和扩展 XMP 的提取、拼接和验证。

## 架构位置

该模块位于 Skia 编解码器子系统的元数据处理层：

```
src/codec/
  ├── SkJpegXmp.h               # XMP 提取函数声明
  ├── SkJpegXmp.cpp             # XMP 提取实现
  ├── SkJpegCodec.cpp           # JPEG 解码器（使用本模块）
  ├── SkJpegSegmentScan.cpp     # JPEG 段扫描器
  └── SkJpegConstants.h         # JPEG 常量定义
include/private/
  └── SkXmp.h                   # XMP 解析器接口
```

作为专用工具模块，它为 JPEG 解码器提供元数据提取能力，是 JPEG 元数据管线的关键组成部分。

## 主要类与结构体

本模块采用函数式设计，没有定义类，仅提供工具函数。主要使用以下外部类型：

### SkXmp (外部类)

XMP 元数据解析器，定义在 `include/private/SkXmp.h`。

**工厂方法：**

```cpp
static std::unique_ptr<SkXmp> Make(sk_sp<const SkData> xmpStandard);
static std::unique_ptr<SkXmp> Make(sk_sp<const SkData> xmpStandard,
                                   sk_sp<const SkData> xmpExtended);
```

**关键方法：**

```cpp
const char* getExtendedXmpGuid() const;  // 获取扩展 XMP 的 GUID
```

### Part (内部类型)

用于扩展 XMP 片段管理的类型别名：

```cpp
using Part = std::pair<uint32_t, sk_sp<const SkData>>;
```

- `first`：片段在完整数据中的偏移量
- `second`：片段数据的智能指针

## 公共 API 函数

### SkJpegMakeXmp

```cpp
std::unique_ptr<SkXmp> SkJpegMakeXmp(
    const std::vector<sk_sp<const SkData>>& decoderApp1Params);
```

从 JPEG 的 APP1 段列表中提取并构造完整的 XMP 元数据对象。

**参数：**
- `decoderApp1Params`：JPEG 文件中所有 APP1 段的参数数据列表

**返回值：**
- 成功：包含完整 XMP 元数据的 `SkXmp` 对象
- 失败：`nullptr`（未找到标准 XMP 或解析失败）

**处理流程：**

1. 调用 `read_xmp_standard()` 提取标准 XMP 数据
2. 使用标准 XMP 创建初始 `SkXmp` 对象
3. 检查是否存在扩展 XMP 的 GUID
4. 如果存在，调用 `read_xmp_extended()` 提取扩展数据
5. 使用标准和扩展数据重新创建 `SkXmp` 对象

## 内部实现细节

### read_xmp_standard

```cpp
static sk_sp<SkData> read_xmp_standard(
    const std::vector<sk_sp<const SkData>>& decoderApp1Params);
```

提取标准 XMP 元数据，遵循 **XMP Specification Part 3: Storage in files, Section 1.1.3: JPEG**。

**实现逻辑：**

1. 定义签名大小：`kSigSize = sizeof(kXMPStandardSig)`
2. 遍历所有 APP1 段：
   - 跳过小于签名大小的段
   - 跳过签名不匹配的段（`memcmp` 检查）
3. 找到匹配段后，使用 `SkData::MakeWithoutCopy` 零拷贝包装数据
   - 跳过签名部分，仅包装实际 XMP 内容
   - 数据生命周期由原始 `decoderApp1Params` 管理

**返回值：**
- 成功：指向 XMP 数据的 `SkData`（零拷贝）
- 失败：`nullptr`

### read_xmp_extended

```cpp
static sk_sp<SkData> read_xmp_extended(
    const std::vector<sk_sp<const SkData>>& decoderApp1Params,
    const char* guidAscii);
```

提取并验证扩展 XMP 元数据，遵循 **XMP Specification Part 3, Section 1.1.3.1: Extended XMP in JPEG**。

**扩展 XMP 结构：**

每个扩展 XMP 段包含：
1. **签名**（空字符结尾字符串）：`"http://ns.adobe.com/xmp/extension/\0"`
2. **GUID**（32 字节 ASCII 十六进制）：完整扩展 XMP 的 MD5 哈希值
3. **完整长度**（4 字节大端序无符号整数）：拼接后的总长度
4. **偏移量**（4 字节大端序无符号整数）：当前片段在总数据中的位置
5. **数据片段**：实际的 XMP 内容

**实现流程：**

#### 1. GUID 验证

```cpp
SkMD5::Digest guidAsDigest;
for (size_t i = 0; i < kGuidAsciiSize; ++i) {
    uint8_t digit = 0;
    if (guidAscii[i] >= '0' && guidAscii[i] <= '9') {
        digit = guidAscii[i] - '0';
    } else if (guidAscii[i] >= 'A' && guidAscii[i] <= 'F') {
        digit = guidAscii[i] - 'A' + 10;
    } else {
        SkCodecPrintf("GUID is not upper-case hex.\n");
        return nullptr;
    }
    // 每两个字符组成一个字节
    if (i % 2 == 0) {
        guidAsDigest.data[i / 2] = 16 * digit;
    } else {
        guidAsDigest.data[i / 2] += digit;
    }
}
```

将 32 字节 ASCII 十六进制 GUID 转换为 16 字节 `SkMD5::Digest`。要求：
- 长度必须为 32 字节
- 仅包含 '0'-'9' 和 'A'-'F'（大写）

#### 2. 片段收集

遍历 APP1 段，收集所有匹配的扩展 XMP 片段：

```cpp
for (const auto& params : decoderApp1Params) {
    // 检查头部大小
    if (params->size() <= kHeaderSize) continue;

    // 检查签名
    if (memcmp(params->bytes(), kXMPExtendedSig, kSigSize) != 0) continue;

    // 检查 GUID 匹配
    if (memcmp(guidAscii, partGuidAscii, kGuidAsciiSize) != 0) continue;

    // 解析完整长度和偏移量（大端序）
    uint32_t partFullLength = 0;
    uint32_t partOffset = 0;
    for (size_t i = 0; i < 4; ++i) {
        partFullLength = (partFullLength * 256) + partFullLengthBytes[i];
        partOffset = (partOffset * 256) + partOffsetBytes[i];
    }

    // 验证一致性
    if (!parts.empty() && partFullLength != fullLength) {
        SkCodecPrintf("Multiple parts had different total lengths.\n");
        return nullptr;
    }

    // 添加到片段列表
    parts.push_back({partOffset, partData});
}
```

#### 3. 片段排序与拼接

```cpp
// 按偏移量排序
std::sort(parts.begin(), parts.end(), [](const Part& a, const Part& b) {
    return std::get<0>(a) < std::get<0>(b);
});

// 拼接数据
auto xmpExtendedData = SkData::MakeUninitialized(fullLength);
uint8_t* xmpExtendedCurrent = xmpExtendedBase;
for (const auto& part : parts) {
    uint32_t currentOffset = xmpExtendedCurrent - xmpExtendedBase;
    uint32_t partOffset = std::get<0>(part);

    // 验证连续性
    if (partOffset != currentOffset) {
        SkCodecPrintf("XMP extension parts not contiguous\n");
        return nullptr;
    }

    // 验证不溢出
    if (partData->size() > fullLength - currentOffset) {
        SkCodecPrintf("XMP extension parts overflow\n");
        return nullptr;
    }

    memcpy(xmpExtendedCurrent, partData->data(), partData->size());
    xmpExtendedCurrent += partData->size();
}
```

#### 4. MD5 验证

```cpp
SkMD5 md5;
md5.write(xmpExtendedData->data(), xmpExtendedData->size());
if (md5.finish() != guidAsDigest) {
    SkCodecPrintf("XMP extension did not hash to GUID.\n");
    return nullptr;
}
```

计算拼接后数据的 MD5 哈希，必须与 GUID 匹配，确保数据完整性。

## 依赖关系

**外部依赖：**
- `SkXmp`：XMP 解析器（`include/private/SkXmp.h`）
- `SkMD5`：MD5 哈希计算（`src/core/SkMD5.h`）
- `SkData`：不可变数据容器（`include/core/SkData.h`）

**内部依赖：**
- `SkCodecPriv.h`：编解码器私有工具（`SkCodecPrintf`）
- `SkJpegConstants.h`：JPEG 常量定义（`kXMPStandardSig`、`kXMPExtendedSig`）

**依赖方：**
- `SkJpegCodec`：JPEG 解码器主类
- `SkJpegSourceMgr`：JPEG 源管理器

## 设计模式与设计决策

### 1. 函数式设计

采用纯函数而非类封装：
- **简单性**：XMP 提取是一次性操作，无需维护状态
- **复用性**：函数可以独立测试和复用
- **零开销**：避免对象构造/析构开销

### 2. 零拷贝优化

标准 XMP 使用 `SkData::MakeWithoutCopy`：
- 避免内存分配和拷贝
- 数据生命周期由外部管理（`decoderApp1Params`）
- 仅在扩展 XMP 需要拼接时才分配新内存

### 3. 防御性编程

严格的验证机制：
- **GUID 格式验证**：仅接受大写十六进制
- **片段连续性检查**：确保无重叠、无间隙
- **长度一致性验证**：所有片段声明的总长度必须一致
- **MD5 完整性验证**：防止数据损坏或篡改

### 4. 早期失败策略

遇到任何不一致立即返回 `nullptr`：
- 避免部分损坏的元数据污染结果
- 简化错误处理逻辑
- 为调试提供清晰的失败点

### 5. 大端序解析

手动解析 4 字节大端序整数：
```cpp
for (size_t i = 0; i < 4; ++i) {
    value = (value * 256) + bytes[i];
}
```
这比位移操作更清晰，且跨平台兼容。

## 性能考量

### 1. 内存效率

**标准 XMP**：
- 零拷贝包装，仅 16 字节开销（`SkData` 对象）
- 无额外内存分配

**扩展 XMP**：
- 仅在确认存在时才分配内存
- 使用 `SkData::MakeUninitialized` 避免零初始化

### 2. 扫描优化

单遍扫描所有 APP1 段：
- 同时收集标准和扩展 XMP
- 避免多次遍历段列表

### 3. 排序开销

使用 `std::sort` 对片段排序：
- 时间复杂度：O(n log n)
- 实际中片段数量很少（通常 < 10）
- 排序后可以在 O(n) 时间内验证连续性

### 4. MD5 验证开销

仅对扩展 XMP 计算 MD5：
- 标准 XMP 不需要哈希验证
- MD5 计算是流式的，内存友好
- 开销远小于 JPEG 解码本身

### 5. 字符串比较

使用 `memcmp` 而非字符串函数：
- 固定长度比较，避免 `strlen` 调用
- 编译器可以内联并优化为 SIMD 指令

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `include/private/SkXmp.h` | XMP 解析器接口 | 本模块创建 SkXmp 对象 |
| `src/codec/SkXmp.cpp` | XMP 解析器实现 | 处理 XML 解析和元数据提取 |
| `src/codec/SkJpegCodec.cpp` | JPEG 解码器 | 调用本模块提取元数据 |
| `src/codec/SkJpegSegmentScan.cpp` | JPEG 段扫描器 | 提供 APP1 段数据 |
| `src/codec/SkJpegConstants.h` | JPEG 常量定义 | 提供 XMP 签名常量 |
| `src/core/SkMD5.h` | MD5 哈希工具 | 用于扩展 XMP 验证 |
| `src/codec/SkCodecPriv.h` | 编解码器私有工具 | 提供调试打印功能 |
| `include/private/SkGainmapInfo.h` | 增益映射信息 | XMP 中可能包含的 HDR 元数据 |

---

*本文档由 Claude Code 自动生成*
