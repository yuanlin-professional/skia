# SkBitmapProcState

> 源文件: src/core/SkBitmapProcState.h, src/core/SkBitmapProcState.cpp

## 概述

`SkBitmapProcState` 是 Skia 图形库中用于位图采样和处理的核心状态机。该模块封装了位图绘制过程中所需的所有状态信息,包括变换矩阵、平铺模式、采样选项等,并负责选择最优化的处理函数(Shader/Matrix/Sample Proc)来执行像素采样。通过 SIMD 优化和多种快速路径,实现高性能的位图渲染。

## 架构位置

```
src/core/
  ├── SkBitmapProcState.cpp           # 核心状态机实现
  ├── SkBitmapProcState.h             # 状态机接口
  ├── SkBitmapProcState_matrixProcs.cpp  # 矩阵变换处理器
  ├── SkBitmapProcState_opts.cpp      # 默认优化实现
  ├── SkBitmapProcState_opts_ssse3.cpp   # SSSE3 优化
  └── SkBitmapProcState_opts_lasx.cpp    # LASX 优化
```

本模块位于 Skia 渲染管线的采样层,负责将源位图像素通过变换矩阵和采样策略转换为目标像素。

## 主要类与结构体

### SkBitmapProcState

| **属性** | **说明** |
|---------|---------|
| **继承关系** | 独立结构体 |
| **作用** | 位图处理状态容器,选择和执行采样策略 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fImage` | `const SkImage_Base*` | 源图像 |
| `fPixmap` | `SkPixmap` | 像素数据映射 |
| `fInvMatrix` | `SkMatrix` | 逆变换矩阵 |
| `fPaintAlpha` | `SkAlpha` | 绘制透明度 |
| `fTileModeX` | `SkTileMode` | X 轴平铺模式 |
| `fTileModeY` | `SkTileMode` | Y 轴平铺模式 |
| `fBilerp` | `bool` | 是否启用双线性插值 |
| `fInvSx` | `SkFixed3232` | X 轴逆缩放因子 |
| `fInvKy` | `SkFixed3232` | Y 轴逆倾斜因子 |
| `fFilterOneX` | `SkFixed` | X 轴过滤系数 |
| `fFilterOneY` | `SkFixed` | Y 轴过滤系数 |
| `fAlphaScale` | `uint16_t` | Alpha 缩放值 (0-256) |

**函数指针类型:**

| 类型 | 签名 | 用途 |
|------|------|------|
| `ShaderProc32` | `void (*)(const void* ctx, int x, int y, SkPMColor[], int count)` | 完整着色器流程 |
| `MatrixProc` | `void (*)(const SkBitmapProcState&, uint32_t[], int count, int x, int y)` | 矩阵变换处理 |
| `SampleProc32` | `void (*)(const SkBitmapProcState&, const uint32_t[], int, SkPMColor[])` | 像素采样处理 |

### SkBitmapProcStateAutoMapper

| **属性** | **说明** |
|---------|---------|
| **继承关系** | 辅助工具类 |
| **作用** | 自动映射设备坐标到源位图坐标 |

**功能说明:**
- 将设备空间的整数坐标 `(x, y)` 映射到位图空间
- 自动应用变换矩阵和采样偏移
- 处理双线性插值和最近邻采样的坐标调整

## 公共 API 函数

### 构造与初始化

```cpp
SkBitmapProcState(const SkImage_Base* image, SkTileMode tmx, SkTileMode tmy);
```

**功能:** 构造状态机,指定源图像和平铺模式。

```cpp
bool setup(const SkMatrix& inv, SkColor color, const SkSamplingOptions& sampling);
```

**功能:** 初始化状态并选择处理函数,返回是否成功。内部调用 `init()` 和 `chooseProcs()`。

### 处理函数访问

```cpp
ShaderProc32 getShaderProc32() const;
MatrixProc getMatrixProc() const;
SampleProc32 getSampleProc32() const;
```

**功能:** 获取已选择的处理函数指针。

### 缓冲区管理

```cpp
int maxCountForBufferSize(size_t bufferSize) const;
```

**功能:** 根据缓冲区大小计算可处理的最大像素数,考虑过滤和矩阵类型。

## 内部实现细节

### 初始化流程

```cpp
bool init(const SkMatrix& inverse, SkAlpha paintAlpha, const SkSamplingOptions& sampling) {
    // 1. 获取合适的 Mipmap 级别
    auto* access = SkMipmapAccessor::Make(&fAlloc, fImage, inv, sampling.mipmap);
    std::tie(fPixmap, fInvMatrix) = access->level();
    fInvMatrix.preConcat(inv);

    // 2. 调整矩阵到单位坐标空间
    if (fTileModeX != SkTileMode::kClamp || fTileModeY != SkTileMode::kClamp) {
        SkMatrixPriv::PostIDiv(&fInvMatrix, fPixmap.width(), fPixmap.height());
    }

    // 3. 优化接近单位矩阵的情况
    if (just_trans_general(*forward)) {
        fInvMatrix.setTranslate(-forward->getTranslateX(), -forward->getTranslateY());
    }

    // 4. 决定是否启用双线性插值
    if (integral_translate_only || !valid_for_filtering()) {
        fBilerp = false;
    }
}
```

### 处理函数选择策略

```cpp
bool chooseProcs() {
    // 1. 选择矩阵处理器
    fMatrixProc = this->chooseMatrixProc(translate_only);

    // 2. 选择采样处理器
    if (fInvMatrix.isScaleTranslate()) {
        fSampleProc32 = fBilerp ? SkOpts::S32_alpha_D32_filter_DX
                                : S32_alpha_D32_nofilter_DX;
    } else {
        fSampleProc32 = fBilerp ? SkOpts::S32_alpha_D32_filter_DXDY
                                : S32_alpha_D32_nofilter_DXDY;
    }

    // 3. 尝试选择快速路径着色器
    if (fAlphaScale == 256 && !fBilerp &&
        SkTileMode::kClamp == fTileModeX && SkTileMode::kClamp == fTileModeY &&
        fInvMatrix.isScaleTranslate()) {
        fShaderProc32 = Clamp_S32_opaque_D32_nofilter_DX_shaderproc;
    } else {
        fShaderProc32 = this->chooseShaderProc32();
    }
}
```

### 快速路径着色器

**Clamp_S32_opaque_D32_nofilter_DX:**
- 条件: 仅缩放平移、Clamp 模式、无过滤、不透明
- 优化: 直接内存拷贝,循环展开,边界检查一次完成

```cpp
static void Clamp_S32_opaque_D32_nofilter_DX_shaderproc(...) {
    // 快速路径: 无需 clamp
    if ((uint64_t)SkFixed3232ToInt(fx) <= maxX &&
        (uint64_t)SkFixed3232ToInt(fx + dx * (count - 1)) <= maxX) {
        for (int i = 0; i < count4; ++i) {
            // 4 像素批量处理
            dst[0] = src[SkFixed3232ToInt(fx)]; fx += dx;
            dst[1] = src[SkFixed3232ToInt(fx)]; fx += dx;
            dst[2] = src[SkFixed3232ToInt(fx)]; fx += dx;
            dst[3] = src[SkFixed3232ToInt(fx)]; fx += dx;
            dst += 4;
        }
    }
}
```

**Clamp_S32_D32_nofilter_trans:**
- 条件: 纯平移、Clamp 模式、无过滤
- 优化: 分三段处理(左边界/中间/右边界),减少分支

**Repeat_S32_D32_nofilter_trans:**
- 条件: 纯平移、Repeat 模式、无过滤
- 优化: 循环拷贝,利用内存连续性

### 坐标偏移计算

```cpp
SkBitmapProcStateAutoMapper(const SkBitmapProcState& s, int x, int y) {
    SkPoint pt = s.fInvMatrix.mapPoint({
        SkIntToScalar(x) + SK_ScalarHalf,  // 像素中心
        SkIntToScalar(y) + SK_ScalarHalf,
    });

    SkFixed biasX = 0, biasY = 0;
    if (s.fBilerp) {
        // 双线性插值: 偏移 -0.5 * filterOne
        biasX = s.fFilterOneX >> 1;
        biasY = s.fFilterOneY >> 1;
    } else {
        // 最近邻: 向下舍入偏移
        biasX = 1;
        biasY = 1;
    }

    fX = SkScalarToFixed3232(pt.x()) - SkFixedToFixed3232(biasX);
    fY = SkScalarToFixed3232(pt.y()) - SkFixedToFixed3232(biasY);
}
```

### SIMD 优化机制

通过 `SkOpts` 命名空间提供多平台 SIMD 实现:

```cpp
namespace SkOpts {
    extern void (*S32_alpha_D32_filter_DX)(...);     // 水平过滤
    extern void (*S32_alpha_D32_filter_DXDY)(...);   // 全方位过滤

