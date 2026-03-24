# BlendModes.cpp

> 源文件: `modules/skottie/src/BlendModes.cpp`

## 概述

`BlendModes.cpp` 实现了 Skottie 动画引擎中 Lottie 混合模式到 Skia 混合模式的映射。该文件处理 After Effects 中定义的 17 种标准混合模式（从 Normal 到 Add）以及自定义混合模式（如 Hard Mix），将它们转换为对应的 `SkBlendMode` 或 `SkRuntimeEffect` 自定义混合器，并附加到场景图节点上。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，属于 Skottie 的内部实现层。在渲染管线中，混合模式在图层/形状节点构建时被解析和附加：

```
Lottie JSON ("bm" 字段) -> get_blender() -> SkBlendMode / SkRuntimeEffect -> sksg::BlenderEffect
```

## 主要类与结构体

该文件不定义类或结构体，仅使用匿名命名空间中的静态函数和数据。

### `CustomBlenders` 枚举
```cpp
enum CustomBlenders { HARDMIX = 17 };
```
- 定义了超出标准 `SkBlendMode` 范围的自定义混合模式索引。

## 公共 API 函数

### `AnimationBuilder::attachBlendMode()`
```cpp
sk_sp<sksg::RenderNode> AnimationBuilder::attachBlendMode(const skjson::ObjectValue& jobject,
                                                           sk_sp<sksg::RenderNode> child) const;
```
- **功能**: 为渲染节点附加混合模式效果。
- **参数**:
  - `jobject`: 包含 `"bm"` 字段的 JSON 对象
  - `child`: 要附加混合模式的子节点
- **返回值**: 包装了混合效果的新节点，如果是默认 SrcOver 模式则返回原始子节点。
- **副作用**: 如果使用了非平凡混合模式，设置 `fHasNontrivialBlending = true`，这会导致 `Animation::render()` 使用顶层隔离渲染。

## 内部实现细节

### 整体处理流程

1. 从 JSON 对象的 `"bm"` 字段读取混合模式索引值。
2. 将索引值与标准混合模式映射表和自定义混合模式进行匹配。
3. 如果是 SrcOver（默认），返回 null blender（优化路径）。
4. 如果是标准模式，创建对应的 `SkBlender`。
5. 如果是自定义模式（如 Hard Mix），使用 SkSL 运行时着色器创建自定义 `SkBlender`。
6. 将混合器包装为 `sksg::BlenderEffect` 场景图节点。

### 混合模式映射表
```cpp
static constexpr SkBlendMode kBlendModeMap[] = { ... };
```
17 种标准混合模式从 Lottie JSON 的 `"bm"` 索引映射到 `SkBlendMode`：
| 索引 | Lottie 模式 | SkBlendMode |
|------|-------------|-------------|
| 0    | Normal      | kSrcOver    |
| 1    | Multiply    | kMultiply   |
| 2    | Screen      | kScreen     |
| 3    | Overlay     | kOverlay    |
| 4    | Darken      | kDarken     |
| 5    | Lighten     | kLighten    |
| 6    | Color Dodge | kColorDodge |
| 7    | Color Burn  | kColorBurn  |
| 8    | Hard Light  | kHardLight  |
| 9    | Soft Light  | kSoftLight  |
| 10   | Difference  | kDifference |
| 11   | Exclusion   | kExclusion  |
| 12   | Hue         | kHue        |
| 13   | Saturation  | kSaturation |
| 14   | Color       | kColor      |
| 15   | Luminosity  | kLuminosity |
| 16   | Add         | kPlus       |

### Hard Mix 自定义混合器
```cpp
static sk_sp<SkBlender> hardMix();
```
- **实现**: 使用 `SkRuntimeEffect::MakeForBlender()` 编译自定义 SkSL 着色器代码。
- **SkSL 着色器代码**:
  ```glsl
  half4 main(half4 src, half4 dst) {
      src.rgb = unpremul(src).rgb + unpremul(dst).rgb;
      src.rgb = min(floor(src.rgb), 1) * src.a;
      return src + (1 - src.a)*dst;
  }
  ```
- **算法解释**: 将源和目标颜色（unpremul 后）相加，取整数部分（floor 将 >= 1 的通道变为 1，< 1 的变为 0），然后重新预乘 alpha 并与目标混合。这实现了 After Effects Hard Mix 模式的视觉效果。
- **单例模式**: 使用 C++ 静态局部变量的线程安全懒初始化，确保 SkRuntimeEffect 只编译一次。`release()` 将编译结果从 `sk_sp` 中提取出来作为裸指针持有（静态生命周期），避免在程序退出时的析构竞争。

### `get_blender()` 分发逻辑
```cpp
static sk_sp<SkBlender> get_blender(const skjson::ObjectValue&, const AnimationBuilder*);
```
分发逻辑按以下优先级处理：
1. 从 JSON 的 `"bm"` 字段读取模式索引（默认为 0，即 Normal/SrcOver）
2. 如果模式为 0（SrcOver），返回 `nullptr`（等效于 SrcOver，但标识为无非平凡混合）
3. 如果模式在 1-16 的标准映射范围内，使用 `SkBlender::Mode(kBlendModeMap[mode])` 创建标准混合器
4. 如果模式为 HARDMIX (17)，使用自定义 SkSL 混合器
5. 其他未知模式（> 17 或负值）输出警告日志并返回 `nullptr`（回退到 SrcOver）

