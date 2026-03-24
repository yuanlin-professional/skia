# make_lotties_with_assets

> 源文件: infra/bots/task_drivers/perf_puppeteer_skottie_frames/make_lotties_with_assets/make_lotties_with_assets.go

## 概述

`make_lotties_with_assets` 是一个实用工具程序，用于将 `lottie-samples` 的文件结构转换为 `perf_puppeteer_skottie_frames` 所需的格式。该程序读取一个包含多个 Lottie JSON 文件的输入目录，为每个文件创建一个子目录，并将 JSON 重命名为 `data.json`。处理后的文件被存储到 CIPD 包 `skia/internal/lotties_with_assets` 中，供性能测试使用。

## 架构位置

```
skia/
└── infra/
    └── bots/
        └── task_drivers/
            └── perf_puppeteer_skottie_frames/
                └── make_lotties_with_assets/
                    └── make_lotties_with_assets.go  # 文件转换工具
```

该程序是离线工具，用于准备测试数据，而非 CI 任务的一部分。

## 主要类与结构体

### 命令行标志

```go
inputDir := flag.String("input", "", "The input directory of lottie files")
outputDir := flag.String("output", "", "The output directory which will have the correct structure")
```

- **input**: 包含 Lottie JSON 文件的源目录
- **output**: 转换后的目标目录

## 公共 API 函数

### main()

```go
func main()
```

主函数执行以下流程：
1. 解析命令行参数
2. 读取输入目录中的所有条目
3. 筛选 `.json` 文件
4. 对每个 JSON 文件：
   - 清理文件名（去除前缀和后缀）
   - 创建子目录
   - 复制 JSON 内容到 `data.json`
5. 处理错误并退出

## 内部实现细节

### 文件名清理

```go
newName := strings.TrimPrefix(inputJSON, "lottiefiles.com - ")
newName = strings.TrimSuffix(newName, ".json")
newName = strings.ReplaceAll(newName, " ", "_")
```

转换示例：
- `"lottiefiles.com - Cool Animation.json"` → `"Cool_Animation"`
- `"Another Example.json"` → `"Another_Example"`

这确保目录名：
- 无特殊字符
- 适合文件系统和 URL
- 便于脚本处理

### 目录结构转换

**输入结构**:
```
input/
├── lottiefiles.com - animation1.json
├── lottiefiles.com - animation2.json
└── animation3.json
```

**输出结构**:
```
output/
├── animation1/
│   └── data.json
├── animation2/
│   └── data.json
└── animation3/
│   └── data.json
```

每个动画有独立的目录，方便后续添加资源文件（图片、字体等）到 `images/` 子目录。

### 错误处理

程序在遇到错误时立即退出并打印详细信息：

```go
if err := os.MkdirAll(subDir, 0755); err != nil {
    fmt.Printf("Could not make %s: %s\n", subDir, err)
    os.Exit(1)
}
```

所有错误使用退出码 1，便于脚本检测失败。

### 文件权限

```go
os.MkdirAll(subDir, 0755)  // 目录：rwxr-xr-x
```

目录权限设置为 755，允许所有用户读取和执行，但只有所有者可写。

## 依赖关系

### 标准库依赖

```go
import (
    "flag"        // 命令行参数解析
    "fmt"         // 格式化输出
    "os"          // 文件系统操作
    "path/filepath"  // 路径处理
    "strings"     // 字符串操作
)
```

该程序无外部依赖，纯标准库实现。

### 数据流

```
命令行参数
    ↓
os.ReadDir(inputDir) → 获取文件列表
    ↓
筛选 .json 文件
    ↓
for each JSON:
    清理文件名 → 创建目录 → 复制内容
    ↓
完成
```

### CIPD 集成

处理后的文件被打包到 CIPD：

```bash
cipd create -name skia/internal/lotties_with_assets -in ./lotties/ -tag version:NN
```

其中 `NN` 是版本号。CIPD 包随后被 CI 任务下载使用。

## 设计模式与设计决策

### 简单性优先

程序采用最直接的实现：
- 顺序处理（无并发）
- 立即失败（无重试）
- 无复杂的配置选项

这种简单性合理，因为：
- 处理的文件数量有限（~100 个）
- 运行频率低（仅在更新测试集时）
- 错误通常需要人工干预

### 单一职责

程序只做一件事：文件结构转换。不包括：
- Lottie 验证
- 资源提取
- 性能测试

这使得程序易于理解和维护。

### 就地转换

程序不修改输入文件，所有输出到独立目录。这：
- 保留原始数据
- 允许重复运行
- 便于调试

### 退出码策略

所有错误使用退出码 1：
```go
os.Exit(1)
```

这允许 shell 脚本轻松检测失败：
```bash
if ! make_lotties_with_assets --input src --output dst; then
    echo "Conversion failed!"
    exit 1
fi
```

## 性能考量

### 顺序处理

```go
for _, entry := range xf {
    // 处理每个文件
}
```

顺序处理的影响：
- 简单实现
- 文件数量少（~100），总时间可接受（几秒）
- 避免并发复杂性

如果未来需要处理数千个文件，可以考虑并发。

### 内存使用

```go
inputBytes, err := os.ReadFile(filepath.Join(*inputDir, inputJSON))
```

每次完整读取文件到内存。对于 Lottie JSON（通常 10 KB - 1 MB），这是可接受的。如果处理大文件（数百 MB），应考虑流式复制。

### 文件系统效率

```go
os.MkdirAll(subDir, 0755)  // 如果目录存在，不报错
```

使用 `MkdirAll` 而非 `Mkdir`，自动创建父目录，减少额外检查。

## 相关文件

### 使用该工具的程序

- **perf_puppeteer_skottie_frames.go**: 消费转换后的 Lottie 文件

### CIPD 配置

- **infra/bots/assets/lotties_with_assets/**: CIPD 资产定义
- **CIPD 包**: `skia/internal/lotties_with_assets`

### Lottie 源数据

- **lottie-samples**: 上游 Lottie 示例仓库
- **lottiefiles.com**: Lottie 动画社区网站

### 构建系统

- **bazel/Makefile**: 可能包含运行该工具的目标
- **CI 配置**: 定义何时更新 CIPD 包

### 文档

程序注释中包含 CIPD 更新指令：
```go
// 可以使用以下命令更新新版本：
// cipd create -name skia/internal/lotties_with_assets -in ./lotties/ -tag version:NN
```

这是内嵌的操作文档，确保维护者知道如何使用工具。

### 相关工具

- **tools/**: 其他 Skia 实用工具
- **infra/bots/assets/**: 其他 CIPD 资产管理脚本

该程序虽然简单，但在 Skia 性能测试基础设施中扮演重要角色，确保测试数据的一致性和可重现性。
