# SkShaper_skunicode 实现 - Unicode BiDi 运行迭代器

> 源文件: `modules/skshaper/src/SkShaper_skunicode.cpp`

## 概述

SkShaper_skunicode.cpp 实现了基于 SkUnicode 接口的双向文本（BiDi）运行迭代器。它将 UTF-8 文本转换为 UTF-16 后交给 SkUnicode 的 BiDi 分析器处理，然后提供一个逐运行推进的迭代器，每个运行内的所有字符具有相同的 BiDi 嵌入级别。该迭代器是 HarfBuzz 塑形器处理混合方向文本时的关键组件。

## 架构位置

位于 skshaper 模块的 Unicode 处理层，实现了 SkShaper_skunicode.h 声明的接口。通过 SkUnicode 抽象层间接使用 ICU、ICU4X 或 libgrapheme 等 Unicode 后端。

## 主要类与结构体

### `SkUnicodeBidiRunIterator`
继承自 `SkShaper::BiDiRunIterator`，实现 BiDi 运行迭代：
- `fBidi`: SkBidiIterator 实例，提供按位置查询 BiDi 级别的能力
- `fEndOfCurrentRun`: 当前运行在 UTF-8 中的结束位置
- `fBegin` / `fEnd`: 文本的 UTF-8 起止指针
- `fUTF16LogicalPosition`: 当前逻辑位置（UTF-16 偏移）
- `fLevel`: 当前运行的 BiDi 嵌入级别

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SkShapers::unicode::BidiRunIterator(unicode, utf8, bytes, level)` | 创建 BiDi 运行迭代器 |
| `SkShaper::MakeIcuBiDiRunIterator(utf8, bytes, level)` | 旧版创建接口（使用全局 Unicode 实例） |

## 内部实现细节

### BiDi 迭代器工作流程

#### `consume()` 方法
1. 从 `fBidi->getLevelAt()` 获取当前位置的 BiDi 级别
2. 读取一个 UTF-8 字符，计算其 UTF-16 编码长度
3. 推进 `fUTF16LogicalPosition`
4. 持续扫描后续字符，直到 BiDi 级别发生变化
5. 更新 `fEndOfCurrentRun` 到分界位置

#### UTF-8 / UTF-16 坐标同步
由于 SkBidiIterator（基于 ICU 的 ubidi）使用 UTF-16 索引，而 SkShaper 使用 UTF-8 偏移，迭代器需要同步两种坐标系：
- `fEndOfCurrentRun`: UTF-8 指针，用于返回给 SkShaper
- `fUTF16LogicalPosition`: UTF-16 索引，用于查询 SkBidiIterator

### BidiRunIterator 创建流程
1. 验证输入长度可容纳 int32_t（ubidi 的限制）
2. 将 UTF-8 转换为 UTF-16（两次调用：计算大小 + 实际转换）
3. 确定 BiDi 方向（偶数级别 = LTR，奇数 = RTL）
4. 调用 `SkUnicode::makeBidiIterator` 创建分析器
5. 包装为 `SkUnicodeBidiRunIterator` 返回

### 无效 UTF-8 处理
`utf8_next` 辅助函数将无效 UTF-8 序列替换为 U+FFFD（REPLACEMENT CHARACTER），确保不会因编码错误而崩溃。

### 旧版 API 支持
`SkShaper::MakeIcuBiDiRunIterator` 使用静态局部变量缓存 SkUnicode 实例（`get_unicode()`），按优先级尝试 ICU > libgrapheme > ICU4X。

## 依赖关系

- **SkUnicode**: BiDi 分析抽象接口
- **SkBidiIterator**: BiDi 级别查询接口
- **SkUTF**: UTF-8/UTF-16 编码转换
- **SkShaper**: BiDiRunIterator 基类
- 可选的 Unicode 后端：SkUnicode_icu, SkUnicode_libgrapheme, SkUnicode_icu4x

## 设计模式与设计决策

1. **适配器模式**: SkUnicodeBidiRunIterator 将 SkBidiIterator 的按位置查询接口适配为 SkShaper 的运行迭代器接口。
2. **坐标系桥接**: 内部维护 UTF-8 和 UTF-16 双重位置，解决了 ICU 和 SkShaper 使用不同编码索引的问题。
3. **Unicode 后端抽象**: 通过 `sk_sp<SkUnicode>` 注入依赖，支持编译时和运行时切换 Unicode 实现。

## 性能考量

- UTF-8 到 UTF-16 的转换是 O(n) 的前置开销，不可避免
- `getLevelAt()` 在 ICU 中是 O(1) 查询，整体迭代为 O(n)
- 旧版 API 使用静态局部变量缓存 Unicode 实例，避免重复初始化
- 每次调用 `consume()` 推进一个完整的 BiDi 运行，不做单字符级别的回调

## 相关文件

- `modules/skshaper/include/SkShaper_skunicode.h` - 公共接口
- `modules/skunicode/include/SkUnicode.h` - SkUnicode 接口
- `modules/skshaper/src/SkShaper_harfbuzz.cpp` - BiDi 迭代器的主要消费者
- `src/base/SkUTF.h` - UTF 编码工具
