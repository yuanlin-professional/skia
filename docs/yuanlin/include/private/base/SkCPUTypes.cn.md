# SkCPUTypes

> 源文件: `include/private/base/SkCPUTypes.h`

## 概述
SkCPUTypes 定义了用于参数传递和局部变量的快速整数类型。这些类型在历史上用于优化性能,但在现代架构上的必要性已经降低,主要保留用于 API 兼容性。

## 架构位置
该头文件位于 Skia 基础类型系统的底层,属于基础设施层。它为 Skia 的颜色处理、像素操作等模块提供历史遗留的类型定义,目前正在逐步淘汰中。

## 类型定义

### U8CPU
```cpp
typedef unsigned U8CPU;
```

**说明**:
- 用于表示 8 位无符号整数的快速类型
- 实际是 `unsigned int`,通常为 32 位
- 设计初衷是在某些架构上 32 位整数运算比 8 位更快

**用途**:
- 参数传递(避免类型提升开销)
- 局部变量(在寄存器中操作)
- **不适用于存储**(浪费内存)

**典型使用场景**:
- 颜色分量(alpha, red, green, blue)
- 像素值的中间计算
- 位操作和掩码运算

### U16CPU
```cpp
typedef unsigned U16CPU;
```

**说明**:
- 用于表示 16 位无符号整数的快速类型
- 实际是 `unsigned int`,通常为 32 位
- 避免某些架构上 16 位运算的低效性

**用途**:
- 参数传递
- 局部变量
- **不适用于存储**

**典型使用场景**:
- Unicode 字符处理(BMP 字符)
- 16 位颜色格式(RGB565)
- 索引和计数器

## 内部实现细节

### 历史背景
在早期的 CPU 架构上(如 x86 早期型号):
- 8 位和 16 位运算需要额外的部分寄存器访问
- 32 位寄存器操作是最自然和高效的
- 使用 32 位类型可以避免零扩展和符号扩展开销

### 现代架构的变化
在现代 CPU 上:
- 8 位和 16 位运算已经很高效
- 编译器优化能自动处理类型提升
- 使用 32 位类型反而可能浪费寄存器和内存带宽

### ABI 考量
```cpp
// TODO(bungeman,kjlubick) There are a lot of assumptions throughout the codebase
// that these types are 32 bits, when they could be more or less.
```

**问题**:
- 整个代码库假设这些类型是 32 位
- 但 `unsigned` 的大小是平台相关的(虽然通常是 32 位)
- 改变类型定义可能破坏 ABI(应用二进制接口)

**建议方向**:
- 公共 API 应停止使用这些类型
- 内部可以考虑使用 `uint_fast8_t` 和 `uint_fast16_t`
- 但公共 API 不能使用,因为 fast 类型的大小不固定,会导致 ABI 不兼容

## 依赖关系

### 依赖的模块
无直接依赖,这是一个基础类型定义文件。

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkColor.h | 颜色分量类型(SkAlpha, SkColor) |
| SkImageInfo.h | 像素格式处理 |
| SkPaint.h | 颜色和样式参数 |
| 各种图像编解码器 | 像素数据处理 |
| 文本渲染模块 | 字符编码处理 |

## 设计模式与设计决策

### 性能优化的历史遗产
最初设计时的假设:
- CPU 对原生字长的操作最快
- 避免部分寄存器访问的性能损失
- 减少类型转换的指令开销

### 向后兼容性
保留这些类型定义的原因:
- 大量现有代码依赖这些类型
- 公共 API 稳定性要求
- 避免破坏性的 API 变更

### 逐步淘汰策略
文件注释表明的未来方向:
1. 公共 API 停止使用这些类型
2. 内部实现迁移到标准类型
3. 最终可能完全移除这些定义

### 类型安全权衡
使用 `unsigned` 而非固定大小类型:
- **优点**: 性能可能更好(理论上)
- **缺点**: 大小不确定,可能导致跨平台问题

## 性能考量

### 寄存器使用
在参数传递中:
```cpp
// 使用 U8CPU
void setAlpha(U8CPU alpha) {
    // alpha 已经在 32 位寄存器中,无需扩展
}

// vs 使用 uint8_t
void setAlpha(uint8_t alpha) {
    // 可能需要零扩展指令(在某些老架构上)
}
```

