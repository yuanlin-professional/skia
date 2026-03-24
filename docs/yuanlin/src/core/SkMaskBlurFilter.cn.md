# SkMaskBlurFilter

> 源文件: src/core/SkMaskBlurFilter.h, src/core/SkMaskBlurFilter.cpp

## 概述

`SkMaskBlurFilter` 是 Skia 中实现单通道高斯模糊的核心类,专门用于对 alpha 遮罩执行高质量的模糊处理。该类基于 W3C Filter Effects 规范实现,支持各种遮罩格式 (BW/A8/ARGB32/LCD16),通过三次 box filter 逼近高斯核,并使用 SIMD 优化实现高性能处理。

## 架构位置

`SkMaskBlurFilter` 位于 Skia 模糊处理管线的算法层:
- 被 `SkMaskFilterBase` 的模糊子类调用
- 实现符合 W3C 标准的高斯模糊算法
- 支持水平和垂直方向独立的 sigma 值
- 为小 sigma (<2.0) 和大 sigma (>=2.0) 提供不同的优化路径

## 主要类与结构体

### 核心类

| 类名 | 说明 |
|------|------|
| SkMaskBlurFilter | 模糊滤镜接口类 |
| PlanGauss | 高斯模糊计划 (内部实现) |
| PlanGauss::Scan | 扫描线模糊执行器 |

### 关键成员变量

**SkMaskBlurFilter**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fSigmaW | const double | 水平方向 sigma (限制在 0-135) |
| fSigmaH | const double | 垂直方向 sigma (限制在 0-135) |

**PlanGauss** (内部类):
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fWeight | uint64_t | 归一化权重 (定点数 0.32) |
| fBorder | int | 模糊扩展边界 |
| fSlidingWindow | int | 滑动窗口大小 (2 * fBorder + 1) |
| fPass0Size | int | 第一次 box filter 大小 |
| fPass1Size | int | 第二次 box filter 大小 |
| fPass2Size | int | 第三次 box filter 大小 |

## 公共 API 函数

### 构造函数

```cpp
SkMaskBlurFilter(double sigmaW, double sigmaH);
```

参数自动限制在 `[0.0, 135.0]` 范围:
- Sigma < 0.01: 视为无模糊
- Sigma >= 135: 超过此值可能导致 uint32 溢出

### 查询方法

```cpp
// 判断是否为无效模糊 (sigma 过小)
bool hasNoBlur() const;
```

阈值:
```cpp
constexpr double kNoWindowSigma = 0.531923;  // 或 1/3 (历史兼容)
```

### 核心模糊函数

```cpp
// 对源遮罩应用模糊,返回边界扩展量
SkIPoint blur(const SkMask& src, SkMaskBuilder* dst) const;
```

**返回值**: `{radiusX, radiusY}` 表示边界扩展像素数

## 内部实现细节

### 三次 Box Filter 逼近

高斯模糊通过三次 box filter 卷积逼近:
```
窗口大小 = floor(sigma * 3 * sqrt(2 * π) / 4 + 0.5)
```

#### 奇数窗口示例 (window=7)
```
       S
    aaaAaaa
    bbbBbbb
    cccCccc
       D
```
边界扩展: `3 * ((window - 1) / 2)`

#### 偶数窗口示例 (window=6)
```
      S
   aaaAaa
    bbBbbb
   cccCccc
      D
```
边界扩展: `3 * (window / 2) - 1`

### 归一化权重计算

```cpp
auto divisor = (window & 1) == 1
    ? window3           // 奇数: window^3
    : window3 + window2;  // 偶数: window^3 + window^2

fWeight = static_cast<uint64_t>(round(1.0 / divisor * (1ull << 32)));
```

使用 32 位定点数存储权重,保证精度。

### 小 Sigma 优化路径 (sigma < 2.0)

使用 SIMD 加速的直接卷积:

#### 水平模糊函数族
```cpp
blur_x_radius_1()  // radius=1, 3 像素宽度
blur_x_radius_2()  // radius=2, 5 像素宽度
blur_x_radius_3()  // radius=3, 7 像素宽度
blur_x_radius_4()  // radius=4, 9 像素宽度
```

#### SIMD 卷积原理
对于 radius=1 的 3 点卷积 `[G1, G0, G1]`:
```cpp
// 源数据 S[n..n+7] 乘以高斯系数
auto v0 = mulhi(s0, g0);
auto v1 = mulhi(s0, g1);

// 目标累加
*d0 += v1;  // D[n..n+7] += S[n..n+7] * G[1]
*d0 += {_____, v0[0], ..., v0[6]};  // D[n..n+8] += {0, S[n..n+7] * G[0]}
*d8 += {v0[7], _____, ...};
*d0 += {_____, _____, v1[0], ..., v1[5]};  // D[n..n+9] += {0, 0, S[n..n+7] * G[1]}
*d8 += {v1[6], v1[7], ...};
```

使用 8 宽 SIMD 寄存器 (`fp88 = skvx::Vec<8, uint16_t>`),8.8 定点数格式。

### 大 Sigma 路径 (sigma >= 2.0)

使用分离的 box filter:

#### 扫描线模糊
```cpp
template <typename AlphaIter>
void blur(const AlphaIter srcBegin, const AlphaIter srcEnd,
          uint8_t* dst, int dstStride, uint8_t* dstEnd) const {
    // 三级累加和
    sum0 += leadingEdge;
    sum1 += sum0;
    sum2 += sum1;

    *dst = finalScale(sum2);  // 应用权重归一化

    // 循环缓冲区更新
    sum2 -= *buffer2Cursor;
    *buffer2Cursor = sum1;
    // ...
}
```

