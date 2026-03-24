# SkDebugUtils

> 源文件
> - src/core/SkDebugUtils.h

## 概述

`SkDebugUtils` 是 Skia 图形库中提供调试辅助工具的头文件模块。它包含一组内联函数和宏,用于在开发和调试过程中可视化数据、转换枚举值为字符串、以及dump 缓冲区内容。这些工具主要在 Debug 构建中启用,Release 构建中会被优化为空操作以保持性能。

该模块的核心功能是 `SkDumpBuffer`,可以将灰度缓冲区以 ASCII 艺术形式打印到控制台,方便开发者直观查看像素数据。这对于调试遮罩、Alpha 通道、字形光栅化等场景特别有用。

## 架构位置

`SkDebugUtils` 位于 Skia 的调试基础设施层:

```
Skia Debug Infrastructure
  ├─ Debug Output
  │   ├─ SkDebugUtils ← 当前模块(调试工具集)
  │   └─ SkDebug.h (SkDebugf 输出)
  ├─ Assert & Validation
  │   └─ SkAssert.h (断言宏)
  └─ Debug Visualization
      └─ Viewer Tools (图形界面调试)
```

这是一个纯头文件模块,提供编译时调试辅助。

## 主要类与结构体

该模块不包含类或结构体,仅提供独立函数和宏。

## 公共 API 函数

### SkTileModeToStr

```cpp
static constexpr const char* SkTileModeToStr(SkTileMode tm)
```

将 `SkTileMode` 枚举值转换为字符串。

**参数**:
- `tm`: 平铺模式枚举值

**返回值**: 对应的字符串常量

**映射表**:

| SkTileMode 值 | 返回字符串 |
|--------------|----------|
| kClamp | "Clamp" |
| kRepeat | "Repeat" |
| kMirror | "Mirror" |
| kDecal | "Decal" |

**用途**:
- 调试输出日志
- 序列化配置
- 错误消息格式化

**实现细节**:
- `constexpr` 函数,编译时求值
- 使用 `SkUNREACHABLE` 标记不可能的分支,帮助编译器优化

### SkDumpBuffer

```cpp
inline void SkDumpBuffer(uint8_t const* const buffer, int w, int h, int rowBytes,
                         bool dumpActualValues = false)
```

以可视化形式转储灰度缓冲区到控制台。

**参数**:
- `buffer`: 指向 8 位灰度数据的指针
- `w`: 缓冲区宽度(像素)
- `h`: 缓冲区高度(像素)
- `rowBytes`: 每行字节数(跨度),可能大于 `w`
- `dumpActualValues`:
  - `false`(默认): 使用 ASCII 字符可视化(0-F 表示亮度)
  - `true`: 打印实际像素值(0-255 数字)

**行为**:
- **Debug 构建**: 打印缓冲区内容
- **Release 构建**: 空操作,无性能开销

**可视化模式**(dumpActualValues = false):
- 使用 16 个 ASCII 字符表示灰度级别:`'0123456789ABCDEF'`
- 像素值 0-15 → '0', 16-31 → '1', ..., 240-255 → 'F'
- 直观显示图像形状和密度分布

**数值模式**(dumpActualValues = true):
- 打印每个像素的实际值(0-255)
- 用制表符分隔,适合精确检查

## 内部实现细节

### 条件编译

```cpp
#if defined(SK_DEBUG)
inline void SkDumpBuffer(...) {
    // 实际实现
}
#else
inline void SkDumpBuffer(uint8_t*, int, int, int) {}  // 空操作
#endif
```

**设计原因**:
- Debug 构建提供完整功能
- Release 构建避免不必要的字符串操作和 I/O
- 调用代码无需 `#ifdef`,始终可以调用该函数

### 灰度映射算法

```cpp
static constexpr char shades[] = {'0', '1', '2', '3', '4', '5', '6', '7',
                                  '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'};
int idx = static_cast<int>(pixelValue * std::size(shades) / 256);
SkDebugf("%c", shades[idx]);
```

**映射公式**: `index = pixelValue * 16 / 256 = pixelValue / 16`

**范围保护**: `SkASSERT(idx >= 0 && idx < 16)`

### 输出示例

**可视化模式输出**:
```
000000000000000
001234567898000
003456789ABC000
0012345678AB000
000000000000000
```

**数值模式输出**:
```
0    0    0    0    15   32   64   128  255
0    16   32   48   64   80   96   112  128
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkTileMode.h | SkTileMode 枚举定义 |
| include/private/base/SkAssert.h | SkASSERT, SkUNREACHABLE 宏 |
| include/private/base/SkDebug.h | SkDebugf 输出函数 |
| <array> | std::size() 模板函数 |
| <cstdint> | uint8_t 类型 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| src/core/SkMask.cpp | 遮罩数据调试 |
| src/core/SkGlyph.cpp | 字形光栅化调试 |
| src/core/SkBlitter.cpp | 位块传输调试 |
| 测试代码 | 单元测试验证 |

## 设计模式与设计决策

### 设计模式

1. **工具类模式**: 提供静态函数,无状态
2. **条件编译模式**: Debug/Release 行为差异化
3. **内联函数模式**: 头文件实现,减少链接依赖

### 设计决策

**为何使用头文件实现**:
- 调试工具通常小且频繁调用
- 内联避免函数调用开销
- 无需单独编译单元,简化构建

**为何 Release 构建为空操作**:
- 调试输出在生产环境无用
- I/O 操作开销大,影响性能
- 减小二进制体积(移除字符串常量)

**ASCII 可视化的设计选择**:
- 16 级灰度足够识别形状和梯度
- ASCII 字符在任何终端都能显示
- 比图形界面调试更快(无需启动 GUI)
- 适合远程调试和 CI 日志

**为何支持 rowBytes 参数**:
- 实际缓冲区可能有行填充(对齐)
- 支持子区域转储(buffer 可能指向大图像的一部分)
- 与 Skia 像素数据布局一致(SkPixmap, SkBitmap)

**dumpActualValues 参数的必要性**:
- 可视化模式快速识别模式
- 数值模式精确验证像素值
- 两种模式互补,满足不同调试需求

## 性能考量

### 优化策略

1. **条件编译**: Release 构建零开销
2. **constexpr 函数**: `SkTileModeToStr` 编译时求值
3. **内联函数**: 避免函数调用开销
4. **字符映射**: 使用查表而非复杂计算

### 性能特征

- **Release 构建**: 完全无开销(空函数被内联消除)
- **Debug 构建**:
  - `SkDumpBuffer`: 主要开销在 I/O(SkDebugf)
  - 典型 100x100 缓冲区: ~10ms(取决于终端速度)
  - `SkTileModeToStr`: ~0ns(constexpr 或表查找)

### 使用建议

- 仅在开发和调试时使用,不要保留在频繁执行的代码路径
- 大缓冲区转储可能很慢,考虑转储子区域
- 如果需要保存输出,重定向 stderr 到文件

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/private/base/SkDebug.h | 依赖 | SkDebugf 输出函数 |
| include/private/base/SkAssert.h | 依赖 | 断言和不可达标记 |
| include/core/SkTileMode.h | 依赖 | 平铺模式枚举 |
| src/core/SkMask.cpp | 使用者 | 遮罩数据调试 |
| src/core/SkGlyph.cpp | 使用者 | 字形调试 |
| tests/ | 使用者 | 单元测试验证 |
