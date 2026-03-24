# BisectSlide

> 源文件: tools/viewer/BisectSlide.h, tools/viewer/BisectSlide.cpp

## 概述

`BisectSlide` 是 Skia Viewer 工具中用于从 SKP(Skia Picture)文件中隔离单个路径的二分查找工具。该组件从 SKP 文件中提取所有路径及其绘制参数(Paint 和变换矩阵),然后通过交互式二分搜索帮助用户快速定位导致问题的特定路径。这对于调试复杂 SKP 文件中的渲染问题至关重要,因为 SKP 可能包含数千条路径,手动检查不切实际。

该类提供了简洁的键盘接口:'x' 键丢弃一半路径,'X' 键切换丢弃哪一半,'Z' 键回退到上一步,'D' 键输出当前路径信息。通过几轮二分搜索(log2(N)轮),用户可以从数千条路径中快速隔离出单个问题路径。该工具维护了完整的搜索历史栈,支持回退操作,并能生成重现路径,便于 bug 报告和测试用例创建。

## 架构位置

`BisectSlide` 位于 Skia 项目的 `tools/viewer` 目录下:

```
Slide (基础幻灯片接口)
  └─> BisectSlide (路径二分查找工具)
```

依赖的核心模块:
- **tools/ToolUtils.h**: 提供 `ExtractPathsFromSKP()` 工具函数
- **include/core/SkPicture.h**: SKP 文件格式
- **tools/viewer/Slide.h**: 幻灯片基类

## 主要类与结构体

### BisectSlide

```cpp
class BisectSlide : public Slide {
public:
    static sk_sp<BisectSlide> Create(const char filepath[]);

    SkISize getDimensions() const override { return fDrawBounds.size(); }
    bool onChar(SkUnichar c) override;
    void draw(SkCanvas* canvas) override;

private:
    explicit BisectSlide(const char filepath[]);

    struct FoundPath {
        SkPath fPath;          // 路径几何
        SkPaint fPaint;        // 绘制样式
        SkMatrix fViewMatrix;  // 变换矩阵
    };

    SkString fFilePath;                     // SKP 文件路径
    SkIRect fDrawBounds;                    // 所有路径的联合边界
    skia_private::TArray<FoundPath> fFoundPaths;   // 保留的路径
    skia_private::TArray<FoundPath> fTossedPaths;  // 丢弃的路径
    skia_private::TArray<char> fTrail;             // 搜索轨迹(x/X序列)
    std::stack<std::pair<...>> fPathHistory;       // 历史栈(用于回退)
};
```

**关键成员变量**:
- `fFilePath`: 原始 SKP 文件路径,用于生成重现命令
- `fDrawBounds`: 所有路径边界的并集,用于设置画布尺寸
- `fFoundPaths`: 当前保留的路径集合,二分搜索的目标
- `fTossedPaths`: 当前丢弃的路径集合,可通过 'X' 键切换
- `fTrail`: 搜索轨迹字符串,如 "xxXx",用于重现搜索路径
- `fPathHistory`: 历史栈,每次二分时压栈,支持回退

### FoundPath 结构体

```cpp
struct FoundPath {
    SkPath fPath;          // 路径对象
    SkPaint fPaint;        // 绘制参数(颜色、笔触等)
    SkMatrix fViewMatrix;  // 视图变换矩阵
};
```

存储从 SKP 提取的路径完整上下文,确保重绘时效果一致。

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<BisectSlide> Create(const char filepath[])
```

从 SKP 文件创建二分查找幻灯片:
```cpp
SkFILEStream stream(filepath);
if (!stream.isValid()) {
    SkDebugf("BISECT: invalid input file at \"%s\"\n", filepath);
    return nullptr;
}