双向扫描:
1. 从左到右扫描,生成初始输出
2. 从右到左扫描,填充右边界

#### 转置优化
水平模糊时同时转置数据:
```cpp
// 水平模糊 + 转置到临时缓冲区
for (int y = 0; y < srcH; ++y) {
    scanW.blur(start, end, &tmp[y], tmpW, tmpStart + tmpW * tmpH);
}

// 垂直模糊 + 转置回原方向
scanH.blur(tmpStart, tmpStart + tmpW, dstStart, dst->fRowBytes, ...);
```

减少内存访问不连续性。

### 格式转换

支持各种输入格式自动转换为 A8:
```cpp
static void bw_to_a8(uint8_t* a8, const uint8_t* from, int width);
static void lcd_to_a8(uint8_t* a8, const uint8_t* from, int width);
static void argb32_to_a8(uint8_t* a8, const uint8_t* from, int width);
```

LCD16 格式转换:
```cpp
unsigned rgb = reinterpret_cast<const uint16_t*>(from)[i];
unsigned r = SkPacked16ToR32(rgb);
unsigned g = SkPacked16ToG32(rgb);
unsigned b = SkPacked16ToB32(rgb);
a8[i] = (r + g + b) / 3;  // RGB 平均作为 alpha
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkGaussFilter | 小 sigma 的高斯系数计算 |
| SkMask | 遮罩数据结构 |
| src/base/SkVx.h | SIMD 向量运算 |
| SkArenaAlloc | 临时缓冲区分配 |
| SkColorPriv | 颜色格式转换 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkBlurMaskFilterImpl | 使用 SkMaskBlurFilter 实现模糊 |
| SkMaskFilterBase | 模糊滤镜的基类 |

## 设计模式与设计决策

### 1. 策略模式 - 双路径算法
```cpp
SkIPoint blur(const SkMask& src, SkMaskBuilder* dst) const {
    if (fSigmaW < 2.0 && fSigmaH < 2.0) {
        return small_blur(fSigmaW, fSigmaH, src, dst);  // 直接卷积
    }
    // 三次 box filter
}
```

### 2. 模板特化 - AlphaIter
为每种遮罩格式特化迭代器:
```cpp
SkMask::AlphaIter<SkMask::kA8_Format>
SkMask::AlphaIter<SkMask::kBW_Format>
SkMask::AlphaIter<SkMask::kARGB32_Format>
SkMask::AlphaIter<SkMask::kLCD16_Format>
```

编译时分发,零运行时开销。

### 3. 函数指针表 - BlurX/BlurY
```cpp
using BlurX = decltype(blur_x_radius_1);

static void blur_x_rect(BlurX blur, ...) {
    // 调用 blur 指针
}

switch (radius) {
    case 1: blur_x_rect(blur_x_radius_1, ...); break;
    case 2: blur_x_rect(blur_x_radius_2, ...); break;
    // ...
}
```

### 4. RAII 资源管理
```cpp
SkSTArenaAlloc<1024> alloc;
auto buffer = alloc.makeArrayDefault<uint32_t>(bufferSize);
auto tmp = alloc.makeArrayDefault<uint8_t>(tmpW * tmpH);
// 自动释放
```

## 性能考量

### 1. Sigma 上限限制
```cpp
constexpr double kMaxSigma = 135.0;
```
防止溢出:
```
window = floor(sigma * 3 * sqrt(2π) / 4)
window <= 255  =>  sigma <= 135
sum2_max = (window + 1)^3 * 255 < 2^32
```

### 2. SIMD 优化
- 使用 8 宽 `skvx::Vec<8, uint16_t>` 处理
- 8.8 定点数格式避免浮点运算
- 编译器自动向量化

### 3. 缓存友好
```cpp
// 按行处理,连续内存访问
for (int y = 0; y < dstH; y++) {
    blur_row(blur, g0, g1, g2, g3, g4, src, srcW, dst, dstW);
    src += srcStride;
    dst += dstStride;
}
```

### 4. 转置优化
减少垂直方向的跨行访问:
```cpp
// 水平模糊时转置,垂直模糊变为水平扫描
```

### 5. 循环缓冲区
三个循环缓冲区避免大数组分配:
```cpp
buffer0Cursor = (buffer0Cursor + 1) < fBuffer0End
    ? buffer0Cursor + 1
    : fBuffer0;  // 回绕
```

### 6. Fuzzer 保护
```cpp
#if defined(SK_BUILD_FOR_FUZZER)
if (size > 10000000) {  // 限制临时缓冲区大小
    return {0, 0};
}
#endif
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkGaussFilter.h | 依赖 | 高斯系数计算 |
| src/core/SkMask.h | 依赖 | 遮罩数据结构 |
| src/base/SkVx.h | 依赖 | SIMD 向量类 |
| src/base/SkArenaAlloc.h | 依赖 | 内存分配器 |
| src/core/SkColorPriv.h | 依赖 | 像素格式转换 |
| src/core/SkMaskFilterBase.h | 使用者 | 模糊滤镜基类 |
| include/effects/SkBlurMaskFilter.h | 公共接口 | 模糊滤镜 API |
