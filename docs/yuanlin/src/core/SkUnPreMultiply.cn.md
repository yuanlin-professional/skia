# SkUnPreMultiply

> 源文件: include/core/SkUnPreMultiply.h, src/core/SkUnPreMultiply.cpp

## 概述

`SkUnPreMultiply` 是 Skia 颜色处理系统中的工具类,专门用于将预乘 alpha 颜色转换为非预乘格式。预乘 alpha 是 Skia 内部使用的标准颜色表示,但某些场景(如导出图像、颜色选择器)需要非预乘格式。该类提供了高效的查找表实现,避免昂贵的浮点除法运算。

## 架构位置

`SkUnPreMultiply` 位于 Skia 核心 API 层的颜色处理子系统:

- **上游**: 颜色转换、图像导出、像素操作
- **同级**: `SkColor`、`SkPMColor`、颜色混合
- **特点**: 纯静态工具类,无实例

## 主要类与结构体

### SkUnPreMultiply

**继承关系**:
- 无继承,纯静态工具类

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `gTable` | `static const uint32_t[256]` | 预计算的缩放因子表 |
| `Scale` | `typedef uint32_t` | 缩放因子类型别名 |

## 公共 API 函数

### 核心 API

| 函数签名 | 功能描述 |
|---------|---------|
| `static const Scale* GetScaleTable()` | 获取完整缩放表指针 |
| `static Scale GetScale(U8CPU alpha)` | 获取特定 alpha 的缩放因子 |
| `static U8CPU ApplyScale(Scale, U8CPU)` | 应用缩放因子到颜色分量 |
| `static SkColor PMColorToColor(SkPMColor)` | 转换预乘颜色到非预乘 |

## 内部实现细节

### 预乘 Alpha 原理

**预乘格式** (Skia 内部):
```
R' = R * A / 255
G' = G * A / 255
B' = B * A / 255
存储: (A, R', G', B')
```

**非预乘格式** (用户友好):
```
存储: (A, R, G, B)
其中 R, G, B 是原始颜色值
```

**反向转换** (去预乘):
```
R = R' * 255 / A
G = G' * 255 / A
B = B' * 255 / A
```

### 查找表生成

缩放因子表在编译时生成,每个 alpha 值(0-255)对应一个缩放因子:

```cpp
const uint32_t SkUnPreMultiply::gTable[256] = {
    0x00000000,  // alpha = 0 (特殊处理)
    0xFF000000,  // alpha = 1
    0x7F800000,  // alpha = 2
    // ... 253 个值
};
```

**生成算法** (构建时):
```cpp
#ifdef BUILD_DIVIDE_TABLE
void SkUnPreMultiply_BuildTable() {
    for (unsigned i = 0; i <= 255; i++) {
        uint32_t scale;
        if (0 == i) {
            scale = 0;  // 避免除零
        } else {
            scale = ((255 << 24) + (i >> 1)) / i;
        }
        SkDebugf(" 0x%08X,", scale);

        // 验证精度
        for (int j = 1; j <= i; j++) {
            uint32_t test = (j * scale + (1 << 23)) >> 24;
            uint32_t div = roundf(j * 255.0f / i);
            int diff = SkAbs32(test - div);
            SkASSERT(diff <= 1 && test <= 255);
        }
    }
}
#endif
```

**表项格式**:
- 32 位定点数
- 小数点位于第 24 位
- 表示 255/alpha 的近似值

### 缩放因子应用

```cpp
static U8CPU ApplyScale(Scale scale, U8CPU component) {
    SkASSERT(component <= 255);
    return (scale * component + (1 << 23)) >> 24;
}
```

**算法分析**:
1. `scale * component`: 定点数乘法(48 位结果)
2. `+ (1 << 23)`: 四舍五入偏移
3. `>> 24`: 右移提取整数部分

**精度保证**:
- 误差 ≤ 1
- 结果 ≤ 255(无溢出)

### 完整转换流程

```cpp
SkColor SkUnPreMultiply::PMColorToColor(SkPMColor c) {
    const unsigned a = SkGetPackedA32(c);  // 提取 alpha
    const Scale scale = GetScale(a);       // 查表

    return SkColorSetARGB(
        a,                                  // alpha 不变
        ApplyScale(scale, SkGetPackedR32(c)),  // 反向缩放 R
        ApplyScale(scale, SkGetPackedG32(c)),  // 反向缩放 G
        ApplyScale(scale, SkGetPackedB32(c))   // 反向缩放 B
    );
}
```

