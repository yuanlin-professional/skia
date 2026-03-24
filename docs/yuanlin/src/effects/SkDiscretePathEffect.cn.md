# SkDiscretePathEffect

> 源文件
> - include/effects/SkDiscretePathEffect.h
> - src/effects/SkDiscretePathEffect.cpp

## 概述

`SkDiscretePathEffect` 是 Skia 图形库中用于创建离散化和随机扰动路径效果的特效。该特效将连续的路径分割成固定长度的线段,并随机偏移每个端点,创造出粗糙、手绘、抖动等艺术效果。通过控制段长度和偏移幅度两个参数,可以实现从轻微抖动到显著变形的各种视觉效果。

该特效常用于艺术创作、手绘风格图形、草图效果、动画特效等场景。例如:模拟手绘线条的不稳定性、创建波浪形边缘、实现电流或闪电效果、为机械绘图添加有机感等。通过调整随机种子辅助参数,可以生成可重现或变化的随机效果。

## 架构位置

`SkDiscretePathEffect` 位于 Skia 特效模块的路径处理层:

- 位于 `include/effects/` 公共接口目录
- 内部实现类 `SkDiscretePathEffectImpl` 位于同一源文件中
- 继承自 `SkPathEffectBase` → `SkPathEffect`
- 使用 `SkPathMeasure` 进行路径测量和遍历
- 使用自定义的 `LCGRandom` 线性同余随机数生成器
- 与 `SkPathBuilder` 协作构建输出路径

## 主要类与结构体

### SkDiscretePathEffect

**继承关系:**
- 这是一个工厂类,不直接实例化
- 提供静态创建方法和注册函数

### SkDiscretePathEffectImpl(内部实现类)

**继承关系:**
- 基类:`SkPathEffectBase` → `SkPathEffect` → `SkFlattenable`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSegLength` | `SkScalar` | 段长度,定义路径分割的颗粒度 |
| `fPerterb` | `SkScalar` | 扰动幅度,定义随机偏移的最大距离 |
| `fSeedAssist` | `uint32_t` | 种子辅助值,用于修改随机数种子 |

### LCGRandom(内部随机数类)

线性同余随机数生成器,专为该特效设计:

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSeed` | `uint32_t` | 当前随机数种子 |

**公式:**
```
seed' = seed × 1664525 + 1013904223
```

这是"Numerical Recipes in C"中推荐的常量,提供良好的随机性质。

## 公共 API 函数

### Make

```cpp
static sk_sp<SkPathEffect> Make(SkScalar segLength, SkScalar deviation,
                               uint32_t seedAssist = 0);
```

创建离散路径特效:

- **参数:**
  - `segLength`: 段长度,必须 > 0 且为有限值,定义路径分割的间隔
  - `deviation`: 偏移幅度,必须为有限值,定义随机扰动的最大距离
  - `seedAssist`: 种子辅助值,默认 0,用于控制随机性
- **返回:**特效智能指针,参数无效时返回 `nullptr`
- **失败条件:**
  - 任一参数为 NaN 或无穷大
  - `segLength` ≤ 0

**使用示例:**
```cpp
// 创建中等粗糙度效果:每 10 像素一段,偏移最多 3 像素
auto effect = SkDiscretePathEffect::Make(10.0f, 3.0f);

// 细腻的抖动效果
auto effect2 = SkDiscretePathEffect::Make(5.0f, 1.0f);

// 粗犷的手绘效果
auto effect3 = SkDiscretePathEffect::Make(20.0f, 8.0f);

// 每次生成不同的随机效果(使用时间戳作为 seedAssist)
auto effect4 = SkDiscretePathEffect::Make(10.0f, 3.0f, getCurrentTime());

// 可重现的效果(固定 seedAssist)
auto effect5 = SkDiscretePathEffect::Make(10.0f, 3.0f, 42);
```

**seedAssist 说明:**
- `seedAssist = 0`(默认):每次对同一路径产生相同效果(用于测试和一致性)
- `seedAssist ≠ 0`:产生不同的随机效果,适合动画和变化效果
- 实际种子 = `seedAssist ^ pathLength`,确保不同路径有不同种子

### RegisterFlattenables

```cpp
static void RegisterFlattenables();
```

注册序列化工厂函数:
- 在 Skia 初始化时调用
- 支持从序列化数据重建特效
- 向后兼容旧名称("SkDiscretePathEffect")

## 内部实现细节

### onFilterPath 实现

```cpp
bool onFilterPath(SkPathBuilder* dst, const SkPath& src,
                  SkStrokeRec* rec, const SkRect*, const SkMatrix&) const;
```

路径离散化的核心逻辑:

**处理流程:**

1. **判断填充模式:**通过 `rec->isFillStyle()` 检测
2. **初始化测量:**创建 `SkPathMeasure` 对象测量路径
3. **计算种子:**`seed = fSeedAssist ^ pathLength` 确保可重现性
4. **遍历每个轮廓:**
   - 获取轮廓长度
   - 检查是否太短无需分割
   - 计算段数:n = round(length / fSegLength)
   - 对于闭合路径,调整起始位置到中点
5. **生成离散点:**
   - 沿路径均匀采样 n 个点
   - 获取每个点的位置和切线
   - 使用 `Perterb` 函数随机偏移点
6. **连接点:**使用 `lineTo` 连接所有离散点
7. **处理闭合:**如果原路径闭合,调用 `close()`

### Perterb 函数

```cpp
static void Perterb(SkPoint* p, const SkVector& tangent, SkScalar scale);
```

对点进行垂直于切线方向的随机偏移:

1. **计算法向量:**将切线逆时针旋转 90° 得到法向量
2. **归一化并缩放:**设置法向量长度为 `scale`
3. **应用偏移:**`p += normal`

