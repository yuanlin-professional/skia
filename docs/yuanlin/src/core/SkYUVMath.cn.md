# SkYUVMath

> 源文件: src/core/SkYUVMath.h, src/core/SkYUVMath.cpp

## 概述

SkYUVMath 是 Skia 中用于 YUV 和 RGB 色彩空间转换的数学工具模块。该模块提供了多种标准色彩空间（如 JPEG、Rec601、Rec709、BT2020 等）的颜色矩阵转换功能,支持 full range 和 limited range 两种数值范围,以及 8/10/12/16 位深度的色彩表示。模块内部包含预编译的转换矩阵表,通过查表方式高效实现 RGB 与 YUV 之间的双向转换。

## 架构位置

SkYUVMath 位于 Skia 核心渲染层的色彩管理子系统中:

```
src/core/
  ├── SkYUVMath.h/cpp        # YUV 数学转换（本模块）
  ├── SkImageInfo.h           # 图像信息定义
  ├── SkYUVAPixmaps.cpp      # YUVA 像素映射
  └── SkColorMatrix.cpp       # 颜色矩阵处理
```

该模块为 Skia 的图像解码、视频渲染和硬件加速提供底层数学支持。

## 主要类与结构体

该模块主要通过函数接口提供服务,核心数据结构如下:

| 结构体/枚举 | 继承关系 | 关键成员变量 | 说明 |
|------------|---------|------------|------|
| `YUVCoeff` | 无 | `float Kr, Kb`<br>`int bits`<br>`Range range` | YUV 系数结构,定义色彩空间参数 |
| `Range` 枚举 | 无 | `kFull`, `kLimited` | 数值范围类型 |

### 主要常量表

模块定义了多个预编译的转换矩阵常量表（20个浮点数组成的 5x4 矩阵）:

- `rgb_to_yuv_array[]`: RGB 到 YUV 转换矩阵数组
- `yuv_to_rgb_array[]`: YUV 到 RGB 转换矩阵数组
- 28 种色彩空间的具体矩阵常量（如 `JPEG_full_rgb_to_yuv`、`Rec709_limited_yuv_to_rgb` 等）

## 公共 API 函数

### 核心转换函数

```cpp
// RGB 到 YUV 转换矩阵
void SkColorMatrix_RGB2YUV(SkYUVColorSpace cs, float m[20]);

// YUV 到 RGB 转换矩阵
void SkColorMatrix_YUV2RGB(SkYUVColorSpace cs, float m[20]);

// 调试工具：输出矩阵表
void SkColorMatrix_DumpYUVMatrixTables();
```

### 函数说明

**SkColorMatrix_RGB2YUV**
- 功能: 获取指定色彩空间的 RGB 到 YUV 转换矩阵
- 参数:
  - `cs`: SkYUVColorSpace 枚举值
  - `m`: 输出的 20 元素浮点数组（5x4 矩阵）
- 返回: 通过参数 `m` 返回矩阵数据

**SkColorMatrix_YUV2RGB**
- 功能: 获取指定色彩空间的 YUV 到 RGB 转换矩阵
- 参数:
  - `cs`: SkYUVColorSpace 枚举值
  - `m`: 输出的 20 元素浮点数组（5x4 矩阵）
- 返回: 通过参数 `m` 返回矩阵数据

## 内部实现细节

### 矩阵生成算法

模块支持四种类型的色彩空间转换:

**1. YCbCr 转换** (`make_rgb_to_yuv_matrix_ycbcr`)
```cpp
// 基于 Kr 和 Kb 系数计算 YCbCr 矩阵
Kr, Kb -> Kg = 1.0 - Kr - Kb
Cr = 0.5 / (1.0 - Kb)
Cb = 0.5 / (1.0 - Kr)
```

**2. YDZDX 转换** (`make_rgb_to_yuv_matrix_ydzdx`)
- 特殊的差分色彩空间
- 应用与 YCbCr 类似的范围校正

**3. GBR 转换** (`make_rgb_to_yuv_matrix_gbr`)
- 简单的通道重排
- 将 RGB 重新排列为 GBR 顺序

