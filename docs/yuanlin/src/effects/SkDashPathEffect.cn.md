# SkDashPathEffect

> 源文件
> - include/effects/SkDashPathEffect.h
> - src/effects/SkDashPathEffect.cpp

## 概述

`SkDashPathEffect` 是 Skia 图形库中用于创建虚线描边效果的路径特效。该特效通过定义一组交替的"开"(on)和"关"(off)间隔,将实线路径转换为虚线路径。支持相位(phase)参数来控制虚线模式的起始偏移,实现虚线动画等高级效果。

虚线特效广泛应用于图形绘制、UI 设计、数据可视化等场景。例如:虚线边框、图表中的参考线、选择框、路径指示器等。通过动态调整相位参数,可以创建"行进中的蚂蚁"(marching ants)动画效果,常见于图像编辑软件的选区指示。

## 架构位置

`SkDashPathEffect` 位于 Skia 特效模块的路径处理层:

- 位于 `include/effects/` 公共接口目录
- 内部实现类 `SkDashImpl` 位于 `src/effects/SkDashImpl.h`
- 继承自 `SkPathEffectBase` → `SkPathEffect`
- 使用 `SkDashPath` 工具类进行实际虚线化处理
- 支持优化的点绘制模式(asPoints)用于硬件加速
- 与描边系统(`SkStrokeRec`)紧密集成

## 主要类与结构体

### SkDashPathEffect

**继承关系:**
- 这是一个工厂类,不直接实例化
- 实际实现类 `SkDashImpl` 继承自 `SkPathEffectBase`

### SkDashImpl(内部实现类)

**继承关系:**
- 基类:`SkPathEffectBase` → `SkPathEffect` → `SkFlattenable`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fIntervals` | `skia_private::AutoTArray<SkScalar>` | 间隔数组,偶数索引为"开",奇数索引为"关" |
| `fPhase` | `SkScalar` | 规范化后的相位偏移 |
| `fInitialDashLength` | `SkScalar` | 第一个虚线段的长度 |
| `fInitialDashIndex` | `int32_t` | 起始间隔索引(0 或 1) |
| `fIntervalLength` | `SkScalar` | 所有间隔的总长度 |

## 公共 API 函数

### Make

```cpp
static sk_sp<SkPathEffect> Make(SkSpan<const SkScalar> intervals, SkScalar phase);
```

创建虚线路径特效:

- **参数:**
  - `intervals`: 间隔数组,必须包含偶数个元素(≥2),偶数索引为"开"长度,奇数索引为"关"长度
  - `phase`: 相位偏移,定义虚线模式的起始位置,对间隔总和取模
- **返回:**特效智能指针,参数无效时返回 `nullptr`
- **验证:**使用 `SkDashPath::ValidDashPath` 验证参数有效性

**使用示例:**
```cpp
// 简单虚线:10 像素开,20 像素关
SkScalar intervals[] = {10.0f, 20.0f};
auto effect = SkDashPathEffect::Make(intervals, 0);

// 点划线:5 像素开,10 像素关,20 像素开,10 像素关
SkScalar intervals2[] = {5.0f, 10.0f, 20.0f, 10.0f};
auto effect2 = SkDashPathEffect::Make(intervals2, 0);

// 带相位的虚线(偏移 25 像素开始)
// 等价于:5 像素关,10 像素开,20 像素关,10 像素开,...
auto effect3 = SkDashPathEffect::Make(intervals, 25.0f);
```

**相位说明:**
- `phase` 对间隔总和取模,因此 `-5, 25, 55, 85` 等对于总和 30 的间隔效果相同
- 正相位:向前偏移模式
- 负相位:向后偏移模式

## 内部实现细节

### 构造函数初始化

```cpp
SkDashImpl::SkDashImpl(SkSpan<const SkScalar> intervals, SkScalar phase)
```

构造时调用 `SkDashPath::CalcDashParameters` 计算:
- `fPhase`: 规范化相位(0 到间隔总和之间)
- `fIntervalLength`: 所有间隔的总和
- `fInitialDashLength`: 第一个可见虚线段的剩余长度
- `fInitialDashIndex`: 起始位置是"开"(0)还是"关"(1)

### onFilterPath 实现

```cpp
bool onFilterPath(SkPathBuilder* builder, const SkPath& src,
                  SkStrokeRec* rec, const SkRect* cullRect,
                  const SkMatrix&) const;
```

委托给 `SkDashPath::InternalFilter` 进行实际处理:
- 遍历源路径的所有轮廓和段
- 根据间隔模式分割路径
- 只保留"开"间隔的路径段
- 支持剔除矩形优化

### 点绘制优化(asPoints)

```cpp
bool onAsPoints(PointData* results, const SkPath& src,
                const SkStrokeRec& rec, const SkMatrix& matrix,
                const SkRect* cullRect) const;
