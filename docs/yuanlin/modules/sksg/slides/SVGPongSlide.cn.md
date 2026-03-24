# SVGPongSlide -- 基于场景图的 Pong 游戏演示

> 源文件: `modules/sksg/slides/SVGPongSlide.cpp`

## 概述

`SVGPongSlide.cpp` 实现了一个经典的 Pong（乒乓球）游戏演示，展示了 Skia Scene Graph (sksg) 模块的实际使用。整个游戏在一个归一化的 1x1 坐标空间中运行，通过变换矩阵映射到实际窗口大小。游戏包含两个球拍、一个球和一个带虚线中线的背景，球拍由简单的 AI 控制。该文件是 sksg 模块的集成测试和教学示例。

## 架构位置

```
Slide (Viewer 框架的幻灯片基类)
└── PongSlide (Pong 游戏幻灯片)
    └── sksg::Scene (场景图根)
        └── TransformEffect (坐标变换)
            └── Group (场景组)
                ├── Draw(bg_path, bg_paint)      -- 背景
                ├── Draw(paddle0.shadow, shadow)  -- 球拍0阴影
                ├── Draw(paddle1.shadow, shadow)  -- 球拍1阴影
                ├── Draw(ball.shadow, shadow)     -- 球阴影
                ├── Draw(paddle0.object, blue)    -- 球拍0
                ├── Draw(paddle1.object, red)     -- 球拍1
                └── Draw(ball.object, green)      -- 球
```

该文件属于 Skia 的 Viewer 工具中的演示幻灯片，不属于核心库。它展示了如何使用 sksg 构建动态交互场景。

## 主要类与结构体

### `PongSlide`
```cpp
class PongSlide final : public Slide {
    struct Object {
        sk_sp<sksg::RRect> objectNode, shadowNode;
        SkPoint pos;
        SkVector spd;
        SkSize size;
        void initialize(const SkRRect& rrect, const SkPoint& p, const SkVector& s);
        void posTick(SkScalar dt);
        void updateDom();
    };
    std::unique_ptr<sksg::Scene> fScene;
    sk_sp<sksg::Matrix<SkMatrix>> fContentMatrix;
    Object fPaddle0, fPaddle1, fBall;
    SkRandom fRand;
};
```

### `Object` 内部结构
游戏对象（球或球拍），包含场景图节点引用（实体和阴影）、物理状态（位置和速度）以及尺寸信息。

## 公共 API 函数

### `PongSlide::load(w, h)`
初始化游戏：创建所有场景图节点、构建场景树、设置坐标变换。

### `PongSlide::draw(canvas)`
每帧渲染：调用 `fScene->revalidate()` 更新场景状态，然后 `fScene->render(canvas)` 渲染。可选地绘制失效区域可视化。

### `PongSlide::animate(nanos)`
每帧动画更新：计算时间增量、更新对象位置、执行物理约束、同步场景图节点。

### `PongSlide::resize(w, h)`
窗口大小变化时更新坐标变换矩阵。

### `PongSlide::onChar(uni)`
键盘输入：`[`/`]` 调整时间缩放，`I` 切换失效区域可视化。

## 内部实现细节

### 游戏物理

- **归一化坐标空间**：游戏逻辑在 [0,1] 空间中运行，通过 `fContentMatrix` 变换到实际窗口大小。这使得游戏逻辑与窗口大小无关。

- **球反射**：`box_reflect` 函数实现了无限反射的边界约束。通过模运算和条件反射，将任意越界位置映射回有效范围，支持球在多次反弹后仍能正确定位。

- **球速随机化**：每次水平反弹时通过 `fuzzBallSpeed` 添加速度扰动，并限制在 `[kBallSpeedMin, kBallSpeedMax]` 范围内，增加游戏趣味性。

### AI 球拍控制

- **接球方**（catcher）：计算球到达己方边界时的 Y 坐标（`find_yintercept`），设置速度使球拍恰好到达该位置。

- **发球方**（pitcher）：在球飞向对手时，球拍向中心位置移动，准备下一次接球。

### 场景图使用

- **sksg::RRect**：球和球拍使用圆角矩形节点。

- **sksg::Path**：背景使用路径节点绘制边界线和虚线中线。

- **sksg::Color**：各对象使用不同颜色（绿球、蓝/红球拍、黑色阴影）。

- **sksg::Draw**：将几何节点和颜色节点组合为可渲染节点。

- **sksg::Group**：将所有 Draw 节点组织在一个组中。

- **sksg::TransformEffect + Matrix**：顶层变换将归一化坐标映射到窗口坐标。

- **sksg::Scene**：包装根节点，提供 revalidate/render 接口。

### 阴影模拟

每个对象有两个 RRect 节点：实体和阴影。阴影位置根据对象与画面中心的距离偏移（模拟视差），营造简单的 3D 效果。

### 失效可视化

`fShowInval` 标志启用时，在渲染后遍历 `InvalidationController` 记录的失效矩形，用红色半透明填充和红色描边绘制。

## 依赖关系

- `modules/sksg/include/SkSGDraw.h` -- Draw 节点
- `modules/sksg/include/SkSGGroup.h` -- Group 节点
- `modules/sksg/include/SkSGPaint.h` -- Color 画笔节点
- `modules/sksg/include/SkSGPath.h` -- Path 几何节点
- `modules/sksg/include/SkSGRect.h` -- RRect 几何节点
- `modules/sksg/include/SkSGScene.h` -- Scene 根容器
- `modules/sksg/include/SkSGTransform.h` -- Matrix / TransformEffect
- `modules/sksg/include/SkSGInvalidationController.h` -- 失效区域收集
- `tools/viewer/Slide.h` -- Viewer 幻灯片基类
- `tools/timer/TimeUtils.h` -- 时间工具
- `src/base/SkRandom.h` -- 随机数生成

## 设计模式与设计决策

1. **场景图驱动的动画**：游戏对象的视觉表示完全由场景图管理，动画逻辑只需更新场景图节点的属性，重新验证和渲染由场景图框架自动处理。

2. **归一化坐标系统**：所有游戏逻辑在 [0,1] 归一化空间中进行，通过单一变换矩阵适配任意窗口大小。这是响应式布局的简单高效实现。

3. **物理/视觉分离**：Object 结构将物理状态（pos, spd）与场景图节点（objectNode, shadowNode）分离，`updateDom` 方法负责同步两者。

4. **增量更新**：只更新变化的节点属性，场景图的失效/重新验证机制确保只重新计算受影响的子树。

5. **绘制顺序控制**：通过 Group 中的节点添加顺序控制绘制层次（阴影在实体下方，球拍在球上方）。

## 性能考量

- 归一化坐标避免了窗口大小变化时重建场景图，只需更新变换矩阵。
- 场景图的增量更新机制使得每帧只重新计算和绘制变化的部分。
- InvalidationController 收集的失效区域可用于局部重绘优化。
- 阴影节点是额外的 Draw 调用，但圆角矩形的绘制开销很低。
- `box_reflect` 使用纯数学运算（模运算和条件分支），无内存分配。
- 每帧的 `update_pos` 通过 `makeOffset` 创建新的 SkRRect，涉及少量的值拷贝。

## 相关文件

- `modules/sksg/include/SkSGScene.h` -- Scene 类定义
- `modules/sksg/include/SkSGGroup.h` -- Group 节点
- `modules/sksg/include/SkSGDraw.h` -- Draw 节点
- `modules/sksg/include/SkSGTransform.h` -- 变换节点
- `modules/sksg/include/SkSGInvalidationController.h` -- 失效控制器
- `tools/viewer/Slide.h` -- Viewer 幻灯片框架
