# chrome_fuzz - Chrome 图像滤镜模糊测试工具

> 源文件: `tools/chrome_fuzz.cpp`

## 概述

`chrome_fuzz` 是一个为 Chromium 设计的模糊测试工具,用于安全地反序列化和测试 SkImageFilter。它读取序列化的滤镜数据,使用验证反序列化确保无内存安全问题,然后尝试使用该滤镜进行实际绘制。

## 架构位置

属于 Skia 安全测试工具,配合 Cluster-Fuzz 使用。

## 公共 API 函数

- **`read_test_case()`**: 从文件读取测试数据
- **`run_test_case()`**: 验证反序列化并尝试绘制
- **`read_and_run_test_case()`**: 组合读取和运行
- **`main()`**: 处理命令行参数中的所有测试文件

## 内部实现细节

- 使用 `SkValidatingDeserializeImageFilter` 安全反序列化
- 在 24x24 像素的位图上测试滤镜渲染
- 输出 `#EOF` 标记帮助 Cluster-Fuzz 区分成功运行和崩溃

## 依赖关系

- `SkFlattenableSerialization.h` - 验证反序列化
- `include/core/SkImageFilter.h` - 图像滤镜

## 设计模式与设计决策

- **防御性反序列化**: 使用验证版本避免恶意输入导致的内存问题
- **EOF 标记**: Cluster-Fuzz 标准协议

## 性能考量

设计为快速运行大量模糊测试用例,单个用例开销极小。

## 相关文件

- Chromium 的 Cluster-Fuzz 基础设施
