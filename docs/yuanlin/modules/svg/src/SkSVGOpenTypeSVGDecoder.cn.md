# SkSVGOpenTypeSVGDecoder

> 源文件: [modules/svg/src/SkSVGOpenTypeSVGDecoder.cpp](../../../../modules/svg/src/SkSVGOpenTypeSVGDecoder.cpp)

## 概述

`SkSVGOpenTypeSVGDecoder` 实现了 OpenType SVG 字体表的解码器，使 Skia 能够渲染使用 SVG 定义的彩色字形（如 emoji 和装饰字体）。该解码器将 OpenType 字体中嵌入的 SVG 文档解析为 `SkSVGDOM`，然后按字形 ID 渲染指定的 SVG 元素。

它还实现了一个内部的 `DataResourceProvider`，用于处理 SVG 中 base64 编码的内联图像数据（data URI），支持 JPEG 和 PNG 格式。

## 架构位置

```
SkOpenTypeSVGDecoder (抽象接口，定义在 include/core/)
  └── SkSVGOpenTypeSVGDecoder      ← 本文件（SVG 模块提供的具体实现）
        ├── SkSVGDOM                 （SVG DOM 管理器，持有解析后的 SVG 树）
        └── DataResourceProvider     （内部资源提供者，处理 data URI）

OpenType 字体渲染管线:
  SkTypeface → SkScalerContext → SkOpenTypeSVGDecoder::render() → SkCanvas

数据流:
  OpenType SVG 表数据 (uint8_t[])
    → SkMemoryStream
      → SkSVGDOM::Builder::make()
        → SkSVGDOM (缓存)
          → renderNode(glyphId) → SkCanvas
```

`SkSVGOpenTypeSVGDecoder` 是 Skia 字体渲染管线与 SVG 模块之间的桥梁。它实现了 `SkOpenTypeSVGDecoder` 抽象接口，使得 Skia 核心无需直接依赖 SVG 模块即可支持 SVG 字体渲染。

## 主要类与结构体

### `SkSVGOpenTypeSVGDecoder`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fSkSvg` | `sk_sp<SkSVGDOM>` | 解析后的 SVG DOM |
| `fApproximateSize` | `size_t` | SVG 数据的近似大小（字节） |

### `DataResourceProvider`（内部匿名命名空间）

继承自 `skresources::ResourceProvider`，专门处理 data URI 格式的内联图像资源。

## 公共 API 函数

### `Make(const uint8_t* svg, size_t svgLength)`
静态工厂方法，从原始 SVG 字节数据创建解码器：
1. 创建内存流
2. 配置 `SkSVGDOM::Builder` 并设置 `DataResourceProvider`
3. 解析 SVG 文档
4. 返回解码器实例

### `approximateSize()`
返回 SVG 数据的近似大小，用于内存管理和缓存决策。

### `render(SkCanvas& canvas, int upem, SkGlyphID glyphId, SkColor foregroundColor, SkSpan<SkColor> palette)`
渲染指定字形：
1. 设置容器尺寸为 upem x upem（每 em 单位数）
2. 配置前景色（`currentColor`）
3. 处理调色板颜色（COLR 调色板）
4. 构建字形 ID 字符串（如 "glyph123"）
5. 调用 `SkSVGDOM::renderNode()` 渲染目标节点

## 内部实现细节

### DataResourceProvider

实现了 data URI 图像解码，作为匿名命名空间中的内部类：

1. **工厂方法**: `Make()` 创建实例，使用私有默认构造函数
2. **URI 匹配**: 检查 URI 是否以 "data:image/" 开头
3. **编码检测**: 查找 ";base64," 编码标记字符串
4. **Base64 解码**: 使用 `SkBase64::Decode` 两遍调用（第一遍计算解码后大小，第二遍实际解码到预分配的 `SkData` 缓冲区）
5. **格式识别**: 通过文件魔数（而非 MIME 类型）检测格式：
   - `SkPngDecoder::IsPng()` 检测 PNG 格式
   - `SkJpegDecoder::IsJpeg()` 检测 JPEG 格式
   - 其他格式触发 `SkDEBUGFAIL`（OpenType SVG 规范仅要求 PNG 和 JPEG）
6. **资产创建**: 将解码后的 `SkCodec` 包装为 `MultiFrameImageAsset`

### 字形渲染流程

渲染流程的关键细节：

1. **容器尺寸**: 设置为 upem x upem，确保 SVG 坐标系与字体设计空间一致。upem（units per em）通常为 1000 或 2048。
2. **前景色传播**: 通过 `SkSVGPresentationContext::fInherited.fColor` 设置，使 SVG 中的 `currentColor` 引用能正确解析为用户指定的文本颜色。
3. **调色板支持**: 将 COLR 调色板颜色映射为命名颜色（"color0", "color1", ...），存储在 `SkSVGPresentationContext::fNamedColors` 中。这允许 SVG 字形内部通过 `var(--color0)` 等方式引用调色板颜色。
4. **字形 ID 格式**: 使用 "glyph" + 字形 ID 数字作为 SVG 元素的 ID 标识（如 "glyph65"），这是 OpenType SVG 表的标准约定。

### 字符串构建

