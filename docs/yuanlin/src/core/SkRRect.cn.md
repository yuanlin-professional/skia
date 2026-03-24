# SkRRect

> 源文件
> - include/core/SkRRect.h
> - src/core/SkRRect.cpp

## 概述

`SkRRect` 是 Skia 中表示圆角矩形（Rounded Rectangle）的核心数据结构。它描述一个带有圆角的矩形，每个角可以有独立的 X 轴和 Y 轴半径，支持从简单矩形到复杂椭圆角的各种形状。

`SkRRect` 广泛应用于 UI 渲染，支持 CSS border-radius 属性的完整语义。它通过类型系统优化不同复杂度的圆角矩形，从简单到复杂分为 6 种类型。

主要特性：
- 支持每个角独立的椭圆半径（最多 8 个半径值）
- 自动处理半径重叠和缩放
- 类型优化（Empty、Rect、Oval、Simple、NinePatch、Complex）
- 支持包含性检测、变换、序列化

## 架构位置

`SkRRect` 位于 Skia 核心图形 API（`include/core`）中，是形状表示系统的重要组件。

在 Skia 架构中的位置：
```
形状表示层 → SkRRect（圆角矩形） → 路径/绘制 → 渲染管线
```

应用场景：
- **UI 渲染**：按钮、卡片、对话框的圆角
- **CSS 渲染**：border-radius 属性实现
- **裁剪区域**：圆角裁剪
- **形状动画**：平滑的形状过渡

## 主要类与结构体

### SkRRect

圆角矩形表示。

**继承关系**
- 无继承关系（独立类）
- 标记为 `SK_API`（公共 API）
- 使用 `SK_BEGIN_REQUIRE_DENSE` 确保内存布局紧凑

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fRect` | `SkRect` | 边界矩形 |
| `fRadii` | `SkVector[4]` | 四个角的半径（UL, UR, LR, LL） |
| `fType` | `int32_t` | 类型标记（6 种类型之一） |

**枚举：Type**

| 类型 | 值 | 说明 |
|------|-----|------|
| `kEmpty_Type` | 0 | 空矩形（宽度或高度为 0） |
| `kRect_Type` | 1 | 矩形（所有半径为 0） |
| `kOval_Type` | 2 | 椭圆（半径填满整个矩形） |
| `kSimple_Type` | 3 | 简单圆角（四个角半径相同） |
| `kNinePatch_Type` | 4 | 九宫格（左右 X 半径相同，上下 Y 半径相同） |
| `kComplex_Type` | 5 | 复杂圆角（任意半径组合） |

**枚举：Corner**

| 角 | 索引 | 说明 |
|----|------|------|
| `kUpperLeft_Corner` | 0 | 左上角 |
| `kUpperRight_Corner` | 1 | 右上角 |
| `kLowerRight_Corner` | 2 | 右下角 |
| `kLowerLeft_Corner` | 3 | 左下角 |

## 公共 API 函数

### 构造函数

```cpp
SkRRect() = default;  // 默认构造（Empty）
SkRRect(const SkRRect& rrect) = default;
SkRRect& operator=(const SkRRect& rrect) = default;
```

### 静态构造函数

**基本形状**
```cpp
static SkRRect MakeEmpty();  // 空圆角矩形
static SkRRect MakeRect(const SkRect& r);  // 矩形（无圆角）
static SkRRect MakeOval(const SkRect& oval);  // 椭圆
```

**圆角矩形**
```cpp
static SkRRect MakeRectXY(const SkRect& rect, SkScalar xRad, SkScalar yRad);
// 所有角使用相同的 (xRad, yRad)

static SkRRect MakeRectRadii(const SkRect& rect, const SkVector radii[4]);
// 每个角独立指定半径
```

### 设置函数

```cpp
void setEmpty();  // 设为空
void setRect(const SkRect& rect);  // 设为矩形
void setOval(const SkRect& oval);  // 设为椭圆
void setRectXY(const SkRect& rect, SkScalar xRad, SkScalar yRad);  // 统一圆角
void setNinePatch(const SkRect& rect, SkScalar leftRad, SkScalar topRad,
                  SkScalar rightRad, SkScalar bottomRad);  // 九宫格
