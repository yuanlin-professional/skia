# SkICC

> 源文件
> - include/encode/SkICC.h
> - src/encode/SkICC.cpp

## 概述

`SkICC` 模块负责生成和编写符合 ICC(International Color Consortium)标准的颜色配置文件数据。该模块支持将 Skia 的颜色空间描述(传递函数和色域矩阵)转换为标准的 ICC profile 二进制格式,用于图像编码、颜色管理和跨设备颜色一致性保证。

模块提供了对多种颜色空间的支持,包括 sRGB、Display P3、Rec2020 等标准色域,以及 sRGB、线性、伽马 2.2、PQ(感知量化)、HLG(混合对数伽马)等传递函数。对于 HDR(高动态范围)内容,模块实现了复杂的色调映射逻辑,将 HDR 内容映射到 SDR(标准动态范围)显示设备。

## 架构位置

`SkICC` 位于 Skia 编码模块的颜色管理层:

- 位于 `include/encode/` 和 `src/encode/` 目录
- 作为编码器和颜色空间模块的桥梁
- 被图像编码器(PNG、JPEG、WebP)用于嵌入颜色配置文件
- 依赖 `skcms` 库进行底层颜色管理计算
- 与 `SkColorSpace` 协同工作,将 Skia 颜色空间转换为 ICC 标准

## 主要类与结构体

### ICCHeader

ICC 配置文件头结构,包含 128 字节的标准头信息:

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `size` | `uint32_t` | 配置文件总大小(计算得出) |
| `version` | `uint32_t` | ICC 版本(4.3 或 4.4) |
| `profile_class` | `uint32_t` | 配置文件类别(Display) |
| `data_color_space` | `uint32_t` | 数据颜色空间(RGB) |
| `pcs` | `uint32_t` | 配置文件连接空间(XYZ 或 LAB) |
| `creation_date_*` | `uint16_t` | 创建日期时间戳 |
| `signature` | `uint32_t` | ACSP 签名 |
| `illuminant_X/Y/Z` | `uint32_t` | D50 标准光源 XYZ 值 |
| `tag_count` | `uint32_t` | 标签数量 |

### 常量定义

**色域 CICP 编码:**

| 常量 | 值 | 说明 |
|------|---|------|
| `kCICPPrimariesSRGB` | 1 | sRGB/Rec.709 色域 |
| `kCICPPrimariesP3` | 12 | Display P3 色域 |
| `kCICPPrimariesRec2020` | 9 | Rec.2020 色域 |

**传递函数 CICP 编码:**

| 常量 | 值 | 说明 |
|------|---|------|
| `kCICPTrfnSRGB` | 1 | sRGB 传递函数 |
| `kCICPTrfn2Dot2` | 4 | 伽马 2.2 |
| `kCICPTrfnLinear` | 8 | 线性传递函数 |
| `kCICPTrfnPQ` | 16 | PQ (Perceptual Quantizer) |
| `kCICPTrfnHLG` | 18 | HLG (Hybrid Log-Gamma) |

**编码常量:**

| 常量 | 值 | 说明 |
|------|---|------|
| `kOne16CurveType` | 0xFFFF | curveType 中 1.0 对应的 16 位值 |
| `kOne16XYZ` | 0x8000 | XYZ 编码中 1.0 对应的 16 位值 |
| `kD50_x/y/z` | 0.9642/1.0/0.8249 | D50 标准光源坐标 |
| `kToneMapInputMax` | 1000/203 | 色调映射输入最大值(约 4.926) |

## 公共 API 函数

### SkWriteICCProfile (传递函数版本)

```cpp
sk_sp<SkData> SkWriteICCProfile(const skcms_TransferFunction& fn,
                                const skcms_Matrix3x3& toXYZD50);
```

根据传递函数和色域矩阵生成 ICC 配置文件:

