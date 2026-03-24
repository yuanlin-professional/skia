# RectanizerSkyline

> 源文件: src/gpu/RectanizerSkyline.h, src/gpu/RectanizerSkyline.cpp

## 概述

`RectanizerSkyline` 是 Skia GPU 层中的矩形打包算法实现,采用 Skyline 算法(天际线算法)将多个不同尺寸的矩形高效地打包到一个固定大小的二维空间中。该算法广泛应用于纹理图集(texture atlas)、字体缓存等场景,能够最大化空间利用率,减少内存浪费。

Skyline 算法通过维护一个"天际线"数据结构来跟踪当前已分配区域的轮廓,每次添加新矩形时寻找最适合的位置,并更新天际线。该实现基于 Jukka Jylanki 的矩形打包研究。

## 架构位置

`RectanizerSkyline` 位于 Skia GPU 层的资源管理基础设施:

- 命名空间: `skgpu`
- 模块位置: `src/gpu/`
- 继承关系: 继承自抽象基类 `Rectanizer`
- 应用场景: 字体图集打包、纹理图集管理、动态资源分配

该类是 `Rectanizer` 的默认实现(通过 `Rectanizer::Factory` 创建),被标记为 `final` 以避免虚函数表开销。

## 主要类与结构体

### 继承关系

```
Rectanizer (抽象基类)
└── RectanizerSkyline (final 实现)
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSkyline` | `SkTDArray<SkylineSegment>` | 天际线段数组,维护当前空间轮廓 |
| `fAreaSoFar` | `int32_t` | 已分配的总面积(像素数) |
| `fWidth` | `int` (继承) | 打包空间的总宽度 |
| `fHeight` | `int` (继承) | 打包空间的总高度 |

### 内部结构体

#### SkylineSegment

```cpp
struct SkylineSegment {
    int fX;       // 段的起始 X 坐标
    int fY;       // 段的 Y 坐标(高度)
    int fWidth;   // 段的宽度
};
```

每个 `SkylineSegment` 表示天际线上的一个水平段,描述从 `(fX, fY)` 开始,宽度为 `fWidth` 的区域上方是空闲空间。

## 公共 API 函数

### 构造与析构

```cpp
// 构造函数,指定打包空间大小
RectanizerSkyline(int w, int h);

// 析构函数
~RectanizerSkyline() final;
```

### 核心接口(覆盖基类)

```cpp
// 重置到初始状态,清空所有已分配区域
void reset() final;

// 尝试添加矩形,成功返回 true 并填充位置
bool addRect(int w, int h, SkIPoint16* loc) final;

// 返回空间使用率(0.0-1.0)
float percentFull() const final;
```

### 继承的基类接口

```cpp
// 获取总宽度和高度
int width() const;
int height() const;

// 添加带边距的矩形
bool addPaddedRect(int width, int height, int16_t padding, SkIPoint16* loc);
```

## 内部实现细节

### Skyline 算法原理

Skyline 算法将二维空间的占用情况抽象为一条"天际线",由一系列水平段组成:

1. **初始状态**: 天际线为一条底部的水平线 `[(0, 0, width)]`
2. **添加矩形**: 寻找天际线上能容纳矩形的最佳位置
3. **更新天际线**: 在放置位置插入新的段,调整受影响的段
4. **合并段**: 合并相邻的同高度段

### addRect 实现流程

```cpp
bool RectanizerSkyline::addRect(int width, int height, SkIPoint16* loc) {
    // 1. 边界检查
    if (width > this->width() || height > this->height()) {
        return false;
    }

    // 2. 寻找最佳位置
    int bestIndex = -1;
    int bestY = this->height() + 1;
    int bestWidth = this->width() + 1;

    for (int i = 0; i < fSkyline.size(); ++i) {
        int y;
        if (this->rectangleFits(i, width, height, &y)) {
            // 优先选择 Y 最小的位置,其次选择宽度最小的段
            if (y < bestY || (y == bestY && fSkyline[i].fWidth < bestWidth)) {
                bestIndex = i;
                bestY = y;
                bestX = fSkyline[i].fX;
                bestWidth = fSkyline[i].fWidth;
            }
        }
    }

    // 3. 放置矩形并更新天际线
    if (bestIndex != -1) {
        addSkylineLevel(bestIndex, bestX, bestY, width, height);
        loc->fX = bestX;
        loc->fY = bestY;
        fAreaSoFar += width * height;
        return true;
    }

    return false;
}
```

### rectangleFits 检查逻辑

```cpp
bool rectangleFits(int skylineIndex, int width, int height, int* ypos) const {
    int x = fSkyline[skylineIndex].fX;

    // 检查宽度是否超出边界
    if (x + width > this->width()) {
        return false;
    }

    // 计算需要的最大高度
    int widthLeft = width;
    int i = skylineIndex;
    int y = fSkyline[skylineIndex].fY;

    while (widthLeft > 0) {
        y = std::max(y, fSkyline[i].fY);  // 取所有覆盖段的最大高度
        if (y + height > this->height()) {
            return false;
        }
        widthLeft -= fSkyline[i].fWidth;
        ++i;
    }

    *ypos = y;
    return true;
}
```

### addSkylineLevel 更新天际线

