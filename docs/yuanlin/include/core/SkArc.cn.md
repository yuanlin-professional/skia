# SkArc

> 源文件: `include/core/SkArc.h`

## 概述

SkArc 是表示椭圆弧或楔形扇区的结构体,封装了在椭圆边界上绘制弧线段或包含中心点的扇形所需的所有参数。它统一了弧线和扇形的表示,通过类型标志区分开放弧和闭合楔形,是 Skia 绘制系统中圆弧相关操作的核心数据结构。

## 架构位置

SkArc 位于 Skia 核心几何类型层,属于形状描述子系统。它被 SkCanvas 的弧线绘制方法和内部几何处理模块使用,提供了比传统 drawArc 参数更清晰的语义表达。该结构体是几何数据与绘制逻辑之间的桥梁。

## 主要类与结构体

### SkArc

**职责描述**: 封装圆弧或扇形的完整几何定义,包括外接椭圆、角度范围和类型标志。

**继承关系**: 无继承(纯数据结构体)

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fOval | SkRect | 包含圆弧的椭圆的外接矩形 |
| fStartAngle | SkScalar | 圆弧起始角度(度数),0度为水平向右 |
| fSweepAngle | SkScalar | 扫描角度(度数),正值为顺时针 |
| fType | Type | 圆弧类型(开放弧或闭合楔形) |

## 嵌套类型

### SkArc::Type 枚举

```cpp
enum class Type : bool {
    kArc,   // 开放弧线,仅沿椭圆周边
    kWedge  // 闭合楔形,包含椭圆中心点
};
```

**类型对比**:

| 类型 | 几何形状 | 是否包含中心 | 用途 |
|------|---------|------------|------|
| kArc | 开放曲线段 | 否 | 描边、曲线路径 |
| kWedge | 扇形(饼图切片) | 是 | 填充、饼图 |

**视觉差异**:
- **kArc**: 仅绘制圆弧本身,两端为开放端点
- **kWedge**: 绘制扇形,包含从中心到圆弧两端的直线

## 公共 API 函数

### 访问器方法

#### `const SkRect& oval() const`
- **功能**: 获取椭圆外接矩形
- **返回值**: 常量引用,避免拷贝

#### `SkScalar startAngle() const`
- **功能**: 获取起始角度(度数)
- **返回值**: 角度值,0度为水平向右(东)

#### `SkScalar sweepAngle() const`
- **功能**: 获取扫描角度(度数)
- **返回值**: 正值为顺时针,负值为逆时针

#### `bool isWedge() const`
- **功能**: 检查是否为楔形扇区
- **返回值**: true 表示楔形,false 表示开放弧

### 工厂方法

#### `static SkArc Make(const SkRect& oval, SkScalar startAngleDegrees, SkScalar sweepAngleDegrees, Type type)`
- **功能**: 创建 SkArc 对象的首选工厂方法
- **参数**:
  - `oval`: 椭圆的外接矩形
  - `startAngleDegrees`: 起始角度(度数)
  - `sweepAngleDegrees`: 扫描角度(度数)
  - `type`: 圆弧类型(kArc 或 kWedge)
- **返回值**: 初始化完成的 SkArc 对象

#### `static SkArc Make(const SkRect& oval, SkScalar startAngleDegrees, SkScalar sweepAngleDegrees, bool useCenter)` (已废弃)
- **功能**: 兼容传统 useCenter 参数的工厂方法
- **参数**:
  - `useCenter`: true 映射到 kWedge,false 映射到 kArc
- **状态**: 标记为 Deprecated,用于辅助遗留代码迁移
- **说明**: 新代码应使用明确的 Type 参数版本

### 比较运算符

#### `friend bool operator==(const SkArc& a, const SkArc& b)`
- **功能**: 判断两个 SkArc 是否相等
- **比较内容**: 所有成员变量(fOval, fStartAngle, fSweepAngle, fType)
- **返回值**: 完全相等时返回 true

#### `friend bool operator!=(const SkArc& a, const SkArc& b)`
- **功能**: 判断两个 SkArc 是否不等
- **实现**: `!(a == b)`

## 内部实现细节

### 角度约定

**坐标系统**:
- 原点在外接矩形的中心
- 0度指向水平右侧(东方向)
- 角度按顺时针方向增加

**角度示意**:
```
        270°
         |
180° ----+---- 0°
         |
        90°
```

### 扫描角度语义

**正值**: 顺时针扫描
```cpp
SkArc arc = SkArc::Make(rect, 0, 90, Type::kArc);
// 从0度(东)到90度(南),顺时针1/4圆
```

**负值**: 逆时针扫描
```cpp
SkArc arc = SkArc::Make(rect, 0, -90, Type::kArc);
// 从0度(东)到270度(北),逆时针1/4圆
```

**超过360度**: 允许多圈扫描
```cpp
SkArc arc = SkArc::Make(rect, 0, 720, Type::kArc);
// 完整旋转两圈
```

