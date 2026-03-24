# SkShaper_skunicode - Unicode BiDi 运行迭代器接口

> 源文件: `modules/skshaper/include/SkShaper_skunicode.h`

## 概述

SkShaper_skunicode.h 声明了基于 SkUnicode 接口的 BiDi（双向文本）运行迭代器创建函数。该迭代器将 UTF-8 文本按 Unicode 双向算法分割为具有相同嵌入级别的运行段，是 HarfBuzz 塑形器处理混合方向文本（如阿拉伯语与英语混排）所必需的组件。

## 架构位置

位于 `SkShapers::unicode` 命名空间，是 skshaper 模块中 Unicode 处理层的一部分。它连接了 SkUnicode 抽象接口和 SkShaper 的 BiDiRunIterator。

## 主要类与结构体

无类定义，仅提供命名空间级工厂函数。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `BidiRunIterator(unicode, utf8, utf8Bytes, bidiLevel)` | 创建 BiDi 运行迭代器 |

参数：
- `unicode`: SkUnicode 实例，提供 BiDi 算法实现
- `utf8` / `utf8Bytes`: UTF-8 文本
- `bidiLevel`: 默认 BiDi 嵌入级别（偶数 = LTR，奇数 = RTL）

## 依赖关系

- **SkUnicode**: 双向文本分析的抽象接口
- **SkShaper**: BiDiRunIterator 基类定义
- **SkRefCnt**: SkUnicode 的引用计数管理

## 设计模式与设计决策

1. **接口分离**: BiDi 迭代器独立于塑形器和脚本迭代器，可被不同的塑形后端复用。
2. **Unicode 后端抽象**: 通过 `sk_sp<SkUnicode>` 参数注入，支持 ICU、ICU4X、libgrapheme 等多种 Unicode 实现。

## 性能考量

- BiDi 分析的主要开销在 SkUnicode 内部（通常是 ICU 的 ubidi 实现）
- UTF-8 到 UTF-16 的转换是必要的，因为大多数 BiDi 实现基于 UTF-16

## 相关文件

- `modules/skshaper/src/SkShaper_skunicode.cpp` - 实现文件
- `modules/skunicode/include/SkUnicode.h` - SkUnicode 接口
- `modules/skshaper/include/SkShaper.h` - BiDiRunIterator 基类

## 使用示例

```cpp
auto unicode = SkUnicodes::ICU::Make();

// 创建 LTR 默认的 BiDi 迭代器
auto bidi = SkShapers::unicode::BidiRunIterator(
    unicode, utf8, utf8Bytes, 0);  // 0 = LTR

// 创建 RTL 默认的 BiDi 迭代器（用于阿拉伯语/希伯来语为主的文本）
auto bidiRtl = SkShapers::unicode::BidiRunIterator(
    unicode, utf8, utf8Bytes, 1);  // 1 = RTL
```

## 使用注意事项

1. `unicode` 参数不能为空，否则返回 nullptr
2. `bidiLevel` 为偶数表示默认 LTR，奇数表示默认 RTL
3. 文本内部的 BiDi 方向由 Unicode 双向算法自动检测
4. 输入文本必须是有效的 UTF-8 编码
5. 文本长度必须能用 int32_t 表示（约 2GB 限制）
6. 内部会进行 UTF-8 到 UTF-16 的转换，有 O(n) 的前置开销

### BiDi 级别说明
| 级别 | 方向 | 典型用途 |
|------|------|---------|
| 0 | LTR | 英语、中文等从左到右文本 |
| 1 | RTL | 阿拉伯语、希伯来语等从右到左文本 |
| 2+ | 嵌套 | 混合方向文本中的嵌套层级 |

迭代器产生的运行中，每个运行内所有字符具有相同的 BiDi 嵌入级别。塑形器根据级别决定文本的视觉排列方向。
