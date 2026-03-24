# FuzzSkRuntimeColorFilter

> 源文件: fuzz/oss_fuzz/FuzzSkRuntimeColorFilter.cpp

## 概述

`FuzzSkRuntimeColorFilter.cpp` 是 Skia 中用于模糊测试运行时颜色滤镜(Runtime Color Filter)的工具。该模块通过 OSS-Fuzz 框架对 SkRuntimeEffect 的颜色滤镜模式进行自动化安全测试,主要验证运行时 SkSL 颜色滤镜程序的编译和执行稳定性。模糊测试器将输入字节流视为 SkSL 颜色滤镜程序,自动生成所需的 uniform 变量和子对象,并在两种编译优化模式下分别测试。

该测试工具与 `FuzzSkRuntimeBlender.cpp` 结构相似,但专注于颜色滤镜功能。

## 架构位置

- **路径**: `fuzz/oss_fuzz/FuzzSkRuntimeColorFilter.cpp`
- **模块层次**: 测试工具层 > 模糊测试子系统 > OSS-Fuzz 集成
- **测试目标**: SkRuntimeEffect 的颜色滤镜功能

## 主要类与结构体

### 核心函数

#### `FuzzSkRuntimeColorFilter_Once`
```cpp
static bool FuzzSkRuntimeColorFilter_Once(const SkString& shaderText,
                                          const SkRuntimeEffect::Options& options)
```

**功能**: 执行单次颜色滤镜模糊测试
- **编译**: 使用 `SkRuntimeEffect::MakeForColorFilter` 编译 SkSL 代码
- **创建**: 生成有效输入并创建 `SkColorFilter` 实例
- **应用**: 将滤镜应用到 `SkPaint` 并绘制
- **验证**: 在 4x4 光栅化表面上执行绘制操作

#### `FuzzSkRuntimeColorFilter`
```cpp
bool FuzzSkRuntimeColorFilter(const uint8_t *data, size_t size)
```

**功能**: 主测试入口,执行双重测试
- **第一次**: `forceUnoptimized = true` (禁用内联优化)
- **第二次**: `forceUnoptimized = false` (启用内联优化)
- **返回**: 任一测试是否成功

#### `LLVMFuzzerTestOneInput`
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
```
**功能**: LibFuzzer 入口点,输入限制 3000 字节

## 公共 API 函数

使用的 SkRuntimeEffect API:
- `SkRuntimeEffect::MakeForColorFilter()`: 创建颜色滤镜运行时效果
- `SkRuntimeEffect::makeColorFilter()`: 实例化颜色滤镜对象
- `FuzzCreateValidInputsForRuntimeEffect()`: 生成有效输入数据

使用的渲染 API:
- `SkPaint::setColorFilter()`: 应用颜色滤镜
- `SkSurfaces::Raster()`: 创建光栅化表面
- `SkCanvas::drawPaint()`: 执行绘制

## 内部实现细节

### 测试流程

```
输入字节流 → SkSL 颜色滤镜程序
    ↓
编译为 SkRuntimeEffect (优化关闭)
    ↓
生成 uniform 数据和子对象
    ↓
创建 SkColorFilter 实例
    ↓
应用到 SkPaint 并绘制 (4x4 表面)
    ↓
重复上述流程 (优化开启)
```

### 双路径测试策略

与 `FuzzSkRuntimeBlender` 相同:
- **优化禁用**: 暴露函数调用相关的问题
- **优化启用**: 测试实际生产环境的代码路径

**设计理念**: 双重测试覆盖不同编译路径,提高缺陷检测率。

### 颜色滤镜应用

```cpp
SkPaint paint;
paint.setColor(SK_ColorRED);
paint.setColorFilter(std::move(cf));
s->getCanvas()->drawPaint(paint);
```

**测试点**:
- 颜色滤镜的创建
- 滤镜应用到绘制管线
- 实际的颜色变换执行

### 最小化测试表面

```cpp
sk_sp<SkSurface> s = SkSurfaces::Raster(SkImageInfo::MakeN32Premul(4, 4));
```
使用 4x4 像素表面,最小化渲染开销,专注于滤镜逻辑测试。

## 依赖关系

**核心模块**:
- `include/core/SkCanvas.h`: 画布绘制
- `include/core/SkPaint.h`: 绘制属性(包括颜色滤镜)
- `include/core/SkShader.h`: 着色器(头文件引入)
- `include/core/SkSurface.h`: 绘制表面
- `include/effects/SkRuntimeEffect.h`: 运行时效果

**模糊测试框架**:
- `fuzz/Fuzz.h`: 模糊测试基础设施
- `fuzz/FuzzCommon.h`: 通用工具(`FuzzCreateValidInputsForRuntimeEffect`)

**GPU 支持**:
- `src/gpu/ganesh/GrShaderCaps.h`: GPU 着色器能力(间接依赖)

## 设计模式与设计决策

### 1. 双重测试模式

**理由**: 与混合器测试相同,覆盖优化和非优化路径,提高覆盖率。

### 2. 隔离执行

每次测试创建独立环境,避免状态污染。

### 3. 最小化验证

仅验证执行流程,不验证颜色变换的正确性。

### 4. 早期退出

```cpp
if (!effect) return false;
if (!cf) return false;
if (!s) return false;
```
在失败点提前退出,提高测试效率。

## 性能考量

### 1. 输入大小限制

**3000 字节**: 与混合器测试相同,控制编译时间。

### 2. 最小化渲染开销

**4x4 表面**: 最小化像素处理,专注于滤镜逻辑。

### 3. 双重测试的开销

**权衡**: 2x 时间成本 vs. 更高的缺陷检测率。

## 相关文件

### 同类型测试器

1. **`fuzz/oss_fuzz/FuzzSkRuntimeBlender.cpp`**
   - 测试运行时混合器
   - 几乎相同的测试结构

2. **`fuzz/oss_fuzz/FuzzSkRuntimeShader.cpp`** (如果存在)
   - 测试运行时着色器

### 核心依赖

3. **`fuzz/FuzzCommon.h` / `.cpp`**
   - 提供 `FuzzCreateValidInputsForRuntimeEffect`

4. **`include/effects/SkRuntimeEffect.h`**
   - SkRuntimeEffect 核心接口

5. **`src/sksl/SkSLCompiler.h`**
   - SkSL 编译器实现

### 测试文件

6. **`tests/SkRuntimeEffectTest.cpp`**
   - SkRuntimeEffect 单元测试

7. **`gm/runtimecolorfilter.cpp`** (如果存在)
   - 运行时颜色滤镜的视觉测试

该模糊测试器通过双重测试策略,为 Skia 的运行时颜色滤镜功能提供了全面的安全性测试,确保在处理任意 SkSL 程序时的稳定性,是运行时效果系统质量保证的关键组件。
