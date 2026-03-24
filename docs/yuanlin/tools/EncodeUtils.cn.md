# EncodeUtils

> 源文件：tools/EncodeUtils.h, tools/EncodeUtils.cpp

## 概述

`EncodeUtils` 是 Skia 工具库中提供图像编码功能的辅助模块。该模块封装了常见的图像编码操作，包括将 Bitmap 编码为 PNG 文件和生成 Base64 编码的 Data URI。Data URI 功能特别适合在日志和测试报告中嵌入图像，无需额外的文件管理。这些工具函数广泛用于测试失败时的图像输出和调试场景。

## 架构位置

- 位于 `tools/` 目录
- 在 `ToolUtils` 命名空间中
- 使用 `SkPngEncoder` 进行 PNG 编码
- 使用 `SkBase64` 进行 Base64 编码
- 主要服务于测试和调试工具

## 主要类与结构体

无类定义，提供三个实用函数。

### BitmapToBase64DataURI

```cpp
bool BitmapToBase64DataURI(const SkBitmap& bitmap, SkString* dst)
```
- **功能**：将 Bitmap 编码为 Base64 Data URI
- **参数**：
  - `bitmap`: 源位图
  - `dst`: 输出 URI 字符串
- **返回值**：成功返回 `true`
- **输出格式**：`data:image/png;base64,<base64-data>`
- **限制**：最大 1MB（防止日志溢出）

### EncodeImageToPngFile (Bitmap)

```cpp
bool EncodeImageToPngFile(const char* path, const SkBitmap& src)
```
- **功能**：将 Bitmap 编码并保存为 PNG 文件
- **参数**：
  - `path`: 输出文件路径
  - `src`: 源位图
- **返回值**：成功返回 `true`

### EncodeImageToPngFile (Pixmap)

```cpp
bool EncodeImageToPngFile(const char* path, const SkPixmap& src)
```
- **功能**：将 Pixmap 编码并保存为 PNG 文件
- **参数**：
  - `path`: 输出文件路径
  - `src`: 源像素图
- **返回值**：成功返回 `true`

## 内部实现细节

### Base64 Data URI 生成

**优化编码**：
```cpp
SkPngEncoder::Options options;
options.fFilterFlags = SkPngEncoder::FilterFlag::kAll;  // 所有过滤器
options.fZLibLevel = 9;  // 最高压缩级别
```
最小化 PNG 大小，适合嵌入日志。

**大小限制**：
```cpp
static const size_t kMaxBase64Length = 1024 * 1024;
if (len > kMaxBase64Length) {
    dst->printf("Encoded image too large (%u bytes)", ...);
    return false;
}
```
防止巨大图像填满日志系统。

**编码流程**：
1. 从 Bitmap 提取 Pixmap
2. 编码为 PNG（高压缩）
3. Base64 编码
4. 添加 Data URI 前缀

### PNG 文件编码

```cpp
bool EncodeImageToPngFile(const char* path, const SkPixmap& src) {
    SkFILEWStream file(path);
    return file.isValid() && SkPngEncoder::Encode(&file, src, {});
}
```
- 使用文件写入流
- 默认 PNG 编码选项（平衡质量和大小）
- 验证文件流有效性

## 依赖关系

**Skia 核心**：
- `include/core/SkBitmap.h`
- `include/core/SkPixmap.h`
- `include/core/SkStream.h`
- `include/encode/SkPngEncoder.h`

**编码工具**：
- `src/base/SkBase64.h` - Base64 编码

## 设计模式与设计决策

### 外观模式
简化 PNG 编码和 Base64 转换的复杂操作。

### 关键决策
1. **高压缩 Data URI**：牺牲编码速度换取更小体积
2. **大小限制**：防止日志系统过载
3. **重载函数**：支持 Bitmap 和 Pixmap 两种输入
4. **错误消息**：失败时提供详细错误信息

## 性能考量

### Base64 编码开销
- PNG 编码时间：取决于图像大小和压缩级别 9
- Base64 编码：约 33% 数据膨胀
- 适合小图像（< 1024×1024）
- 不适合频繁调用或大图像

### 文件编码
- 默认编码选项，平衡速度和大小
- 适合测试输出和快照保存

## 相关文件

- `include/encode/SkPngEncoder.h` - PNG 编码器
- `src/base/SkBase64.h` - Base64 编码
- `tests/` - 测试失败时使用 Data URI
- `gm/` - GM 测试输出