void setRectRadii(const SkRect& rect, const SkVector radii[4]);  // 任意半径
```

### 访问器

**类型查询**
```cpp
Type getType() const;
bool isEmpty() const;
bool isRect() const;
bool isOval() const;
bool isSimple() const;
bool isNinePatch() const;
bool isComplex() const;
```

**几何属性**
```cpp
const SkRect& rect() const;        // 边界矩形
const SkRect& getBounds() const;   // 同 rect()
SkScalar width() const;            // 宽度
SkScalar height() const;           // 高度
SkVector getSimpleRadii() const;   // 简单类型的半径
SkVector radii(Corner corner) const;  // 指定角的半径
SkSpan<const SkVector> radii() const; // 所有半径
```

### 几何操作

**内外缩**
```cpp
void inset(SkScalar dx, SkScalar dy, SkRRect* dst) const;  // 内缩到 dst
void inset(SkScalar dx, SkScalar dy);  // 原地内缩
void outset(SkScalar dx, SkScalar dy, SkRRect* dst) const;  // 外扩到 dst
void outset(SkScalar dx, SkScalar dy);  // 原地外扩
```

**平移**
```cpp
void offset(SkScalar dx, SkScalar dy);  // 原地平移
SkRRect makeOffset(SkScalar dx, SkScalar dy) const;  // 返回平移后的副本
```

**变换**
```cpp
std::optional<SkRRect> transform(const SkMatrix& matrix) const;  // 矩阵变换
bool transform(const SkMatrix& matrix, SkRRect* dst) const;  // 旧版接口
```

### 包含性检测

```cpp
bool contains(const SkRect& rect) const;  // 检测矩形是否在圆角矩形内
```

### 比较

```cpp
friend bool operator==(const SkRRect& a, const SkRRect& b);
friend bool operator!=(const SkRRect& a, const SkRRect& b);
```

### 验证和序列化

```cpp
bool isValid() const;  // 检查数据有效性

static constexpr size_t kSizeInMemory = 12 * sizeof(SkScalar);
size_t writeToMemory(void* buffer) const;  // 序列化
size_t readFromMemory(const void* buffer, size_t length);  // 反序列化
```

### 调试

```cpp
void dump(bool asHex) const;  // 打印到标准输出
void dump() const;            // 打印（十进制）
void dumpHex() const;         // 打印（十六进制）
SkString dumpToString(bool asHex) const;  // 转为字符串
```

## 内部实现细节

### 类型计算（computeType）

**自动类型推断算法**
```cpp
void SkRRect::computeType() {
    // 1. 检查空矩形
    if (fRect.isEmpty()) {
        fType = kEmpty_Type;
        return;
    }

    // 2. 检查所有角是否为方角
    bool allCornersSquare = (所有角半径为 0);
    if (allCornersSquare) {
        fType = kRect_Type;
        return;
    }

    // 3. 检查所有半径是否相等
    bool allRadiiEqual = (所有半径相同);
    if (allRadiiEqual) {
        if (半径 >= 半边长) {
            fType = kOval_Type;
        } else {
            fType = kSimple_Type;
        }
        return;
    }

    // 4. 检查是否为九宫格
    if (radii_are_nine_patch(fRadii)) {
        fType = kNinePatch_Type;
    } else {
        fType = kComplex_Type;
    }
}
```

**九宫格判断**
```cpp
bool radii_are_nine_patch(const SkVector radii[4]) {
    return radii[UL].fX == radii[LL].fX &&  // 左边 X 半径相同
           radii[UL].fY == radii[UR].fY &&  // 上边 Y 半径相同
           radii[UR].fX == radii[LR].fX &&  // 右边 X 半径相同
           radii[LL].fY == radii[LR].fY;    // 下边 Y 半径相同
}
```

### 半径缩放（scaleRadii）

当半径之和超过边长时，按比例缩放所有半径以适应矩形。

**算法：W3C CSS 规范**
```
设 f = min(Li/Si)
其中 i ∈ {top, right, bottom, left}
     Si = 该边两个相邻角的半径之和
     Li = 该边的长度
