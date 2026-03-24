# SkSpriteBlitter

> 源文件
> - src/core/SkSpriteBlitter.h

## 概述

`SkSpriteBlitter` 是 Skia 中专门用于快速矩形块传输(sprite blitting)的抽象基类。它从 `SkBlitter` 派生,但将主要操作从逐像素的 `blitH`/`blitV` 转变为更高效的 `blitRect`,专注于将整个矩形图像块一次性绘制到目标表面。该类是 Skia 位图绘制快速路径的核心,广泛用于 UI 渲染、纹理映射和精灵系统。

## 架构位置

`SkSpriteBlitter` 位于 Skia 的快速路径绘制层:

- **快速路径**: 绕过通用 `SkDraw` 管道的优化分支
- **位图绘制**: `SkCanvas::drawBitmap` 的底层实现
- **像素格式特化**: 针对不同格式有具体子类实现

## 主要类与结构体

### SkSpriteBlitter (抽象基类)

**继承关系**:
```
SkBlitter
  └── SkSpriteBlitter (抽象)
        ├── Sprite_D32_S32 (32位ARGB, 实现在 SkSpriteBlitter_ARGB32.cpp)
        └── (其他像素格式的实现)
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDst` | `SkPixmap` | 目标表面像素数据 |
| `fSource` | `const SkPixmap` | 源图像像素数据 |
| `fLeft` | `int` | 源图像在目标中的左偏移 |
| `fTop` | `int` | 源图像在目标中的上偏移 |
| `fPaint` | `const SkPaint*` | 绘制参数 |

## 公共 API 函数

### 构造与初始化

```cpp
// 构造函数
SkSpriteBlitter(const SkPixmap& source);

// 设置目标和绘制参数
virtual bool setup(const SkPixmap& dst,
                   int left, int top,
                   const SkPaint& paint);
```

**参数**:
- `dst`: 目标像素缓冲区
- `left`, `top`: 源图像在目标中的位置
- `paint`: 绘制参数(alpha, 混合模式等)

**返回值**: 如果配置成功返回 `true`,否则返回 `false`(回退到通用路径)

### 核心绘制接口

```cpp
// 必须实现的纯虚函数
virtual void blitRect(int x, int y, int width, int height) = 0;
```

**功能**: 绘制矩形区域

**参数**:
- `x`, `y`: 目标坐标
- `width`, `height`: 矩形尺寸

### 禁用的接口

```cpp
// 这些函数在 SkSpriteBlitter 中不应被调用
void blitH(int x, int y, int width) override;
void blitAntiH(int x, int y, const SkAlpha[], const int16_t[]) override;
void blitV(int x, int y, int height, SkAlpha alpha) override;
void blitMask(const SkMask&, const SkIRect&) override;
```

**说明**: 这些函数在基类中实现为断言失败,强制子类只使用 `blitRect`

### 静态工厂函数

```cpp
static SkSpriteBlitter* ChooseL32(const SkPixmap& source,
                                  const SkPaint& paint,
                                  SkArenaAlloc* allocator);
```

**功能**: 为 32 位目标格式选择合适的 sprite blitter

**返回值**:
- 成功: 指向合适的 `SkSpriteBlitter` 子类实例
- 失败: `nullptr`(需要回退到通用 blitter)

## 内部实现细节

### 接口禁用实现

基类通过断言防止误用:

```cpp
void SkSpriteBlitter::blitH(int x, int y, int width) {
    SkDEBUGFAIL("how did we get here?");
    // SkSpriteBlitter 不应使用 blitH
}

void SkSpriteBlitter::blitAntiH(int x, int y,
                                const SkAlpha antialias[],
                                const int16_t runs[]) {
    SkDEBUGFAIL("how did we get here?");
}

// ... 其他类似实现
```

### 坐标系统

```cpp
// 坐标转换关系:
// - (x, y): 目标坐标
// - (x - fLeft, y - fTop): 源图像坐标

// 使用示例(在子类中):
uint32_t* dst = fDst.writable_addr32(x, y);
const uint32_t* src = fSource.addr32(x - fLeft, y - fTop);
```

### 典型子类实现模式

