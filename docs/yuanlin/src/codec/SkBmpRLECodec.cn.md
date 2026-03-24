# SkBmpRLECodec - BMP RLE 压缩解码器

> 源文件: `src/codec/SkBmpRLECodec.h`, `src/codec/SkBmpRLECodec.cpp`

## 概述

`SkBmpRLECodec` 实现了 BMP 图像文件中 RLE（Run-Length Encoding，游程编码）压缩格式的解码。RLE 压缩是 BMP 格式特有的一种简单压缩方式，支持 RLE4（4 位）、RLE8（8 位）和 RLE24（24 位）三种变体。与逐行解码不同，RLE 解码本质上是全图解码，因为 RLE 流可以跳过任意数量的行和像素。

## 架构位置

```
SkCodec (基类)
  └── SkBmpCodec (BMP 基类)
        └── SkBmpRLECodec
              └── SkBmpRLESampler (内部采样器类)
```

该类只能通过 `SkBmpCodec::MakeFromStream` 创建。

## 主要类与结构体

### `SkBmpRLECodec`
- 继承自 `SkBmpCodec`
- 维护 4096 字节的流缓冲区 (`fStreamBuffer`)
- 支持颜色表 (`fColorTable`)
- 管理 RLE 解码状态（当前字节位置、采样率、跳行计数）

### `SkBmpRLESampler` (内部类)
- 继承自 `SkSampler`
- 委托 `setSampleX` 和 `fillWidth` 给 `SkBmpRLECodec`
- 在需要时延迟创建

## 公共 API 函数

### 构造函数
接受编码信息、流、位深度、颜色数量、每色字节数、像素偏移和行顺序等参数。

### 采样接口
- `setSampleX(int)`: 设置 X 方向采样率
- `fillWidth()`: 返回采样后的宽度

## 内部实现细节

### RLE 解码状态机 (`decodeRLE`)
核心解码循环读取两字节为一组：
- **转义模式** (`flag == 0`):
  - `task == 0` (EOL): 行结束，移到下一行
  - `task == 1` (EOF): 文件结束
  - `task == 2` (DELTA): 跳过 dx、dy 个像素/行
  - 其他: 绝对模式，逐个读取 `task` 个像素
- **运行模式** (`flag > 0`):
  - 重复 `task` 值 `flag` 次
  - RLE24: 读取额外 2 字节构成完整颜色
  - RLE4: 高低 4 位交替使用

### 颜色表处理 (`createColorTable`)
- 从流中读取颜色表（最多 256 色）
- 使用 `ChoosePackColorProc` 根据目标颜色类型选择打包函数
- 未使用的颜色表条目填充为黑色（防止越界访问）

### 像素设置
- `setPixel(...)`: 使用颜色表索引设置单个像素
- `setRGBPixel(...)`: 使用 RGB 值设置单个像素（RLE24）
- 两者都检查 `SkCodecPriv::IsCoordNecessary` 以支持采样
- 支持 RGBA_8888、BGRA_8888 和 RGB_565 目标格式

### 流缓冲管理
- 使用 4096 字节固定缓冲区 (`kBufferSize`)
- `initializeStreamBuffer`: 初始读取
- `checkForMoreData`: 将剩余数据移到缓冲区头部，然后从流中读取更多数据

### 扫描行解码
- `decodeRows`: 处理背景填充和行跳过
- `fLinesToSkip`: RLE 的 DELTA 操作可能跳过多行，此字段追踪待跳过的行数
- 颜色变换通过 `applyColorXform` 在解码后进行

### 背景填充
RLE 编码允许跳过像素，因此解码前先用 `SkSampler::Fill` 将整个目标区域设为透明/黑色。

## 依赖关系

- `SkBmpCodec`: BMP 基类
- `SkSampler`: 采样基类
- `SkColorPalette`: 颜色调色板
- `SkCodecPriv`: 工具函数（坐标计算、颜色打包等）
- `SkColorData` / `SkColorPriv`: 颜色操作

## 设计模式与设计决策

### 全图解码
RLE 编码是非线性的（可以跳到任意位置），因此不能真正地逐行解码。实现上总是预填充背景，然后执行完整的 RLE 解码。

### 采样感知
RLE 解码器直接感知采样参数（`fSampleX`），在设置像素时检查坐标是否需要输出，避免了解码后再采样的开销。

### 固定大小缓冲区
使用 4096 字节的固定缓冲区，确保能容纳最大的绝对模式序列（255 * 3 + 1 = 766 字节）。

### 不支持子集
由于 RLE 编码的非线性特性，不支持子集解码。

## 性能考量

- 固定缓冲区避免了动态内存分配
- 采样检查在像素级别进行，跳过不需要的像素写入
- `checkForMoreData` 使用 `memmove` 紧凑缓冲区，减少流读取次数
- 颜色变换在整行解码完成后批量进行
- 对于 `kRGBA_F16` 目标格式，使用中间 `uint32_t` 缓冲区避免逐像素 F16 转换

## 相关文件

- `src/codec/SkBmpCodec.h` / `.cpp`: BMP 基类
- `src/codec/SkSampler.h`: 采样器基类
- `src/codec/SkColorPalette.h`: 颜色调色板
- `src/codec/SkCodecPriv.h`: 编解码器私有工具
- `src/codec/SkBmpStandardCodec.h`: BMP 标准（非压缩）编解码器
- `src/codec/SkBmpMaskCodec.h`: BMP 位掩码编解码器
