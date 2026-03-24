# FuzzSKP (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzSKP.cpp

## 概述

测试 Skia Picture (SKP) 格式的反序列化和回放。SKP 是 Skia 的专有格式,用于记录和回放绘图命令序列,广泛用于性能测试和调试。

## 架构位置

测试 `include/core/SkPicture.h` 的序列化/反序列化和回放功能。

## 主要类与结构体

### FuzzSKP 函数

```cpp
void FuzzSKP(const uint8_t *data, size_t size)
```

执行流程:
1. 从数据反序列化 Picture: `SkPicture::MakeFromData(data, size)`
2. 创建 128x160 的光栅 surface
3. 回放 Picture: `canvas->drawPicture(pic)`
4. 查询 Picture 元数据:
   - `approximateBytesUsed()`: 内存使用估计
   - `approximateOpCount()`: 操作数量

### LLVMFuzzerTestOneInput

无大小限制,接受任意长度的 SKP 数据。

## 内部实现细节

### SKP 格式

SKP 是二进制格式,包含:
- 绘图命令流
- 资源引用(图像、字体)
- 变换矩阵栈
- 裁剪区域

### 回放环境

使用固定大小 canvas(128x160)确保测试一致性。

### 鲁棒性测试

测试点:
- 格式错误的 SKP 文件
- 不完整的数据
- 恶意构造的命令序列
- 无效的资源引用

## 依赖关系

- `include/core/SkPicture.h`: Picture 接口
- `src/core/SkPictureRecord.cpp`: 录制实现
- `src/core/SkPicturePlayback.cpp`: 回放实现

## 设计模式与设计决策

### 录制-回放模式

SKP 将绘图命令记录为可回放的序列,支持:
- 延迟渲染
- 多次回放
- 性能分析

### 安全性优先

SKP 反序列化是攻击面,fuzzing 发现潜在的:
- 缓冲区溢出
- 整数溢出
- 无限循环
- 内存泄漏

## 性能考量

- **反序列化**: 解析二进制格式
- **回放**: 执行所有绘图命令
- **内存**: 大 Picture 可能消耗显著内存

## 相关文件

- `tools/viewer/SKPSlide.cpp`: SKP 查看工具
- `tools/skp/`: SKP 工具集
- `tests/PictureTest.cpp`: Picture 单元测试

该 fuzzer 自 2020 年运行,是发现 SKP 格式问题的主要工具,对 Skia 的安全性至关重要。
