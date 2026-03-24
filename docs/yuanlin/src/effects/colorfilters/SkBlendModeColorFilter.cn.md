# SkBlendModeColorFilter - 混合模式颜色滤镜

> 源文件:
> - `src/effects/colorfilters/SkBlendModeColorFilter.h`
> - `src/effects/colorfilters/SkBlendModeColorFilter.cpp`

## 概述

`SkBlendModeColorFilter` 实现了基于混合模式（blend mode）的颜色滤镜。它将一个指定颜色通过指定的混合模式与输入源颜色进行混合。这是最常用的颜色滤镜类型之一，通过 `SkColorFilters::Blend()` 工厂函数创建。

该滤镜内部始终以 sRGB 颜色空间存储颜色，在实际执行时转换到目标颜色空间。

## 架构位置

```
include/core/SkColorFilter.h           // 公共 API
  |
  v
SkColorFilters::Blend()                // 工厂函数
  |
  v
SkBlendModeColorFilter                 // 本类
  |
  v
SkColorFilterBase -> SkColorFilter     // 继承链
```

## 主要类与结构体

### `SkBlendModeColorFilter`

继承自 `SkColorFilterBase`，为 `final` 类。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fColor` | `SkColor4f` | 混合颜色，始终存储在 sRGB 空间 |
| `fMode` | `SkBlendMode` | 混合模式 |

**公共方法：**

- `color()` - 返回存储的 sRGB 颜色
- `mode()` - 返回混合模式
- `appendStages()` - 追加光栅管线阶段
- `onIsAlphaUnchanged()` - 判断 alpha 是否不变
- `type()` - 返回 `Type::kBlendMode`

## 公共 API 函数

### `SkColorFilters::Blend()` (SkColor4f 版本)

```cpp
static sk_sp<SkColorFilter> Blend(const SkColor4f& color,
                                   sk_sp<SkColorSpace> colorSpace,
                                   SkBlendMode mode);
```

工厂函数，包含以下优化逻辑：

1. **颜色空间转换**：先将输入颜色从 `colorSpace` 转换到 sRGB 存储
2. **模式折叠**：
   - `kClear` 折叠为 `kSrc`（颜色设为透明）
   - `kSrcOver` 且 alpha=0 折叠为 `kDst`；alpha=1 折叠为 `kSrc`
3. **空操作检测**：以下情况返回 nullptr（即不创建滤镜）：
   - `kDst` 模式
   - alpha=0 且模式为 `kSrcOver`/`kDstOver`/`kDstOut`/`kSrcATop`/`kXor`/`kDarken`
   - alpha=1 且模式为 `kDstIn`

### `SkColorFilters::Blend()` (SkColor 版本)

```cpp
static sk_sp<SkColorFilter> Blend(SkColor color, SkBlendMode mode);
```

便捷版本，将 `SkColor` 转换为 `SkColor4f` 后调用上述版本。

## 内部实现细节

### `appendStages()` 实现

```cpp
bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const;
```

1. 将当前源颜色移动到目标寄存器（`move_src_dst`）
2. 将 `fColor` 从 sRGB 转换到管线目标颜色空间（unpremul -> premul）
3. 将转换后的颜色作为常量追加到管线
4. 调用 `SkBlendMode_AppendStages()` 追加混合操作

### `onIsAlphaUnchanged()`

仅在以下两种混合模式下返回 `true`：
- `kDst`：结果为 `[Da, Dc]`，alpha 不变
- `kSrcATop`：结果为 `[Da, Sc * Da + (1 - Sa) * Dc]`，alpha 不变

### 序列化/反序列化

- `flatten()`：写入 `SkColor4f` 和混合模式
- `CreateProc()`：读取时根据 SKP 版本决定是读 8-bit 还是 32-bit 颜色
  - 旧版本（`< kBlend4fColorFilter`）：读取 `SkColor`（8-bit sRGB）
  - 新版本：读取 `SkColor4f`（32-bit sRGB）

## 依赖关系

- `SkColorFilterBase`：基类
- `SkBlendModePriv.h`：`SkBlendMode_AppendStages()` 函数
- `SkColorSpaceXformSteps`：颜色空间转换
- `SkRasterPipeline`：光栅管线操作
- `SkPicturePriv`：版本常量（`kBlend4fColorFilter`）

## 设计模式与设计决策

1. **颜色空间标准化**：颜色始终存储在 sRGB 中，延迟到执行时转换到目标空间，简化序列化
2. **工厂方法中的优化**：在创建时即检测空操作，避免不必要的滤镜对象分配
3. **向后兼容**：`CreateProc` 支持旧版 8-bit 颜色格式的 SKP 文件
4. **旧名称兼容**：注册 `SkModeColorFilter` 旧名称以兼容历史 SKP

## 性能考量

1. **空操作消除**：工厂函数中检测各种空操作情况，直接返回 nullptr
2. **模式折叠**：将复杂模式在创建时折叠为更简单的模式
3. **管线效率**：使用三阶段（move_src_dst、constant_color、blend）实现，管线操作最少化

### 管线执行流程图

```
输入源颜色 (src 寄存器)
  |
  v
move_src_dst          -> 源颜色移到 dst 寄存器
  |
  v
色彩空间转换           -> fColor: sRGB unpremul -> dstCS premul
  |
  v
appendConstantColor   -> 转换后的颜色放入 src 寄存器
  |
  v
SkBlendMode_AppendStages -> 执行混合操作 (src op dst -> src)
  |
  v
混合结果 (src 寄存器)
```

### 空操作检测完整表

以下组合被检测为空操作（工厂返回 nullptr）：

| 条件 | 说明 |
|------|------|
| mode == kDst | 结果始终为目标颜色 |
| alpha=0, mode=kSrcOver | 透明色覆盖无效果 |
| alpha=0, mode=kDstOver | 透明色在下方无效果 |
| alpha=0, mode=kDstOut | 透明色排除无效果 |
| alpha=0, mode=kSrcATop | 透明色在上方无效果 |
| alpha=0, mode=kXor | 透明色异或无效果 |
| alpha=0, mode=kDarken | 透明色变暗无效果 |
| alpha=1, mode=kDstIn | 不透明色内部无效果 |

### 序列化格式

**新版本格式（>= kBlend4fColorFilter）：**
```
[SkColor4f: 16 bytes] [uint32_t mode: 4 bytes]
```

**旧版本格式：**
```
[SkColor: 4 bytes] [uint32_t mode: 4 bytes]
```

## 相关文件

- `include/core/SkColorFilter.h` - `SkColorFilters::Blend()` 公共声明
- `src/effects/colorfilters/SkColorFilterBase.h` - 基类
- `src/core/SkBlendModePriv.h` - 混合模式管线追加
- `src/core/SkColorSpaceXformSteps.h` - 色彩空间转换
- `src/core/SkPicturePriv.h` - 版本常量
- `src/core/SkValidationUtils.h` - 模式验证
