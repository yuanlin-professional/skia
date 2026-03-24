# SkColorFilterBase - 颜色滤镜基类

> 源文件:
> - `src/effects/colorfilters/SkColorFilterBase.h`
> - `src/effects/colorfilters/SkColorFilterBase.cpp`

## 概述

`SkColorFilterBase` 是 Skia 中所有颜色滤镜的内部基类，继承自公共 API 类 `SkColorFilter`。它定义了颜色滤镜子类必须实现的核心接口，包括将滤镜操作追加到光栅管线（raster pipeline）的能力，以及类型标识、序列化和单色过滤等功能。

该文件还提供了类型安全的向下转型辅助函数 `as_CFB()`，用于在 Skia 内部代码中将 `SkColorFilter` 转换为 `SkColorFilterBase`。

## 架构位置

```
include/core/SkColorFilter.h          // 公共 API
  |
  v
src/effects/colorfilters/
  SkColorFilterBase.h                   // 内部基类（本文件）
  |
  +-- SkBlendModeColorFilter.h          // 混合模式颜色滤镜
  +-- SkColorSpaceXformColorFilter.h    // 色彩空间变换滤镜
  +-- SkComposeColorFilter               // 组合滤镜
  +-- SkMatrixColorFilter               // 矩阵颜色滤镜
  +-- SkRuntimeColorFilter              // 运行时颜色滤镜
  +-- SkTableColorFilter                // 查表颜色滤镜
  +-- SkWorkingFormatColorFilter         // 工作格式滤镜
```

## 主要类与结构体

### `SkColorFilterBase`

继承自 `SkColorFilter`（公共类），是所有内部颜色滤镜实现的基类。

**枚举类型 `Type`：**

```cpp
enum class Type {
    kNoop,
    kBlendMode,
    kColorSpaceXform,
    kCompose,
    kGaussian,
    kMatrix,
    kRuntime,
    kTable,
    kWorkingFormat,
};
```

通过宏 `SK_ALL_COLOR_FILTERS(M)` 自动展开所有颜色滤镜类型。

### 辅助函数

| 函数 | 说明 |
|------|------|
| `as_CFB(SkColorFilter*)` | 将指针向下转型为 `SkColorFilterBase*` |
| `as_CFB(const SkColorFilter*)` | const 版本 |
| `as_CFB(const sk_sp<SkColorFilter>&)` | 智能指针版本 |
| `as_CFB_sp(sk_sp<SkColorFilter>)` | 将智能指针转型为 `sk_sp<SkColorFilterBase>` |

## 公共 API 函数

### 纯虚函数

```cpp
virtual bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const = 0;
```
将滤镜操作追加到光栅管线。子类必须实现此方法。参数 `shaderIsOpaque` 提示输入是否不透明，允许优化（如跳过 premul/unpremul 转换）。

```cpp
virtual Type type() const = 0;
```
返回滤镜的具体类型标识。

### 虚函数（带默认实现）

```cpp
virtual bool onIsAlphaUnchanged() const { return false; }
```
返回滤镜是否不修改 alpha 通道。默认返回 `false`。

```cpp
virtual SkRuntimeEffect* asRuntimeEffect() const { return nullptr; }
```
如果滤镜是 runtime effect，返回对应指针；否则返回 nullptr。

### 关键成员方法

```cpp
bool affectsTransparentBlack() const;
```
判断滤镜是否会改变透明黑色。通过实际调用 `filterColor4f(SkColors::kTransparent)` 来测试。

```cpp
virtual SkPMColor4f onFilterColor4f(const SkPMColor4f& color, SkColorSpace* dstCS) const;
```
对单个颜色值应用滤镜。默认实现使用 `SkRasterPipeline` 进行模拟执行。

### 受保护的虚函数

```cpp
virtual bool onAsAColorMatrix(float[20]) const;
virtual bool onAsAColorMode(SkColor* color, SkBlendMode* bmode) const;
```
尝试将滤镜表示为颜色矩阵或颜色模式。默认都返回 `false`。

## 内部实现细节

### `onFilterColor4f` 默认实现

当子类没有直接重写 `onFilterColor4f` 时，基类使用光栅管线模拟执行：

1. 分配栈上 arena（2048 字节，足够小型 SkSL 程序使用）
2. 创建 `SkRasterPipeline` 并追加常量颜色
3. 构建 `SkStageRec` 并调用 `appendStages()`
4. 追加 `store_f32` 操作，运行管线处理 1 像素
5. 返回过滤后的颜色

### Flattenable 注册函数

文件声明了所有内部颜色滤镜的注册函数：

- `SkRegisterComposeColorFilterFlattenable()`
- `SkRegisterMatrixColorFilterFlattenable()`
- `SkRegisterModeColorFilterFlattenable()`
- `SkRegisterSkColorSpaceXformColorFilterFlattenable()`
- `SkRegisterTableColorFilterFlattenable()`
- `SkRegisterWorkingFormatColorFilterFlattenable()`

## 依赖关系

### 内部依赖

- `SkColorFilter`：公共基类
- `SkFlattenable`：序列化/反序列化支持
- `SkRasterPipeline`：光栅管线执行
- `SkStageRec`：管线阶段记录
- `SkColorData.h` / `SkColor.h`：颜色类型定义

### 被依赖

所有内部颜色滤镜子类都继承此基类。

## 设计模式与设计决策

1. **桥接模式**：`SkColorFilter`（公共接口）与 `SkColorFilterBase`（内部实现）分离，隐藏实现细节
2. **类型枚举**：使用 `Type` 枚举和 `SK_ALL_COLOR_FILTERS` 宏进行类型标识，便于类型分发
3. **模板方法模式**：`onFilterColor4f` 提供了基于 raster pipeline 的默认实现，子类可选择重写
4. **向下转型辅助**：提供类型安全的 `as_CFB()` 系列函数，避免裸 `static_cast`

## 性能考量

1. **`onFilterColor4f` 默认实现**：使用栈分配的 2048 字节 arena，避免堆分配
2. **`affectsTransparentBlack()`**：通过实际过滤一个像素来判断，虽简单但每次调用都会创建临时管线
3. **`shaderIsOpaque` 提示**：允许子类在已知输入不透明时跳过 premul/unpremul 转换

## 相关文件

- `include/core/SkColorFilter.h` - 公共 API 类
- `src/effects/colorfilters/SkBlendModeColorFilter.h` - 混合模式滤镜
- `src/effects/colorfilters/SkColorSpaceXformColorFilter.h` - 色彩空间变换滤镜
- `src/core/SkRasterPipeline.h` - 光栅管线
- `src/core/SkEffectPriv.h` - `SkStageRec` 定义
