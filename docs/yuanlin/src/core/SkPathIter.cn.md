# SkPathIter

> 源文件
> - include/core/SkPathIter.h
> - src/core/SkPathIter.cpp

## 概述

`SkPathIter` 是 Skia 路径迭代系统的核心迭代器类,提供了遍历路径动词和点的简洁接口。该类设计用于替代旧的 `SkPath::Iter`,提供更现代、更安全的迭代方式。

主要特性包括:返回包含动词、点和权重的结构体、自动处理 Close 动词的点生成、支持 C++17 范围 for 循环、零开销抽象等。该迭代器广泛应用于路径绘制、变换、分析等场景。

## 架构位置

`SkPathIter` 位于 Skia 路径系统的迭代器层:

```
include/core/
├── SkPath (路径主类)
├── SkPathIter (路径迭代器) ← 当前组件
└── SkPathTypes (路径类型定义)

src/core/
├── SkPathIter.cpp (实现)
├── SkPathPriv.h (使用 SkPathIter)
└── SkPathBuilder.cpp (使用 SkPathIter)
```

迭代器层次:
```
SkPathIter (基础迭代器)
    ↓
SkPathContourIter (轮廓级迭代器)
    ↓
SkPathEdgeIter (边缘迭代器,在 SkPathPriv.h)
```

## 主要类与结构体

### SkPathIter 类

**继承关系**: 无(独立类)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| pIndex | size_t | 当前点索引 |
| vIndex | size_t | 当前动词索引 |
| cIndex | size_t | 当前圆锥权重索引 |
| fPoints | SkSpan<const SkPoint> | 点数组视图 |
| fVerbs | SkSpan<const SkPathVerb> | 动词数组视图 |
| fConics | SkSpan<const float> | 圆锥权重数组视图 |
| fClosePointStorage | std::array<SkPoint, 2> | Close 动词的点存储 |

**返回类型**:

```cpp
struct Rec {
    SkSpan<const SkPoint> fPoints;    // 当前动词的点
    float                 fConicWeight; // 圆锥权重(-1表示非圆锥)
    SkPathVerb            fVerb;       // 动词类型

    float conicWeight() const {
        SkASSERT(fVerb == SkPathVerb::kConic);
        return fConicWeight;
    }
};
```

### SkPathContourIter 类

轮廓级迭代器,按轮廓分组返回路径数据。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPoints | SkSpan<const SkPoint> | 剩余点 |
| fVerbs | SkSpan<const SkPathVerb> | 剩余动词 |
| fConics | SkSpan<const float> | 剩余权重 |

**返回类型**:

```cpp
struct Rec {
    SkSpan<const SkPoint>    fPoints;  // 当前轮廓的点
    SkSpan<const SkPathVerb> fVerbs;   // 当前轮廓的动词
    SkSpan<const float>      fConics;  // 当前轮廓的权重
};
```

## 公共 API 函数

### SkPathIter 构造

```cpp
SkPathIter(SkSpan<const SkPoint> pts,
           SkSpan<const SkPathVerb> vbs,
           SkSpan<const float> cns);
```

**特性**:
- 自动修剪尾部 Move 动词(兼容旧行为)
- 接受 Span 视图,零拷贝
- 轻量级构造

### 迭代方法

```cpp
// 获取下一个动词和点
std::optional<Rec> next();

// 查看下一个动词(不移动迭代器)
std::optional<SkPathVerb> peekNextVerb() const;
```

### SkPathContourIter 构造

```cpp
SkPathContourIter(SkSpan<const SkPoint> pts,
                  SkSpan<const SkPathVerb> vbs,
                  SkSpan<const float> cns);
```

### 轮廓迭代

```cpp
// 获取下一个轮廓
std::optional<Rec> next();
```

## 内部实现细节

### next() 实现

```cpp
std::optional<SkPathIter::Rec> SkPathIter::next() {
    if (vIndex >= fVerbs.size()) {
        return {};  // 迭代结束
    }

    size_t n = 0;
    float w = -1;
    SkPathVerb v;

    switch (v = fVerbs[vIndex++]) {
        case SkPathVerb::kMove:
            // 保存到 fClosePointStorage[1] 用于 Close
            fClosePointStorage[1] = fPoints[pIndex++];
            return Rec{{&fClosePointStorage[1], 1}, w, v};

        case SkPathVerb::kLine:  n = 1; break;
        case SkPathVerb::kQuad:  n = 2; break;
        case SkPathVerb::kConic:
            n = 2;
            w = fConics[cIndex++];
            break;
        case SkPathVerb::kCubic: n = 3; break;

        case SkPathVerb::kClose:
            // 构造从最后点到第一点的线段
            fClosePointStorage[0] = fPoints[pIndex-1];
            return Rec{fClosePointStorage, w, v};
    }

    // 返回前一个点 + n 个新点
    auto start = pIndex - 1;
    pIndex += n;
    return Rec{{&fPoints[start], n+1}, w, v};
}
```

**关键设计**:
1. Move 返回单点,存储在 `fClosePointStorage[1]`
2. 段动词(Line/Quad/Conic/Cubic)返回包含起点的点数组
3. Close 返回隐式线段的两个端点

### 尾部 Move 修剪

构造函数中的兼容逻辑:

```cpp
SkPathIter::SkPathIter(...) {
    // 为兼容旧 SkPath::Iter,修剪尾部 Move
    if (!vbs.empty() && vbs.back() == SkPathVerb::kMove) {
        fVerbs = vbs.first(vbs.size() - 1);
    }
}
```

### SkPathContourIter::next() 实现

```cpp
std::optional<SkPathContourIter::Rec> SkPathContourIter::next() {
    if (fVerbs.empty()) {
        return {};
    }

    SkASSERT(fVerbs[0] == SkPathVerb::kMove);
    size_t npts = 1, nvbs = 1, nws = 0;

    // 扫描直到遇到下一个 Move 或 Close
    for (size_t i = 1; i < fVerbs.size(); ++i) {
        switch (fVerbs[i]) {
            case SkPathVerb::kMove: goto DONE;
            case SkPathVerb::kLine:  npts += 1; break;
            case SkPathVerb::kQuad:  npts += 2; break;
            case SkPathVerb::kConic: npts += 2; nws += 1; break;
            case SkPathVerb::kCubic: npts += 3; break;
            case SkPathVerb::kClose: nvbs += 1; goto DONE;
        }
        nvbs += 1;
    }

DONE:
    // 构造当前轮廓的 Rec
    Rec rec = {
        fPoints.subspan(0, npts),
        fVerbs.subspan(0, nvbs),
        fConics.subspan(0, nws),
    };

    // 更新剩余数据
    fPoints = fPoints.last(fPoints.size() - npts);
    fVerbs  = fVerbs.last(fVerbs.size() - nvbs);
    fConics = fConics.last(fConics.size() - nws);

    return rec;
}
```

### peekNextVerb 实现

```cpp
std::optional<SkPathVerb> SkPathIter::peekNextVerb() const {
    if (vIndex < fVerbs.size()) {
        return fVerbs[vIndex];
    }
    return {};
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPathTypes | SkPathVerb 枚举 |
| SkPoint | 点坐标 |
| SkSpan | 视图容器 |
| std::optional | 可选返回值 |
| std::array | 固定数组 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkPathPriv | 内部迭代辅助 |
| SkPathBuilder | 路径构建 |
| SkPathData | 数据访问 |
| SkPath | 迭代接口 |
| 渲染管线 | 路径遍历 |

## 设计模式与设计决策

### 迭代器模式

提供统一的遍历接口:
```cpp
for (auto rec = iter.next(); rec; rec = iter.next()) {
    // 处理动词
}
```

### std::optional 返回

使用 `std::optional` 表示迭代结束:
```cpp
std::optional<Rec> next();
// 返回 {} 表示结束
```
优点:
- 类型安全
- 明确语义
- 避免哨兵值

### 零拷贝视图

使用 `SkSpan` 传递数据:
- 不拷贝原始数据
- 轻量级构造
- 范围检查(调试模式)

### 内存局部性

`fClosePointStorage` 使用栈数组:
- 避免堆分配
- 缓存友好
- 简化生命周期管理

### 值语义

`Rec` 结构体包含值:
```cpp
struct Rec {
    SkSpan<const SkPoint> fPoints;  // 视图,非指针
    float fConicWeight;             // 值
    SkPathVerb fVerb;               // 枚举
};
```
- 易于使用
- 避免生命周期问题
- 支持结构化绑定

### C++17 结构化绑定

支持现代 C++ 语法:
```cpp
while (auto rec = iter.next()) {
    auto [verb, pts, weight] = *rec;
    // 使用解包的值
}
```

### 兼容性设计

修剪尾部 Move 保持与旧 API 兼容:
```cpp
// SkPathData 定义不创建此模式,但旧代码可能依赖修剪
if (!vbs.empty() && vbs.back() == SkPathVerb::kMove) {
    fVerbs = vbs.first(vbs.size() - 1);
}
```

## 性能考量

### 轻量级迭代器

迭代器大小优化:
- 仅存储索引和视图
- 无虚函数开销
- 可内联 `next()` 调用

### 分支优化

动词处理使用跳转表(编译器优化):
```cpp
switch (verb) {
    case SkPathVerb::kLine:  n = 1; break;
    case SkPathVerb::kQuad:  n = 2; break;
    // ... 编译器生成跳转表
}
```

### 避免分配

Close 动词点使用栈存储:
```cpp
std::array<SkPoint, 2> fClosePointStorage;
// 不需要堆分配
```

### 紧凑循环

`SkPathContourIter` 单次遍历:
- 不回溯
- 线性时间
- 缓存友好

### 早期退出

```cpp
if (vIndex >= fVerbs.size()) {
    return {};  // 立即返回
}
```

### 点共享

段动词共享起点:
```cpp
// Line: pts[0..1]
// Quad: pts[0..2]
// 起点 pts[0] 是上一个动词的终点
return {{&fPoints[start], n+1}, w, v};
```

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPathTypes.h | 依赖 | SkPathVerb 定义 |
| include/core/SkPoint.h | 依赖 | 点坐标类型 |
| include/core/SkSpan.h | 依赖 | 视图容器 |
| include/core/SkPath.h | 使用 | 路径主类 |
| src/core/SkPathPriv.h | 使用 | 私有辅助(SkPathEdgeIter) |
| src/core/SkPathBuilder.cpp | 使用 | 路径构建 |
| src/core/SkPathData.cpp | 使用 | 数据访问 |