如果 f < 1，则所有半径乘以 f
```

**实现细节**
1. 使用双精度计算避免溢出：
   ```cpp
   double width = (double)fRect.fRight - (double)fRect.fLeft;
   double scale = compute_min_scale(radii[0].fX, radii[1].fX, width, 1.0);
   ```

2. 应用 `SkScaleToSides::AdjustRadii` 调整半径
3. 使用 `flush_to_zero` 处理相对极小值
4. 调用 `clamp_to_zero` 清理负值和零值

**flush_to_zero 策略**
```cpp
// 如果 a + b == a，说明 b 相对于 a 太小，将 b 设为 0
if (a + b == a) b = 0;
```

### 包含性检测（checkCornerContainment）

**算法：椭圆方程**
```
点 (x, y) 在椭圆内当且仅当：
    (x - cx)²     (y - cy)²
    ---------- + ---------- <= 1
       a²            b²
```

**步骤**
1. 判断点在哪个角的影响范围内
2. 将点转换为该角的椭圆坐标系（canonical coordinates）
3. 应用椭圆方程判断
4. 非角区域直接返回 `true`

### 变换（transform）

**支持的变换类型**
- 缩放
- 平移
- 90°/270° 旋转（轴对齐）
- 翻转

**不支持的变换**
- 任意角度旋转
- 倾斜（skew）
- 透视变换

**90° 旋转处理**
```cpp
if (isClockwise) {
    // 顺时针：交换 X/Y，调整角索引
    dst->fRadii[i].fX = fRadii[(i + 3) % 4].fY;
    dst->fRadii[i].fY = fRadii[(i + 3) % 4].fX;
}
```

**翻转处理**
- `flipX`：左右角互换
- `flipY`：上下角互换
- `flipX && flipY`：对角互换

### 内边界计算（InnerBounds）

**SkRRectPriv::InnerBounds 算法**

计算圆角矩形内部的最大内接矩形，考虑三种策略：
1. **水平内缩**：左右边内缩，保留上下完整
2. **垂直内缩**：上下边内缩，保留左右完整
3. **全边内缩**：所有边按 `(1 - √2/2)` 缩放因子内缩

选择面积最大的策略。

**关键公式**
```cpp
static constexpr SkScalar kScale = (1.f - SK_ScalarRoot2Over2) + 1e-5f;
// kScale ≈ 0.293，确保内接矩形角点在圆弧内
```

### 保守交集（ConservativeIntersect）

**SkRRectPriv::ConservativeIntersect 算法**

计算两个圆角矩形的交集，如果交集仍为圆角矩形则返回，否则返回空。

**步骤**
1. 计算边界矩形的交集
2. 对每个角：
   - 如果两个圆角矩形共享角点，选择半径较大的
   - 如果交集角点来自 A，检查 A 的角是否在 B 内
   - 如果交集角点来自 B，检查 B 的角是否在 A 内
   - 如果是新角点，检查是否在两个圆角矩形内
3. 验证半径不重叠（`AreRectAndRadiiValid` + `scaleRadii`）

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRect` | 边界矩形表示 |
| `SkPoint` / `SkVector` | 半径表示 |
| `SkMatrix` | 变换操作 |
| `SkScalar` | 标量类型 |
| `SkScaleToSides` | 半径调整算法 |
| `SkRRectPriv` | 私有辅助函数 |
| `SkPathPriv` | 路径推导 |
| `SkBuffer` | 序列化支持 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPath` | 圆角矩形路径生成 |
| `SkCanvas` | 绘制圆角矩形 |
| `SkClipStack` | 圆角裁剪 |
| `SkRTree` | 空间索引（边界矩形） |
| `SkShader` | 圆角遮罩 |

## 设计模式与设计决策

### 设计模式

1. **类型标记模式（Type Tag）**
   - 使用 `fType` 区分 6 种类型
   - 优化不同复杂度的处理

2. **工厂方法模式**
   - 静态 `Make*` 函数构造不同类型

3. **值语义**
   - 默认拷贝和赋值
   - 无动态内存分配

### 设计决策

**为何需要 6 种类型**
- **性能优化**：简单类型可快速处理
- **内存优化**：简单类型无需存储所有半径
- **渲染优化**：不同类型使用不同的光栅化路径

**为何半径可能被缩放**
- **CSS 兼容性**：遵循 W3C 规范
- **数学正确性**：避免半径重叠导致无效形状

**为何使用双精度缩放**
- **数值稳定性**：单精度可能完全丢失缩放需求（crbug.com/463920）
- **极端值支持**：处理非常大或非常小的矩形

**为何变换可能失败**
- **形状限制**：非轴对齐变换无法用圆角矩形表示
- **明确语义**：返回 `std::optional` 或 `bool`

**为何使用 `SK_BEGIN_REQUIRE_DENSE`**
- **内存布局**：确保没有填充字节
- **序列化保证**：`kSizeInMemory` 精确

**为何包含性检测使用椭圆方程**
- **精确性**：准确判断点与圆弧的关系
- **效率**：避免复杂的曲线求交

**为何支持九宫格类型**
- **常见场景**：许多 UI 元素使用九宫格圆角
- **优化机会**：渲染和裁剪可以优化

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 构造 | O(1) | 简单赋值 |
| 类型计算 | O(1) | 固定比较次数 |
| 半径缩放 | O(1) | 固定计算量 |
| 包含性检测 | O(1) | 椭圆方程计算 |
| 变换 | O(1) | 矩阵运算 |
| 序列化 | O(1) | 固定大小拷贝 |

### 空间复杂度

**内存占用**
```
sizeof(SkRRect) = sizeof(SkRect) + 4 * sizeof(SkVector) + sizeof(int32_t)
                = 4 * 4 + 4 * 8 + 4 = 52 字节
