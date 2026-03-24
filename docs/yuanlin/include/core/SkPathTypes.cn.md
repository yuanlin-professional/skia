# SkPathTypes

> 源文件: `include/core/SkPathTypes.h`

## 概述
SkPathTypes 定义了 Skia 路径系统的核心枚举类型和辅助函数，包括填充规则、路径方向、路径段类型和路径操作指令。这些类型是 SkPath 实现的基础，决定了路径的渲染行为和几何表达。

## 架构位置
位于 Skia 核心模块 (`include/core`)，作为路径子系统的基础类型定义层。被 SkPath、SkCanvas、路径构建器等组件广泛使用，是 2D 矢量图形系统的核心。

## 枚举类型

### SkPathFillType
```cpp
enum class SkPathFillType : uint8_t {
    kWinding,         // 非零绕组规则
    kEvenOdd,         // 奇偶规则
    kInverseWinding,  // 反向非零绕组
    kInverseEvenOdd,  // 反向奇偶规则
    kDefault = kWinding,
};
```

**填充规则说明**:

#### kWinding (非零绕组规则)
- **算法**: 从点发出射线，统计路径边与射线交叉时的有向计数
  - 顺时针交叉: +1
  - 逆时针交叉: -1
- **判定**: 计数非零的区域为"内部"
- **用途**: 复杂路径的标准填充方式，符合直觉

#### kEvenOdd (奇偶规则)
- **算法**: 统计射线与路径边的交叉次数
- **判定**: 奇数次交叉为"内部"，偶数次为"外部"
- **用途**: 简单路径，镂空效果

#### kInverseWinding / kInverseEvenOdd
- **行为**: 反转填充区域，"外部"被填充，"内部"为空
- **用途**: 镂空效果、剪裁掩码

### SkPathDirection
```cpp
enum class SkPathDirection : uint8_t {
    kCW,   // 顺时针方向
    kCCW,  // 逆时针方向
    kDefault = kCW,
};
```

**方向意义**:
- 影响绕组规则的计算
- 决定路径的"内侧"和"外侧"
- 用于路径布尔运算和描边

### SkPathSegmentMask
```cpp
enum SkPathSegmentMask {
    kLine_SkPathSegmentMask   = 1 << 0,  // 0x01
    kQuad_SkPathSegmentMask   = 1 << 1,  // 0x02
    kConic_SkPathSegmentMask  = 1 << 2,  // 0x04
    kCubic_SkPathSegmentMask  = 1 << 3,  // 0x08
};
```

**位掩码设计**:
- 可组合多种段类型：`kLine_SkPathSegmentMask | kQuad_SkPathSegmentMask`
- 用于快速检查路径包含的段类型
- 优化渲染器的路径分析

### SkPathVerb
```cpp
enum class SkPathVerb : uint8_t {
    kMove,   // 移动到新位置（1 点）
    kLine,   // 直线段（2 点）
    kQuad,   // 二次贝塞尔曲线（3 点）
    kConic,  // 圆锥曲线（3 点 + 1 权重）
    kCubic,  // 三次贝塞尔曲线（4 点）
    kClose,  // 闭合当前轮廓（0 点）
    kLast_Verb = kClose,
};
```

**路径指令**:
- 描述 SkPath 的基本操作
- 与点数组配合表达完整路径
- 对应 SkPath::RawIter 返回的指令类型

## 辅助函数

### SkPathFillType_IsEvenOdd
```cpp
static inline bool SkPathFillType_IsEvenOdd(SkPathFillType ft)
```
- **功能**: 检查是否为奇偶规则（包括反向奇偶）
- **实现**: `(static_cast<int>(ft) & 1) != 0`
- **位模式**: 利用枚举值的最低位标识奇偶特性

### SkPathFillType_IsInverse
```cpp
static inline bool SkPathFillType_IsInverse(SkPathFillType ft)
```
- **功能**: 检查是否为反向填充规则
- **实现**: `(static_cast<int>(ft) & 2) != 0`
- **位模式**: 利用次低位标识反向特性

### SkPathFillType_ToggleInverse
```cpp
static inline SkPathFillType SkPathFillType_ToggleInverse(SkPathFillType ft)
```
- **功能**: 切换填充规则的反向状态
- **实现**: `static_cast<SkPathFillType>(static_cast<int>(ft) ^ 2)`
- **用途**: 快速创建反向规则

### SkPathFillType_ConvertToNonInverse
```cpp
static inline SkPathFillType SkPathFillType_ConvertToNonInverse(SkPathFillType ft)
```
- **功能**: 移除反向标记，保留基础规则
- **实现**: `static_cast<SkPathFillType>(static_cast<int>(ft) & 1)`
- **用途**: 获取对应的正向规则

## 核心概念

### 填充规则的位编码
SkPathFillType 使用巧妙的位编码：

```
位 1 (0x01): 0 = Winding, 1 = EvenOdd
位 2 (0x02): 0 = Normal,  1 = Inverse

kWinding         = 0b00 = 0
kEvenOdd         = 0b01 = 1
kInverseWinding  = 0b10 = 2
kInverseEvenOdd  = 0b11 = 3
```

这种编码使得规则查询和转换变得高效。

### 路径段类型层次
```
简单 → 复杂:
Move (起点) → Line (直线) → Quad (二次曲线) → Conic (圆锥) → Cubic (三次曲线)
```