**4. YCgCo 转换** (`make_rgb_to_yuv_matrix_ycgco`)
- 使用固定系数 (0.25, 0.5, 0.25)
- 支持 8/10/12/16 位深度

### 矩阵表编译

使用条件编译支持高精度和标准精度:
```cpp
#if defined(SK_YUV_COLOR_SPACE_HIGH_PRECISION)
    // 十六进制浮点数表示
    0x1.322d0ep-2f, ...
#else
    // 标准浮点数表示
    0.299000f, ...
#endif
```

### 矩阵运算

**矩阵转换** (`colormatrix_to_matrix44` / `matrix44_to_colormatrix`):
- 在 5x4 颜色矩阵和 4x4 空间矩阵之间转换
- 保留或注入 alpha 通道

**矩阵求逆**:
- 使用 SkM44 进行矩阵求逆
- 生成 YUV 到 RGB 的逆矩阵

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkImageInfo.h` | 色彩空间枚举定义 |
| `include/core/SkM44.h` | 4x4 矩阵运算 |
| `include/private/base/SkAssert.h` | 断言宏 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `src/effects/SkColorMatrix.cpp` | 颜色矩阵效果实现 |
| `src/gpu/` | GPU 纹理上传和着色器 |
| 图像解码器 | JPEG/PNG 解码 YUV 处理 |
| 视频解码器 | 视频帧色彩空间转换 |

## 设计模式与设计决策

### 查表法优化

**决策**: 使用预编译的常量矩阵表而非运行时计算

**理由**:
- 消除重复计算开销
- 保证数值精度一致性
- 支持快速路径优化

**实现**:
```cpp
const float* yuv_to_rgb_array[] = {
    JPEG_full_yuv_to_rgb,
    Rec601_limited_yuv_to_rgb,
    // ... 28 种色彩空间
};
```

### 双精度支持

通过宏 `SK_YUV_COLOR_SPACE_HIGH_PRECISION` 控制精度:
- 默认模式: 标准浮点数（适用于大多数场景）
- 高精度模式: 十六进制浮点表示（用于专业视频处理）

### 范围处理

**Full Range vs Limited Range**:
- Full Range: [0, 255] 完整范围
- Limited Range: [16, 235] 受限范围（广播电视标准）

```cpp
if (range == kLimited) {
    scaleY  = (219 << shift) / denom;
    addY    = ( 16 << shift) / denom;
}
```

## 性能考量

### 内存布局

**紧凑存储**: 使用 `constexpr float[]` 数组
- 减少内存占用
- 提高缓存命中率
- 支持编译时常量折叠

### 计算优化

1. **避免除法**: 预计算系数
   ```cpp
   const float Cr = 0.5f / (1.0f - Kb);  // 预计算
   ```

2. **矩阵复用**: 通过索引访问预编译表
   ```cpp
   memcpy(m, rgb_to_yuv_array[(unsigned)cs], kSizeOfColorMatrix);
   ```

3. **分支预测**: 使用 `static_assert` 确保枚举值连续

### 数值精度

- 使用 `SK_ScalarHalf` 等常量确保精度
- 通过 SkM44 进行高精度矩阵求逆
- 调试模式下验证转换可逆性

### 平台适配

支持多种位深度（8/10/12/16 位）:
```cpp
const int shift = bits - 8;
const float denom = (1 << bits) - 1;
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkImageInfo.h` | 依赖 | SkYUVColorSpace 枚举定义 |
| `include/core/SkM44.h` | 依赖 | 矩阵运算支持 |
| `src/effects/SkColorMatrix.cpp` | 使用者 | 颜色矩阵效果 |
| `src/core/SkYUVAPixmaps.cpp` | 使用者 | YUVA 像素映射 |
| `include/core/SkYUVAInfo.h` | 相关 | YUVA 信息描述 |
| `src/gpu/ganesh/GrYUVtoRGBEffect.cpp` | 使用者 | GPU YUV 着色器 |
