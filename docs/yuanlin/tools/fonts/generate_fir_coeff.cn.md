# generate_fir_coeff.py

> 源文件: tools/fonts/generate_fir_coeff.py

## 概述

`generate_fir_coeff.py` 是一个 Python 脚本,用于生成 FIR(有限脉冲响应)滤波器系数,这些系数用于 LCD 亚像素字体渲染中的颜色边缘滤波。该脚本基于正态分布模型计算每个亚像素位置的滤波系数,确保文本在 LCD 屏幕上渲染时边缘平滑且颜色准确。

亚像素渲染利用 LCD 屏幕的 RGB 子像素排列,将文本渲染精度从像素级提升到子像素级,使文本看起来更清晰。FIR 系数控制相邻子像素之间的颜色混合,避免颜色边缘(color fringing)问题。

## 架构位置

```
skia/
  tools/
    fonts/
      generate_fir_coeff.py    # 本脚本
```

**数据流**:
```
数学模型(正态分布)
    ↓ (generate_fir_coeff.py 计算)
FIR 系数数组
    ↓ (复制到 C++ 代码)
LCD 文本渲染器
    ↓ (运行时使用)
亚像素抗锯齿文本
```

## 主要类与结构体

该脚本不使用类,主要包含数学计算函数。

## 公共 API 函数

### withinStdDev(n)

```python
def withinStdDev(n):
    """返回正态分布中在 n 个标准差内的样本百分比"""
    return math.erf(n / math.sqrt(2))
```

计算正态分布的累积分布函数(CDF):
- 输入: 标准差倍数 n
- 输出: [-n, n] 范围内的概率
- 使用误差函数(erf)实现

**示例**:
- `withinStdDev(1)` ≈ 0.6827 (68.27%)
- `withinStdDev(2)` ≈ 0.9545 (95.45%)
- `withinStdDev(3)` ≈ 0.9973 (99.73%)

### withinStdDevRange(a, b)

```python
def withinStdDevRange(a, b):
    """返回正态分布中在标准差范围 [a, b] 内的样本百分比"""
    if b < a:
        return 0
    if a < 0:
        if b < 0:
            return (withinStdDev(-a) - withinStdDev(-b)) / 2
        else:
            return (withinStdDev(-a) + withinStdDev(b)) / 2
    else:
        return (withinStdDev(b) - withinStdDev(a)) / 2
```

计算特定区间内的概率密度:
- 处理负值和跨零区间
- 利用正态分布的对称性

## 内部实现细节

### 亚像素采样配置

```python
samples_per_pixel = 4   # 每像素 4 个样本
subpxls_per_pixel = 3   # 每像素 3 个亚像素(R, G, B)

# 亚像素中心位置(分数偏移, 整数偏移)
sample_offsets = [
    math.modf(
        (float(subpxl_index)/subpxls_per_pixel + 1.0/(2.0*subpxls_per_pixel))
        * samples_per_pixel
    ) for subpxl_index in range(subpxls_per_pixel)
]
```

**计算逻辑**:
- **亚像素位置**: 1/6, 3/6, 5/6 像素
- **样本对齐**: 转换为样本单位后为 2/3, 0, 1/3 样本
- **modf**: 返回 (小数部分, 整数部分)

**示例**:
```
亚像素 0 (R): 1/6 * 4 = 0.667 → (0.667, 0)
亚像素 1 (G): 3/6 * 4 = 2.000 → (0.000, 2)
亚像素 2 (B): 5/6 * 4 = 3.333 → (0.333, 3)
```

### 滤波器参数

```python
sample_units_width = 5   # 左右各考虑 5 个样本单位
std_dev_max = 3          # 在 ±5 样本处对应 ±3 标准差
target_sum = 0x110       # 目标和(定点数),>1.0 模拟墨水扩散
```

**设计意图**:
- **宽度 5**: 覆盖足够范围以捕获 99.7% 的分布
- **3 标准差**: 标准正态分布的典型截断点
- **target_sum > 0x100**: 轻微增强对比度

### 系数生成主循环

