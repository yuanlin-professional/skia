# SkTrimPathEffect

> 源文件
> - include/effects/SkTrimPathEffect.h
> - src/effects/SkTrimPathEffect.cpp

## 概述

`SkTrimPathEffect` 是 Skia 图形库中用于路径修剪的特效类,能够提取路径的指定子集或补集。该类通过 "t" 值参数(0.0 到 1.0 之间)定义路径的起始和结束位置,实现对路径的精确裁剪。支持两种模式:普通模式返回 [start, stop] 区间的路径段,反转模式返回该区间的补集([0, start] + [stop, 1])。

该特效广泛应用于动画场景,例如绘制进度条、路径描边动画、加载指示器等。通过动态调整 start 和 stop 参数,可以实现路径逐渐出现或消失的效果,这在 UI 动画和矢量图形动画中非常常见。

## 架构位置

`SkTrimPathEffect` 位于 Skia 特效模块的路径处理层:

- 位于 `include/effects/` 公共接口目录
- 继承自 `SkPathEffect` 路径特效基类
- 内部实现类 `SkTrimPE` 位于 `src/effects/SkTrimPE.h`
- 使用 `SkPathMeasure` 进行路径测量和分段提取
- 与动画系统(如 Lottie)紧密集成
- 可与其他路径特效组合使用

## 主要类与结构体

### SkTrimPathEffect

**继承关系:**
- 这是一个工厂类,不直接实例化
- 实际实现类 `SkTrimPE` 继承自 `SkPathEffectBase`

**枚举类型 Mode:**

| 枚举值 | 说明 |
|--------|------|
| `kNormal` | 普通模式:返回 [start, stop] 区间的路径子集 |
| `kInverted` | 反转模式:返回补集 [0, start] + [stop, 1] |

### SkTrimPE(内部实现类)

**继承关系:**
- 基类:`SkPathEffectBase` → `SkPathEffect` → `SkFlattenable`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStartT` | `SkScalar` | 起始位置,范围 [0.0, 1.0],表示路径总长度的比例 |
| `fStopT` | `SkScalar` | 结束位置,范围 [0.0, 1.0],表示路径总长度的比例 |
| `fMode` | `SkTrimPathEffect::Mode` | 修剪模式(普通/反转) |

## 公共 API 函数

### Make

```cpp
static sk_sp<SkPathEffect> Make(SkScalar startT, SkScalar stopT,
                                Mode mode = Mode::kNormal);
```

创建路径修剪特效实例:

- **参数:**
  - `startT`: 起始 t 值(0.0-1.0),超出范围会被钳制
  - `stopT`: 结束 t 值(0.0-1.0),超出范围会被钳制
  - `mode`: 修剪模式,默认为普通模式
- **返回:**特效智能指针,失败返回 `nullptr`
- **失败条件:**
  - 参数为 NaN
  - 普通模式下 `startT <= 0 && stopT >= 1`(无操作)
  - 反转模式下 `startT >= stopT`(空结果)

**使用示例:**
```cpp
// 提取路径的中间三分之一
auto effect = SkTrimPathEffect::Make(0.33333f, 0.66667f);

// 提取路径的后半部分
auto effect = SkTrimPathEffect::Make(0.5f, 1.0f);

// 反转模式:提取开头和结尾,去掉中间
auto effect = SkTrimPathEffect::Make(0.3f, 0.7f, Mode::kInverted);
```

## 内部实现细节

### onFilterPath 实现

路径修剪的核心逻辑:

```cpp
bool onFilterPath(SkPathBuilder* dst, const SkPath& src,
                  SkStrokeRec*, const SkRect*, const SkMatrix&) const;
```

**处理流程:**

1. **提前退出:**如果 `startT >= stopT` 且为普通模式,返回空路径
2. **第一遍遍历:**计算路径总长度
   - 使用 `SkPathMeasure` 测量所有轮廓
   - 累加所有轮廓的长度得到总长度
3. **计算绝对位置:**
   - `arcStart = totalLength * fStartT`
   - `arcStop = totalLength * fStopT`
4. **第二遍遍历:**提取指定区间的路径段
   - 普通模式:调用 `add_segments(src, arcStart, arcStop, dst)`
   - 反转模式:分两段添加(尾部和头部)

### add_segments 辅助函数

```cpp
static size_t add_segments(const SkPath& src, SkScalar start, SkScalar stop,
                          SkPathBuilder* dst, bool requires_moveto = true);
