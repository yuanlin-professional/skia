# SkottieTest.cpp

> 源文件: `modules/skottie/src/SkottieTest.cpp`

## 概述

`SkottieTest.cpp` 是 Skottie 动画引擎的单元测试文件，包含多个测试用例，验证 Skottie 的 JSON 解析、动画构建、标记（marker）处理、图片加载策略等核心功能的正确性。该文件还包含了针对模糊测试发现的 bug 的回归测试（如 OssFuzz8956），确保这些问题不会再次出现。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，属于 Skottie 模块的测试代码。使用 Skia 的标准测试框架（`DEF_TEST` 宏），可通过 Skia 测试运行器执行。

## 主要类与结构体

### `TestMarkerObserver`（测试内部）
```cpp
class TestMarkerObserver final : public MarkerObserver
```
- **职责**: 用于 `Skottie_Annotations` 测试的标记观察者，收集所有接收到的标记信息。
- **成员**: `fMarkers` -- `std::vector<std::tuple<std::string, float, float>>`

### `TestResourceProvider`（测试内部）
```cpp
class TestResourceProvider final : public skresources::ResourceProvider
```
- **职责**: 用于 `Skottie_Image_Loading` 测试的资源提供者，根据资产 ID 返回不同的图片资产。

### `TestAsset`（测试内部）
```cpp
class TestAsset final : public skresources::ImageAsset
```
- **职责**: 用于 `Skottie_Image_Loading` 测试的模拟图片资产，记录所有 `getFrame()` 调用的时间戳。
- **成员**: `fMultiFrame`（是否多帧）、`fRequestedFrames`（请求帧的时间列表）

## 公共 API 函数

### 测试用例

#### `DEF_TEST(Skottie_OssFuzz8956, reporter)`
- **目的**: 回归测试，验证 OSS-Fuzz 编号 8956 发现的特定畸形 JSON 不会导致解析崩溃。
- **输入**: 包含空关键帧插值参数（`"i": {"x":[]}`）的 Lottie JSON。该输入模拟了一个具有无效关键帧插值曲线的纯色图层。
- **验证**: 解析过程不崩溃即通过（不检查返回值是否为 nullptr）。这种"不崩溃"的验证方式是模糊测试回归用例的标准做法。

#### `DEF_TEST(Skottie_Annotations, reporter)`
- **目的**: 验证 Lottie 标记（markers / annotations）的正确解析和时间归一化转换。
- **验证内容**:
  - 动画持续时间为 10 秒（(op - ip) / fr = (100 - 0) / 10 = 10）
  - 入点为 0.0，出点为 100.0（帧索引单位）
  - 两个标记被正确接收:
    - `marker_1`: 帧 25 开始，持续 25 帧 -> 归一化时间范围 [0.25, 0.50]
    - `marker_2`: 帧 75 开始，持续 0 帧 -> 归一化时间范围 [0.75, 0.75]（零持续时间标记表示时间点）
- **时间计算公式**: frame_number / (fps * duration) = normalized_time。例如帧 25 / (10fps * 10s) = 0.25

#### `DEF_TEST(Skottie_Image_Loading, reporter)`
- **目的**: 验证图片资产的加载策略。
- **测试场景 1 -- 默认加载**:
  - 单帧资产在构建时立即加载（`getFrame(0)` 被调用 1 次）
  - 多帧资产在 seek 时按需加载
  - 单帧资产在后续 seek 中不再加载
- **测试场景 2 -- 延迟加载（`kDeferImageLoading`）**:
  - 构建时不加载任何资产
  - 所有资产在 seek 时按需加载
  - 单帧资产首次 seek 后不再加载

#### `DEF_TEST(Skottie_Layer_NoType, r)`
- **目的**: 验证缺少 `"ty"` 字段的图层不会导致崩溃。
- **验证**: 解析成功（返回非空动画对象）。

## 内部实现细节

- **内联 JSON**: 所有测试用例使用内联 JSON 字符串作为输入，避免对外部文件的依赖。这使得测试完全自包含，无需文件系统访问即可运行。
- **SkMemoryStream**: 将 JSON 字符串包装为内存流（`SkMemoryStream(json, strlen(json))`），符合 `Animation::Make(SkStream*)` 的接口要求。
- **精确浮点比较**: 使用 `SkScalarNearlyZero` 和 `SkScalarNearlyEqual` 进行浮点数比较，避免浮点精度问题导致的测试不稳定。
- **多帧判断逻辑**: `TestAsset::isMultiFrame()` 控制资产是否被视为多帧，这直接影响 Skottie 的图片加载策略——单帧资产在默认模式下会被预加载，多帧资产则按需加载。
- **SkSurfaces::Raster**: 在 `TestAsset::getFrame()` 中创建 10x10 的临时 N32Premul 光栅表面作为返回图片，确保返回的是有效的 `SkImage` 对象。
- **Lottie JSON 结构**: 测试 JSON 遵循 Lottie 格式规范，包含 `"v"`（版本）、`"w"`/`"h"`（尺寸）、`"fr"`（帧率）、`"ip"`/`"op"`（入点/出点）、`"layers"`（图层数组）等必需字段。
- **标记时间归一化**: 在 `Skottie_Annotations` 测试中，标记时间从帧编号转换为归一化值：`frame_number / (fps * duration)`。帧 25 在 10fps/10s 动画中对应归一化时间 0.25。
- **lambda 工厂**: `Skottie_Image_Loading` 中的 `make_animation` lambda 封装了动画构建逻辑，使得相同的 JSON 可以用不同的配置（默认加载 vs 延迟加载）重复测试。
- **图片加载策略的精确验证**: 通过 `TestAsset::requestedFrames()` 精确追踪每次 `getFrame()` 调用的时间戳和次数，验证了不同加载模式下的行为差异：
  - 默认模式：单帧资产在构建时立即加载一次（时间为 0），多帧资产在每次 seek 时按需加载
  - 延迟模式：所有资产在首次 seek 时按需加载

