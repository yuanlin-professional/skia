# SkPMColor

> 源文件: `include/private/chromium/SkPMColor.h`

## 概述
SkPMColor 提供了预乘 Alpha(Premultiplied Alpha)颜色的操作函数。预乘颜色是一种优化的颜色表示方式,其中 RGB 分量已经与 Alpha 值相乘。该文件提供了创建和分解预乘颜色的 API 函数,是 Skia 色彩系统中处理 Alpha 混合优化的基础工具。

## 架构位置
该文件位于 Skia 的 Chromium 私有接口层,属于核心色彩类型系统。它为预乘颜色(SkPMColor 类型)提供操作函数,是图像处理和渲染管线中 Alpha 混合计算的基础。SkPMColor 在 SkColor.h 中定义,此文件提供具体操作。

## 核心概念

### 预乘 Alpha 原理
标准颜色表示:
- RGBA: (R, G, B, A) 分量独立,范围 [0, 255]

预乘颜色表示:
- PMRGBA: (R×A/255, G×A/255, B×A/255, A)
- RGB 分量已经乘以 Alpha

### 预乘的优势
1. **混合优化**: Alpha 混合公式简化
   - 标准: `result = src.rgb * src.a + dst.rgb * (1 - src.a)`
   - 预乘: `result = src.rgb + dst.rgb * (1 - src.a)`

2. **硬件加速**: GPU 混合单元天然支持预乘格式

3. **精度保持**: 避免重复的乘法操作累积误差

## 公共 API 函数

### 颜色创建

#### `SK_API SkPMColor SkPMColorSetARGB(SkAlpha a, uint8_t r, uint8_t g, uint8_t b)`
- **功能**: 从已预乘的 8 位分量创建 SkPMColor 值
- **参数**:
  - `a`: Alpha 分量,0(完全透明)到 255(完全不透明)
  - `r`: 红色分量,0(无红)到 255(全红),**已预乘**
  - `g`: 绿色分量,0(无绿)到 255(全绿),**已预乘**
  - `b`: 蓝色分量,0(无蓝)到 255(全蓝),**已预乘**
- **返回值**: 打包的预乘颜色值
- **注意**: 调用者需要确保 RGB 值已经预乘,函数不会执行预乘操作

### 分量提取

#### `SK_API SkAlpha SkPMColorGetA(SkPMColor)`
- **功能**: 从预乘颜色中提取 Alpha 分量
- **参数**: 预乘颜色值
- **返回值**: Alpha 值,范围 [0, 255]

#### `SK_API uint8_t SkPMColorGetR(SkPMColor)`
- **功能**: 从预乘颜色中提取红色分量
- **参数**: 预乘颜色值
- **返回值**: 预乘的红色值,范围 [0, 255]
- **注意**: 返回的是预乘值,非原始红色

#### `SK_API uint8_t SkPMColorGetG(SkPMColor)`
- **功能**: 从预乘颜色中提取绿色分量
- **参数**: 预乘颜色值
- **返回值**: 预乘的绿色值,范围 [0, 255]
- **注意**: 返回的是预乘值,非原始绿色

#### `SK_API uint8_t SkPMColorGetB(SkPMColor)`
- **功能**: 从预乘颜色中提取蓝色分量
- **参数**: 预乘颜色值
- **返回值**: 预乘的蓝色值,范围 [0, 255]
- **注意**: 返回的是预乘值,非原始蓝色

## 内部实现细节

### SkPMColor 内存布局
SkPMColor 是 32 位整数,通常布局为:
- **小端系统**: B G R A(低字节到高字节)
- **大端系统**: A R G B(低字节到高字节)

实际布局依赖于平台和构建配置。

### 预乘计算示例
从标准 RGBA 转换到预乘:
```cpp
// 标准颜色: 半透明红色 (255, 0, 0, 128)
uint8_t alpha = 128;
uint8_t r = 255, g = 0, b = 0;

// 预乘计算
uint8_t pmR = (r * alpha) / 255;  // 255 * 128 / 255 = 128
uint8_t pmG = (g * alpha) / 255;  // 0
uint8_t pmB = (b * alpha) / 255;  // 0

// 创建预乘颜色
SkPMColor pmColor = SkPMColorSetARGB(alpha, pmR, pmG, pmB);
```

### 函数命名约定
- `SkPMColorSet*`: 创建/设置预乘颜色
- `SkPMColorGet*`: 提取预乘颜色的分量
- 注意与 SkColor 的区别:SkColor 不是预乘的

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkColor | SkPMColor 类型定义,SkAlpha 类型 |
| SkAPI | API 导出宏 |
| cstdint | uint8_t 类型定义 |

### 被依赖的模块
- SkBlitter: 使用预乘颜色进行光栅化
- SkPaint: 内部颜色表示
- SkShader: 着色器颜色输出
- SkColorFilter: 颜色过滤操作
- SkXfermode: Alpha 混合模式
- Chromium 的像素操作代码

