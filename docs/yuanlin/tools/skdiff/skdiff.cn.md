# skdiff

> 源文件
> - tools/skdiff/skdiff.h
> - tools/skdiff/skdiff.cpp

## 概述

`skdiff` 是 Skia 图像差异比较工具的核心模块，提供了图像对比分析的数据结构、算法和接口。该模块定义了差异比较的核心概念（资源、记录、结果类型）、像素级差异计算逻辑、以及多种差异度量方法。它是整个 skdiff 工具的理论和算法基础，被主程序、HTML 生成器和工具函数模块使用。

该模块的核心功能是逐像素比较两幅图像，计算差异统计指标（差异像素比例、平均颜色差异、最大颜色差异等），生成可视化差异图像（彩色差异图和黑白掩码图），并提供多种排序方法用于结果呈现。

## 架构位置

该模块位于 Skia 工具层的图像差异比较工具中：

```
skia/
├── tools/
│   └── skdiff/
│       ├── skdiff.h               # 本模块头文件（核心接口）
│       ├── skdiff.cpp             # 本模块实现（差异计算）
│       ├── skdiff_utils.h         # 工具函数
│       ├── skdiff_html.h          # HTML 报告生成
│       └── skdiff_main.cpp        # 主程序入口
├── include/
│   └── core/
│       ├── SkBitmap.h             # 位图类
│       └── SkColor.h              # 颜色定义
```

该模块的架构角色：
- **核心层**：提供差异比较的数据结构和算法
- **被广泛使用**：所有其他 skdiff 模块依赖本模块
- **独立性**：不依赖其他 skdiff 模块，仅依赖 Skia 核心

## 主要类与结构体

### DiffResource

表示差异比较中的单个资源（图像）。

**成员变量：**
- `SkString fFilename`：文件名
- `SkString fFullPath`：完整路径
- `SkBitmap fBitmap`：位图数据
- `Status fStatus`：资源状态

**Status 枚举：**
- `kDecoded_Status`：已解码
- `kCouldNotDecode_Status`：解码失败
- `kRead_Status`：已读取
- `kCouldNotRead_Status`：读取失败
- `kExists_Status`：文件存在
- `kDoesNotExist_Status`：文件不存在
- `kSpecified_Status`：已指定
- `kUnspecified_Status`：未指定
- `kUnknown_Status`：未知状态

**静态方法：**
```cpp
static Status getStatusByName(const char *name);
static const char *getStatusDescription(Status status);
static bool isStatusFailed(Status status);
static bool getMatchingStatuses(char* selector, bool statuses[kStatusCount]);
```

### DiffRecord

表示一对图像的完整差异比较记录。

**成员变量：**

**资源：**
- `DiffResource fBase`：基准图像
- `DiffResource fComparison`：比较图像
- `DiffResource fDifference`：差异图像（彩色）
- `DiffResource fWhite`：白色背景差异图像（黑白掩码）

**差异统计指标：**
- `float fFractionDifference`：差异像素比例（0.0-1.0）
- `float fWeightedFraction`：加权差异比例（基于 HSV 值）
- `float fAverageMismatchA/R/G/B`：平均 ARGB 差异
- `uint32_t fTotalMismatchA`：总 Alpha 差异
- `uint32_t fMaxMismatchA/R/G/B`：最大 ARGB 差异

**Result 枚举：**
- `kEqualBits_Result`：字节完全相同
- `kEqualPixels_Result`：像素值相同（但字节可能不同）
- `kDifferentPixels_Result`：存在像素差异
- `kDifferentSizes_Result`：尺寸不同
- `kCouldNotCompare_Result`：无法比较
- `kUnknown_Result`：未知结果

**静态方法：**
```cpp
static Result getResultByName(const char *name);
static const char *getResultDescription(Result result);
```

### 比较器类

用于 `qsort` 的比较器，支持多种排序策略：

**CompareDiffMetrics**
按 `fFractionDifference` 降序排列。

**CompareDiffWeighted**
按 `fWeightedFraction` 降序排列。

**CompareDiffMeanMismatches**
按 `max(fAverageMismatchR, G, B)` 降序排列。

**CompareDiffMaxMismatches**
按 `max(fMaxMismatchR, G, B)` 降序排列，平局时按平均值排序。

**通用 compare 模板：**
```cpp
template<typename T> int compare(const void* untyped_lhs, const void* untyped_rhs);
```
应用一阶排序（按 `fResult`）、像素比较（按 `T::comparePixels`）、平局决胜（按文件名）。

