# SkNWayCanvas

> 源文件: include/utils/SkNWayCanvas.h, src/utils/SkNWayCanvas.cpp

## 概述

SkNWayCanvas 是一个特殊的 Canvas 实现,能够将所有绘图操作同时转发到多个子 Canvas。它实现了"一对多"的绘图广播模式,当在 SkNWayCanvas 上执行绘图命令时,所有注册的子 Canvas 都会执行相同的操作。这种设计常用于需要同时向多个目标输出相同图形的场景,例如同时渲染到屏幕和保存到文件。

主要功能:
- 管理多个子 Canvas 的集合
- 转发所有绘图命令到子 Canvas
- 同步状态操作(保存/恢复/变换/裁剪)
- 支持动态添加和移除子 Canvas
- 无需单独的图层或缓冲

## 架构位置

SkNWayCanvas 位于 Skia 的 utils 模块中,作为 Canvas 的高级封装:

```
Skia Graphics Library
├── Core
│   ├── SkCanvas (基础画布接口)
│   ├── SkDevice (设备抽象)
│   └── SkNoDrawCanvas (无绘制基类)
├── Utils
│   ├── SkNWayCanvas (多路广播 Canvas) ← 当前模块
│   ├── SkCanvasStack (Canvas 栈)
│   └── SkCanvasVirtualEnforcer (虚函数强制器)
└── Text
    └── GlyphRunList (文本渲染)
```

SkNWayCanvas 继承自 SkNoDrawCanvas,重写所有绘图和状态管理方法来实现转发逻辑。

## 主要类与结构体

### SkNWayCanvas

**类型**: Canvas 容器类

**继承关系**:
```
SkRefCnt
  └── SkCanvas
        └── SkNoDrawCanvas
              └── SkCanvasVirtualEnforcer<SkNoDrawCanvas>
                    └── SkNWayCanvas
```

**关键成员变量**:

| 成员类型 | 名称 | 访问性 | 说明 |
|---------|------|--------|------|
| SkTDArray<SkCanvas*> | fList | protected | 子 Canvas 指针数组 |

**特性**:
- 使用 SkCanvasVirtualEnforcer 确保所有虚函数被正确重写
- 继承自 SkNoDrawCanvas 避免默认绘图行为
- 所有绘图方法都被重写为转发实现

### SkNWayCanvas::Iter (内部迭代器)

**类型**: 内部辅助类

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| const SkTDArray<SkCanvas*>& | fList | Canvas 列表引用 |
| int | fIndex | 当前迭代位置 |
| SkCanvas* | fCanvas | 当前 Canvas 指针 |

**接口方法**:
- `bool next()`: 移动到下一个 Canvas,返回是否成功
- `SkCanvas* operator->()`: 访问当前 Canvas
- `SkCanvas* get() const`: 获取当前 Canvas 指针

## 公共 API 函数

### 构造函数

```cpp
SkNWayCanvas(int width, int height);
```

**功能**: 创建指定尺寸的 N-Way Canvas。

**参数**:
- `width`: Canvas 宽度
- `height`: Canvas 高度

**特性**:
- 初始状态不包含任何子 Canvas
- 需要通过 addCanvas() 添加目标

### 析构函数

```cpp
~SkNWayCanvas() override;
```

**功能**: 清理资源,调用 removeAll()。

### addCanvas

```cpp
virtual void addCanvas(SkCanvas* canvas);
```

**功能**: 添加子 Canvas 到转发列表。

**参数**:
- `canvas`: 要添加的 Canvas 指针(可以为 nullptr,会被忽略)

**注意事项**:
- 不转移所有权,调用者负责管理子 Canvas 生命周期
- 添加第二个 Canvas 时会进行设备检查(确保设备与 N-Way Canvas 的根设备不同)
- 可以添加任意数量的子 Canvas

### removeCanvas

```cpp
virtual void removeCanvas(SkCanvas* canvas);
```

**功能**: 从转发列表中移除指定 Canvas。

**参数**:
- `canvas`: 要移除的 Canvas 指针

**特性**:
- 使用 removeShuffle 进行快速删除(不保持顺序)
- 如果 Canvas 不在列表中,操作无影响

### removeAll

```cpp
virtual void removeAll();
```

**功能**: 移除所有子 Canvas。

**特性**:
- 重置内部列表为空
- 不会销毁子 Canvas(仅移除引用)