sk_sp<BisectSlide> bisect(new BisectSlide(filepath));
ToolUtils::ExtractPathsFromSKP(filepath, [&](const SkMatrix& matrix,
                                             const SkPath& path,
                                             const SkPaint& paint) {
    SkRect bounds;
    SkIRect ibounds;
    matrix.mapRect(&bounds, path.getBounds());
    bounds.roundOut(&ibounds);
    bisect->fDrawBounds.join(ibounds);  // 扩展边界
    bisect->fFoundPaths.push_back() = {path, paint, matrix};
});
return bisect;
```

**提取流程**:
1. 打开 SKP 文件流
2. 使用 `ExtractPathsFromSKP()` 遍历所有路径
3. 为每条路径计算变换后的边界并合并到 `fDrawBounds`
4. 将路径及其上下文存储到 `fFoundPaths`

### 渲染

```cpp
void draw(SkCanvas* canvas) override
```

绘制当前保留的所有路径:
```cpp
SkAutoCanvasRestore acr(canvas, true);
canvas->translate(-fDrawBounds.left(), -fDrawBounds.top());  // 居中

for (const FoundPath& path : fFoundPaths) {
    SkAutoCanvasRestore acr2(canvas, true);
    canvas->concat(path.fViewMatrix);  // 应用路径的变换矩阵
    canvas->drawPath(path.fPath, path.fPaint);
}
```

平移画布使边界左上角对齐原点,然后依次绘制每条路径。

### 键盘交互

```cpp
bool onChar(SkUnichar c) override
```

处理二分搜索命令:

**'x' - 二分丢弃**:
```cpp
case 'x':
    if (fFoundPaths.size() > 1) {
        size_t midpt = (fFoundPaths.size() + 1) / 2;  // 中点(向上取整)
        fPathHistory.emplace(fFoundPaths, fTossedPaths);  // 保存历史
        fTossedPaths.reset({fFoundPaths.data() + midpt,
                            fFoundPaths.size() - midpt});  // 后半部分
        fFoundPaths.resize_back(midpt);  // 保留前半部分
        fTrail.push_back('x');
    }
    return true;
```

将路径分为两半,保留前半部分,丢弃后半部分。

**'X' - 切换半边**:
```cpp
case 'X':
    if (!fTossedPaths.empty()) {
        using std::swap;
        swap(fFoundPaths, fTossedPaths);  // 交换保留和丢弃
        if ('X' == fTrail.back()) {
            fTrail.pop_back();  // 取消上次切换
        } else {
            fTrail.push_back('X');  // 记录切换
        }
    }
    return true;
```

交换保留和丢弃的路径,允许用户测试另一半。

**'Z' - 回退**:
```cpp
case 'Z':
    if (!fPathHistory.empty()) {
        fFoundPaths = fPathHistory.top().first;
        fTossedPaths = fPathHistory.top().second;
        fPathHistory.pop();
        char ch;
        do {
            ch = fTrail.back();
            fTrail.pop_back();
        } while (ch != 'x');  // 回退到上一个 'x'
    }
    return true;
```

从历史栈恢复上一步状态,撤销 'x' 命令及其后续的 'X' 命令。

**'D' - 输出路径**:
```cpp
case 'D':
    SkDebugf("viewer --bisect %s", fFilePath.c_str());
    if (!fTrail.empty()) {
        SkDebugf(" ");
        for (char ch : fTrail) {
            SkDebugf("%c", ch);
        }
    }
    SkDebugf("\n");
    for (const FoundPath& foundPath : fFoundPaths) {
        foundPath.fPath.dump();  // 输出路径详细信息
    }
    return true;