```

**序列化大小**
```
kSizeInMemory = 12 * sizeof(SkScalar) = 48 字节
（不包含 fType，反序列化时重新计算）
```

### 优化策略

1. **类型快速路径**
   ```cpp
   if (isRect()) {
       // 简单矩形裁剪
   } else if (isOval()) {
       // 椭圆裁剪
   } else {
       // 通用路径
   }
   ```

2. **缓存类型**
   - `fType` 存储避免重复计算

3. **延迟验证**
   - 仅在需要时调用 `isValid()`

4. **避免不必要的缩放**
   - `scaleRadii` 返回是否进行了缩放

### 性能陷阱

- **频繁 setRectRadii**：触发类型计算和缩放
- **复杂包含性检测**：需要检查所有四个角
- **变换失败重试**：非轴对齐变换需要回退到路径

### 使用建议

**优先使用简单类型**
```cpp
// 优先
SkRRect::MakeRectXY(rect, 5, 5);

// 避免（除非真的需要）
SkVector radii[4] = {{5,5}, {5,5}, {5,5}, {5,5}};
SkRRect::MakeRectRadii(rect, radii);
```

**缓存类型判断**
```cpp
bool isSimple = rr.isSimple();
if (isSimple) {
    // 多次使用 isSimple 的优化路径
}
```

**使用 makeOffset 避免拷贝**
```cpp
SkRRect offsetRR = rr.makeOffset(dx, dy);  // 返回值优化（RVO）
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkRect.h` | 依赖 | 边界矩形 |
| `include/core/SkMatrix.h` | 依赖 | 变换矩阵 |
| `src/core/SkRRectPriv.h` | 扩展 | 私有辅助函数 |
| `src/core/SkScaleToSides.h` | 依赖 | 半径调整算法 |
| `src/core/SkPathPriv.h` | 依赖 | 路径推导 |
| `include/core/SkPath.h` | 使用者 | 生成圆角矩形路径 |
| `include/core/SkCanvas.h` | 使用者 | 绘制接口 |
| `src/core/SkClipStack.cpp` | 使用者 | 裁剪栈 |
| `src/gpu/ganesh/GrRRect*` | 相关 | GPU 圆角矩形渲染 |