## 公共 API 函数

### compute_diff

```cpp
void compute_diff(DiffRecord* dr,
                  DiffMetricProc diffFunction,
                  const int colorThreshold);
```

**功能：** 计算两幅图像的像素级差异。

**参数：**
- `dr`：差异记录指针（输入/输出）
- `diffFunction`：差异度量函数指针
- `colorThreshold`：颜色差异阈值（0-255）

**前提条件：**
- `dr->fBase.fBitmap` 和 `dr->fComparison.fBitmap` 已解码
- `dr->fDifference.fBitmap` 和 `dr->fWhite.fBitmap` 已分配相同尺寸

**后置条件：**
- `dr->fResult` 被设置为具体结果
- 差异统计指标被计算
- 差异图像被生成

**实现算法：**

1. **尺寸检查**
   ```cpp
   if (w != dr->fBase.fBitmap.width() || h != dr->fBase.fBitmap.height()) {
       dr->fResult = DiffRecord::kDifferentSizes_Result;
       return;
   }
   ```

2. **逐像素比较**
   ```cpp
   for (int y = 0; y < h; y++) {
       for (int x = 0; x < w; x++) {
           SkPMColor c0 = *dr->fBase.fBitmap.getAddr32(x, y);
           SkPMColor c1 = *dr->fComparison.fBitmap.getAddr32(x, y);
           SkPMColor outputDifference = diffFunction(c0, c1);
           // 计算各通道差异
           uint32_t thisA = SkAbs32(SkGetPackedA32(c0) - SkGetPackedA32(c1));
           uint32_t thisR = SkAbs32(SkGetPackedR32(c0) - SkGetPackedR32(c1));
           uint32_t thisG = SkAbs32(SkGetPackedG32(c0) - SkGetPackedG32(c1));
           uint32_t thisB = SkAbs32(SkGetPackedB32(c0) - SkGetPackedB32(c1));
           // 累加统计
           totalMismatchA += thisA;
           totalMismatchR += thisR;
           totalMismatchG += thisG;
           totalMismatchB += thisB;
           // 加权差异（基于 HSV 值）
           int value = MAX3(thisR, thisG, thisB);
           dr->fWeightedFraction += ((float) value) / 255;
           // 更新最大值
           dr->fMaxMismatchA = std::max(dr->fMaxMismatchA, thisA);
           // ...
       }
   }
   ```

3. **阈值判断**
   ```cpp
   if (!colors_match_thresholded(c0, c1, colorThreshold)) {
       mismatchedPixels++;
       *dr->fDifference.fBitmap.getAddr32(x, y) = outputDifference;
       *dr->fWhite.fBitmap.getAddr32(x, y) = PMCOLOR_WHITE;
   } else {
       *dr->fDifference.fBitmap.getAddr32(x, y) = 0;
       *dr->fWhite.fBitmap.getAddr32(x, y) = PMCOLOR_BLACK;
   }
   ```

4. **结果判定**
   ```cpp
   if (0 == mismatchedPixels) {
       dr->fResult = DiffRecord::kEqualPixels_Result;
   } else {
       dr->fResult = DiffRecord::kDifferentPixels_Result;
   }
   ```

5. **统计计算**
   ```cpp
   dr->fFractionDifference = ((float) mismatchedPixels) / pixelCount;
   dr->fWeightedFraction /= pixelCount;
   dr->fAverageMismatchA = ((float) totalMismatchA) / pixelCount;
   // ...
   ```

### DiffMetricProc

```cpp
typedef SkPMColor (*DiffMetricProc)(SkPMColor, SkPMColor);
```

**功能：** 差异度量函数类型，计算两个像素的差异颜色。

**标准实现：**
```cpp
static inline SkPMColor compute_diff_pmcolor(SkPMColor c0, SkPMColor c1) {
    int dr = SkGetPackedR32(c0) - SkGetPackedR32(c1);
    int dg = SkGetPackedG32(c0) - SkGetPackedG32(c1);
    int db = SkGetPackedB32(c0) - SkGetPackedB32(c1);
    return SkPackARGB32(0xFF, SkAbs32(dr), SkAbs32(dg), SkAbs32(db));
}
```

计算各通道的绝对差值，Alpha 固定为 255。

## 内部实现细节

### 颜色匹配阈值