```cpp
void addSkylineLevel(int skylineIndex, int x, int y, int width, int height) {
    // 1. 插入新段
    SkylineSegment newSegment;
    newSegment.fX = x;
    newSegment.fY = y + height;  // 新的天际线高度
    newSegment.fWidth = width;
    fSkyline.insert(skylineIndex, 1, &newSegment);

    // 2. 删除被新段覆盖的部分
    for (int i = skylineIndex + 1; i < fSkyline.size(); ++i) {
        if (fSkyline[i].fX < fSkyline[i-1].fX + fSkyline[i-1].fWidth) {
            int shrink = fSkyline[i-1].fX + fSkyline[i-1].fWidth - fSkyline[i].fX;
            fSkyline[i].fX += shrink;
            fSkyline[i].fWidth -= shrink;

            if (fSkyline[i].fWidth <= 0) {
                fSkyline.remove(i);  // 完全被覆盖,删除
                --i;
            } else {
                break;  // 部分被覆盖,停止
            }
        } else {
            break;
        }
    }

    // 3. 合并相邻的同高度段
    for (int i = 0; i < fSkyline.size() - 1; ++i) {
        if (fSkyline[i].fY == fSkyline[i+1].fY) {
            fSkyline[i].fWidth += fSkyline[i+1].fWidth;
            fSkyline.remove(i + 1);
            --i;
        }
    }
}
```

### reset 实现

```cpp
void reset() final {
    fAreaSoFar = 0;
    fSkyline.clear();
    // 初始化为底部的单个段
    fSkyline.push_back(SkylineSegment{0, 0, this->width()});
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| Rectanizer | 基类接口 | `src/gpu/Rectanizer.h` |
| SkTDArray | 动态数组容器 | `include/private/base/SkTDArray.h` |
| SkIPoint16 | 16 位整数点 | `src/core/SkIPoint16.h` |
| SkAssert | 断言检查 | `include/private/base/SkAssert.h` |
| std::algorithm | 标准算法(max) | `<algorithm>` |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| GrDrawOpAtlas | 使用方 | Ganesh 绘制操作图集 |
| GrStrikeCache | 使用方 | 字形缓存 |
| sktext::gpu::TextBlobRedrawCoordinator | 使用方 | 文本重绘协调器 |

## 设计模式与设计决策

### 1. 贪心算法策略

算法采用贪心策略选择放置位置:
- **首要目标**: 最小化 Y 坐标(Bottom-Left 放置)
- **次要目标**: 在 Y 相同时,选择宽度最小的段(Best-Fit-Width)

这种策略能够较好地平衡空间利用率和碎片化。

### 2. final 关键字优化

类被标记为 `final`,避免虚函数表查找开销:

```cpp
class RectanizerSkyline final : public Rectanizer
```

在已知使用具体类型的场景中,编译器可以进行去虚拟化优化。

### 3. 工厂方法模式

通过基类的工厂方法创建实例:

```cpp
Rectanizer* Rectanizer::Factory(int width, int height) {
    return new RectanizerSkyline(width, height);
}
```

这使得算法实现可以在运行时或编译时切换(例如切换到 `RectanizerPow2`)。

### 4. 状态跟踪

维护 `fAreaSoFar` 精确跟踪已分配面积,用于:
- 计算空间利用率(`percentFull()`)
- 决策是否需要扩容或创建新图集

### 5. 段合并优化

在更新天际线后主动合并相邻同高度段,减少段数量,提高后续查找效率。

## 性能考量

### 1. 时间复杂度

- **addRect**: O(n^2) 最坏情况,其中 n 是天际线段数
  - 查找最佳位置: O(n * m),m 是平均跨越的段数
  - 更新天际线: O(n)
  - 合并段: O(n)
- **reset**: O(1)
- **percentFull**: O(1)

### 2. 空间复杂度

- 天际线段数量: 最坏情况 O(已添加矩形数)
- 实际使用中,合并操作会大幅减少段数

### 3. 优化措施

**天际线段合并**: 减少段数,提升查找速度
**整数运算**: 所有计算使用整数,避免浮点开销
**提前终止**: `rectangleFits` 中及时返回
**面积跟踪**: 用 `int32_t` 累加,避免每次重新计算

### 4. 缓存友好性

- `SkTDArray` 连续存储,顺序遍历缓存友好
- 结构体小(12 字节),多个段可在同一缓存行

### 5. 实际性能

相比 `RectanizerPow2`:
- **优点**: 空间利用率更高(通常 > 90%)
- **缺点**: 查找时间稍长
- **适用场景**: 需要高空间利用率的长期缓存(字体图集)

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/Rectanizer.h` | 基类 | 抽象接口定义 |
| `src/gpu/RectanizerPow2.h` | 同级实现 | 基于 2 的幂次的简化算法 |
| `src/gpu/ganesh/GrDrawOpAtlas.h` | 使用方 | Ganesh 绘制操作图集 |
| `src/text/gpu/StrikeCache.h` | 使用方 | 字形缓存实现 |
| `tests/RectanizerTest.cpp` | 测试 | 单元测试 |
| `include/private/base/SkTDArray.h` | 依赖 | 动态数组容器 |
| `src/core/SkIPoint16.h` | 依赖 | 16 位坐标点 |