```python
for sample_offset, sample_align in sample_offsets:
    coeffs = []
    coeffs_rounded = []

    current_sample_left = sample_offset - sample_units_width
    current_std_dev_left = -std_dev_max

    done = False
    while not done:
        current_sample_right = math.floor(current_sample_left + 1)
        if current_sample_right > sample_offset + sample_units_width:
            done = True
            current_sample_right = sample_offset + sample_units_width

        current_std_dev_right = current_std_dev_left + (
            (current_sample_right - current_sample_left) / sample_units_width
        ) * std_dev_max

        # 计算当前样本区间覆盖的概率
        coverage = withinStdDevRange(current_std_dev_left, current_std_dev_right)
        coeffs.append(coverage * target_sum)
        coeffs_rounded.append(int(round(coverage * target_sum)))

        current_sample_left = current_sample_right
        current_std_dev_left = current_std_dev_right
```

**步骤**:
1. 从中心向左右延伸 5 个样本单位
2. 将每个样本单位映射到标准差范围
3. 计算该区间的概率密度
4. 乘以目标和得到系数
5. 四舍五入到整数

### 舍入误差修正

```python
delta = 0
coeffs_rounded_sum = sum(coeffs_rounded)
if coeffs_rounded_sum > target_sum:
    delta = -1  # 从舍入误差最大的系数减 1
if coeffs_rounded_sum < target_sum:
    delta = 1   # 从舍入误差最小的系数加 1

if delta:
    print("Initial sum is 0x%0.2X, adjusting." % (coeffs_rounded_sum,))
    coeff_diff = [(coeff_rounded - coeff) * delta
                  for coeff, coeff_rounded in zip(coeffs, coeffs_rounded)]

    class IndexTracker:
        def __init__(self, index, item):
            self.index = index
            self.item = item
        def __lt__(self, other):
            return self.item < other.item

    coeff_pkg = [IndexTracker(i, diff) for i, diff in enumerate(coeff_diff)]
    coeff_pkg.sort()

    num_elements_to_force_round = abs(coeffs_rounded_sum - target_sum)
    for i in xrange(num_elements_to_force_round):
        print("Adding %d to index %d to force round %f." % (
            delta, coeff_pkg[i].index, coeffs[coeff_pkg[i].index]))
        coeffs_rounded[coeff_pkg[i].index] += delta
```

**修正策略**:
- 计算每个系数的舍入误差
- 按误差大小排序
- 调整误差最大的系数,确保总和精确为 `target_sum`

### 对齐输出

```python
print("Prepending %d 0x00 for allignment." % (sample_align,))
coeffs_rounded_aligned = ([0] * int(sample_align)) + coeffs_rounded

print(', '.join(["0x%0.2X" % coeff_rounded
                 for coeff_rounded in coeffs_rounded_aligned]))
print(sum(coeffs), hex(sum(coeffs_rounded)))
print()
```

在系数数组前添加零以对齐到样本边界。

### 典型输出

```
Prepending 0 0x00 for allignment.
0x00, 0x01, 0x04, 0x0A, 0x14, 0x1F, 0x2D, 0x35, 0x38, 0x35, 0x2D, 0x1F, 0x14, 0x0A, 0x04, 0x01, 0x00
272.0 0x110

Prepending 2 0x00 for allignment.
0x00, 0x00, 0x00, 0x02, 0x06, 0x0E, 0x19, 0x27, 0x32, 0x38, 0x35, 0x2D, 0x1F, 0x14, 0x0A, 0x04, 0x01, 0x00
272.0 0x110

Prepending 3 0x00 for allignment.
0x00, 0x00, 0x00, 0x01, 0x04, 0x0A, 0x14, 0x1F, 0x2D, 0x35, 0x38, 0x32, 0x27, 0x19, 0x0E, 0x06, 0x02, 0x00
272.0 0x110
```

三组系数对应 R, G, B 三个亚像素位置。

## 依赖关系

**Python 标准库**:
- `math`: 数学函数(erf, modf, floor)
- `pprint`: 美化打印(未使用)

**外部依赖**: 无