## 设计模式与设计决策

### 显式预乘语义
函数名明确包含"PM"前缀:
- 避免与非预乘函数混淆
- 提醒调用者参数必须已预乘
- 清晰的 API 语义

### 不提供自动预乘
`SkPMColorSetARGB` 不执行预乘计算:
- 调用者可能已有预乘值
- 避免重复计算
- 性能优先设计

### 独立的提取函数
为每个分量提供独立的 Get 函数:
- 清晰的接口
- 优化器可以只提取需要的分量
- 避免返回结构体的开销

### 类型安全
使用 SkPMColor 和 SkColor 作为不同类型:
- 编译期类型检查
- 防止混淆预乘和非预乘颜色
- 增强代码可读性

## 性能考量

### 内联优化
所有函数都标记为 SK_API,通常会内联:
- 零函数调用开销
- 编译器可以优化位操作
- 生成最优机器码

### 位操作实现
内部使用位移和掩码操作:
- 避免浮点运算
- 单指令提取分量
- 单指令打包颜色

### 预乘的混合优势
使用预乘颜色后,Alpha 混合:
- 减少一次乘法(原始混合需要 src.rgb * src.a)
- GPU 硬件直接支持
- 避免在着色器中重复预乘

### SIMD 友好
预乘颜色格式适合 SIMD 优化:
- 4 个字节对齐在 32 位边界
- 可以批量处理多个像素
- SSE/NEON 指令高效

## 使用场景

### 图像解码
解码器生成预乘像素:
```cpp
for (int i = 0; i < pixelCount; ++i) {
    uint8_t a = alphaChannel[i];
    uint8_t r = (redChannel[i] * a) / 255;
    uint8_t g = (greenChannel[i] * a) / 255;
    uint8_t b = (blueChannel[i] * a) / 255;
    pixels[i] = SkPMColorSetARGB(a, r, g, b);
}
```

### Alpha 混合
使用预乘颜色的混合:
```cpp
// 获取预乘的源和目标
SkPMColor src = ...;
SkPMColor dst = ...;

// 提取分量
uint8_t srcA = SkPMColorGetA(src);
uint8_t invSrcA = 255 - srcA;

// 混合(简化公式)
uint8_t outR = SkPMColorGetR(src) + (SkPMColorGetR(dst) * invSrcA) / 255;
uint8_t outG = SkPMColorGetG(src) + (SkPMColorGetG(dst) * invSrcA) / 255;
uint8_t outB = SkPMColorGetB(src) + (SkPMColorGetB(dst) * invSrcA) / 255;
uint8_t outA = srcA + (SkPMColorGetA(dst) * invSrcA) / 255;

SkPMColor result = SkPMColorSetARGB(outA, outR, outG, outB);
```

### 颜色过滤
应用颜色过滤器:
```cpp
SkPMColor applyFilter(SkPMColor color, float brightness) {
    uint8_t a = SkPMColorGetA(color);
    uint8_t r = SkPMColorGetR(color) * brightness;  // 已预乘,直接缩放
    uint8_t g = SkPMColorGetG(color) * brightness;
    uint8_t b = SkPMColorGetB(color) * brightness;
    return SkPMColorSetARGB(a, r, g, b);
}
```

## 常见陷阱

### 误用非预乘值
错误示例:
```cpp
// 错误:直接使用非预乘的 RGB
SkPMColor wrong = SkPMColorSetARGB(128, 255, 0, 0);
// 应该先预乘
uint8_t pmR = (255 * 128) / 255;
SkPMColor correct = SkPMColorSetARGB(128, pmR, 0, 0);
```

### 假设分量独立
错误示例:
```cpp
// 错误:期望提取原始红色
SkPMColor color = ...;  // 半透明红色
uint8_t r = SkPMColorGetR(color);  // 得到预乘值,不是 255
```

### 反预乘丢失精度
从预乘恢复原始颜色会损失精度:
```cpp
uint8_t a = SkPMColorGetA(color);
uint8_t pmR = SkPMColorGetR(color);
uint8_t originalR = (pmR * 255) / a;  // 可能不等于原始值
```

## 平台相关说明

### 字节序差异
不同平台的 SkPMColor 内存布局可能不同:
- 使用提供的函数而非直接位操作
- 保证跨平台兼容性
- 避免硬编码位移值

### SIMD 优化
平台相关的优化实现:
- x86: 使用 SSE2/AVX2 指令
- ARM: 使用 NEON 指令
- 批量处理像素数组

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkColor.h | SkPMColor 类型定义 |
| src/core/SkBlitter.cpp | 主要使用者,光栅化 |
| src/effects/SkColorMatrix.cpp | 颜色变换 |
| src/core/SkXfermode.cpp | Alpha 混合模式 |
| include/core/SkShader.h | 着色器颜色输出 |
| src/opts/SkOpts.h | SIMD 优化实现 |
