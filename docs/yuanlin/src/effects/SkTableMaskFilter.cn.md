# SkTableMaskFilter

> 源文件
> - include/effects/SkTableMaskFilter.h
> - src/effects/SkTableMaskFilter.cpp

## 概述

`SkTableMaskFilter` 是 Skia 图形库中用于对遮罩(mask)的 Alpha 通道进行查找表(LUT)变换的滤镜。该滤镜接受一个 256 元素的映射表,将每个输入 Alpha 值(0-255)映射到新的输出 Alpha 值。通过不同的映射表,可以实现伽马校正、对比度调整、阈值化、色调反转等多种遮罩效果。

**重要提示:**该类已被标记为 DEPRECATED(废弃),将在未来的 Skia 版本中移除。建议使用更现代的颜色滤镜和图像滤镜替代。尽管如此,该类仍然展示了重要的查找表变换技术,在遗留代码和特定场景中仍有应用价值。

## 架构位置

`SkTableMaskFilter` 位于 Skia 特效模块的遮罩处理层:

- 位于 `include/effects/` 公共接口目录
- 内部实现类 `SkTableMaskFilterImpl` 位于源文件中
- 继承自 `SkMaskFilterBase` → `SkMaskFilter`
- 可转换为 `SkImageFilter`(通过 `SkColorFilters::TableARGB`)
- 主要用于文本渲染、抗锯齿处理等遮罩操作
- 与 `SkMask` 数据结构紧密集成

## 主要类与结构体

### SkTableMaskFilter

**继承关系:**
- 这是一个工厂类,不可实例化(构造函数被删除)
- 提供静态工厂方法和工具函数

### SkTableMaskFilterImpl(内部实现类)

**继承关系:**
- 基类:`SkMaskFilterBase` → `SkMaskFilter` → `SkFlattenable`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTable` | `uint8_t[256]` | 查找表,fTable[i] 为输入值 i 的输出映射 |

**类型:**
```cpp
SkMaskFilterBase::Type type() const override {
    return SkMaskFilterBase::Type::kTable;
}
```

## 公共 API 函数

### Create (DEPRECATED)

```cpp
static SkMaskFilter* Create(const uint8_t table[256]);
```

从查找表创建遮罩滤镜:

- **参数:**256 字节的查找表数组
- **返回:**原始指针(旧式 API),由调用者负责管理生命周期
- **行为:**复制查找表到内部存储

**使用示例:**
```cpp
uint8_t table[256];
// 填充查找表...
SkMaskFilter* filter = SkTableMaskFilter::Create(table);
// 使用后需要手动释放
delete filter;
```

### CreateGamma (DEPRECATED)

```cpp
static SkMaskFilter* CreateGamma(SkScalar gamma);
```

创建伽马校正滤镜:

- **参数:**伽马值,典型范围 0.5-3.0
- **返回:**配置好的滤镜
- **原理:**应用幂函数 `output = input^gamma`

**伽马效果:**
- `gamma < 1.0`:提亮(增加低值)
- `gamma = 1.0`:无变化(恒等)
- `gamma > 1.0`:变暗(压缩低值)

**使用示例:**
```cpp
// 提亮效果(伽马 0.5)
auto filter = SkTableMaskFilter::CreateGamma(0.5f);

// 变暗效果(伽马 2.2)
auto filter2 = SkTableMaskFilter::CreateGamma(2.2f);
```

### CreateClip (DEPRECATED)

```cpp
static SkMaskFilter* CreateClip(uint8_t min, uint8_t max);
```

创建裁剪滤镜:

- **参数:**
  - `min`:最小阈值,低于此值的被裁剪为 0
  - `max`:最大阈值,高于此值的被裁剪为 255
- **返回:**配置好的滤镜
- **行为:**将 [min, max] 区间重新缩放到 [0, 255]

**使用示例:**
```cpp
// 裁剪低 Alpha 值(去除弱边缘)
auto filter = SkTableMaskFilter::CreateClip(50, 255);