### 特殊情况处理

**Alpha = 0**:
```cpp
gTable[0] = 0x00000000;
```
- 缩放因子为 0
- 所有颜色分量变为 0
- 避免除零错误

**Alpha = 255**:
```cpp
gTable[255] = 0x01000000;  // 恰好是 1.0 的定点表示
```
- 无需缩放(已经是非预乘)
- 乘以 1.0 后右移相当于恒等变换

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkColor` | 颜色类型定义 |
| `SkColorPriv` | 颜色分量提取宏 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| 图像导出 | 将内部颜色转换为标准格式 |
| 颜色选择器 | 显示非预乘颜色值 |
| 像素读取 | `SkBitmap::readPixels()` 等 |
| PDF 生成 | 某些颜色空间需要非预乘 |

## 设计模式与设计决策

### 设计模式

1. **查找表模式**: 预计算避免运行时除法
2. **静态工具类**: 无状态,纯函数
3. **类型别名**: `Scale` 提供语义清晰性

### 设计决策

**为什么使用查找表而不是直接除法?**

**性能对比**:
```cpp
// 查找表方法 (~3 条指令)
Scale scale = gTable[alpha];
return (scale * component + (1 << 23)) >> 24;

// 直接除法方法 (~30+ 条指令)
if (alpha == 0) return 0;
return (component * 255 + alpha/2) / alpha;
```

- 查找表快 10 倍以上
- 除法是 CPU 上最慢的指令之一
- 256 项表仅占 1KB 内存

**为什么使用定点数而不是浮点数?**
- 定点运算比浮点快(尤其在旧硬件)
- 结果可预测(无浮点精度问题)
- 颜色值是整数,避免转换开销

**舍入策略**
```cpp
+ (1 << 23)  // 加 0.5
```
- 实现四舍五入
- 比截断更准确
- 验证代码确保误差 ≤ 1

**分离查表和应用**

提供 `GetScaleTable()` 允许批量处理:

```cpp
const Scale* table = SkUnPreMultiply::GetScaleTable();
for (int i = 0; i < count; i++) {
    unsigned a = ...;
    Scale scale = table[a];
    // 使用同一 scale 处理多个像素
}
```

**类型安全**
```cpp
typedef uint32_t Scale;
```
- 避免直接使用 `uint32_t`
- 提供语义信息
- 编译器可优化

## 性能考量

### 优化策略

1. **预计算**: 表在编译时生成,运行时零开销
2. **缓存友好**: 256 项表适合 L1 缓存
3. **向量化**: 可批量处理多个像素
4. **分支消除**: 无条件分支(除 alpha=0 检查)

### 性能数据

**典型操作耗时** (估算):
- 查表: ~1 个周期(L1 缓存命中)
- 乘法: ~3 个周期
- 加法 + 移位: ~2 个周期
- **总计**: ~6 个周期

对比浮点除法的 ~30 个周期,提升约 5 倍。

### 使用场景

**适合**:
- 批量像素转换
- 实时颜色选择器
- 图像格式转换

**不适合**:
- 单个像素的偶发转换(表加载成本)
- GPU 着色器(可直接用除法)

### 批量处理示例

```cpp
void ConvertPixels(const SkPMColor* src, SkColor* dst, int count) {
    const SkUnPreMultiply::Scale* table = SkUnPreMultiply::GetScaleTable();

    for (int i = 0; i < count; i++) {
        SkPMColor c = src[i];
        unsigned a = SkGetPackedA32(c);
        SkUnPreMultiply::Scale scale = table[a];

        dst[i] = SkColorSetARGB(
            a,
            SkUnPreMultiply::ApplyScale(scale, SkGetPackedR32(c)),
            SkUnPreMultiply::ApplyScale(scale, SkGetPackedG32(c)),
            SkUnPreMultiply::ApplyScale(scale, SkGetPackedB32(c))
        );
    }
}
```

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkColor.h` | 颜色类型定义 |
| `src/core/SkColorPriv.h` | 内部颜色操作 |
| `include/core/SkBitmap.h` | 使用去预乘进行像素读取 |
| `src/core/SkPixmap.cpp` | 像素格式转换 |
| `src/pdf/SkPDFDevice.cpp` | PDF 颜色空间转换 |