### 默认构造

```cpp
SkArc() = default;
```
- fOval 初始化为空矩形
- fStartAngle 和 fSweepAngle 初始化为 0
- fType 初始化为 kArc

### 私有构造函数

```cpp
private:
    SkArc(const SkRect& oval, SkScalar startAngle, SkScalar sweepAngle, Type type)
            : fOval(oval), fStartAngle(startAngle), fSweepAngle(sweepAngle), fType(type) {}
```
- 强制使用工厂方法创建对象
- 确保参数验证和语义明确

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkRect.h | 椭圆外接矩形类型 |
| SkScalar.h | 角度和坐标的标量类型 |

### 被依赖的模块

SkArc 被以下模块使用:
- **SkCanvas**: drawArc 方法可能接受 SkArc 参数
- **SkPath**: 添加弧线段到路径
- **GPU 后端**: 几何处理和曲面细分
- **测试框架**: 弧线相关的单元测试

## 设计模式与设计决策

### 强类型枚举替代 bool

传统 API 使用 `bool useCenter`:
```cpp
// 旧风格:语义不明确
canvas->drawArc(rect, 0, 90, true, paint);  // true 是什么意思?
```

新设计使用强类型枚举:
```cpp
// 新风格:自文档化
SkArc arc = SkArc::Make(rect, 0, 90, SkArc::Type::kWedge);
canvas->drawArc(arc, paint);
```

**优势**:
- 代码可读性提升
- 编译时类型检查
- 避免 true/false 歧义

### 值语义对象

SkArc 是轻量级值类型:
- 支持拷贝和赋值(编译器生成)
- 无需动态内存分配
- 易于存储在容器中

### 工厂方法设计

私有构造函数 + 静态工厂方法的好处:
- 统一创建入口
- 便于添加参数验证
- 支持命名构造
- 为未来扩展留余地

## 性能考量

### 内存布局

```cpp
sizeof(SkArc) = sizeof(SkRect) + 2*sizeof(SkScalar) + sizeof(bool)
              ≈ 4*4 + 2*4 + 1 = 25 字节(可能对齐到 28 或 32 字节)
```

### 拷贝成本

SkArc 是 POD-like 类型:
- 拷贝仅需内存复制
- 无虚函数,无动态分配
- 适合按值传递

### 使用建议

- **按值传递**: 对象小,拷贝成本低
- **避免指针**: 无需动态分配
- **栈上分配**: 性能最优

## 使用示例

### 绘制饼图扇区

```cpp
SkRect oval = SkRect::MakeXYWH(100, 100, 200, 200);

// 第一个扇区: 0°到120°
SkArc wedge1 = SkArc::Make(oval, 0, 120, SkArc::Type::kWedge);
paint.setColor(SK_ColorRED);
canvas->drawArc(wedge1, paint);

// 第二个扇区: 120°到240°
SkArc wedge2 = SkArc::Make(oval, 120, 120, SkArc::Type::kWedge);
paint.setColor(SK_ColorGREEN);
canvas->drawArc(wedge2, paint);

// 第三个扇区: 240°到360°
SkArc wedge3 = SkArc::Make(oval, 240, 120, SkArc::Type::kWedge);
paint.setColor(SK_ColorBLUE);
canvas->drawArc(wedge3, paint);
```

### 绘制开放弧线

```cpp
SkRect oval = SkRect::MakeXYWH(50, 50, 100, 150);

// 描边圆弧,不连接中心
SkArc arc = SkArc::Make(oval, 45, 270, SkArc::Type::kArc);
paint.setStyle(SkPaint::kStroke_Style);
paint.setStrokeWidth(3);
canvas->drawArc(arc, paint);
```

### 路径中添加圆弧

```cpp
SkPath path;
path.moveTo(100, 100);

SkArc arc = SkArc::Make(
    SkRect::MakeXYWH(150, 100, 100, 100),
    0, 180, SkArc::Type::kArc);

path.arcTo(arc.oval(), arc.startAngle(), arc.sweepAngle(), false);
path.close();

canvas->drawPath(path, paint);
```

## 与 drawArc 的关系

传统 SkCanvas::drawArc 签名:
```cpp
void drawArc(const SkRect& oval, SkScalar startAngle, SkScalar sweepAngle,
             bool useCenter, const SkPaint& paint);
```

可能的未来 API(使用 SkArc):
```cpp
void drawArc(const SkArc& arc, const SkPaint& paint);
```

**优势**:
- 减少参数数量
- 参数语义更清晰
- 圆弧对象可重用

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkRect.h | 椭圆外接矩形 |
| include/core/SkScalar.h | 角度和坐标类型 |
| include/core/SkCanvas.h | 绘制圆弧的 API |
| include/core/SkPath.h | 路径中的圆弧操作 |
| src/core/SkGeometry.h | 圆弧几何计算 |
