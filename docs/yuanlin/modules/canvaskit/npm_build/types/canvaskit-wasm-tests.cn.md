# CanvasKit TypeScript 类型测试 (canvaskit-wasm-tests.ts)

> 源文件: `modules/canvaskit/npm_build/types/canvaskit-wasm-tests.ts`

## 概述

`canvaskit-wasm-tests.ts` 是 CanvasKit npm 包的 TypeScript 类型定义测试文件，约 1081 行代码。它通过编写覆盖 CanvasKit 所有主要 API 的类型正确的调用代码，验证 `index.d.ts` 中的类型定义是否准确和完整。该文件不会被实际执行，而是通过 TypeScript 编译器（`dtslint`）进行静态类型检查。使用 `$ExpectType` 注释标注预期返回类型，确保类型推断正确。

## 架构位置

```
npm run dtslint
  └── TypeScript 编译器
      └── canvaskit-wasm-tests.ts（类型测试代码）
          └── 引用 index.d.ts（类型定义）
              └── 验证所有 API 的类型签名
```

## 主要类与结构体

该文件不定义类或结构体。它通过一系列测试函数，对 `index.d.ts` 中定义的每个接口和类型进行使用验证。

## 公共 API 函数

### 测试函数列表

文件通过模块化的测试函数组织，每个函数测试一组相关的 API：

| 测试函数 | 覆盖的 API |
|---------|-----------|
| `animatedImageTests` | AnimatedImage 的创建、帧操作、尺寸查询 |
| `canvasTests` | Canvas 的所有绘图方法（约 70 个调用） |
| `canvas2DTests` | Canvas2D 兼容层 |
| `colorFilterTests` | ColorFilter 的所有工厂方法 |
| `colorTests` | Color/Color4f/ColorAsInt/parseColorString |
| `contourMeasureTests` | ContourMeasureIter 和 ContourMeasure |
| `imageFilterTests` | ImageFilter 的所有工厂方法 |
| `imageTests` | Image 的像素读取、编码、着色器创建 |
| `fontTests` | Font 的度量、字形查询 |
| `fontMgrTests` | FontMgr 的字体管理 |
| `globalTests` | 全局设置（解码缓存等） |
| `mallocTests` | Malloc/Free 内存管理 |
| `maskFilterTests` | MaskFilter 工厂 |
| `matrixTests` | Matrix/M44/ColorMatrix 辅助方法 |
| `paintTests` | Paint 的所有属性设置方法 |
| `paragraphTests` | Paragraph 的布局和查询 |
| `paragraphBuilderTests` | ParagraphBuilder 的完整构建流程 |
| `pathEffectTests` | PathEffect 的所有工厂方法 |
| `pathTests` | Path/PathBuilder 的所有操作 |
| `pictureTests` | PictureRecorder 和 Picture |
| `rectangleTests` | Rect/IRect/RRect 构造 |
| `runtimeEffectTests` | RuntimeEffect/SkSL 着色器 |
| `skottieTests` | Skottie 动画 API |
| `shaderTests` | Shader 的所有工厂方法 |
| `surfaceTests` | Surface 的创建和操作 |
| `textBlobTests` | TextBlob 的创建 |
| `typefaceTests` | Typeface 的字形查询 |
| `vectorTests` | Vector 辅助方法 |
| `verticesTests` | Vertices 创建 |
| `webGPUTest` | WebGPU 相关 API |

## 内部实现细节

### 类型注入模式

测试函数使用"可选参数注入"模式来获取复杂类型的实例：

```typescript
function canvasTests(CK: CanvasKit, canvas?: Canvas, paint?: Paint, ...) {
    if (!canvas || !paint || ...) return;
    // 从这里开始，TypeScript 知道 canvas 和 paint 不为 null
}
```

这避免了在测试中真正构建每个对象，同时保持了类型检查的有效性。

### `$ExpectType` 注释

使用 `dtslint` 的 `$ExpectType` 注释验证返回类型：

```typescript
const n = img.decodeNextFrame(); // $ExpectType number
const still = img.makeImageAtCurrentFrame(); // $ExpectType Image | null
```

### 数组作为类型灵活输入

测试大量使用普通数组作为颜色、矩形、圆角矩形等的输入，验证 `InputRect`、`InputColor` 等灵活类型别名正确工作：

```typescript
const someColor = [0.9, 0.8, 0.7, 0.6]; // 验证数组被接受为颜色
const someRect = [4, 3, 2, 1]; // 验证数组被接受为矩形
```

### 全面的 Canvas 测试

`canvasTests` 是最大的测试函数，覆盖了 Canvas 接口的几乎所有方法，包括：
- 裁剪操作（clipPath, clipRect, clipRRect）
- 变换操作（concat, rotate, scale, translate, skew）
- 绘图操作（drawImage/Rect/Circle/Path/Text/Glyphs/Shadow/Vertices/DRRect/Arc/Atlas/Patch/Oval）
- 状态管理（save/restore/saveLayer）
- 像素操作（readPixels, writePixels）

### Paragraph 完整流程测试

`paragraphBuilderTests` 测试了段落构建的完整流程：创建 FontProvider → 注册字体 → 创建 ParagraphStyle/TextStyle → 构建 ParagraphBuilder → 推入样式/添加文本/添加占位符 → 构建 Paragraph → 布局 → 查询度量。

### 采样选项测试

图像绘制方法测试了多种采样选项：
- 默认采样：`drawImage(img, x, y)`
- 立方采样：`drawImageCubic(img, x, y, B, C, paint)`
- 过滤+mipmap：`drawImageOptions(img, x, y, filter, mipmap, paint)`

### WebGPU 测试

`webGPUTest` 测试了完整的 WebGPU 工作流：创建设备上下文 → 创建画布上下文 → 创建表面 → 绘制 → 刷新。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `canvaskit-wasm` | 类型定义（`index.d.ts`） |
| `dtslint` / TypeScript 编译器 | 类型检查工具 |

## 设计模式与设计决策

- **类型注入**: 使用可选参数+非空检查模式避免构建实际对象，专注于类型验证
- **全覆盖策略**: 尽可能覆盖每个接口的每个方法，确保类型定义的完整性
- **`$ExpectType` 断言**: 对关键返回值使用类型断言，防止类型定义中的返回类型错误
- **编译即测试**: 文件不需要执行，只需编译通过即证明类型定义正确
- **按功能分组**: 每个测试函数对应一组相关的 API，便于定位类型错误

## 性能考量

- 该文件纯粹是编译时检查，不产生任何运行时代码
- 1081 行的类型测试对 TypeScript 编译器的性能影响不大
- `dtslint` 会报告类型不匹配错误，帮助维护者快速发现类型定义中的回归

## 相关文件

- `modules/canvaskit/npm_build/types/index.d.ts` — 被测试的类型定义文件
- `modules/canvaskit/npm_build/types/tsconfig.json` — TypeScript 编译配置
- `modules/canvaskit/npm_build/package.json` — npm 脚本配置（`npm run dtslint`）
- `modules/canvaskit/canvaskit_bindings.cpp` — 实际 API 实现
