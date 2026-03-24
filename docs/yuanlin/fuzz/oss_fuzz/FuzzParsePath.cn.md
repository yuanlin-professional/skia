# FuzzParsePath

> 源文件: fuzz/oss_fuzz/FuzzParsePath.cpp

## 概述

`FuzzParsePath.cpp` 是 Skia 中用于模糊测试 SVG 路径解析器的工具。该模块针对 `SkParsePath` 工具类进行安全性测试,验证从 SVG 路径字符串到 `SkPath` 对象的解析过程,以及反向序列化的正确性。模糊测试器将任意字节流作为 SVG 路径字符串输入,测试解析器在处理畸形、边界条件和恶意构造的输入时的鲁棒性,确保不会发生崩溃、内存越界或其他安全问题。

该测试工具是 Skia SVG 渲染管线质量保证的重要组成部分,对路径数据的安全处理至关重要。

## 架构位置

该文件位于 Skia 项目的模糊测试基础设施中:

- **路径**: `fuzz/oss_fuzz/FuzzParsePath.cpp`
- **模块层次**: 测试工具层 > 模糊测试子系统 > OSS-Fuzz 集成
- **测试目标**: `SkParsePath` 工具类(SVG 路径解析和序列化)
- **依赖关系**: 依赖核心路径类 (`SkPath`) 和工具模块 (`SkParsePath`)

在 Skia 架构中的位置:
```
fuzz/
├── oss_fuzz/
│   ├── FuzzParsePath.cpp           ← 当前文件
│   ├── FuzzPathop.cpp              (路径操作测试)
│   └── ... (其他模糊测试器)
include/
├── core/SkPath.h                    (路径数据结构)
└── utils/SkParsePath.h              (SVG 路径解析工具)
```

## 主要类与结构体

### 核心函数

#### `FuzzParsePath`
```cpp
void FuzzParsePath(const uint8_t* data, size_t size)
```

**功能**: 执行 SVG 路径解析的模糊测试
- **参数**:
  - `data`: 输入的字节流(作为 SVG 路径字符串)
  - `size`: 输入数据的长度
- **返回值**: 无返回值(void),通过断言检测错误
- **核心逻辑**:
  1. 将字节流转换为空终止的 `SkString`(确保安全处理)
  2. 调用 `SkParsePath::FromSVGString()` 解析为 `SkPath` 对象
  3. 如果解析成功,将路径序列化回 SVG 字符串(绝对和相对两种格式)
  4. 验证序列化结果的有效性(不应包含"Impossible"前缀)

#### `LLVMFuzzerTestOneInput`
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size)
```

**功能**: LibFuzzer 标准入口点
- **输入限制**: 最大 1000 字节(防止超时)
- **返回值**: 始终返回 0(符合 LibFuzzer 规范)
- **集成**: 与 OSS-Fuzz 基础设施的标准接口

## 公共 API 函数

### 对外接口

虽然该文件是测试工具,但其导出的 fuzzing 函数可供其他测试框架调用:

1. **`FuzzParsePath(const uint8_t*, size_t)`**
   - 可被独立测试框架调用
   - 接受任意字节流作为 SVG 路径字符串输入
   - 通过断言验证解析和序列化的正确性

2. **`LLVMFuzzerTestOneInput(const uint8_t*, size_t)`**
   - LibFuzzer 生态系统的标准接口
   - 自动被 OSS-Fuzz 框架调用
   - 包含输入大小限制(1KB)以控制测试时间

### 使用的 Skia API

**路径解析 API**:
- `SkParsePath::FromSVGString(const char*)`: 从 SVG 路径字符串解析为 `SkPath`
- `SkParsePath::ToSVGString(const SkPath&, PathEncoding)`: 将 `SkPath` 序列化为 SVG 字符串
  - `PathEncoding::Absolute`: 使用绝对坐标(如 M, L, C)
  - `PathEncoding::Relative`: 使用相对坐标(如 m, l, c)

**核心数据结构**:
- `SkPath`: Skia 路径对象,存储几何路径数据
- `SkString`: Skia 字符串类,提供安全的字符串操作

## 内部实现细节

### 测试流程

```
输入字节流
    ↓
转换为 SkString (空终止保护)
    ↓
FromSVGString() 解析为 SkPath
    ↓ (如果成功)
序列化为绝对坐标 SVG 字符串
    ↓
序列化为相对坐标 SVG 字符串
    ↓
验证输出有效性(不包含"Impossible")
```

### 空终止符处理

```cpp
SkString input((const char*) data, size);
```

**设计理念**:
- 输入的字节流可能不包含空终止符
- `SkString` 构造函数确保创建有效的 C 风格字符串
- 避免 `FromSVGString` 读取越界内存

### 双向验证机制

**正向解析**: `SVG 字符串 → SkPath`
```cpp
if (auto path = SkParsePath::FromSVGString(input.c_str()))
```

**反向序列化**: `SkPath → SVG 字符串`
```cpp
SkString output1 = SkParsePath::ToSVGString(*path, SkParsePath::PathEncoding::Absolute);
SkString output2 = SkParsePath::ToSVGString(*path, SkParsePath::PathEncoding::Relative);
```

这种双向测试策略验证了:
1. 解析器正确处理输入
2. 序列化器能重新生成有效的 SVG 路径
3. 绝对和相对坐标编码的正确性

### 有效性检查

```cpp
if (output1.startsWith("Impossible") || output2.startsWith("Impossible")) {
    SK_ABORT("invalid SVG created");
}
```

**目的**: 捕获序列化器生成无效输出的情况
- "Impossible" 是错误标记的约定
- 使用 `SK_ABORT` 触发可检测的失败(在调试模式下)
- 确保输出始终是有效的 SVG 路径字符串

### 输入大小限制

```cpp
if (size > 1000) {
    return 0;
}
```

- **原因**: 防止过长的路径字符串导致解析超时
- **平衡**: 在覆盖率和执行效率之间取得平衡
- **经验值**: 1KB 足以表达复杂的 SVG 路径

## 依赖关系

### 直接依赖

**核心模块**:
- `include/core/SkPath.h`: 路径数据结构定义
- `include/core/SkString.h`: 字符串工具类
- `include/utils/SkParsePath.h`: SVG 路径解析和序列化工具

**基础设施**:
- `include/private/base/SkAssert.h`: 断言宏(`SK_ABORT`)

### 数据流依赖

```
原始字节流 → SkString
    ↓
