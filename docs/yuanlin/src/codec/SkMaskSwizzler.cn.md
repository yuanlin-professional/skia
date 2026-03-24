# SkMaskSwizzler - 位掩码像素格式转换器

> 源文件: `src/codec/SkMaskSwizzler.h`, `src/codec/SkMaskSwizzler.cpp`

## 概述

`SkMaskSwizzler` 是专门用于解码使用位掩码定义像素分量的 BMP 图像的像素格式转换器。与 `SkSwizzler` 处理固定格式编码不同，`SkMaskSwizzler` 使用 `SkMasks` 对象在运行时从任意位掩码中提取红、绿、蓝和 Alpha 分量。该类当前仅被 BMP 位掩码编解码器使用，支持 16 位、24 位和 32 位的掩码像素格式。

## 架构位置

```
SkSampler (采样基类)
  └── SkMaskSwizzler
        └── SkMasks (位掩码提取器, 非所有权)
```

该类被 `SkBmpMaskCodec` 使用。

## 主要类与结构体

### `SkMaskSwizzler`
- 继承自 `SkSampler`
- 使用函数指针 (`RowProc`) 进行行处理
- 持有 `SkMasks` 的非所有权指针
- 管理子集宽度、采样率和起始偏移

### `RowProc` 类型定义
```cpp
typedef void (*RowProc)(void* dstRow, const uint8_t* srcRow, int width,
    SkMasks* masks, uint32_t startX, uint32_t sampleX);
```

## 公共 API 函数

### 工厂方法
- `static CreateMaskSwizzler(const SkImageInfo&, bool srcIsOpaque, SkMasks*, uint32_t bitsPerPixel, const SkCodec::Options&)`: 创建掩码转换器，根据位深度、目标颜色类型、不透明度和 Alpha 类型选择最佳的行处理函数。

### 操作
- `swizzle(void* dst, const uint8_t* src)`: 转换一行像素
- `swizzleWidth()`: 返回目标宽度
- `fillWidth()`: 返回填充宽度（用于 SkSampler 接口）

## 内部实现细节

### 行处理函数矩阵
按位深度（16/24/32）x 目标格式（RGBA/BGRA/565）x Alpha 处理（opaque/unpremul/premul）组织，共 21 个行处理函数：

| 位深度 | 目标格式 | Alpha | 函数 |
|---|---|---|---|
| 16 bit | RGBA_8888 | opaque | `swizzle_mask16_to_rgba_opaque` |
| 16 bit | RGBA_8888 | unpremul | `swizzle_mask16_to_rgba_unpremul` |
| 16 bit | RGBA_8888 | premul | `swizzle_mask16_to_rgba_premul` |
| 16 bit | BGRA_8888 | opaque | `swizzle_mask16_to_bgra_opaque` |
| ... | ... | ... | ... |
| 32 bit | RGB_565 | - | `swizzle_mask32_to_565` |

### 16 位处理
直接从 `uint16_t*` 读取像素值，通过 `masks->getRed/Green/Blue/Alpha` 提取分量。

### 24 位处理
从三个字节手动构造 `uint32_t`：
```cpp
uint32_t p = srcRow[0] | (srcRow[1] << 8) | srcRow[2] << 16;
```
源指针按 `3 * sampleX` 步进。

### 32 位处理
直接从 `uint32_t*` 读取像素值，处理逻辑与 16 位类似。

### 采样支持
通过 `startX` 和 `sampleX` 参数实现采样。`onSetSampleX` 更新：
- `fSampleX`: X 采样率
- `fX0`: 起始坐标（`GetStartCoord(sampleX) + fSrcOffset`）
- `fDstWidth`: 采样后的目标宽度

### 子集支持
通过 `options.fSubset` 指定源偏移和源宽度。

## 依赖关系

- `SkSampler`: 采样基类
- `SkMasks`: 位掩码提取器
- `SkCodecPriv`: 工具函数（预乘、坐标计算）
- `SkColorData`: 颜色打包函数
- `SkImageInfo`: 图像信息

## 设计模式与设计决策

### 策略模式
与 `SkSwizzler` 类似，通过函数指针选择行处理策略，避免运行时分支。

### 非所有权指针
`SkMasks` 使用非所有权指针，由外部（`SkBmpMaskCodec`）管理其生命周期。

### 与 SkSwizzler 的关系
注释中提到两者有大量相似的字段和逻辑，未来可能进行代码合并。目前保持独立是因为 `SkMaskSwizzler` 需要 `SkMasks` 参数，而 `SkSwizzler` 不需要。

### 工厂方法返回裸指针
`CreateMaskSwizzler` 返回裸指针而非 `unique_ptr`，这是旧式接口。

## 性能考量

- 每行处理使用直接的指针算术和位操作，开销极小
- 16 位和 32 位路径使用类型化指针访问，可能受益于编译器优化
- 24 位路径需要手动字节组装，相对较慢
- 采样直接通过指针步进跳过像素，无需额外的条件判断
- 目标为 565 格式时省略 Alpha 提取，减少一次掩码操作

## 相关文件

- `src/codec/SkBmpMaskCodec.h` / `.cpp`: 使用此转换器的 BMP 掩码编解码器
- `src/core/SkMasks.h` / `.cpp`: 位掩码提取器
- `src/codec/SkSwizzler.h` / `.cpp`: 通用像素格式转换器
- `src/codec/SkSampler.h`: 采样基类
- `src/codec/SkCodecPriv.h`: 编解码器私有工具
