# SkPathMeasure

> 源文件
> - include/core/SkPathMeasure.h
> - src/core/SkPathMeasure.cpp

## 概述

`SkPathMeasure` 是 Skia 路径测量系统的公共接口类,提供了沿路径测量距离、获取位置和切线、提取子路径等功能。该类是对底层 `SkContourMeasure` 的封装,简化了路径测量操作的使用。

主要功能包括:计算路径长度、在指定距离处获取坐标和切线、提取指定距离区间的路径片段、遍历多轮廓路径等。这些功能广泛应用于路径动画、文字沿路径排版、虚线绘制等场景。

## 架构位置

`SkPathMeasure` 位于 Skia 核心图形层的路径测量子系统:

```
include/core/
├── SkPath (路径主类)
├── SkPathMeasure (路径测量接口) ← 当前组件
└── SkContourMeasure (轮廓测量实现)

src/core/
├── SkPathMeasure.cpp (实现)
├── SkPathMeasurePriv.h (私有辅助)
└── SkContourMeasure.cpp (底层实现)
```

调用关系:
```
用户代码
    ↓
SkPathMeasure (公共接口)
    ↓
SkContourMeasure (轮廓级测量)
    ↓
Segment 列表 (分段数据)
```

## 主要类与结构体

### SkPathMeasure 类

**继承关系**: 无(独立类)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fIter | SkContourMeasureIter | 轮廓迭代器 |
| fContour | sk_sp<SkContourMeasure> | 当前轮廓测量对象 |

**枚举类型**:

```cpp
enum MatrixFlags {
    kGetPosition_MatrixFlag  = 0x01,  // 仅位置
    kGetTangent_MatrixFlag   = 0x02,  // 仅切线
    kGetPosAndTan_MatrixFlag = 0x03   // 位置和切线
};
```

## 公共 API 函数

### 构造和配置

```cpp
// 默认构造函数(空测量)
SkPathMeasure();

// 从路径构造
SkPathMeasure(const SkPath& path,
              bool forceClosed,
              SkScalar resScale = 1);

// 设置路径
void setPath(const SkPath* path, bool forceClosed);
```

**参数说明**:
- `path`: 要测量的路径
- `forceClosed`: 是否强制闭合路径
- `resScale`: 分辨率缩放(>1 提高精度,<1 降低精度)

### 长度查询

```cpp
// 获取当前轮廓长度
SkScalar getLength();
```

返回当前轮廓的总长度,如果路径为空则返回 0。

### 位置和切线

```cpp
// 获取指定距离处的位置和切线
[[nodiscard]] bool getPosTan(SkScalar distance,
                              SkPoint* position,
                              SkVector* tangent);

// 获取指定距离处的矩阵
[[nodiscard]] bool getMatrix(SkScalar distance,
                              SkMatrix* matrix,
                              MatrixFlags flags = kGetPosAndTan_MatrixFlag);
```

**getPosTan**:
- `distance`: 沿路径的距离(会被钳制到 [0, length])
- `position`: 输出位置(可为 nullptr)
- `tangent`: 输出切线方向(可为 nullptr)
- 返回: 成功返回 true,路径为空或零长度返回 false

**getMatrix**:
- 构造包含位置和/或切线的变换矩阵
- `flags`: 控制矩阵包含的信息

### 路径片段提取

```cpp
// 提取指定距离区间的路径片段
bool getSegment(SkScalar startD,
                SkScalar stopD,
                SkPathBuilder* dst,
                bool startWithMoveTo);
```

**参数**:
- `startD`, `stopD`: 起止距离(会被钳制到 [0, length])
- `dst`: 输出路径构建器
- `startWithMoveTo`: 是否以 moveTo 开始新轮廓

**行为**:
- 如果 startD > stopD,返回 false
- 如果区间长度为零,返回 false
- 成功提取返回 true

### 轮廓遍历

```cpp
// 判断当前轮廓是否闭合
bool isClosed();

// 移动到下一个轮廓
bool nextContour();
```

**nextContour**:
- 移动到路径中的下一个轮廓
- 有下一个轮廓返回 true
- 已遍历完所有轮廓返回 false

### 调试接口

```cpp
#ifdef SK_DEBUG
void dump();
#endif

// 访问底层轮廓测量对象
const SkContourMeasure* currentMeasure() const;
```

## 内部实现细节

### 委托模式

`SkPathMeasure` 的所有功能都委托给 `SkContourMeasure`:

```cpp
SkScalar SkPathMeasure::getLength() {
    return fContour ? fContour->length() : 0;
}

bool SkPathMeasure::getPosTan(SkScalar distance,
                               SkPoint* position,
                               SkVector* tangent) {
    return fContour && fContour->getPosTan(distance, position, tangent);
}
```

