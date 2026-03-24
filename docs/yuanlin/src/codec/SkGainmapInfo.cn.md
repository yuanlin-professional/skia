# SkGainmapInfo - ISO 21496-1 增益图信息解析与序列化

> 源文件: `src/codec/SkGainmapInfo.cpp`

## 概述

`SkGainmapInfo.cpp` 实现了 ISO 21496-1 标准定义的增益图（Gainmap）元数据的解析和序列化功能。增益图是 HDR 图像技术的核心组成部分，它描述了如何将 SDR 基础图像转换为 HDR 图像（或反向转换）。该文件处理增益图的版本信息、通道配置（单通道/多通道）、头部余量（headroom）、增益范围、gamma 校正和偏移量等参数，所有数据均以大端有理数格式存储。

## 架构位置

该文件位于 `src/codec/` 目录下，属于 Skia 的 HDR 图像处理子系统。它被 JPEG 和其他图像格式的解码器调用，用于解析图像中嵌入的增益图元数据。解析后的 `SkGainmapInfo` 结构体会被增益图渲染管线使用，以在运行时根据显示器能力动态合成 HDR 效果。

## 主要类与结构体

该文件实现 `SkGainmapInfo` 类的方法（类定义在 `include/private/SkGainmapInfo.h` 中）。

## 公共 API 函数

### `SkGainmapInfo::ParseVersion(const SkData*)`
解析并验证 ISO 21496-1 版本信息。
- 要求 minimum_version 为 0
- writer_version 无限制

### `SkGainmapInfo::Parse(const SkData*, SkGainmapInfo&)`
完整解析 ISO 21496-1 增益图元数据。
- 解析版本、标志位、头部余量、通道参数

### `SkGainmapInfo::SerializeVersion()`
序列化版本信息（minimum_version=0, writer_version=0）。

### `SkGainmapInfo::serialize() const`
将增益图信息序列化为 ISO 21496-1 二进制格式。

### `SkGainmapInfo::isUltraHDRv1Compatible() const`
检查当前信息是否与 UltraHDR v1 格式兼容。
- 不支持 HDR 基础图像
- 不支持非基础色彩空间的增益图数学

## 内部实现细节

### 有理数编解码
- `write_rational_be(stream, float)`: 将浮点数写为大端有符号有理数（分子/分母）
- `write_positive_rational_be(stream, float)`: 写为无符号有理数
- `read_rational_be(stream, float*)` / `read_positive_rational_be(stream, float*)`: 读取有理数
- 分母策略：绝对值 > 1 时使用 `0x1000`，否则使用 `0x10000000`，平衡精度和范围

### ISO 增益图解析流程
`read_iso_gainmap_info()`:
1. 解析版本（minimum_version 必须为 0）
2. 读取标志位：`kIsMultiChannelMask`(bit 7) 和 `kUseBaseColourSpaceMask`(bit 6)
3. 读取基础和备选头部余量（无符号有理数）
4. 按通道数（1 或 3）读取：gainMapMin、gainMapMax、gamma、baseOffset、altrOffset
5. 转换为 `SkGainmapInfo` 格式：
   - 头部余量通过 `exp2()` 从对数域转为线性域
   - 增益比率通过 `exp2()` 转换
   - gamma 取倒数
   - 根据 baseHdrHeadroom 与 altrHdrHeadroom 的大小关系确定基础图像类型（SDR 或 HDR）

### 序列化流程
`serialize()`:
1. 写入版本（0, 0）
2. 确定是否为单通道（所有参数的 RGB 分量相同）
3. 写入标志位
4. 按基础图像类型写入头部余量（log2 域）
5. 按通道写入增益参数（log2 域）

### 单通道检测
`is_single_channel(SkColor4f c)`: 检查 `fR == fG && fG == fB`，决定使用 1 通道还是 3 通道格式。

## 依赖关系

- `include/private/SkGainmapInfo.h`: 类定义
- `include/core/SkColor.h`: `SkColor4f`
- `include/core/SkData.h`, `SkStream.h`: 数据和流
- `src/base/SkEndian.h`: 字节序工具
- `src/codec/SkCodecPriv.h`: `SkCodecPrintf` 调试输出
- `src/core/SkStreamPriv.h`: 大端读写辅助函数

## 设计模式与设计决策

1. **对数/线性域转换**: ISO 规范使用对数域（以 2 为底的头部余量），而 `SkGainmapInfo` 内部使用线性域。解析时通过 `exp2` 转换，序列化时通过 `log2` 反转。

2. **有理数精度策略**: 根据数值范围动态选择分母（`0x1000` 或 `0x10000000`），在精度和可表示范围间取得平衡。

3. **SDR/HDR 自动检测**: 通过比较 baseHdrHeadroom 和 altrHdrHeadroom 的大小自动确定基础图像类型。

4. **UltraHDR 兼容性**: 提供显式的兼容性检查方法，方便与 Android UltraHDR 生态系统集成。

## 性能考量

- **紧凑二进制格式**: 单通道模式仅序列化 1 组参数，减少数据量
- **流式读写**: 使用 `SkDynamicMemoryWStream` 和 `SkMemoryStream` 进行高效的流式操作
- **避免冗余通道**: 当三个通道的参数相同时，自动使用单通道模式

## 相关文件

- `include/private/SkGainmapInfo.h`: 类定义
- `src/codec/SkXmp.cpp`: XMP 元数据中的增益图信息（Adobe/Apple 格式）
- `src/codec/SkJpegConstants.h`: ISO 增益图标记和签名
- `src/codec/SkHdrMetadata.cpp`: HDR 元数据管理