```

输出重现命令和路径详细信息,便于 bug 报告。

### 尺寸查询

```cpp
SkISize getDimensions() const override
```

返回边界尺寸:
```cpp
return fDrawBounds.size();
```

## 内部实现细节

### 二分策略

使用向上取整的中点:
```cpp
size_t midpt = (fFoundPaths.size() + 1) / 2;
```

对于奇数个路径,前半部分多一个:
- 5 个路径 -> 前3后2
- 4 个路径 -> 前2后2

### 历史栈管理

每次 'x' 命令压栈:
```cpp
fPathHistory.emplace(fFoundPaths, fTossedPaths);
```

存储当前状态的深拷贝,支持回退。

'Z' 命令弹栈并恢复:
```cpp
fFoundPaths = fPathHistory.top().first;
fTossedPaths = fPathHistory.top().second;
fPathHistory.pop();
```

### 轨迹字符串

轨迹记录搜索路径:
- "xxXx": 二分 -> 二分 -> 切换 -> 二分
- 可用于命令行重现: `viewer --bisect file.skp xxXx`

'X' 命令智能处理:
```cpp
if ('X' == fTrail.back()) {
    fTrail.pop_back();  // X X 等价于空
} else {
    fTrail.push_back('X');  // 记录切换
}
```

连续两次切换等价于无操作。

### 边界计算

路径边界在加载时预计算:
```cpp
SkRect bounds;
SkIRect ibounds;
matrix.mapRect(&bounds, path.getBounds());  // 变换后的边界
bounds.roundOut(&ibounds);                  // 向外取整到像素
bisect->fDrawBounds.join(ibounds);          // 合并
```

确保所有路径可见。

## 依赖关系

### 直接依赖

- **tools/ToolUtils.h**: 提供 `ExtractPathsFromSKP()` 函数
- **include/core/SkPath.h**: 路径对象
- **include/core/SkPaint.h**: 绘制参数
- **include/core/SkMatrix.h**: 变换矩阵
- **include/core/SkStream.h**: 文件流
- **tools/viewer/Slide.h**: 幻灯片基类

## 设计模式与设计决策

### 工厂模式

使用静态工厂方法而非公共构造函数:
```cpp
static sk_sp<BisectSlide> Create(const char filepath[]);
private:
    explicit BisectSlide(const char filepath[]);
```

工厂方法可以返回 `nullptr` 表示加载失败,构造函数无法做到这一点。

### 命令模式

键盘命令封装为字符:
- 'x': 二分命令
- 'X': 切换命令
- 'Z': 撤销命令
- 'D': 转储命令

轨迹字符串是命令序列的文本表示。

### 备忘录模式

历史栈存储状态快照:
```cpp
std::stack<std::pair<skia_private::TArray<FoundPath>,
                     skia_private::TArray<FoundPath>>> fPathHistory;
```

支持任意次数的回退。

## 性能考量

### 路径拷贝

每次 'x' 和 'X' 命令都拷贝路径数组:
```cpp
fPathHistory.emplace(fFoundPaths, fTossedPaths);  // 深拷贝
```

对于数千条路径,拷贝开销显著,但用户交互频率低,可以接受。

### 二分效率

对于 N 条路径,需要 log2(N) 轮二分:
- 1000 条路径 -> ~10 轮
- 10000 条路径 -> ~13 轮

远快于线性搜索。

### 边界预计算

所有路径边界在加载时计算:
```cpp
bisect->fDrawBounds.join(ibounds);
```

避免每帧重新计算,提升渲染性能。

## 相关文件

### 工具函数

- **tools/ToolUtils.h**: `ExtractPathsFromSKP()` 函数
- **src/utils/SkOSPath.h**: 路径操作工具

### Skia 核心

- **include/core/SkPath.h**: 路径对象
- **include/core/SkPicture.h**: SKP 格式

### Viewer 框架

- **tools/viewer/Slide.h**: 幻灯片基类
- **tools/viewer/Viewer.h**: Viewer 主应用

### 使用场景

该工具在以下场景中特别有用:

1. **渲染 Bug 定位**: 从包含数千条路径的 SKP 中隔离导致崩溃或错误渲染的路径
2. **性能分析**: 找出导致性能问题的复杂路径
3. **测试用例简化**: 从大型 SKP 提取最小重现用例
4. **回归测试**: 创建针对特定路径的单元测试

典型工作流程:
1. 加载问题 SKP: `viewer --bisect problem.skp`
2. 观察渲染,确认问题出现
3. 按 'x' 丢弃一半路径
4. 观察问题是否仍存在:
   - 存在: 继续按 'x'(问题在前半部分)
   - 消失: 按 'X' 切换,再按 'x'(问题在后半部分)
5. 重复步骤 3-4,直到隔离出单个路径
6. 按 'D' 输出路径信息和重现命令
7. 使用 'Z' 回退以验证或探索其他路径

输出示例:
```
viewer --bisect problem.skp xxX
Path:
  moveTo(10, 20)
  lineTo(30, 40)
  close()
```

该工具极大简化了复杂 SKP 文件的调试流程,是 Skia 开发者工具箱中的利器。