    void Init_BitmapProcState() {
        #if defined(SK_CPU_X86)
            if (SkCpu::Supports(SkCpu::SSSE3)) {
                Init_BitmapProcState_ssse3();
            }
        #elif defined(SK_CPU_LOONGARCH)
            if (SkCpu::Supports(SkCpu::LOONGARCH_ASX)) {
                Init_BitmapProcState_lasx();
            }
        #endif
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkMipmapAccessor` | 选择合适的 Mipmap 级别 |
| `SkMatrix` | 坐标变换 |
| `SkPixmap` | 像素数据访问 |
| `SkOpts` | SIMD 优化实现 |
| `SkImage_Base` | 源图像接口 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkDraw` | 位图绘制的主流程 |
| `SkImageShader` | 图像着色器实现 |
| `SkBlitter` | 像素混合写入 |

## 设计模式与设计决策

### 1. 策略模式 (Strategy Pattern)

通过函数指针选择不同的处理策略:
- `ShaderProc32`: 完整流程策略
- `MatrixProc` + `SampleProc32`: 分离变换与采样

### 2. 状态机模式

`setup()` → `init()` → `chooseProcs()` 形成状态转换链,确保状态一致性。

### 3. 惰性求值

仅在 `setup()` 时选择处理函数,避免运行时分支判断。

### 4. 数据局部性优化

```cpp
static constexpr size_t kBMStateSize = 136;
SkSTArenaAlloc<kBMStateSize> fAlloc;
```

使用栈上的小型内存池,减少堆分配开销。

### 5. 固定点数精度

使用 `SkFixed3232` (32.32 定点数) 保持高精度坐标计算,避免浮点运算。

## 性能考量

### 快速路径识别

```cpp
// 最优: 纯平移 + Clamp + 不透明 → 直接内存拷贝
// 次优: 缩放平移 + Clamp + 不透明 → 优化索引计算
// 通用: 仿射变换 + 任意平铺 → 完整管线
```

### SIMD 加速

- **SSSE3:** 8 像素并行处理双线性插值
- **LASX:** 16 像素并行处理 (LoongArch)

### 循环展开

```cpp
int count4 = count >> 2;
for (int i = 0; i < count4; ++i) {
    // 处理 4 个像素
}
```

减少循环开销,提升指令流水线效率。

### 边界检查优化

```cpp
if ((unsigned)SkFixed3232ToInt(fx) <= maxX &&
    (unsigned)SkFixed3232ToInt(fx + dx * (count - 1)) <= maxX) {
    // 快速路径: 无需逐像素 clamp
}
```

### 缓冲区大小计算

```cpp
int maxCountForBufferSize(size_t bufferSize) const {
    size >>= (fInvMatrix.isScaleTranslate() ? 1 : 2);
    size >>= (fBilerp ? 1 : 0);
    return size;
}
```

根据矩阵类型和过滤模式调整缓冲区需求。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkBitmapProcState_matrixProcs.cpp` | 矩阵变换处理器实现 |
| `src/opts/SkBitmapProcState_opts.h` | SIMD 优化接口 |
| `src/core/SkMipmapAccessor.h` | Mipmap 访问器 |
| `include/core/SkMatrix.h` | 矩阵变换 |
| `include/core/SkSamplingOptions.h` | 采样选项 |
| `src/core/SkDraw.cpp` | 绘制流程 |