```

针对特定条件的优化路径:

**启用条件:**
- 路径是单直线段
- 描边宽度 > 0(非填充或细线)
- 间隔恰好 2 个且相等(或近似相等且为整数)
- 端点样式为 `kButt_Cap`(对于方形点)或 `kRound_Cap`(对于圆形点)
- 矩阵保持矩形(无旋转或倾斜,除非是圆形点)

**优点:**
- 返回离散点数组而非路径
- GPU 可以使用点精灵(point sprites)硬件加速绘制
- 对于长直线的虚线,性能提升显著

**点数据结构:**
```cpp
struct PointData {
    SkPoint* fPoints;      // 点位置数组
    int fNumPoints;        // 点数量
    SkPoint fSize;         // 每个点的尺寸
    uint32_t fFlags;       // kCircles_PointFlag 等标志
    std::optional<SkPath> fFirst;  // 可选的第一个部分虚线段
    std::optional<SkPath> fLast;   // 可选的最后一个部分虚线段
};
```

### 剔除优化(cull_line)

```cpp
static bool cull_line(SkPoint* pts, const SkStrokeRec& rec,
                      const SkMatrix& ctm, const SkRect* cullRect,
                      const SkScalar intervalLength);
```

针对水平或垂直直线的剔除优化:
- 检测直线是否与剔除矩形相交
- 裁剪直线到可见区域
- 保持虚线相位同步(通过 `mod intervalLength`)
- 减少不可见部分的处理开销

### 虚线信息查询(asADash)

```cpp
std::optional<DashInfo> asADash() const;
```

返回虚线参数,供其他系统查询:
- 用于序列化
- 用于优化路径合成
- 用于 GPU 着色器参数

### 序列化支持

```cpp
void flatten(SkWriteBuffer& buffer) const;
sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer);
```

序列化虚线参数:
- 写入:相位 + 间隔数组
- 读入:验证并重建特效
- 支持 SKP 格式和跨进程通信

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkDashPath` | 实际虚线化算法实现 |
| `SkPathBuilder` | 构建输出虚线路径 |
| `SkPathEffect` | 路径特效基类 |
| `SkStrokeRec` | 描边参数(宽度、端点、连接) |
| `SkMatrix` | 坐标变换 |
| `SkFlattenable` | 序列化支持 |
| `SkDashPathPriv` | 内部虚线工具 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| 图形绘制系统 | 虚线描边渲染 |
| UI 框架 | 虚线边框、分隔线 |
| 数据可视化 | 图表虚线、网格线 |
| 矢量图形编辑器 | 虚线工具 |
| 动画系统 | 虚线动画(相位动画) |

## 设计模式与设计决策

### 工厂方法模式

使用静态 `Make` 方法:
- 封装验证和初始化逻辑
- 支持创建失败返回 `nullptr`
- 隐藏内部实现类

### 预计算优化

在构造时预计算虚线参数:
- 间隔总和
- 规范化相位
- 初始虚线段信息
- 避免重复计算,提升滤镜应用性能

### 两级实现架构

- **外层:**`SkDashImpl` 处理接口、验证、优化路径
- **内层:**`SkDashPath` 处理核心虚线化算法
- 职责分离,便于测试和维护

### 特殊情况优化

**点绘制优化:**
- 针对简单直线的特殊路径
- 利用 GPU 点精灵硬件
- 显著提升性能

**剔除优化:**
- 针对轴对齐直线
- 避免处理不可见部分
- 保持相位同步

### 相位设计

使用取模运算规范化相位:
- 避免无限大相位值
- 使相位周期性
- 支持动画循环

### 间隔数组设计

使用偶数个元素的数组:
- 偶数索引:"开"(可见)
- 奇数索引:"关"(不可见)
- 交替模式自然表达
- 支持复杂虚线模式(点划线等)

## 性能考量

### 预计算开销

- 构造时计算间隔总和: O(n)
- 规范化相位: O(1)
- 一次性开销,后续应用无额外成本

### 滤镜应用性能

- 需要遍历整个路径:O(路径段数 × 间隔数)
- 对于复杂路径和多间隔,计算量大
- 每个路径段需要多次测量和分割

### 点绘制优化效果

对于满足条件的直线:
- 避免路径构建和描边
- GPU 点精灵绘制:硬件加速
- 性能提升:10-100倍(取决于虚线数量)

### 剔除优化效果

对于长直线:
- 避免处理屏幕外的部分
- 减少内存分配和路径操作
- 对于大范围缩放视图效果显著

### 内存占用

- 间隔数组:动态分配,大小 = 间隔数 × sizeof(SkScalar)
- 通常很小(典型 2-4 个间隔)
- 使用 `AutoTArray` 小数组内联优化

### 缓存考虑

- 虚线化结果未缓存(路径可能很大)
- 每次绘制重新计算
- 对于静态虚线路径,考虑预先虚线化

### 优化建议

- 简化路径以减少段数
- 使用点绘制优化条件(轴对齐直线、简单间隔)
- 提供剔除矩形加速不可见部分跳过
- 对于动画,复用特效对象只改变相位

### 极端情况处理

**防止溢出:**
```cpp
if (!SkIsFinite(numIntervals) || numIntervals > SkDashPath::kMaxDashCount) {
    return false;
}
```

- 限制最大虚线段数(防止内存爆炸)
- 检查浮点有效性
- 避免拒绝服务攻击

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/effects/SkDashPathEffect.h` | 公共接口头文件 |
| `src/effects/SkDashPathEffect.cpp` | 实现文件 |
| `src/effects/SkDashImpl.h` | 内部实现类声明 |
| `src/utils/SkDashPath.h` | 虚线化核心算法 |
| `src/utils/SkDashPathPriv.h` | 虚线化内部工具 |
| `include/core/SkPathEffect.h` | 路径特效基类 |
| `include/core/SkStrokeRec.h` | 描边记录 |
| `include/core/SkPathBuilder.h` | 路径构建器 |
| `src/core/SkPathEffectBase.h` | 路径特效基类实现 |