**几何意义:**
- 偏移方向垂直于路径切线
- 保持路径的大致走向
- 创建波浪形而非完全随机的散乱

### 随机数生成

使用 `LCGRandom` 生成 [-1, 1) 范围的随机数:

```cpp
SkScalar nextSScalar1() {
    return SkFixedToScalar(nextSFixed1());
}

SkFixed nextSFixed1() {
    return nextS() >> 15;  // 取高 17 位作为有符号定点数
}
```

**特点:**
- 快速:只涉及乘法和加法
- 确定性:相同种子产生相同序列
- 适度质量:足够用于视觉效果,非密码学用途

### 段数计算

```cpp
int n = SkScalarRoundToInt(length / fSegLength);
n = std::min(n, kMaxReasonableIterations);  // 100000
```

**限制段数:**
- 防止过小的 `fSegLength` 导致巨大段数
- 限制为 100000 防止性能问题和内存爆炸
- 对于 fuzzer 测试,额外限制路径长度 < 1000

### 闭合路径处理

```cpp
if (meas.isClosed()) {
    n -= 1;               // 少一个点避免重复
    distance += delta/2;   // 从中点开始
}
```

**优化:**
- 避免起点和终点重复
- 从中点开始使闭合更均匀
- 使用 `dst->close()` 正确闭合路径

### 短路径处理

```cpp
if (fSegLength * (2 + doFill) > length) {
    meas.getSegment(0, length, dst, true);  // 太短,直接复制
}
```

对于太短的轮廓(长度 < 2-3 个段长度):
- 不进行分割和扰动
- 直接复制原路径
- 避免过度离散化小细节

### 序列化支持

```cpp
void flatten(SkWriteBuffer& buffer) const;
static sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer);
```

序列化三个参数:
- `fSegLength`
- `fPerterb`
- `fSeedAssist`

支持 SKP 格式和 Flattenable 机制。

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkPathMeasure` | 路径测量、采样、分割 |
| `SkPathBuilder` | 构建输出路径 |
| `SkPathEffect` | 路径特效基类 |
| `SkStrokeRec` | 检测填充/描边模式 |
| `SkPointPriv` | 点旋转操作(RotateCCW) |
| `SkFixed` | 定点数转换 |
| `SkFlattenable` | 序列化支持 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| 艺术创作工具 | 手绘风格效果 |
| 图形编辑器 | 草图滤镜、风格化 |
| 动画系统 | 抖动动画、特效 |
| 游戏引擎 | 手绘风格渲染 |
| UI 框架 | 装饰性边框、分隔线 |

## 设计模式与设计决策

### 工厂方法模式

使用静态 `Make` 方法:
- 封装验证逻辑
- 支持失败返回 `nullptr`
- 隐藏内部实现类

### 确定性随机

基于种子的随机数生成:
- 相同输入产生相同输出(可重现)
- 便于测试和调试
- 支持通过 seedAssist 引入变化

### 种子计算策略

`seed = seedAssist ^ pathLength`:
- 结合路径特征和用户参数
- 不同路径有不同种子
- 简单高效的组合方式
- 额外混淆:`seed ^ (seed << 16 | seed >> 16)` 增加熵

### 垂直扰动设计

扰动方向垂直于切线:
- 保持路径走向
- 产生自然的波动效果
- 避免路径自交

### 段数限制

多重保护防止性能问题:
- 段数上限(100000)
- Fuzzer 下路径长度限制(1000)
- 短路径跳过分割
- 参数有效性检查

### 两阶段处理

测量后再分割:
- 需要总长度来计算段数
- 需要均匀分布采样点
- 无法流式处理(trade-off)

## 性能考量

### 测量开销

- `SkPathMeasure` 需要遍历整个轮廓计算长度
- 对于复杂曲线,涉及细分和近似
- 多轮廓路径需要多次测量

### 采样开销

- 每个采样点需要沿路径定位(二分查找)
- 获取切线需要计算导数
- 段数越多,开销越大

### 随机数生成

- LCG 算法非常快速(乘法 + 加法)
- 每个点一次调用
- 开销可忽略

### 路径构建

- `SkPathBuilder` 动态分配内存
- 大量 `lineTo` 操作
- 可能多次重新分配

### 内存占用

- 输出路径大小 ≈ 段数 × 点大小
- 对于高频率分割,内存增长显著
- 临时数据结构开销较小

### 极端情况

**段数爆炸:**
- 路径长度 10000,段长度 0.1 → 100000 段(已限制)
- 防止内存耗尽和长时间计算

**短路径优化:**
- 跳过无意义的分割
- 避免过度离散化细节

### 优化建议

- 选择合理的段长度(通常 5-20 像素)
- 避免对超长路径应用(考虑简化路径)
- 缓存特效对象复用(如果参数不变)
- 对于动画,考虑预计算部分结果

### Fuzzer 保护

```cpp
#if defined(SK_BUILD_FOR_FUZZER)
if (length > 1000) {
    return false;
}
#endif
```

专门针对 fuzzer 测试的保护,避免模糊测试中的超长计算。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/effects/SkDiscretePathEffect.h` | 公共接口头文件 |
| `src/effects/SkDiscretePathEffect.cpp` | 实现文件(包含内部类) |
| `include/core/SkPathMeasure.h` | 路径测量工具 |
| `include/core/SkPathBuilder.h` | 路径构建器 |
| `include/core/SkPathEffect.h` | 路径特效基类 |
| `src/core/SkPathEffectBase.h` | 路径特效基类实现 |
| `src/core/SkPointPriv.h` | 点操作私有工具 |
| `include/private/base/SkFixed.h` | 定点数工具 |
| `src/core/SkReadBuffer.h` | 序列化读取 |
| `src/core/SkWriteBuffer.h` | 序列化写入 |