## 内部实现细节

### 转发模式实现

所有绘图和状态操作遵循统一的转发模式:

```cpp
void SkNWayCanvas::onDrawXXX(...) {
    Iter iter(fList);
    while (iter.next()) {
        iter->drawXXX(...);
    }
}
```

这种模式确保:
1. 遍历所有子 Canvas
2. 对每个子 Canvas 执行相同操作
3. 按照添加顺序依次调用

### 状态管理

#### 保存操作

```cpp
void willSave() override {
    Iter iter(fList);
    while (iter.next()) {
        iter->save();
    }
    this->INHERITED::willSave();
}
```

**特性**:
- 先转发到所有子 Canvas
- 然后调用基类 willSave 更新自身状态

#### 图层保存策略

```cpp
SaveLayerStrategy getSaveLayerStrategy(const SaveLayerRec& rec) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->saveLayer(rec);
    }
    this->INHERITED::getSaveLayerStrategy(rec);
    return kNoLayer_SaveLayerStrategy;
}
```

**设计决策**:
- 转发 saveLayer 到所有子 Canvas
- 返回 kNoLayer_SaveLayerStrategy,因为 N-Way Canvas 自己不需要图层
- 子 Canvas 会根据自己的需要创建图层

#### 恢复操作

```cpp
void willRestore() override {
    Iter iter(fList);
    while (iter.next()) {
        iter->restore();
    }
    this->INHERITED::willRestore();
}
```

### 变换操作转发

支持多种变换操作:

#### 矩阵拼接

```cpp
void didConcat44(const SkM44& m) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->concat(m);
    }
}
```

#### 矩阵设置

```cpp
void didSetM44(const SkM44& matrix) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->setMatrix(matrix);
    }
}
```

#### 平移和缩放

```cpp
void didTranslate(SkScalar x, SkScalar y) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->translate(x, y);
    }
}

void didScale(SkScalar x, SkScalar y) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->scale(x, y);
    }
}
```

### 裁剪操作转发

支持多种裁剪形状:

```cpp
void onClipRect(const SkRect& rect, SkClipOp op, ClipEdgeStyle edgeStyle) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->clipRect(rect, op, kSoft_ClipEdgeStyle == edgeStyle);
    }
    this->INHERITED::onClipRect(rect, op, edgeStyle);
}

void onClipRRect(const SkRRect& rrect, SkClipOp op, ClipEdgeStyle edgeStyle) override;
void onClipPath(const SkPath& path, SkClipOp op, ClipEdgeStyle edgeStyle) override;
void onClipShader(sk_sp<SkShader> sh, SkClipOp op) override;
void onClipRegion(const SkRegion& deviceRgn, SkClipOp op) override;
```

**特性**:
- 转发后调用基类方法更新自身裁剪状态
- 支持抗锯齿边缘样式转换

### 绘图操作转发

#### 基础形状

```cpp
void onDrawRect(const SkRect& rect, const SkPaint& paint) override;
void onDrawOval(const SkRect& rect, const SkPaint& paint) override;
void onDrawRRect(const SkRRect& rrect, const SkPaint& paint) override;
void onDrawPath(const SkPath& path, const SkPaint& paint) override;
void onDrawArc(const SkRect& rect, SkScalar startAngle, SkScalar sweepAngle,
               bool useCenter, const SkPaint& paint) override;
```

#### 图像绘制

```cpp
void onDrawImage2(const SkImage* image, SkScalar left, SkScalar top,
                  const SkSamplingOptions& sampling, const SkPaint* paint) override;
void onDrawImageRect2(const SkImage* image, const SkRect& src, const SkRect& dst,
                      const SkSamplingOptions& sampling, const SkPaint* paint,
                      SrcRectConstraint constraint) override;
void onDrawImageLattice2(const SkImage* image, const Lattice& lattice,
                         const SkRect& dst, SkFilterMode filter,
                         const SkPaint* paint) override;
void onDrawAtlas2(...) override;
```

#### 文本绘制

```cpp
void onDrawGlyphRunList(const sktext::GlyphRunList& list,
                        const SkPaint& paint) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->onDrawGlyphRunList(list, paint);
    }
}

void onDrawTextBlob(const SkTextBlob* blob, SkScalar x, SkScalar y,
                    const SkPaint& paint) override;
void onDrawSlug(const sktext::gpu::Slug* slug, const SkPaint& paint) override;
```