- **参数:**传递函数和到 XYZD50 的转换矩阵
- **返回:**包含完整 ICC 配置文件数据的 `SkData`
- **支持:**sRGB、线性、伽马、PQ、HLG 等多种传递函数
- **HDR 处理:**自动为 PQ 和 HLG 生成 A2B/B2A 标签和色调映射

### SkWriteICCProfile (配置文件版本)

```cpp
sk_sp<SkData> SkWriteICCProfile(const skcms_ICCProfile* profile,
                                const char* description);
```

根据完整的 ICC 配置文件结构生成二进制数据:

- **参数:**skcms ICC 配置文件结构和描述文本
- **返回:**完整的 ICC 配置文件二进制数据
- **功能:**支持复杂的配置文件(A2B/B2A、CLUT、自定义曲线)

### SkICCFloatXYZD50ToGrid16Lab

```cpp
void SkICCFloatXYZD50ToGrid16Lab(const float* float_xyz, uint8_t* grid16_lab);
```

将浮点 XYZD50 值转换为 16 位 grid_16_lab 格式:

- **输入:**3 个浮点 XYZ 值
- **输出:**写入 6 字节的 grid_16_lab 数据
- **用途:**填充 skcms_A2B 和 skcms_B2A 结构的 grid_16 成员

### SkICCFloatToTable16

```cpp
void SkICCFloatToTable16(const float f, uint8_t* table_16);
```

将浮点值转换为 16 位 table_16 格式:

- **输入:**浮点值(0.0-1.0)
- **输出:**写入 2 字节数据
- **用途:**填充 skcms_Curve 结构的 table_16 成员

## 内部实现细节

### ICC 配置文件结构

一个完整的 ICC 配置文件包含:

1. **128 字节头部:**版本、类别、颜色空间等元信息
2. **标签表:**标签数量和每个标签的偏移/大小
3. **标签数据:**实际的颜色数据(曲线、矩阵、CLUT 等)

### 标签类型

模块生成以下标签:

| 标签 | 说明 |
|------|------|
| `rXYZ/gXYZ/bXYZ` | RGB 三原色的 XYZ 坐标 |
| `wtpt` | 白点(D50) |
| `rTRC/gTRC/bTRC` | RGB 三通道传递曲线 |
| `cicp` | CICP 颜色编码参数(ICC 4.4) |
| `A2B0` | 设备到 PCS 的转换(用于 HDR) |
| `B2A0` | PCS 到设备的转换(用于 HDR) |
| `desc` | 配置文件描述 |
| `cprt` | 版权信息 |

### HDR 色调映射

对于 PQ 和 HLG 传递函数,模块实现复杂的色调映射:

**色调映射曲线:**
```
y = (1 + a*x) / (1 + b*x)
```
其中:
- `a = kToneMapOutputMax / (kToneMapInputMax^2)` ≈ 0.0412
- `b = 1 / kToneMapOutputMax` = 1
- 将 [0, 4.926] 范围映射到 [0, 1]

**A2B 转换流程:**
1. **输入曲线:**PQ/HLG EOTF → 线性光(缩放到 1000/203)
2. **3D LUT:**跨通道色调映射和 HLG OOTF
3. **矩阵:**色域转换到 XYZD50
4. **输出曲线:**线性(恒等)

**HLG 特殊处理:**
- 先应用逆 OETF
- 再应用逐通道 OOTF: `c *= c^0.2`
- 在 LUT 中应用跨通道 OOTF: `Y^0.2`,其中 `Y = 0.2627R + 0.6780G + 0.0593B`

### 数据编码

**XYZ 值编码:**
- 使用 S15.16 定点格式
- 通过 `float_round_to_fixed` 进行四舍五入转换
- 大端序(Big-Endian)存储

**曲线编码:**
- 参数曲线:使用 ParaCurveType 存储 7 参数传递函数
- 查找表:使用 CurveType 存储 16 位查找表
- 指数曲线:对于简单伽马使用 Exponential 类型

**CLUT 编码:**
- 3D 查找表,每维最多 255 个网格点
- 对于 HDR,使用 11x11x11 网格
- 16 位精度,大端序存储