### 路径迭代模型
SkPathVerb 定义了 SkPath::RawIter 的迭代协议：
```cpp
// 伪代码
SkPath::RawIter iter(path);
SkPoint pts[4];
while (SkPathVerb verb = iter.next(pts)) {
    switch (verb) {
        case kMove:  // pts[0] = 移动目标
        case kLine:  // pts[0-1] = 起点和终点
        case kQuad:  // pts[0-2] = 控制点
        case kConic: // pts[0-2] + weight
        case kCubic: // pts[0-3] = 控制点
        case kClose: // 无点数据
    }
}
```

## 使用场景

### 设置填充规则
```cpp
SkPath path;
path.addCircle(50, 50, 40);
path.addCircle(50, 50, 20);
path.setFillType(SkPathFillType::kEvenOdd); // 镂空效果
```

### 检查路径段类型
```cpp
int segmentMask = path.getSegmentMasks();
if (segmentMask & kCubic_SkPathSegmentMask) {
    // 路径包含三次曲线，使用精确渲染器
}
if (segmentMask == kLine_SkPathSegmentMask) {
    // 纯直线路径，使用快速光栅化
}
```

### 路径方向与绕组
```cpp
SkPath outerRect;
outerRect.addRect(rect, SkPathDirection::kCW);  // 顺时针 = 填充

SkPath innerRect;
innerRect.addRect(smallerRect, SkPathDirection::kCCW); // 逆时针 = 挖空

SkPath combined;
combined.addPath(outerRect);
combined.addPath(innerRect);
// 组合后形成镂空矩形
```

### 反向填充应用
```cpp
// 创建镂空蒙版
SkPath maskPath;
maskPath.addCircle(centerX, centerY, radius);
maskPath.setFillType(SkPathFillType::kInverseWinding);
// 现在圆外部被填充，圆内部透明
```

## 内部实现细节

### 内存优化
所有枚举使用 uint8_t 作为底层类型：
- 节省内存（1 字节 vs 4 字节）
- 提高缓存效率
- 足够表达所需的值范围

### 位操作优化
辅助函数使用位操作而非 if-else：
```cpp
// 快速路径：单次位测试
bool isEvenOdd = (ft & 1) != 0;

// 慢速路径：分支跳转
// bool isEvenOdd = (ft == kEvenOdd || ft == kInverseEvenOdd);
```

### 枚举类安全性
使用 `enum class` 而非传统枚举：
- 强类型，避免隐式转换
- 作用域隔离，防止命名冲突
- 需要显式转换才能进行位操作

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `include/core/SkTypes.h` | 基础类型定义 |
| `<cstdint>` | uint8_t 定义 |

### 被依赖的模块
- **SkPath**: 路径类的核心，直接使用所有这些类型
- **SkCanvas**: 绘图时需要理解填充规则
- **路径效果**: SkPathEffect 处理路径变换
- **路径测量**: SkPathMeasure 分析路径段
- **光栅化器**: 渲染时执行填充规则

## 设计模式与设计决策

### 位标志设计
SkPathFillType 的位编码体现了优秀的 API 设计：
- 正交特性分离：基础规则 vs 反向标志
- 高效查询：单次位操作即可判断
- 易于扩展：理论上可添加更多规则（但 4 种已足够）

### 类型安全枚举
C++11 的 `enum class` 提供了类型安全：
```cpp
// 错误：类型不匹配
// int x = SkPathFillType::kWinding; // 需要显式转换

// 正确：
SkPathFillType ft = SkPathFillType::kWinding;
```

### 命名约定
- 枚举类型：CamelCase
- 枚举值：kCamelCase（k 前缀）
- 辅助函数：TypeName_Operation 风格

## 性能考量

### 编译期常量
枚举值在编译期确定，允许编译器优化：
```cpp
if (fillType == SkPathFillType::kWinding) {
    // 编译器可直接比较常量值
}
```

### 内联优化
所有辅助函数标记为 `inline`：
- 零函数调用开销
- 编译器可进一步优化位操作

### 缓存友好
uint8_t 大小使得：
- 多个枚举值可紧凑存储
- 减少内存带宽消耗
- 提高 CPU 缓存命中率

## 图形学原理

### Winding Number 算法
非零绕组规则基于数学中的绕数（winding number）概念：
```
对于点 P 和闭合曲线 C:
winding(P, C) = ∑(边 e 绕 P 的有向角度) / 2π
```

### Even-Odd 规则的简洁性
奇偶规则更简单，但在复杂路径中可能产生意外：
- 自交路径的填充可能不符合直觉
- 适合简单的镂空场景

### Conic 曲线的特殊性
圆锥曲线（Conic）是二次贝塞尔的推广：
- 通过权重参数可精确表达圆弧和椭圆弧
- 比三次曲线更节省空间
- Skia 特有，标准 SVG 不直接支持

## 历史演进

### 版权信息
2019 Google LLC，表明这是相对较新的模块化设计，可能是从 SkPath.h 中分离出来的。

### API 演进
- 早期 Skia 可能使用传统 enum
- 现代版本采用 enum class 提升类型安全
- 辅助函数名称遵循统一的命名规范

## 相关文件
| 文件 | 关系 |
|------|------|
| `include/core/SkPath.h` | 使用这些类型的主要类 |
| `include/core/SkCanvas.h` | 绘图时应用填充规则 |
| `include/pathops/SkPathOps.h` | 路径布尔运算需要理解方向 |
| `include/core/SkPaint.h` | 绘制风格影响填充行为 |
| `src/core/SkScan.h` | 光栅化器实现填充算法 |
