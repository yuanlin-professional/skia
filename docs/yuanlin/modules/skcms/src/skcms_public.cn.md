# skcms_public - skcms 颜色管理公共 API

> 源文件: `modules/skcms/src/skcms_public.h`

## 概述

skcms_public.h 定义了 skcms 颜色管理系统的全部公共 API。skcms 是一个轻量级的 ICC 颜色配置文件解析和颜色转换库，支持解析 ICC v2/v4 配置文件、各种传输函数（sRGB/PQ/HLG）、色域矩阵变换、A2B/B2A 多维查找表、以及覆盖数十种像素格式的高性能颜色空间转换。该文件是 skcms 对外的唯一接口。

## 架构位置

skcms_public.h 是 skcms 库的公共 API 层，位于整个 skcms 架构的最顶层。它定义了所有用户可见的类型和函数，下层由 skcms_Transform.h、Transform_inl.h 和 skcms_internals.h 提供实现。Skia 通过此 API 进行所有颜色空间相关操作。

## 主要类与结构体

### `skcms_Matrix3x3` / `skcms_Matrix3x4`
行主序矩阵类型，分别用于色域变换（3x3）和带平移的仿射变换（3x4）。

### `skcms_TransferFunction`
7 参数分段传输函数，表示编码值到线性值的映射：
- 线性段: `sign(encoded) * (c*|encoded| + f)`, 当 `|encoded| < d`
- 指数段: `sign(encoded) * ((a*|encoded| + b)^g + e)`, 当 `|encoded| >= d`

### `skcms_TFType`（枚举）
传输函数类型分类：sRGBish、PQish、HLGish、HLGinvish、PQ、HLG、Invalid。

### `skcms_Curve`（联合体）
统一表示参数化传输函数或一维查找表：
- 参数模式: `alias_of_table_entries == 0`，包含 `skcms_TransferFunction`
- 查找表模式: `table_entries > 0`，包含 8 位或 16 位表指针

### `skcms_A2B` / `skcms_B2A`
ICC 配置文件中的复杂色彩变换结构：
- **A2B** (设备->PCS): 可选的 A 曲线 + CLUT -> 可选的 M 曲线 + 矩阵 -> B 曲线
- **B2A** (PCS->设备): B 曲线 -> 可选的矩阵 + M 曲线 -> 可选的 CLUT + A 曲线

### `skcms_CICP`
编码指示信息（Coding-Independent Code Points），包含色域、传输特性、矩阵系数和全范围标志。

### `skcms_ICCProfile`
ICC 配置文件的解析结果：
- `buffer` / `size`: 原始配置文件数据
- `trc[3]`: RGB 传输响应曲线
- `toXYZD50`: 到 XYZD50 的色域变换矩阵
- `A2B` / `B2A`: 复杂变换数据
- `CICP`: 编码指示信息
- `has_*` 布尔标志指示各字段的有效性

### `skcms_PixelFormat`（枚举）
约 40 种像素格式，覆盖：
- 灰度: A_8, G_8, GA_88
- RGB 紧凑: RGB_565, ABGR_4444
- 8 位: RGB_888, RGBA_8888, BGRA_8888 (含 sRGB 变体)
- 10 位: RGBA_1010102, BGRA_1010102, XR 变体
- 16 位整数: RGB/RGBA_161616LE/BE
- 半精度浮点: RGB/RGBA_hhh(h), 含 Norm 变体
- 单精度浮点: RGB/RGBA_fff(f)

### `skcms_AlphaFormat`（枚举）
Alpha 处理模式：Opaque（不透明）、Unpremul（非预乘）、PremulAsEncoded（编码预乘）。

### `skcms_Signature`（枚举）
常见 ICC 签名值，包括色彩空间签名（RGB, CMYK, Gray, Lab, XYZ 等）和多通道签名（2CLR-15CLR）。

## 公共 API 函数

### 矩阵操作
| 函数 | 说明 |
|------|------|
| `skcms_Matrix3x3_invert` | 3x3 矩阵求逆（不支持原地操作） |
| `skcms_Matrix3x3_concat` | 3x3 矩阵乘法 |

### 传输函数
| 函数 | 说明 |
|------|------|
| `skcms_TransferFunction_eval` | 求值传输函数 |
| `skcms_TransferFunction_invert` | 求逆传输函数 |
| `skcms_TransferFunction_getType` | 获取传输函数类型 |
| `skcms_TransferFunction_makePQish` | 构造 PQ 类传输函数 |
| `skcms_TransferFunction_makeScaledHLGish` | 构造缩放 HLG 类传输函数 |
| `skcms_TransferFunction_makePQ` | 构造标准 PQ 传输函数 |
| `skcms_TransferFunction_makeHLG` | 构造标准 HLG 传输函数 |
| `skcms_TransferFunction_isSRGBish` 等 | 传输函数类型判断系列 |