## 依赖关系

- **Skia 核心**: `SkBlendMode`, `SkBlender`, `SkData`, `SkRefCnt`, `SkString`
- **`include/effects/SkRuntimeEffect.h`**: SkSL 运行时效果，用于 Hard Mix 自定义混合器的着色器编译
- **`modules/jsonreader/SkJSONReader.h`**: JSON DOM 解析器，用于读取 JSON 对象
- **`modules/skottie/include/Skottie.h`**: Logger 类型，用于输出未知混合模式的警告
- **`modules/skottie/src/SkottieJson.h`**: `ParseDefault` JSON 工具函数，用于从 JSON 对象中提取带默认值的字段
- **`modules/skottie/src/SkottiePriv.h`**: `AnimationBuilder` 类声明，提供 `attachBlendMode` 方法和 `fHasNontrivialBlending` 标志
- **`modules/sksg/include/SkSGRenderEffect.h`**: `sksg::BlenderEffect` 场景图节点，将混合器应用到渲染节点上
- **`modules/sksg/include/SkSGRenderNode.h`**: 场景图渲染节点基类

## 设计模式与设计决策

- **查找表模式**: 标准混合模式使用 `constexpr` 数组进行 O(1) 查找，简洁高效。数组索引直接对应 Lottie 的 `"bm"` 字段值，无需额外的映射逻辑。
- **Null Object 优化**: SrcOver 模式（`mode == 0`）返回 `nullptr`（而非 `SkBlender::Mode(kSrcOver)`），这允许 `attachBlendMode` 跳过 `BlenderEffect` 节点的创建，同时作为"无非平凡混合"的标识符。这是一个关键的优化决策，因为大多数 Lottie 图层使用默认的 SrcOver 模式。
- **SkSL 自定义混合**: 对于标准 `SkBlendMode` 无法表达的混合模式（如 Hard Mix），使用 SkSL 运行时着色器实现，展示了 Skia 的可扩展性。这种方式允许在不修改 Skia 核心的情况下添加任意的自定义混合效果。
- **单例 SkRuntimeEffect**: Hard Mix 的 SkRuntimeEffect 使用 C++ 静态局部变量的线程安全懒初始化（C++11 保证的 magic statics），确保着色器编译只发生一次，且在多线程环境中是安全的。
- **优雅降级**: 未知混合模式（`mode > HARDMIX` 或不在已知范围内）不会导致崩溃，而是通过 `abuilder->log()` 输出警告并回退到 SrcOver（返回 `nullptr`）。
- **switch 的 default 分支**: 自定义混合模式的 `switch` 语句在 `default` 分支中 `break`，然后在函数末尾输出警告。这种结构确保了所有未处理的模式都会产生日志记录。

## 性能考量

- **O(1) 模式查找**: 标准混合模式的查找是简单的数组索引操作（`kBlendModeMap[mode]`），无性能开销。数组大小固定为 17 个元素。
- **自定义混合器的 GPU 成本**: Hard Mix 使用 SkSL 着色器，在 GPU 上每像素执行额外的着色器代码（`unpremul`、加法、`floor`、重新预乘），比标准硬件混合模式稍慢，但在现代 GPU 上开销通常可以接受。
- **SkRuntimeEffect 编译成本**: Hard Mix 着色器通过静态局部变量的懒初始化确保仅在首次使用时编译一次。`SkRuntimeEffect::MakeForBlender` 的编译时间约为数毫秒，之后的 `makeBlender(nullptr)` 调用近乎零成本。
- **BlenderEffect 节点开销**: 每个非 SrcOver 的混合模式都会在场景图中插入一个 `sksg::BlenderEffect` 节点，增加渲染树的深度。这会额外消耗一次 `saveLayer` 和一次混合操作。
- **顶层隔离的触发**: 一旦动画中存在非平凡混合模式（`fHasNontrivialBlending == true`），整个动画渲染时都会使用 `saveLayer` 进行顶层隔离，增加一次纹理分配和混合操作。这是一个全局影响——即使只有一个图层使用了非标准混合模式，整个动画都需要额外的隔离层。
- **SrcOver 的 null 优化**: 返回 `nullptr` 而非 `SkBlender::Mode(kSrcOver)` 是一个重要优化，因为它避免了 `BlenderEffect` 节点的创建和 `fHasNontrivialBlending` 标志的设置。大多数 Lottie 图层使用 SrcOver，因此这个优化覆盖了最常见的情况。
- **内存开销**: 标准混合模式映射表是编译时常量（`constexpr`），不占用运行时内存。Hard Mix 的 `SkRuntimeEffect` 是全局单例，内存开销极小。

## 相关文件

- `modules/skottie/src/SkottiePriv.h` -- `AnimationBuilder::attachBlendMode` 声明、`fHasNontrivialBlending` 成员
- `modules/skottie/src/Skottie.cpp` -- `fHasNontrivialBlending` 影响 `Animation::render()` 的行为
- `modules/sksg/include/SkSGRenderEffect.h` -- `sksg::BlenderEffect` 场景图节点
- `include/core/SkBlendMode.h` -- Skia 标准混合模式枚举
- `include/core/SkBlender.h` -- `SkBlender` 基类
- `include/effects/SkRuntimeEffect.h` -- SkSL 运行时效果框架