```cpp
class Sprite_Example : public SkSpriteBlitter {
public:
    Sprite_Example(const SkPixmap& src, ...) : SkSpriteBlitter(src) {
        // 预计算优化参数
    }

    void blitRect(int x, int y, int width, int height) override {
        // 获取源和目标指针
        auto* dst = fDst.writable_addr(...);
        auto* src = fSource.addr(...);

        // 逐行处理
        for (int row = 0; row < height; row++) {
            // 行级优化操作(可能使用 SIMD)
            process_row(dst, src, width);

            dst = (...)((char*)dst + dstRB);
            src = (...)((char*)src + srcRB);
        }
    }
};
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlitter` | 基类接口 |
| `SkPixmap` | 像素数据访问 |
| `SkPaint` | 绘制参数 |
| `SkArenaAlloc` | 快速内存分配器 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkDraw::drawBitmap` | 主要调用者 |
| `SkBitmapDevice` | 位图设备绘制 |
| `SkCanvas` | 通过设备间接调用 |

## 设计模式与设计决策

### 1. 抽象工厂模式

```cpp
// 静态工厂方法根据条件创建具体实现
SkSpriteBlitter* ChooseL32(...) {
    if (/* 满足条件 */) {
        return allocator->make<Sprite_D32_S32>(...);
    }
    return nullptr;  // 回退到通用路径
}
```

### 2. 模板方法模式

基类定义接口规范,子类实现具体算法:

```cpp
// 基类定义契约
class SkSpriteBlitter : public SkBlitter {
    virtual void blitRect(...) = 0;  // 子类实现

    // 禁用不应使用的接口
    void blitH(...) override { SkDEBUGFAIL(...); }
};
```

### 3. 策略模式

不同像素格式使用不同的 blitting 策略:
- **32位ARGB**: `Sprite_D32_S32`(可能使用 SSE2/NEON)
- **其他格式**: 各自的特化实现

### 4. 设计权衡

**为什么需要单独的 SkSpriteBlitter?**

| 方面 | SkBlitter | SkSpriteBlitter |
|------|-----------|----------------|
| 主要操作 | blitH/blitV | blitRect |
| 使用场景 | 通用扫描转换 | 矩形块传输 |
| 性能 | 灵活但较慢 | 专注优化 |
| 变换支持 | 完整 | 无(仅平移) |

**为什么禁用其他 blit 函数?**
- **接口明确**: 强制使用 `blitRect`,避免混淆
- **性能优化**: 子类可专注于矩形优化,不分散精力
- **早期错误检测**: 误用会立即触发断言

**为什么使用 SkPixmap?**
- **直接访问**: 避免通过虚函数访问像素
- **格式信息**: 包含色彩空间、alpha 类型等元数据
- **内存布局**: 提供 rowBytes 等信息,支持子图像

## 性能考量

### 1. 内存布局优化

```cpp
// fSource 和 fDst 是值成员,避免间接访问
const SkPixmap fSource;  // 直接存储,无指针跳转
SkPixmap fDst;
```

### 2. 减少虚函数调用

只有 `blitRect` 是虚函数,避免每像素虚函数开销:

```cpp
// 通用 SkBlitter: 每像素调用 blitH
for (int y = 0; y < height; y++) {
    blitter->blitH(x, y, width);  // 虚函数调用
}

// SkSpriteBlitter: 一次虚函数调用
spriteBlitter->blitRect(x, y, width, height);  // 内部无虚函数
```

### 3. SIMD 友好

矩形块传输易于 SIMD 优化:

```cpp
void blitRect(...) {
    for (int row = 0; row < height; row++) {
        // 整行处理,利于向量化
        simd_copy_row(dst, src, width);
    }
}
```

### 4. 缓存友好

连续内存访问模式:

```cpp
// 顺序访问源和目标
for (int row = 0; row < height; row++) {
    memcpy(dst, src, width * 4);  // 连续复制
    dst += dstRowBytes;
    src += srcRowBytes;
}
```

### 5. 快速路径检查

```cpp
bool setup(const SkPixmap& dst, int left, int top, const SkPaint& paint) {
    if (paint.getColorFilter() || paint.getMaskFilter()) {
        return false;  // 回退到通用路径
    }

    fDst = dst;
    fLeft = left;
    fTop = top;
    return true;
}
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkSpriteBlitter.h` | 本文件(抽象基类定义) |
| `src/core/SkSpriteBlitter_ARGB32.cpp` | 32位ARGB实现 |
| `src/core/SkBlitter.h` | 基类定义 |
| `src/core/SkDraw.cpp` | 主要调用者 |
| `src/core/SkPixmap.h` | 像素数据接口 |
| `src/core/SkBitmapDevice.cpp` | 位图设备实现 |
| `src/base/SkArenaAlloc.h` | 内存分配器 |