### ICC 配置文件
| 函数 | 说明 |
|------|------|
| `skcms_Parse` / `skcms_ParseWithA2BPriority` | 解析 ICC 配置文件 |
| `skcms_sRGB_profile` / `skcms_XYZD50_profile` | 获取标准配置文件 |
| `skcms_ApproximatelyEqualProfiles` | 配置文件近似相等测试 |
| `skcms_AreApproximateInverses` | 曲线近似逆测试 |
| `skcms_ApproximateCurve` | 用参数函数近似曲线 |
| `skcms_GetCHAD` / `skcms_GetWTPT` | 获取色度适应矩阵/白点 |
| `skcms_GetInputChannelCount` | 获取输入通道数 |

### 颜色转换
| 函数 | 说明 |
|------|------|
| `skcms_Transform` | 核心颜色转换函数 |
| `skcms_MakeUsableAsDestination` | 使配置文件可用作目标 |
| `skcms_MakeUsableAsDestinationWithSingleCurve` | 使配置文件可用作光栅化目标 |

### 工具函数
| 函数 | 说明 |
|------|------|
| `skcms_AdaptToXYZD50` | 从指定白点到 D50 的色度适应矩阵 |
| `skcms_PrimariesToXYZD50` | 从 RGB 原色计算到 XYZD50 的矩阵 |
| `skcms_DisableRuntimeCPUDetection` | 禁用运行时 CPU 检测 |
| `skcms_Init` | 初始化空配置文件 |
| `skcms_SetTransferFunction` | 设置配置文件的传输函数 |
| `skcms_SetXYZD50` | 设置配置文件的色域矩阵 |

## 内部实现细节

### DLL 导出控制
通过 `SKCMS_API` 宏支持三种场景：
- 静态链接: 无属性
- DLL 导出 (Windows): `__declspec(dllexport)`
- DLL 导入 (Windows): `__declspec(dllimport)`
- 共享库 (非 Windows): `__attribute__((visibility("default")))`

### PQ 传输函数编码
PQ 使用特殊编码方式：`g = -5` 标识 PQ 类型，`a` 存储 HDR 参考白亮度（默认 203 nits）。转换管线为：PQ EOTF -> 乘以 10000 nits -> 除以参考白 -> 色域变换到 XYZD50。

### HLG 传输函数编码
HLG 使用 `g = -6` 标识，`a` 存储参考白亮度，`b` 存储峰值亮度（默认 1000 nits），`c` 存储系统 gamma（默认 1.2）。转换包含 OOTF 通道混合步骤。

### A2B 优先级
`skcms_Parse` 默认按 A2B0（感知）> A2B1（相对比色）的优先级选择，忽略 A2B2（饱和度）。用户可通过 `skcms_ParseWithA2BPriority` 自定义优先级。

## 依赖关系

- **C 标准库**: stdbool.h, stddef.h, stdint.h, string.h
- 无外部库依赖（skcms 是自包含的）

## 设计模式与设计决策

1. **纯 C API**: 使用 `extern "C"` 和 C 类型，确保最大的跨语言兼容性和 ABI 稳定性。
2. **内联便利函数**: `skcms_Parse`、`skcms_Init` 等简单函数定义为 `static inline`，零调用开销。
3. **联合类型表示曲线**: `skcms_Curve` 使用 C 联合体同时支持参数化和查找表两种曲线表示。
4. **HDR 传输函数复用**: PQ 和 HLG 复用 `skcms_TransferFunction` 的 7 个参数槽位，通过 `g` 的特殊值区分类型。

## 性能考量

- **skcms_Transform 是热路径**: 所有像素级颜色转换都通过此单一入口，内部自动分发到最优 SIMD 路径
- **配置文件等价性快速检测**: `skcms_ApproximatelyEqualProfiles` 允许跳过相同配置文件之间的无效转换
- **运行时 CPU 检测**: 默认启用，可通过 `skcms_DisableRuntimeCPUDetection` 关闭以减少首次调用延迟

## 相关文件

- `modules/skcms/src/skcms_Transform.h` - 内部操作定义
- `modules/skcms/src/Transform_inl.h` - 操作实现
- `modules/skcms/src/skcms_internals.h` - 内部工具