## 依赖关系

- **`include/core/SkStream.h`**: `SkMemoryStream` 内存流，将内联 JSON 字符串包装为流对象
- **`include/core/SkSurface.h`**: `SkSurfaces::Raster` 创建 CPU 光栅表面，用于生成测试图片
- **`modules/skottie/include/Skottie.h`**: `Animation`, `Animation::Builder`, `MarkerObserver` 等被测试类型
- **`modules/skresources/include/SkResources.h`**: `ResourceProvider`, `ImageAsset` 资源加载接口
- **`tests/Test.h`**: `DEF_TEST` 宏定义测试用例，`REPORTER_ASSERT` 宏执行断言
- **标准库**: `<cmath>`, `<string>`, `<tuple>`, `<vector>` 用于测试数据结构和计算

## 设计模式与设计决策

- **模拟对象模式**: `TestMarkerObserver`、`TestResourceProvider`、`TestAsset` 都是模拟对象（Mock），用于验证 Skottie 的行为而非实际渲染结果。每个模拟对象只实现需要的接口方法，保持最小化。
- **回归测试**: `Skottie_OssFuzz8956` 直接来自 OSS-Fuzz 发现的问题（编号 8956），使用原始的问题输入作为测试数据，确保修复后不会再次出现该问题。这是安全敏感的模糊测试回归。
- **参数化测试**: `Skottie_Image_Loading` 通过 lambda 函数 `make_animation` 参数化测试逻辑，使相同的动画 JSON 可以在不同配置（默认加载 vs 延迟加载）下复用，避免代码重复。
- **防御性验证**: `Skottie_Layer_NoType` 验证了缺失必需字段 `"ty"`（图层类型）时的容错行为，确保解析器不会因为缺失字段而崩溃。
- **断言宏风格**: 使用 Skia 的 `REPORTER_ASSERT(reporter, condition)` 而非标准库的 assert，确保测试失败时提供清晰的报告而非直接终止进程。
- **最小化 JSON**: 每个测试用例的 JSON 只包含验证目标功能所需的最少字段，减少无关因素的干扰。例如 `Skottie_OssFuzz8956` 的 JSON 仅包含一个带畸形关键帧的纯色图层。
- **作用域隔离**: `Skottie_Image_Loading` 使用花括号作用域 `{}` 隔离默认加载和延迟加载两个测试场景，确保资产对象在场景结束时被正确释放。

## 性能考量

- 测试用例设计轻量，使用最小的 JSON 输入和 10x10 像素的测试表面，确保单个测试在毫秒级别完成。
- 不执行实际渲染（无 `render()` 调用），仅验证解析和帧跳转逻辑，避免了 GPU 上下文和表面分配的开销。
- 测试可以快速执行，适合 CI/CD 流水线中的频繁运行。所有测试均为确定性的，不依赖外部资源。
- 内联 JSON 字符串避免了文件 I/O，进一步减少了测试执行时间。

## 测试覆盖的功能点

| 测试用例 | 覆盖功能 | 验证方式 |
|---------|---------|---------|
| Skottie_OssFuzz8956 | JSON 解析容错 | 不崩溃 |
| Skottie_Annotations | 标记解析和时间归一化 | 值精确比较 |
| Skottie_Image_Loading | 图片加载策略 | 调用次数追踪 |
| Skottie_Layer_NoType | 缺失字段容错 | 返回非空 |

## 相关文件

- `modules/skottie/include/Skottie.h` -- 被测试的公共 API（Animation, Builder, MarkerObserver）
- `modules/skottie/src/Skottie.cpp` -- 被测试的核心实现（JSON 解析、帧跳转）
- `modules/skottie/fuzz/FuzzSkottieJSON.cpp` -- 模糊测试入口，补充了随机输入的测试覆盖
- `modules/skresources/include/SkResources.h` -- ResourceProvider 和 ImageAsset 接口
- `tests/Test.h` -- Skia 测试框架（DEF_TEST, REPORTER_ASSERT 宏）
- `include/core/SkStream.h` -- SkMemoryStream 内存流
- `include/core/SkSurface.h` -- SkSurfaces::Raster 用于创建测试图片