### 配置文件描述生成

描述字符串优先级:
1. **显式 sRGB:**"sRGB"
2. **命名空间:**如 "Display P3 Gamut with PQ Transfer"
3. **MD5 哈希:**如 "Google/Skia/[hash]"

### 标签优化

相同内容的标签共享数据:
- gTRC 和 bTRC 可以引用 rTRC 的数据
- 通过空 `SkData` 表示复用前一个标签

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `skcms` | 底层颜色科学计算库 |
| `SkColorSpace` | Skia 颜色空间抽象 |
| `SkData` | 不可变数据容器 |
| `SkMD5` | 哈希计算(用于描述) |
| `SkEndian` | 字节序转换 |
| `SkStream` | 动态内存写入流 |
| `SkFixed` | 定点数转换 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkPngEncoder` | 嵌入 ICC 配置文件到 PNG |
| `SkJpegEncoder` | 嵌入 ICC 配置文件到 JPEG |
| `SkWebpEncoder` | 嵌入 ICC 配置文件到 WebP |
| 颜色管理工具 | 导出颜色配置文件 |

## 设计模式与设计决策

### 数据驱动设计

使用配置结构体(skcms_ICCProfile)驱动生成:
- 灵活支持不同复杂度的配置文件
- 统一的生成逻辑处理各种情况
- 易于扩展新的标签类型

### 两层 API 设计

提供简化版和完整版两个接口:
- **简化版:**只需传递函数和矩阵,自动处理常见情况
- **完整版:**接受完整配置文件结构,支持高级功能
- 满足不同用户的需求

### 延迟计算

配置文件大小在写入时计算:
- 先收集所有标签数据
- 计算偏移和总大小
- 一次性写入完整数据
- 避免多次遍历和调整

### HDR 特殊处理

对 PQ 和 HLG 使用 A2B/B2A 而非简单曲线:
- 标准 TRC 标签无法表达复杂的色调映射
- A2B/B2A 提供完整的设备-PCS 转换
- 3D LUT 支持跨通道色调映射
- 确保 HDR 内容在 SDR 设备上正确显示

### CICP 标签支持

添加 CICP(Coding-Independent Code Points)标签:
- 提供紧凑的颜色编码描述
- 支持 ICC 4.4 标准
- 便于与视频标准互操作

## 性能考量

### 内存效率

- **流式写入:**使用 `SkDynamicMemoryWStream` 避免预分配大缓冲区
- **数据共享:**相同标签复用数据,减少存储
- **按需生成:**只生成必要的标签

### 计算优化

- **预计算常量:**色调映射参数在编译时计算
- **查找表缓存:**TRC 和 LUT 数据预先计算并存储
- **浮点精度:**使用 `float` 进行计算,转换时才用定点

### 大小优化

- **参数曲线优先:**对于简单传递函数使用参数形式而非查找表
- **合理的 LUT 大小:**HDR 使用 11x11x11(3993 点),平衡精度和大小
- **标签对齐:**4 字节对齐,兼容性和性能兼顾

### HDR 处理精度

- **65 点 TRC:**足够精度的输入曲线
- **11x11x11 LUT:**色调映射的合理精度
- **16 位编码:**保持足够的数值精度

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/encode/SkICC.h` | 公共接口头文件 |
| `src/encode/SkICC.cpp` | ICC 生成实现 |
| `src/encode/SkICCPriv.h` | 内部辅助定义 |
| `modules/skcms/skcms.h` | skcms 颜色管理库 |
| `include/core/SkColorSpace.h` | Skia 颜色空间 |
| `include/core/SkData.h` | 数据容器 |
| `src/core/SkMD5.h` | MD5 哈希 |
| `src/base/SkEndian.h` | 字节序转换 |
| `include/encode/SkPngEncoder.h` | PNG 编码器(使用方) |
| `include/encode/SkJpegEncoder.h` | JPEG 编码器(使用方) |