#### 特殊绘制

```cpp
void onDrawPaint(const SkPaint& paint) override;
void onDrawPoints(PointMode mode, size_t count, const SkPoint pts[],
                  const SkPaint& paint) override;
void onDrawVerticesObject(const SkVertices* vertices, SkBlendMode bmode,
                          const SkPaint& paint) override;
void onDrawPatch(const SkPoint cubics[12], const SkColor colors[4],
                 const SkPoint texCoords[4], SkBlendMode bmode,
                 const SkPaint& paint) override;
void onDrawShadowRec(const SkPath& path, const SkDrawShadowRec& rec) override;
```

### 特殊操作处理

#### SaveBehind 支持

```cpp
bool onDoSaveBehind(const SkRect* bounds) override {
    Iter iter(fList);
    while (iter.next()) {
        SkCanvasPriv::SaveBehind(iter.get(), bounds);
    }
    this->INHERITED::onDoSaveBehind(bounds);
    return false;
}
```

**说明**: 使用 SkCanvasPriv 访问私有 API。

#### ResetClip 支持

```cpp
void onResetClip() override {
    Iter iter(fList);
    while (iter.next()) {
        SkCanvasPriv::ResetClip(iter.get());
    }
    this->INHERITED::onResetClip();
}
```

#### DrawBehind 支持

```cpp
void onDrawBehind(const SkPaint& paint) override {
    Iter iter(fList);
    while (iter.next()) {
        SkCanvasPriv::DrawBehind(iter.get(), paint);
    }
}
```

### 高级绘图功能

#### Edge AA Quad

```cpp
void onDrawEdgeAAQuad(const SkRect& rect, const SkPoint clip[4],
                      QuadAAFlags aa, const SkColor4f& color, SkBlendMode mode) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->experimental_DrawEdgeAAQuad(rect, clip, aa, color, mode);
    }
}
```

#### Edge AA ImageSet

```cpp
void onDrawEdgeAAImageSet2(const ImageSetEntry set[], int count,
                           const SkPoint dstClips[], const SkMatrix preViewMatrices[],
                           const SkSamplingOptions& sampling, const SkPaint* paint,
                           SrcRectConstraint constraint) override {
    Iter iter(fList);
    while (iter.next()) {
        iter->experimental_DrawEdgeAAImageSet(
            set, count, dstClips, preViewMatrices, sampling, paint, constraint);
    }
}
```

### 复合对象绘制

```cpp
void onDrawPicture(const SkPicture* picture, const SkMatrix* matrix,
                   const SkPaint* paint) override;
void onDrawDrawable(SkDrawable* drawable, const SkMatrix* matrix) override;
void onDrawAnnotation(const SkRect& rect, const char key[], SkData* data) override;
```

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 说明 |
|-----|------|------|
| SkCanvas | 核心接口 | 子 Canvas 类型 |
| SkNoDrawCanvas | 工具基类 | 提供无绘制实现 |
| SkCanvasVirtualEnforcer | 编译器辅助 | 确保虚函数覆盖 |
| SkTDArray | 容器 | 动态数组存储子 Canvas |
| SkCanvasPriv | 私有 API | 访问 Canvas 私有方法 |
| SkPaint | 绘图样式 | 绘图参数 |
| SkPath | 几何路径 | 路径绘制 |
| SkImage | 图像数据 | 图像绘制 |
| SkTextBlob | 文本数据 | 文本绘制 |
| GlyphRunList | 文本渲染 | 字形运行列表 |

### 被依赖的模块

| 模块 | 使用场景 | 说明 |
|-----|---------|------|
| 屏幕录制工具 | 同时显示和保存 | 一个 Canvas 显示,一个 Canvas 保存到视频 |
| 多显示器输出 | 多屏渲染 | 同时输出到多个显示设备 |
| 调试工具 | 可视化调试 | 同时渲染和记录绘图命令 |
| 测试框架 | 输出验证 | 同时渲染到多个后端进行对比 |
| SkCanvasStack | 图层管理 | SkCanvasStack 内部使用 |

## 设计模式与设计决策

### 代理模式 (Proxy Pattern)

SkNWayCanvas 实现了代理模式的变体:
- **标准代理**: 一对一转发
- **N-Way 代理**: 一对多广播

