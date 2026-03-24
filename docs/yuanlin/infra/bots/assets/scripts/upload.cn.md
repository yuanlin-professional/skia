# scripts 资产上传脚本

> 源文件: infra/bots/assets/scripts/upload.py

## 概述

通用的资产上传脚本，通过 common 模块调用资产管理系统的上传功能。该脚本是所有资产包的标准上传入口，实际上传逻辑由 `infra/bots/assets/assets.py` 实现。

## 架构位置

位于 `infra/bots/assets/scripts/`，是资产管理工作流的标准组件。每个资产包都包含相同的 upload.py。

## 主要类与结构体

极简脚本，只有导入和调用。

## 公共 API 函数

脚本作为主程序执行：
```python
if __name__ == '__main__':
    common.run('upload')
```

`common.run('upload')` 会：
1. 确定资产名称（从目录名）
2. 解析命令行参数
3. 调用 assets.py 的上传功能
4. 将资产打包并上传到 CIPD

## 内部实现细节

### 委托模式

脚本本身不包含任何上传逻辑，完全委托给 common.run()。这种设计：
- 保持脚本一致性
- 集中管理上传逻辑
- 易于维护和更新

### CIPD 集成

实际上传到 Chrome Infrastructure Package Deployment 系统，提供：
- 版本管理
- 权限控制
- 全球分发

## 设计模式与设计决策

这是标准的代理模式，upload.py 是资产管理系统的本地代理。

## 相关文件

- `common.py`: 提供 run() 函数
- `infra/bots/assets/assets.py`: 实际的上传实现
- CIPD 服务: 资产存储后端
