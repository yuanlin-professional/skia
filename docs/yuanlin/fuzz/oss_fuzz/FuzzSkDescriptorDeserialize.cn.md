# FuzzSkDescriptorDeserialize.cpp - SkDescriptor 反序列化模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzSkDescriptorDeserialize.cpp`

## 概述

本文件实现了针对 `SkDescriptor` 反序列化的模糊测试。`SkDescriptor` 是 Skia 字体子系统中的核心数据结构，用于紧凑地描述字形（glyph）的渲染参数和查找键。该测试将随机字节数据尝试反序列化为 `SkAutoDescriptor`，然后执行校验和计算、有效性验证和条目查找等操作，用于发现字体描述符序列化/反序列化中的安全问题。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，覆盖了 Skia 字体渲染管线中的描述符子系统。`SkDescriptor` 在字体缓存和字形光栅化过程中被频繁使用，其反序列化安全性对于防止通过恶意字体触发漏洞至关重要。

## 主要类与结构体

- **`SkAutoDescriptor`**: 自动管理内存的 `SkDescriptor` 封装
- **`SkDescriptor`**: 字形描述符，包含标签化的条目集合
- **`SkReadBuffer`**: Skia 的安全反序列化缓冲区

## 公共 API 函数

- **`FuzzSkDescriptorDeserialize(const uint8_t *data, size_t size)`**: 核心模糊测试函数
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 入口点，输入限制 1024 字节

## 内部实现细节

### 测试流程

1. 创建 `SkReadBuffer` 包装输入数据
2. 调用 `SkAutoDescriptor::MakeFromBuffer()` 尝试反序列化
3. 如果成功，执行以下操作：
   - `computeChecksum()`: 重新计算校验和
   - `isValid()`: 验证描述符的结构完整性
   - `findEntry(117, &ignore)`: 使用任意标签值（117）查找条目

### 输入限制

1024 字节的限制比其他模糊测试更小，因为 `SkDescriptor` 是一个紧凑的数据结构，不需要大量数据。

## 依赖关系

- **`src/core/SkDescriptor.h`**: 描述符核心定义
- **`src/core/SkReadBuffer.h`**: 安全反序列化缓冲区

## 设计模式与设计决策

- **多层验证**: 同时测试反序列化、校验和计算和条目查找，覆盖多个代码路径
- **任意标签查找**: 使用常量 117 作为查找标签，触发条目遍历逻辑而不依赖特定标签值
- **小输入限制**: 1024 字节足以覆盖 `SkDescriptor` 的典型大小
- **安全缓冲区**: 使用 `SkReadBuffer` 而非直接内存操作，提供额外的边界检查

## 性能考量

- `SkDescriptor` 操作为纯内存计算，延迟极低
- 1024 字节的输入限制确保极快的测试迭代速度
- 校验和计算是 O(n) 操作，对小描述符几乎无开销
- `SkReadBuffer` 提供的边界检查在调试模式下会进行额外验证

### SkDescriptor 数据格式

`SkDescriptor` 内部使用标签-长度-值（TLV）格式存储条目：
- 每个条目包含一个 32 位标签 ID、一个 32 位长度字段和可变长度的数据
- 描述符头部包含总长度和校验和
- `MakeFromBuffer` 在反序列化时验证头部信息和条目边界

### 在字体缓存中的角色

`SkDescriptor` 在 Skia 的字体缓存系统（SkStrike）中作为查找键使用。每个不同的字体 + 大小 + 变换 + 渲染设置组合对应一个唯一的描述符。描述符的校验和用于快速比较和哈希表查找。

## 相关文件

- `src/core/SkDescriptor.h` / `src/core/SkDescriptor.cpp` - SkDescriptor 实现
- `src/core/SkReadBuffer.h` - 反序列化缓冲区
- `src/core/SkGlyph.h` - 字形数据结构（使用 SkDescriptor 作为键）
- `src/core/SkStrike.h` - 字形缓存（使用 SkDescriptor 查找）
- `src/core/SkScalerContext.cpp` - 字形缩放上下文（创建 SkDescriptor）
- `tests/DescriptorTest.cpp` - SkDescriptor 单元测试
- `src/core/SkFont.cpp` - 字体类（使用 SkDescriptor 构建缓存键）
- `src/core/SkStrikeCache.cpp` - 全局字形缓存（依赖 SkDescriptor 索引）
- `fuzz/oss_fuzz/FuzzTextBlobDeserialize.cpp` - TextBlob 反序列化模糊测试（类似的序列化测试）
- `src/core/SkWriteBuffer.h` - 序列化缓冲区（SkDescriptor 的序列化对应工具）