```

逐轮廓提取路径段:

- **参数:**
  - `start/stop`: 绝对长度位置(非 t 值)
  - `requires_moveto`: 是否需要 moveTo(用于连续路径段)
- **逻辑:**
  - 遍历所有轮廓,累计当前偏移
  - 当轮廓范围与 [start, stop] 有交集时,使用 `SkPathMeasure::getSegment` 提取
  - 跨多个轮廓时,后续段自动连接
- **返回:**遍历的轮廓数量

### 反转模式的特殊处理

反转模式需要返回两段路径:[stop, totalLength] + [0, start]

**关键优化:**
1. **顺序调整:**先添加尾部段,再添加头部段
2. **闭合路径优化:**
   - 如果源路径只有一个闭合轮廓,两段之间不插入 moveTo
   - 保持路径连续性,避免断开
3. **requires_moveto 标志:**
   - 第一段(尾部):总是需要 moveTo
   - 第二段(头部):单闭合轮廓时不需要 moveTo

### 序列化支持

```cpp
void flatten(SkWriteBuffer& buffer) const;
sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer);
```

支持路径特效的序列化和反序列化:
- 写入:三个值(startT, stopT, mode)
- 读取:验证并重新创建特效
- 用于 Skia 的图片序列化(SKP 格式)

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkPathMeasure` | 路径长度测量和段提取 |
| `SkPathBuilder` | 构建输出路径 |
| `SkPathEffect` | 路径特效基类 |
| `SkFlattenable` | 序列化支持 |
| `SkTPin` | 参数值钳制 |
| `SkReadBuffer/SkWriteBuffer` | 序列化读写 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| 动画系统 | 使用修剪特效实现路径动画 |
| Lottie 渲染器 | 支持 After Effects 修剪路径效果 |
| UI 框架 | 进度指示器、加载动画 |
| 矢量图形工具 | SVG 路径修剪 |

## 设计模式与设计决策

### 工厂方法模式

`SkTrimPathEffect` 作为工厂类:
- 公开静态 `Make` 方法创建实例
- 隐藏内部实现类 `SkTrimPE`
- 便于未来更换实现而不影响 API

### 两遍算法

路径修剪采用两遍处理:
1. **第一遍:**测量总长度
2. **第二遍:**提取路径段

**优点:**
- 简单清晰,易于理解和维护
- 支持多轮廓路径
- 处理跨轮廓的路径段

**代价:**
- 需要两次遍历路径
- 对于复杂路径有性能影响

### 比例参数设计

使用 [0.0, 1.0] 的 t 值而非绝对长度:
- **设备无关:**不依赖路径的实际长度单位
- **直觉友好:**百分比概念易于理解
- **动画友好:**线性插值产生均匀动画效果
- **规范化:**避免浮点精度问题

### 反转模式优化

为单闭合轮廓路径避免插入 moveTo:
- 保持路径连续性
- 支持闭合路径的修剪动画
- 正确处理填充和描边

### 参数验证

在工厂方法中进行完整验证:
- 钳制到有效范围 [0, 1]
- 检测无操作情况并返回 `nullptr`
- 避免创建无效特效对象

## 性能考量

### 两遍遍历开销

- **第一遍:**只计算长度,相对轻量
- **第二遍:**提取路径段,涉及更多计算
- **优化机会:**对于简单路径(单线段),可以跳过测量直接计算

### 路径段提取

`SkPathMeasure::getSegment` 是性能关键点:
- 内部使用二分查找定位段
- 涉及曲线细分和近似
- 对于贝塞尔曲线计算复杂

### 内存分配

- `SkPathBuilder` 动态分配路径数据
- 可能多次分配以容纳提取的路径段
- 对于多轮廓路径,分配次数增加

### 缓存友好性

- 连续遍历路径数据,缓存友好
- 两遍遍历可能导致缓存失效
- 对于小路径影响有限

### 优化建议

- 对于动画,考虑预计算路径长度
- 批量处理多个修剪操作
- 对于实时动画,使用较低的曲线细分精度

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/effects/SkTrimPathEffect.h` | 公共接口头文件 |
| `src/effects/SkTrimPathEffect.cpp` | 实现文件 |
| `src/effects/SkTrimPE.h` | 内部实现类声明 |
| `include/core/SkPathMeasure.h` | 路径测量工具 |
| `include/core/SkPathBuilder.h` | 路径构建器 |
| `include/core/SkPathEffect.h` | 路径特效基类 |
| `src/core/SkReadBuffer.h` | 序列化读取 |
| `src/core/SkWriteBuffer.h` | 序列化写入 |
| `include/private/base/SkTPin.h` | 数值钳制工具 |
