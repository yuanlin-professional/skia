# SkHdrAgtmParse - AGTM 二进制语法解析与序列化

> 源文件: `src/codec/SkHdrAgtmParse.cpp`

## 概述

`SkHdrAgtmParse.cpp` 实现了 SMPTE ST 2094-50 标准中定义的自适应全局色调映射（Adaptive Global Tone Map, AGTM）元数据的二进制解析和序列化功能。AGTM 是 HDR 图像的色调映射描述符，定义了如何将 HDR 内容适配到不同显示头部余量（headroom）的设备上。该文件包含两个层次的处理：底层的二进制语法元素解析/序列化（对应 SMPTE 规范的 Annex C.2），以及语法元素与高层元数据项之间的语义转换（对应 Annex C.3）。

## 架构位置

该文件位于 `src/codec/` 目录下，属于 Skia 的 HDR 元数据处理子系统。它实现了 `skhdr::AdaptiveGlobalToneMap` 类的 `parse()` 和 `serialize()` 方法，这些方法被 HDR 图像的编码器和解码器调用。解析出的 AGTM 数据会被 `SkHdrAgtm.cpp` 中的色调映射算法使用。

## 主要类与结构体

### `AgtmSyntax`（匿名命名空间内）
AGTM 二进制格式的完整语法元素集合，对应 SMPTE ST 2094-50 Annex C.2 中定义的所有字段。

**常量**:
- `kNumChromaticityValues = 8`: 色度坐标值数量（RGBW 各 XY）
- `kMaxNumAlternateImages = 4`: 最大备选图像数
- `kMaxNumControlPoints = 32`: 增益曲线最大控制点数
- `kNumMixCoefficients = 6`: 混合系数数量（R,G,B,Max,Min,Component）

**语法元素字段**:
- `application_version`, `minimum_application_version`: 应用版本信息（3 位）
- `has_custom_hdr_reference_white_flag`, `has_adaptive_tone_map_flag`: 功能标志
- `hdr_reference_white`: HDR 参考白电平
- `baseline_hdr_headroom`: 基线 HDR 头部余量
- `use_reference_white_tone_mapping_flag`: 是否使用参考白色调映射
- `num_alternate_images`: 备选图像数量
- `gain_application_space_chromaticities_flag`: 增益应用色彩空间类型
- `gain_application_space_chromaticities[]`: 自定义色度坐标
- `alternate_hdr_headrooms[]`: 各备选图像的头部余量
- `component_mixing_type[]`, `component_mixing_coefficient[][]`: 分量混合参数
- `gain_curve_*`: 增益曲线控制点参数

### `BitfieldReader` / `BitfieldWriter`（匿名命名空间内）
位域读写辅助类，处理单字节内位域的按位读取和写入。

## 公共 API 函数

### `skhdr::AdaptiveGlobalToneMap::parse(const SkData*)`
从二进制数据解析 AGTM 元数据。
- 返回 `true` 表示成功，`false` 表示数据无效
- 解析后填充 `fHdrReferenceWhite`、`fHeadroomAdaptiveToneMap` 等字段
- 最终调用 `AgtmHelpers::Validate` 验证规范约束

### `skhdr::AdaptiveGlobalToneMap::serialize() const`
将 AGTM 元数据序列化为二进制数据。
- 返回 `sk_sp<SkData>`，失败时返回 `nullptr`
- 序列化前先调用 `AgtmHelpers::Validate` 验证合法性
- 支持将 RWTMO 等效的映射自动标记为 `use_reference_white_tone_mapping_flag`

## 内部实现细节

### 数值转换函数
- `float_to_uint16(f, clamp_min, clamp_max, offset, scale)`: 浮点数转 uint16，支持缩放、偏移和钳位
- `uint16_to_float(v, clamp_min, clamp_max, offset, scale)`: uint16 转浮点数，`float_to_uint16` 的逆运算

### 语法解析层级（Annex C.2）
按层级结构解析：
1. `parse_application_info()`: 解析应用信息（版本号 + 色彩体积变换）
2. `parse_color_volume_transform()`: 解析 HDR 参考白 + 自适应色调映射
3. `parse_adaptive_tone_map()`: 解析基线头部余量、备选图像列表及其参数
4. `parse_component_mixing()`: 解析分量混合参数（4 种预设 + 自定义系数）
5. `parse_gain_curve()`: 解析增益曲线控制点（X、Y、theta/PCHIP 斜率）

### 语义转换层级（Annex C.3）
解析完语法元素后进行语义转换：
- **C.3.3**: HDR 参考白从 uint16 转浮点数（scale=5.0）
- **C.3.4**: 基线头部余量从 uint16 转浮点数（scale=10000.0）；RWTMO 检测
- **C.3.5**: 增益应用空间色度坐标（0=Rec709, 1=P3, 2=Rec2020, 3=自定义）
- **C.3.6**: 分量混合类型（0=maxRGB, 1=component, 2=均衡混合, 3=自定义系数；系数归一化）
- **C.3.7**: 增益曲线控制点（X/Y/theta 转换为浮点值和斜率；支持 PCHIP 自动斜率）

### 序列化逻辑
`serialize()` 执行与解析相反的流程：
1. 验证元数据有效性
2. 检测是否可以使用 RWTMO 简化表示
3. 将浮点参数转回 uint16 语法元素
4. 按 Annex C.2 的结构写入二进制流

### 增益曲线符号处理
解析时，如果 `baseline_hdr_headroom < alternate_hdr_headrooms[a]`（即备选图像的头部余量更大），Y 值为正（增益）；否则为负（衰减）。序列化时使用相同的符号约定。

### RETURN_ON_FALSE 宏
简化错误处理的宏，在解析失败时输出调试信息并返回 `false`。

## 依赖关系

- `include/core/SkStream.h`: 内存流读写
- `include/private/base/SkFloatingPoint.h`: `SK_FloatPI` 常量
- `src/codec/SkHdrAgtmPriv.h`: AGTM 辅助函数（`PopulateSlopeFromPCHIP`, `PopulateUsingRwtmo`, `Validate`）
- `src/core/SkStreamPriv.h`: 大端 16 位读写（`ReadU16BE`, `WriteU16BE`）

## 设计模式与设计决策

1. **两层架构**: 语法层（二进制格式）和语义层（元数据含义）分离，使得格式变更和语义扩展互不影响。

2. **宏简化错误处理**: `RETURN_ON_FALSE` 宏在保持简洁性的同时提供调试诊断。

3. **预设值优化**: 4 种预设的分量混合类型（type 0-2）避免了序列化 6 个系数，节省空间。

4. **PCHIP 斜率压缩**: 支持 PCHIP 自动斜率计算，进一步减少需要存储的控制点参数。

5. **RWTMO 自动检测**: 序列化时自动检测是否等效于 RWTMO，使用单标志位替代完整的映射参数。

## 性能考量

- **单遍解析**: 二进制数据在单次顺序读取中完成解析
- **紧凑二进制格式**: 使用位域和 uint16 编码，最小化存储开销
- **零分配解析**: `AgtmSyntax` 在栈上分配，解析过程不涉及堆内存分配
- **编译时静态断言**: 验证常量与上层结构体的一致性

## 相关文件

- `src/codec/SkHdrAgtmPriv.h`: AGTM 辅助函数声明
- `src/codec/SkHdrAgtm.cpp`: AGTM 色调映射评估和着色器实现
- `include/private/SkHdrMetadata.h`: HDR 元数据公共接口
- `src/codec/SkHdrMetadata.cpp`: HDR 元数据序列化