// 提取中间范围并重新缩放
auto filter2 = SkTableMaskFilter::CreateClip(64, 192);
```

### 工具函数

#### MakeGammaTable

```cpp
static void MakeGammaTable(uint8_t table[256], SkScalar gamma);
```

生成伽马校正查找表:

```cpp
for (int i = 0; i < 256; i++) {
    float x = i / 255.0f;
    table[i] = clamp(round(pow(x, gamma) * 255), 0, 255);
}
```

#### MakeClipTable

```cpp
static void MakeClipTable(uint8_t table[256], uint8_t min, uint8_t max);
```

生成裁剪查找表:

- `[0, min]` → 0(裁剪为黑)
- `[min, max]` → [0, 255](线性重映射)
- `[max, 255]` → 255(裁剪为白)

**实现:**
```cpp
SkFixed scale = (1 << 16) * 255 / (max - min);
memset(table, 0, min + 1);
for (int i = min + 1; i < max; i++) {
    table[i] = SkFixedRoundToInt(scale * (i - min));
}
memset(table + max, 255, 256 - max);
```

## 内部实现细节

### filterMask 实现

```cpp
bool filterMask(SkMaskBuilder* dst, const SkMask& src,
                const SkMatrix&, SkIPoint* margin) const override;
```

核心遮罩变换逻辑:

**处理流程:**

1. **格式检查:**只处理 `kA8_Format`(8 位 Alpha)遮罩
2. **设置输出遮罩:**
   - 边界 = 源边界
   - 行字节 = 4 字节对齐的宽度
   - 格式 = `kA8_Format`
3. **分配输出缓冲区:**如果源有图像数据
4. **逐像素变换:**
   - 外层循环:遍历所有行
   - 内层循环:遍历行内所有像素
   - 应用查找表:`dstP[x] = table[srcP[x]]`
5. **填充对齐字节:**将行末的填充字节置零
6. **设置边距:**为 0(滤镜不扩展遮罩)

**关键代码:**
```cpp
const uint8_t* table = fTable;
for (int y = dst->fBounds.height() - 1; y >= 0; --y) {
    for (int x = dstWidth - 1; x >= 0; --x) {
        dstP[x] = table[srcP[x]];  // 查找表映射
    }
    srcP += src.fRowBytes;
    dstP += dstWidth;
    for (int i = extraZeros - 1; i >= 0; --i) {
        *dstP++ = 0;  // 填充对齐字节
    }
}
```

### 4 字节对齐

```cpp
dst->rowBytes() = SkAlign4(dst->fBounds.width());
int extraZeros = dst->fRowBytes - dstWidth;
```

**原因:**
- 提高内存访问效率(SIMD、缓存行对齐)
- 某些平台的 blitter 要求对齐
- 避免未初始化内存被读取

### asImageFilter 转换

```cpp
std::pair<sk_sp<SkImageFilter>, bool> asImageFilter(const SkMatrix&,
                                                     const SkPaint&) const override;
```

将遮罩滤镜转换为图像滤镜:

```cpp
sk_sp<SkColorFilter> colorFilter = SkColorFilters::TableARGB(
    fTable,   // Alpha 表
    nullptr,  // Red 表(不变)
    nullptr,  // Green 表(不变)
    nullptr   // Blue 表(不变)
);
return std::make_pair(SkImageFilters::ColorFilter(colorFilter, nullptr), false);
```

**用途:**
- 将遮罩滤镜应用到全彩图像
- 只影响 Alpha 通道,RGB 通道不变
- 支持图像滤镜管线

### 序列化支持

```cpp
void flatten(SkWriteBuffer& wb) const override;
sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer);
```

序列化查找表:
- 写入:256 字节数组
- 读取:读取 256 字节并创建滤镜
- 向后兼容旧名称("SkTableMF")

### RegisterFlattenables

```cpp
void RegisterFlattenables() {
    SK_REGISTER_FLATTENABLE(SkTableMaskFilterImpl);
    SkFlattenable::Register("SkTableMF", SkTableMaskFilterImpl::CreateProc);
}
```

注册序列化工厂:
- 新名称:SkTableMaskFilterImpl
- 旧名称:SkTableMF(向后兼容)

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkMaskFilter` | 遮罩滤镜基类 |
| `SkMask` / `SkMaskBuilder` | 遮罩数据结构 |
| `SkColorFilter` | 转换为颜色滤镜 |
| `SkImageFilter` | 转换为图像滤镜 |
| `SkAlign` | 内存对齐工具 |
| `SkFixed` | 定点数计算 |
| `SkTPin` | 数值钳制 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| 文本渲染系统 | 遮罩后处理(伽马、锐化) |
| 抗锯齿处理 | Alpha 调整 |
| 遗留代码 | 旧版遮罩效果 |