使用固定大小栈数组 + `SkStrAppendU32` 构建字形和颜色 ID 字符串，避免堆分配。数组初始化为 "glyph" 或 "color" 前缀，然后追加数字后缀。

### 空调色板优化

当 `palette.empty()` 为真时，跳过整个调色板处理代码路径，包括 `SkMakeEnumerate` 遍历和 `THashMap` 创建。`pctx.fNamedColors` 保持为 nullptr，SVG 渲染时不会尝试查找命名颜色。

### 析构函数

`SkSVGOpenTypeSVGDecoder::~SkSVGOpenTypeSVGDecoder()` 使用 `= default`，依赖 `sk_sp<SkSVGDOM>` 的析构函数自动释放 SVG DOM 资源。

## 依赖关系

- **Skia Core**: `SkCanvas`, `SkColor`, `SkData`, `SkScalar`, `SkSize`, `SkSpan`, `SkStream`, `SkString`, `SkTypes`
- **Skia Codec**: `SkCodec`, `SkJpegDecoder`, `SkPngDecoder`
- **Skia Internal**: `SkBase64`, `SkEnumerate`, `SkTHash`
- **Skia Modules**: `SkResources`（资源提供者）
- **SVG 模块**: `SkSVGDOM`, `SkSVGAttribute`, `SkSVGRenderContext`, `SkSVGTypes`

## 设计模式与设计决策

1. **桥接模式**: 该类桥接了 Skia 的字体渲染管线（`SkOpenTypeSVGDecoder` 接口）和 SVG 模块（`SkSVGDOM`），使两个子系统保持独立。这种解耦设计允许 Skia 核心在不依赖 SVG 模块的情况下定义字体渲染接口。

2. **内部资源提供者**: `DataResourceProvider` 作为内部类，专门处理 OpenType SVG 字体中允许的 data URI 格式，简化了外部依赖。不支持外部文件引用是有意为之的安全决策。

3. **不设置字体管理器**: 注释说明故意不设置 Builder 的字体管理器和排版工具，因为 SVG 字形不应包含 `<text>` 元素。这是 OpenType SVG 规范的限制。

4. **调色板颜色映射**: 使用 "colorN" 命名约定将 OpenType 调色板颜色桥接到 SVG 的命名颜色系统，实现了 COLR 规范与 SVG 的交互。调色板索引从 0 开始，与 CSS Color 规范中的 `color(0)` 对应。

5. **栈分配字符串**: 字形和颜色 ID 字符串使用栈上固定大小数组，避免在每次字形渲染时进行堆分配。数组大小由 `kSkStrAppendU32_MaxSize` 保证足够容纳最大的 32 位无符号整数。

6. **两遍 Base64 解码**: `decode_datauri` 使用两遍调用 `SkBase64::Decode` -- 第一遍计算解码后的数据大小，第二遍执行实际解码。这避免了过度分配内存。

7. **编解码器格式检测**: 使用 `IsPng` 和 `IsJpeg` 魔数检查确定数据格式，而非依赖 URI 中的 MIME 类型。这更加可靠，因为 URI 中的类型信息可能不准确。

## 性能考量

- SVG DOM 解析只执行一次（在 `Make` 时），后续渲染复用同一 DOM，这是关键的性能优化
- 每次字形渲染仅调用 `renderNode()`，只渲染目标字形而非整个 SVG 文档
- base64 解码在图像首次加载时执行，但 `MultiFrameImageAsset` 可能提供缓存
- 栈分配的 ID 字符串避免了热路径上的堆分配，对于字形渲染这样的高频操作至关重要
- `approximateSize()` 当前仅返回原始 SVG 数据大小，标注为 TODO，更精确的估算应考虑解析后的 DOM 开销
- 字形渲染路径中的 `SkSVGPresentationContext` 创建包含哈希映射（`namedColors`），当调色板非空时有额外分配开销
- `SkSVGDOM::renderNode` 内部需要进行 ID 查找和渲染上下文构建，但这些操作相对于实际 SVG 渲染开销较小
- 解码器未设置字体管理器和排版工具，避免了加载不需要的字体子系统
- `DataResourceProvider` 使用 base64 内联数据，无需文件系统 I/O
- 对于包含大量字形的 SVG 字体文件，DOM 持久化避免了每个字形的重新解析，但内存占用与 SVG 文件大小成正比

## 相关文件

- `modules/svg/include/SkSVGOpenTypeSVGDecoder.h` - 头文件定义
- `include/core/SkOpenTypeSVGDecoder.h` - 抽象接口定义，Skia 核心的解码器契约
- `modules/svg/include/SkSVGDOM.h` - SVG DOM 管理器，提供 Builder 和渲染接口
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文和命名颜色支持
- `modules/skresources/include/SkResources.h` - 资源提供者接口，DataResourceProvider 的基类
- `include/codec/SkPngDecoder.h` - PNG 解码器，用于 data URI 图像
- `include/codec/SkJpegDecoder.h` - JPEG 解码器，用于 data URI 图像
- `src/base/SkBase64.h` - Base64 编解码工具
- `src/core/SkEnumerate.h` - 枚举辅助工具，用于调色板遍历
- `src/core/SkTHash.h` - 哈希映射实现，用于命名颜色存储
