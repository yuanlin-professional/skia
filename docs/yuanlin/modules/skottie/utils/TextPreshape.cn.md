# TextPreshape - Lottie 文本预整形工具

> 源文件: [`modules/skottie/utils/TextPreshape.h`](../../../modules/skottie/utils/TextPreshape.h), [`modules/skottie/utils/TextPreshape.cpp`](../../../modules/skottie/utils/TextPreshape.cpp)

## 概述

TextPreshape 是一个 Lottie 动画预处理工具，用于将动画中的文本层预先进行文本整形（shaping），并将整形结果直接嵌入 JSON 数据中。这使得动画在播放时无需执行昂贵的文本整形操作，同时确保字形路径数据可用于基于路径的字体渲染。

预整形将每个字形转换为 Lottie 路径格式（贝塞尔曲线），存储为自定义字体数据，并在文本值中嵌入预先计算好的字形位置信息。

## 架构位置

位于 Skottie 工具层，作为构建时/预处理步骤使用：

- **调用者**: 构建工具、预处理脚本、服务器端渲染
- **核心依赖**: Skottie 的 Shaper（文本整形器）、AnimationBuilder（JSON 解析）
- **输入/输出**: Lottie JSON -> 预整形后的 Lottie JSON

## 主要类与结构体

### `Preshape` 函数（公共 API）
```cpp
bool Preshape(const char* json, size_t size, SkWStream*,
              const sk_sp<SkFontMgr>&, const sk_sp<SkShapers::Factory>&,
              const sk_sp<skresources::ResourceProvider>&);
```

### `Preshaper` 内部类
核心预整形器，负责遍历 Lottie JSON 中的文本层并执行整形。

### `GlyphCache` 内部类
字形缓存，按字体名称分组存储每个字符的路径和宽度数据。避免同一字体中相同字符的重复处理。

### `GlyphCache::GlyphRec` 结构体
存储单个字形的 Unicode ID、宽度和 SkPath 路径。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Preshape(json, size, stream, fontMgr, shaperFactory, resourceProvider)` | 从 JSON 字符串预整形 |
| `Preshape(data, stream, fontMgr, shaperFactory, resourceProvider)` | 从 SkData 预整形 |

## 内部实现细节

### 预整形流程
1. 解析 Lottie JSON 为 DOM
2. 使用 AnimationBuilder 解析字体信息
3. 遍历所有图层（包括资产中的嵌套合成）
4. 对类型为 5（文本层）的图层提取文本值
5. 使用 Skottie::Shaper 执行文本整形
6. 将整形结果注入 JSON:
   - `"gl"`: 预整形字形数组（位置、字符、行号、簇索引）
   - `"gs"`: 考虑自动缩放后的有效字体大小
   - `"f"`: 更新为预整形字体名称（原名 + "_preshaped"）

### 字形路径转换（pathToLottie）
将 SkPath 转换为 Lottie 路径格式：
- Lottie 路径使用 (vertex, in_tangent, out_tangent) 元组表示三次贝塞尔曲线
- 切线控制点使用相对坐标
- 二次曲线自动提升为三次曲线
- 支持多轮廓路径

### 字形标准化
所有字形路径按 100 的标准化大小存储（`scale = 100 / font.getSize()`），与 Lottie 自定义字体约定一致。

### 字体数据输出
- `fonts.list`: 包含更新后的字体元数据（名称后缀 "_preshaped"）
- `chars`: 包含每个字形的字符ID、字体族、样式、标准化宽度和路径数据

## 依赖关系

- `modules/jsonreader/SkJSONReader.h` - JSON 解析和构建
- `modules/skottie/include/Skottie.h` - AnimationBuilder
- `modules/skottie/include/TextShaper.h` - 文本整形器
- `modules/skottie/src/SkottieJson.h` - JSON 值解析工具
- `modules/skottie/src/text/TextValue.h` - 文本值解析
- `modules/skshaper/include/SkShaper_factory.h` - 整形器工厂
- `src/core/SkGeometry.h` - 二次到三次曲线转换
- `src/core/SkPathPriv.h` - 路径遍历

## 设计模式与设计决策

### 离线预处理
将昂贵的文本整形操作从运行时移到构建时，是经典的预计算优化策略。

### 字体名称空间隔离
预整形字体使用 "_preshaped" 后缀，避免与原始字体冲突，同时允许动画文件同时包含预整形和非预整形文本。

### JSON 就地修改
使用 skjson DOM 的 `writable()` 方法直接修改解析后的 JSON 树，然后序列化输出，避免了手动 JSON 构建的复杂性。

## 性能考量

- GlyphCache 使用线性搜索（预期字形数量少）
- SkArenaAlloc 用于所有 JSON 值分配，统一释放
- 标准化大小为 100 保证了 Lottie 播放器的兼容性
- 仅处理可转换为路径的字形，彩色字形被跳过

## 相关文件

- `modules/skottie/include/TextShaper.h` - 文本整形 API
- `modules/skottie/src/text/TextValue.h` - 文本值结构
- `modules/jsonreader/SkJSONReader.h` - JSON DOM
- `modules/skottie/src/SkottieJson.h` - JSON 解析工具