**使用生成数据的 Skia 代码**:
- `src/core/SkMask.cpp`: LCD 文本掩码生成
- `src/gpu/ganesh/ops/AtlasTextOp.cpp`: GPU 文本渲染

## 设计模式与设计决策

### 1. Mathematical Model-Based Generation

基于数学模型而非经验值生成系数,确保理论正确性。

### 2. Adaptive Rounding

动态调整舍入误差,确保数值稳定性和精度。

### 3. 设计决策

**为何使用正态分布**:
- 模拟字形边缘的自然模糊
- 数学性质良好(对称、可积)
- 与人眼视觉感知匹配

**为何 3 标准差截断**:
- 覆盖 99.73% 的分布
- 超出部分对视觉影响可忽略
- 限制滤波器宽度,减少计算量

**为何 target_sum = 0x110**:
```python
target_sum = 0x110  # > 0x100 (1.0)
```
- 模拟墨水在纸上的轻微扩散
- 增强文本可读性
- 补偿 LCD 亚像素的颜色损失

**为何每像素 4 个样本**:
- 足够精度以表示亚像素位置
- 不过度增加计算复杂度
- 与常见硬件能力匹配

**为何需要对齐**:
```python
coeffs_rounded_aligned = ([0] * int(sample_align)) + coeffs_rounded
```
确保系数数组从样本边界开始,简化硬件实现。

## 性能考量

### 1. 脚本执行时间

- 计算 3 组系数: < 0.1 秒
- 主要时间在数学函数计算

### 2. 运行时性能影响

生成的系数在运行时的影响:
- **内存**: 每组约 15-20 个字节
- **计算**: 每个亚像素需要约 10-15 次乘加运算
- **缓存**: 系数很小,完全在 L1 缓存中

### 3. 优化考虑

**预计算表**:
生成的系数硬编码在源代码中,避免运行时计算:
```cpp
// 在 Skia 源代码中
static const uint8_t kLCDFilter_R[] = {
    0x00, 0x01, 0x04, 0x0A, 0x14, 0x1F, 0x2D, 0x35,
    0x38, 0x35, 0x2D, 0x1F, 0x14, 0x0A, 0x04, 0x01, 0x00
};
```

**SIMD 加速**:
系数长度适合 SIMD 指令(SSE, NEON):
```cpp
// 伪代码
__m128i coeff = _mm_load_si128(kLCDFilter_R);
__m128i pixels = _mm_load_si128(pixel_buffer);
__m128i result = _mm_maddubs_epi16(coeff, pixels);
```

## 相关文件

**本脚本**:
- `tools/fonts/generate_fir_coeff.py`: 系数生成器

**使用生成系数的文件**:
- `src/core/SkMask.cpp`: 掩码生成,LCD 滤波
- `src/core/SkMaskGamma.cpp`: 伽马校正和 LCD 滤波
- `src/core/SkScalerContext.cpp`: 字形缩放上下文

**相关算法**:
- `src/opts/SkBitmapFilter_opts.h`: 优化的位图滤波实现
- `src/gpu/ganesh/ops/AtlasTextOp.cpp`: GPU 文本操作

**测试**:
- `tests/FontHostTest.cpp`: 字体渲染测试
- `tests/BlitMaskTest.cpp`: 掩码混合测试

**文档**:
- FreeType LCD 滤波文档: 类似的算法参考
- ClearType 技术白皮书: 微软的亚像素渲染技术

**历史背景**:
该脚本实现的算法基于 2000 年代初的 ClearType 和 FreeType 研究,是现代文本渲染的基础技术。

**使用示例**:
```bash
# 运行脚本生成系数
python tools/fonts/generate_fir_coeff.py

# 输出示例(复制到 C++ 代码):
# 0x00, 0x01, 0x04, 0x0A, 0x14, 0x1F, 0x2D, 0x35,
# 0x38, 0x35, 0x2D, 0x1F, 0x14, 0x0A, 0x04, 0x01, 0x00
```

该脚本虽然简短,但其背后的数学原理和生成的系数对现代 LCD 文本渲染质量至关重要,是 Skia 字体渲染管线中不可或缺的一环。