### 构造流程

```cpp
SkPathMeasure::SkPathMeasure(const SkPath& path,
                             bool forceClosed,
                             SkScalar resScale)
    : fIter(path, forceClosed, resScale)  // 初始化迭代器
{
    fContour = fIter.next();  // 获取第一个轮廓
}
```

### setPath 实现

```cpp
void SkPathMeasure::setPath(const SkPath* path, bool forceClosed) {
    // 处理 nullptr(重置为空路径)
    fIter.reset(path ? *path : SkPath(), forceClosed);
    fContour = fIter.next();  // 移动到第一个轮廓
}
```

### 轮廓切换

```cpp
bool SkPathMeasure::nextContour() {
    fContour = fIter.next();  // 获取下一个轮廓
    return !!fContour;        // 转换为 bool
}
```

### 矩阵标志转换

```cpp
bool SkPathMeasure::getMatrix(SkScalar distance,
                              SkMatrix* matrix,
                              MatrixFlags flags) {
    // 直接转换枚举(值匹配)
    return fContour && fContour->getMatrix(
        distance, matrix,
        (SkContourMeasure::MatrixFlags)flags);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 输入路径对象 |
| SkContourMeasure | 底层测量实现 |
| SkContourMeasureIter | 轮廓迭代器 |
| SkPathBuilder | 路径片段输出 |
| SkMatrix | 位置/切线矩阵 |
| SkPoint | 位置坐标 |
| SkVector | 切线向量 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| 动画系统 | 沿路径动画 |
| 文本渲染 | 文字沿路径排版 |
| 路径效果 | 虚线、箭头等 |
| UI 工具包 | 路径交互 |
| 测试代码 | 路径验证 |

## 设计模式与设计决策

### 门面模式(Facade)

`SkPathMeasure` 为复杂的轮廓测量系统提供简化接口:
- 隐藏 `SkContourMeasureIter` 和 `SkContourMeasure` 的细节
- 提供易用的 API
- 自动管理轮廓迭代

### 委托模式

所有实际工作委托给 `SkContourMeasure`:
```cpp
bool SkPathMeasure::isClosed() {
    return fContour && fContour->isClosed();
}
```
好处:
- 代码复用
- 职责分离
- 便于维护

### 空对象模式

使用 nullptr 表示无轮廓状态:
```cpp
SkScalar SkPathMeasure::getLength() {
    return fContour ? fContour->length() : 0;
}
```
优点:
- 避免特殊检查
- 简化调用代码
- 一致的行为

### 智能指针管理

使用 `sk_sp<SkContourMeasure>` 管理生命周期:
- 自动引用计数
- 异常安全
- 避免内存泄漏

### 移动语义支持

```cpp
SkPathMeasure(SkPathMeasure&&) = default;
SkPathMeasure& operator=(SkPathMeasure&&) = default;
```
支持高效的对象传递。

### [[nodiscard]] 属性

关键方法标记为 `[[nodiscard]]`:
```cpp
[[nodiscard]] bool getPosTan(...);
[[nodiscard]] bool getMatrix(...);
```
强制调用者检查返回值,避免忽略错误。

## 性能考量

### 惰性计算

仅在首次访问时计算轮廓数据:
- `SkContourMeasure` 按需构建分段表
- 避免对未使用轮廓的计算开销

### 缓存优化

- 轮廓长度缓存在 `SkContourMeasure` 中
- 分段表构建后持久化
- 重复查询无额外开销

### 分辨率控制

`resScale` 参数允许性能/精度权衡:
- `resScale > 1`: 更高精度,更多分段
- `resScale < 1`: 更低精度,更少分段
- 默认 `resScale = 1` 平衡性能和质量

### 最小接口

仅暴露必要功能:
- 减少 ABI 表面积
- 便于内联优化
- 降低编译依赖

### 零拷贝设计

- `getPosTan` 直接输出到调用者提供的指针
- 避免临时对象创建
- 减少内存分配

### 短路求值

```cpp
return fContour && fContour->getPosTan(...);
```
- 如果 `fContour` 为空,直接返回 false
- 避免空指针解引用检查

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkContourMeasure.h | 依赖 | 轮廓测量实现 |
| src/core/SkPathMeasurePriv.h | 使用 | 私有辅助函数 |
| include/core/SkPath.h | 输入 | 路径对象 |
| include/core/SkPathBuilder.h | 输出 | 路径构建器 |
| include/core/SkMatrix.h | 依赖 | 变换矩阵 |
| include/core/SkPoint.h | 依赖 | 点和向量 |
| src/core/SkGeometry.h | 间接 | 曲线几何(通过 SkContourMeasure) |
