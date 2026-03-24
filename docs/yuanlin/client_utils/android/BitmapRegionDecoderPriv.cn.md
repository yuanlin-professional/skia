# BitmapRegionDecoderPriv.h - Android 位图区域解码器私有工具

> 源文件: `client_utils/android/BitmapRegionDecoderPriv.h`

## 概述

本文件定义了 Android `BitmapRegionDecoder` 的私有辅助工具，提供了图像子集（subset）坐标校正功能。核心函数 `adjust_subset_rect` 接收原始图像尺寸和请求的解码子集区域，自动校正越界坐标，并计算输出位图中的偏移位置。该工具确保区域解码操作即使在子集部分超出图像边界时也能正确执行。

## 架构位置

该文件位于 `client_utils/android/` 目录下，是 Skia 面向 Android Framework 提供的客户端工具之一。它被 `SkBitmapRegionDecoder`（Android 的 `BitmapRegionDecoder` Java API 的底层实现）使用，处理图像区域解码时的坐标校正逻辑。

## 主要类与结构体

### SubsetType 枚举
- **`kFullyInside_SubsetType`**: 请求的子集完全在图像范围内
- **`kPartiallyInside_SubsetType`**: 请求的子集部分超出图像范围
- **`kOutside_SubsetType`**: 请求的子集完全在图像范围外

## 公共 API 函数

- **`adjust_subset_rect(const SkISize& imageDims, SkIRect* subset, int* outX, int* outY)`**: 校正子集坐标的内联函数
  - **输入**: `imageDims`（原始图像尺寸）、`subset`（请求的子集区域，同时作为输出）
  - **输出**: `subset`（校正后的有效解码区域）、`outX`/`outY`（子集在输出位图中的偏移量）
  - **返回值**: `SubsetType` 枚举，指示子集与图像的空间关系

## 内部实现细节

### 坐标校正逻辑

1. **左上角裁剪**: 将负坐标的左/上边界裁剪到 0（`std::max(0, subset->fLeft)`）
2. **输出偏移计算**: 如果输入偏移为负，解码结果需要在输出位图中偏移放置（`*outX = left - subset->fLeft`）
3. **宽高限制**: 确保解码范围不超过图像边缘和子集边缘（`std::min` 约束）
4. **完全越界检测**: 如果校正后的宽或高 <= 0，返回 `kOutside_SubsetType`
5. **部分越界检测**: 如果输出偏移不为零或校正后的尺寸与原请求不同，返回 `kPartiallyInside_SubsetType`

### 内联实现

函数声明为 `inline`，因为它是纯计算逻辑，代码体积小，适合内联以避免函数调用开销。

## 依赖关系

- **`include/core/SkRect.h`**: `SkIRect` 和 `SkISize` 类型定义

## 设计模式与设计决策

- **三态返回值**: `SubsetType` 枚举清晰地表达了三种可能的空间关系，调用者可据此决定后续行为
- **输入/输出参数复用**: `subset` 参数既是输入也是输出，避免额外的结构体分配
- **防御性坐标处理**: 允许负坐标输入（Android API 不限制子集坐标范围），内部自动处理边界情况
- **头文件实现**: 作为纯内联函数实现在头文件中，无需对应的 .cpp 文件

## 性能考量

- 纯整数算术操作，无浮点运算
- `inline` 声明消除了函数调用开销
- 无内存分配，所有操作在调用者提供的参数上就地执行
- 适合在解码热路径中调用
- `std::max` 和 `std::min` 调用在现代编译器上会被优化为条件移动指令

### 使用场景示例

典型的调用模式如下：
1. Android Framework 收到区域解码请求（包含子集矩形）
2. 调用 `adjust_subset_rect` 校正坐标
3. 根据返回的 `SubsetType` 决定后续行为：
   - `kFullyInside`: 直接解码到输出位图
   - `kPartiallyInside`: 先清零输出位图，然后解码到指定偏移位置
   - `kOutside`: 返回空位图或错误

### 边界条件处理

函数正确处理了以下边界条件：
- 子集完全在图像左侧或上方（负坐标且绝对值大于子集宽高）
- 子集跨越图像边界（一半在内一半在外）
- 子集完全包含图像（子集比图像大）
- 子集与图像完全重合

## 相关文件

- `client_utils/android/BRDAllocator.h` - 区域解码器的内存分配接口
- `src/android/SkBitmapRegionCodec.cpp` - 区域解码器实现
- `include/codec/SkAndroidCodec.h` - Android 编解码器接口
- `include/core/SkRect.h` - 矩形类型定义