**注意:**由于已废弃,新代码应避免依赖该类。

## 设计模式与设计决策

### 工厂方法模式

提供多种工厂方法:
- `Create`:通用方法,接受自定义表
- `CreateGamma`:便捷方法,自动生成伽马表
- `CreateClip`:便捷方法,自动生成裁剪表

### 策略模式

通过不同的查找表实现不同策略:
- 伽马校正策略
- 裁剪策略
- 自定义映射策略

### 查找表优化

使用预计算的查找表:
- **优势:**
  - 查找操作 O(1),非常快速
  - 避免重复计算(如幂函数)
  - 缓存友好(256 字节,一个缓存行)
- **劣势:**
  - 只支持 8 位输入
  - 需要内存存储表(256 字节/滤镜)
  - 灵活性受限

### 就地处理

不修改源遮罩,创建新输出:
- 保持输入不变(纯函数)
- 支持多次应用
- 便于缓存和复用

### 4 字节对齐

输出行字节对齐到 4 字节:
- 提高访问效率
- 兼容 SIMD 操作
- 遵循平台约定

### 废弃决策

标记为 DEPRECATED:
- **原因:**
  - 功能被 `SkColorFilter` 覆盖
  - API 风格陈旧(原始指针)
  - 只支持 8 位遮罩
  - 更通用的滤镜系统已存在
- **迁移路径:**使用 `SkColorFilters::TableARGB`

## 性能考量

### 查找表访问

- 单次查找:O(1),约 1-2 纳秒
- 256 字节表:完全装入 L1 缓存
- 分支预测友好(顺序访问)

### 内存访问模式

- 逐行扫描:缓存友好
- 连续读写:最优化内存带宽
- 对齐访问:避免跨缓存行

### 内存分配

- 输出缓冲区:一次分配
- 查找表:静态分配(构造时)
- 无动态分配开销

### 并行化潜力

- 逐像素独立:天然并行
- 可 SIMD 优化:批量查找
- 可多线程:分块处理

**SIMD 优化示例(概念):**
```cpp
// 使用 SSSE3 pshufb 指令
__m128i pixels = _mm_loadu_si128(srcP);
__m128i result = _mm_shuffle_epi8(table_vec, pixels);
_mm_storeu_si128(dstP, result);
```

### 性能对比

| 操作 | 时间复杂度 | 实际性能 |
|------|-----------|---------|
| 查找表 | O(n) | 非常快 |
| 伽马计算(pow) | O(n) | 慢 100 倍 |
| 线性映射 | O(n) | 快 2 倍 |

其中 n 为像素数。

### 优化建议

- 复用滤镜实例(表只需创建一次)
- 对于小遮罩,直接计算可能更快(避免对象创建)
- 考虑 SIMD 优化批量查找
- 对于高分辨率遮罩,考虑并行处理

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/effects/SkTableMaskFilter.h` | 公共接口头文件 |
| `src/effects/SkTableMaskFilter.cpp` | 实现文件 |
| `include/core/SkMaskFilter.h` | 遮罩滤镜基类 |
| `src/core/SkMaskFilterBase.h` | 遮罩滤镜基类实现 |
| `src/core/SkMask.h` | 遮罩数据结构 |
| `include/core/SkColorFilter.h` | 颜色滤镜(替代) |
| `include/effects/SkImageFilters.h` | 图像滤镜(替代) |
| `include/private/base/SkAlign.h` | 对齐工具 |
| `include/private/base/SkFixed.h` | 定点数工具 |
| `src/core/SkReadBuffer.h` | 序列化读取 |
| `src/core/SkWriteBuffer.h` | 序列化写入 |