```cpp
static inline bool colors_match_thresholded(SkPMColor c0, SkPMColor c1,
                                           const int threshold) {
    int da = SkGetPackedA32(c0) - SkGetPackedA32(c1);
    int dr = SkGetPackedR32(c0) - SkGetPackedR32(c1);
    int dg = SkGetPackedG32(c0) - SkGetPackedG32(c1);
    int db = SkGetPackedB32(c0) - SkGetPackedB32(c1);

    return ((SkAbs32(da) <= threshold) &&
            (SkAbs32(dr) <= threshold) &&
            (SkAbs32(dg) <= threshold) &&
            (SkAbs32(db) <= threshold));
}
```

**功能：** 判断两个颜色是否在阈值范围内匹配。

**用途：** 允许容忍小的颜色差异（如压缩伪影、浮点精度问题）。

### 加权差异计算

```cpp
int value = MAX3(thisR, thisG, thisB);
dr->fWeightedFraction += ((float) value) / 255;
```

**原理：** 使用 HSV 颜色空间的 Value（值）作为权重。

**优势：** 强调感知上更明显的差异。

### 差异图像生成

**彩色差异图（fDifference）：**
- 差异像素：显示为 RGB 差异的绝对值
- 相同像素：显示为黑色（0）

**黑白掩码图（fWhite）：**
- 差异像素：显示为白色
- 相同像素：显示为黑色

**用途：** 黑白掩码便于快速识别差异区域。

### 状态匹配器

```cpp
bool DiffResource::getMatchingStatuses(char* selector, bool statuses[kStatusCount]);
```

**功能：** 根据选择器字符串设置状态掩码。

**选择器语法：**
- `"any"`：所有状态
- `"failed"`：所有失败状态
- `"Decoded,Exists"`：逗号分隔的状态名列表

**用途：** 命令行参数解析，过滤要显示的记录。

## 依赖关系

### 外部依赖

**Skia 核心：**
- `SkBitmap`：位图操作
- `SkColor`、`SkPMColor`：颜色类型
- `SkColorPriv.h`：颜色通道提取宏
- `SkTypes.h`：基础类型
- `SkString`：字符串类
- `SkTArray`：数组容器

**标准库：**
- `<cstring>`：`strcmp`、`strchr`、`strlen`

### 被依赖关系

该模块被以下组件使用：
- `skdiff_main.cpp`：主程序
- `skdiff_utils.cpp`：工具函数
- `skdiff_html.cpp`：HTML 生成器

## 设计模式与设计决策

### 设计模式

1. **策略模式**
   - `DiffMetricProc` 函数指针
   - 可插拔的差异度量算法

2. **模板方法模式**
   - `compare<T>` 模板函数
   - 统一的排序框架

3. **状态模式**
   - `DiffResource::Status` 枚举
   - `DiffRecord::Result` 枚举

### 设计决策

1. **多种差异度量**
   - 差异像素比例（简单直观）
   - 加权差异（感知优化）
   - 平均/最大颜色差异（详细分析）

2. **阈值机制**
   - 允许容忍小差异
   - 处理浮点精度问题
   - 处理压缩伪影

3. **两种差异图像**
   - 彩色图：显示差异细节
   - 黑白图：快速定位差异区域

4. **分层状态系统**
   - 从高级到低级：Decoded → Read → Exists → Specified
   - 便于诊断问题

5. **多重排序策略**
   - 一阶排序：按结果类型
   - 二阶排序：按差异度量
   - 平局决胜：按文件名

## 性能考量

### 优势

1. **逐像素处理**
   - 单次遍历计算所有指标
   - 避免多次遍历

2. **整数运算**
   - 差异计算使用整数
   - 仅在最后除法转浮点

### 潜在瓶颈

1. **大图像处理**
   - O(width × height) 复杂度
   - 大分辨率图像慢

2. **内存访问**
   - 逐像素随机访问
   - 缓存命中率低

### 优化建议

- 使用 SIMD 指令并行处理
- 分块处理提高缓存命中
- 多线程处理多对图像
- 早期退出（差异过大时）

## 相关文件

**同模块文件：**
- `tools/skdiff/skdiff_utils.h`：工具函数
- `tools/skdiff/skdiff_html.h`：HTML 生成
- `tools/skdiff/skdiff_main.cpp`：主程序

**Skia 核心：**
- `include/core/SkBitmap.h`：位图类
- `include/core/SkColor.h`：颜色定义
- `src/core/SkColorPriv.h`：颜色私有接口

**相关工具：**
- `tools/viewer/`：可视化工具
- `gm/`：Golden Master 测试