### 现代编译器优化
现代编译器的优化能力:
- 自动进行寄存器分配和大小优化
- 消除不必要的类型转换
- 使得显式使用 32 位类型的优势不明显

### 内存 vs 速度权衡
```cpp
// 存储时浪费空间
struct Pixel {
    U8CPU r, g, b, a;  // 16 字节!
};

// 应该使用
struct Pixel {
    uint8_t r, g, b, a;  // 4 字节
};
```

### 函数调用约定
在某些调用约定下:
- 小于 32 位的参数会被提升到 32 位
- 使用 U8CPU 避免了调用者的提升操作
- 但在现代 ABI 中,这种差异通常可以忽略

## 使用场景

### 颜色分量处理
```cpp
U8CPU alpha = 255;
U8CPU red = (color >> 16) & 0xFF;

// 中间计算
U8CPU blended = (alpha * foreground + (255 - alpha) * background) / 255;
```

### 像素格式转换
```cpp
void convertRGB565ToRGBA(U16CPU rgb565, U8CPU* rgba) {
    rgba[0] = (rgb565 >> 11) << 3;  // R
    rgba[1] = ((rgb565 >> 5) & 0x3F) << 2;  // G
    rgba[2] = (rgb565 & 0x1F) << 3;  // B
    rgba[3] = 255;  // A
}
```

### 局部变量优化
```cpp
void processPixels(const uint8_t* src, uint8_t* dst, int count) {
    for (int i = 0; i < count; ++i) {
        U8CPU value = src[i];  // 读取到快速类型
        value = (value * 3) / 4;  // 快速运算
        dst[i] = static_cast<uint8_t>(value);  // 写回存储
    }
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkColor.h | 使用 U8CPU 定义 SkAlpha 等 |
| include/core/SkImageInfo.h | 像素格式定义 |
| include/private/base/SkTypes.h | 其他基础类型定义 |

## 注意事项

### 不要用于存储
```cpp
// 错误:浪费内存
class Image {
    U8CPU pixels[1000000];  // 4MB 而非 1MB!
};

// 正确:使用固定大小类型
class Image {
    uint8_t pixels[1000000];  // 1MB
};
```

### 类型转换
从存储类型读取时需要转换:
```cpp
uint8_t stored_value = 100;
U8CPU working_value = stored_value;  // 隐式提升
// ... 操作 working_value
stored_value = static_cast<uint8_t>(working_value);  // 显式缩窄
```

### 范围检查
虽然是 32 位类型,但应保持在有效范围内:
```cpp
U8CPU value = 255;
value = value + 10;  // 现在是 265,超出 uint8_t 范围!
// 使用前应该截断
value = value & 0xFF;  // 或使用 SkToU8
```

### 跨平台差异
虽然 `unsigned` 通常是 32 位,但标准不保证:
- 某些嵌入式平台可能是 16 位
- 某些 64 位平台的 `unsigned` 可能是 64 位(极少见)
- 不应依赖具体大小,仅作为"快速类型"使用

## 现代替代方案

### 标准快速类型
C99/C++11 提供了更好的替代:
```cpp
#include <cstdint>

uint_fast8_t fast_u8;   // 最快的至少 8 位类型
uint_fast16_t fast_u16; // 最快的至少 16 位类型
```

**优势**:
- 标准定义,语义明确
- 保证最小大小
- 编译器根据目标平台选择最优大小

**劣势**:
- 大小平台相关,不能用于 ABI
- 不能用于公共 API

### 使用建议
- **新代码**: 直接使用 `uint8_t`, `uint16_t`
- **性能关键内部代码**: 考虑 `uint_fast8_t`, `uint_fast16_t`
- **公共 API**: 使用固定大小类型,避免 ABI 问题
- **遗留代码**: 可以继续使用 U8CPU/U16CPU 保持一致性

## 总结
SkCPUTypes 是 Skia 历史优化的遗留产物,反映了早期 CPU 架构的性能特性。在现代系统中,其性能优势已经不明显,主要保留用于兼容性。新代码应该使用标准的固定大小整数类型(uint8_t, uint16_t)或快速类型(uint_fast8_t, uint_fast16_t)。