SkParsePath::FromSVGString → std::optional<SkPath>
    ↓
SkParsePath::ToSVGString → SkString (绝对)
    ↓
SkParsePath::ToSVGString → SkString (相对)
```

### 编译依赖

- **必需宏**: `SK_BUILD_FOR_LIBFUZZER` (启用 LibFuzzer 集成)
- **可选宏**: `SK_DEBUG` (启用 `SK_ABORT` 断言)

## 设计模式与设计决策

### 1. 往返测试模式(Round-Trip Testing)

**设计决策**: 测试解析和序列化的完整循环
**理由**:
- 验证数据转换的可逆性
- 确保解析器和序列化器的一致性
- 发现格式转换中的信息丢失或损坏

### 2. 双编码验证

**设计决策**: 同时测试绝对和相对坐标编码
**优点**:
- 覆盖两种主要的 SVG 路径表示法
- 发现特定编码格式的缺陷
- 提高测试覆盖率

### 3. 安全优先的字符串处理

**设计决策**: 强制使用 `SkString` 包装原始字节流
**理由**:
- 防止空终止符缺失导致的缓冲区溢出
- 提供一致的字符串语义
- 避免未定义行为

### 4. 早期退出策略

**设计决策**: 解析失败时立即返回,不执行后续测试
```cpp
if (auto path = SkParsePath::FromSVGString(input.c_str())) {
    // 仅在成功时执行序列化测试
}
```
**优点**:
- 避免在无效状态下继续执行
- 减少无意义的测试操作
- 提高测试效率

### 5. 无返回值设计

**设计决策**: `FuzzParsePath` 不返回布尔值或状态码
**理由**:
- 模糊测试的目标是检测崩溃和断言失败
- 正常执行完成即视为成功
- 简化测试逻辑

## 性能考量

### 1. 输入大小限制

**实现**: 限制输入最大 1000 字节
**影响**:
- 控制 SVG 路径解析时间
- 防止模糊测试超时
- 平衡测试覆盖率和执行速度

### 2. 最小化内存分配

**策略**:
- 使用栈分配的 `SkString` 对象
- `SkPath` 通过智能指针管理(自动释放)
- 避免不必要的深拷贝

**效果**: 减少内存分配开销,提高测试吞吐量

### 3. 避免冗余验证

该测试器专注于解析和序列化的正确性,不验证:
- 路径的几何有效性
- 渲染输出的正确性
- 复杂的数学计算

这种聚焦策略提高了测试效率。

### 4. 条件性序列化测试

```cpp
if (auto path = SkParsePath::FromSVGString(...)) {
    // 仅在解析成功时执行序列化
}
```

避免对无效输入进行无意义的序列化测试,节省计算资源。

## 相关文件

### 同类型的模糊测试器

1. **`fuzz/oss_fuzz/FuzzPathop.cpp`**
   - 测试路径操作(布尔运算、路径合并等)
   - 互补的路径功能测试

2. **`fuzz/oss_fuzz/FuzzCanvas.cpp`** (如果存在)
   - 测试画布绘制路径的功能
   - 验证路径的渲染管线

### 核心依赖文件

3. **`include/utils/SkParsePath.h`**
   - SVG 路径解析器的接口定义
   - 提供 `FromSVGString` 和 `ToSVGString` 函数

4. **`src/utils/SkParsePath.cpp`**
   - SVG 路径解析器的实现
   - 包含路径命令解析逻辑(M, L, C, Q, A 等)

5. **`include/core/SkPath.h`**
   - 路径数据结构定义
   - 提供路径操作和查询接口

### 测试基础设施

6. **`fuzz/Fuzz.h` / `fuzz/Fuzz.cpp`**
   - Skia 模糊测试框架核心(虽然本文件未直接使用)
   - 提供通用的模糊测试工具

7. **`tools/oss_fuzz/fuzz.json`** (如果存在)
   - OSS-Fuzz 配置文件
   - 定义模糊测试目标和选项

### 相关测试文件

8. **`tests/ParsePathTest.cpp`** (如果存在)
   - `SkParsePath` 的单元测试
   - 提供正确性验证的补充

9. **`gm/pathfuzz.cpp`** (如果存在)
   - 路径的视觉测试(Golden Master)
   - 验证路径渲染的正确性

### SVG 相关模块

10. **`modules/svg/include/SkSVGPath.h`**
    - SVG 路径元素的封装
    - 使用 `SkParsePath` 解析 `d` 属性

11. **`modules/svg/src/SkSVGPath.cpp`**
    - SVG 路径元素的实现
    - 集成路径解析到 SVG 渲染管线

### 构建配置

12. **`BUILD.gn`** (相关部分)
    - 定义模糊测试目标的编译规则
    - 配置 LibFuzzer 链接选项

该模糊测试器通过简洁而全面的测试策略,为 Skia 的 SVG 路径解析功能提供了强有力的安全性保障,确保在处理任意输入时的稳定性和正确性。