**优势**:
- 对客户端透明,使用方式与普通 Canvas 相同
- 动态组合多个目标 Canvas
- 无需修改现有绘图代码

### 迭代器模式 (Iterator Pattern)

内部 Iter 类封装遍历逻辑:
- **简化代码**: 避免在每个方法中重复遍历逻辑
- **类型安全**: 提供 operator-> 语法糖
- **封装变化**: 如果列表结构改变,只需修改 Iter

### 模板方法模式 (Template Method)

继承自 SkNoDrawCanvas:
- **基础框架**: SkNoDrawCanvas 提供状态管理框架
- **定制行为**: 子类重写 onDrawXXX 方法实现转发
- **代码复用**: 避免重新实现 Canvas 的复杂状态逻辑

### 组合优于继承

使用组合管理子 Canvas:
- **灵活性**: 运行时动态添加/移除子 Canvas
- **松耦合**: 子 Canvas 可以是任意实现
- **多重目标**: 支持任意数量的子 Canvas

### 无图层策略

getSaveLayerStrategy 返回 kNoLayer_SaveLayerStrategy:
- **避免冗余**: N-Way Canvas 自身不需要缓冲
- **委托责任**: 子 Canvas 各自决定是否创建图层
- **性能优化**: 减少不必要的内存分配

### 设备检查机制

添加第二个 Canvas 时的断言:
```cpp
if (!fList.empty()) {
    SkASSERT(fList[0]->rootDevice() != this->rootDevice());
}
```

**原因**: 确保 N-Way Canvas 作为封装器使用,而非直接在第一个 Canvas 上绘制。

### 虚函数强制器

使用 SkCanvasVirtualEnforcer 模板:
- **编译期检查**: 确保所有虚函数都被重写
- **防止遗漏**: 避免意外继承基类行为
- **类型安全**: 提供更强的类型检查

## 性能考量

### 线性复杂度

每次绘图操作的时间复杂度:
- **时间**: O(n),其中 n 是子 Canvas 数量
- **空间**: O(1),不额外分配内存
- **适用场景**: 子 Canvas 数量较少(通常 2-5 个)

### 无缓冲开销

直接转发的优势:
- 不创建中间缓冲区
- 不进行像素复制
- 内存占用仅为子 Canvas 列表

### 迭代器开销

Iter 类的性能:
- 栈分配,无堆内存分配
- 简单的索引递增,开销极小
- 编译器可以内联优化

### 虚函数调用开销

每个绘图操作涉及的虚函数调用:
1. 客户端调用 SkNWayCanvas 方法
2. SkNWayCanvas 遍历列表
3. 每个子 Canvas 的虚函数调用

**缓解策略**:
- 现代 CPU 的分支预测优化虚函数调用
- 如果子 Canvas 类型相同,可能受益于指令缓存

### 状态同步成本

状态操作(save/restore/clip/transform):
- 必须同步到所有子 Canvas
- 状态不匹配会导致绘制错误
- 建议避免频繁的状态切换

### 绘图命令合并

无法合并绘图命令:
- 每个命令立即转发到所有子 Canvas
- 不进行批处理或优化
- 如需优化,考虑使用 SkPicture 先录制再重放

### 内存占用

```
sizeof(SkNWayCanvas) ≈ sizeof(SkCanvas) + sizeof(SkTDArray<SkCanvas*>)
                      ≈ ~100 bytes + n * sizeof(void*)
```

非常轻量级,适合大量实例。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/utils/SkNWayCanvas.h | 公共接口声明 |
| src/utils/SkNWayCanvas.cpp | 实现代码 |
| include/utils/SkNoDrawCanvas.h | 无绘制基类 |
| include/core/SkCanvas.h | Canvas 基类 |
| include/core/SkCanvasVirtualEnforcer.h | 虚函数强制器 |
| include/private/base/SkTDArray.h | 动态数组容器 |
| src/core/SkCanvasPriv.h | Canvas 私有 API |
| src/utils/SkCanvasStack.h | Canvas 栈(使用 N-Way Canvas) |
| include/core/SkPaint.h | 绘图样式 |
| include/core/SkPath.h | 路径几何 |
| include/core/SkImage.h | 图像数据 |
| include/core/SkTextBlob.h | 文本 blob |
| src/text/gpu/Slug.h | GPU 文本渲染 |
