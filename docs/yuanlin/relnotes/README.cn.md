# relnotes/ - Skia 版本发布说明

## 概述

`relnotes/` 目录包含即将发布的里程碑版本的发布说明。每个 Markdown 文件
（除 README.md 外）都被视为发布说明内容。在发布流程中，这些文件的内容会被
自动汇总到顶层的 `RELEASE_NOTES.md` 文件中，然后这些单独的文件会被删除。

## 工作流程

```
开发者编写发布说明
       ↓
relnotes/*.md 文件
       ↓
发布工具自动汇总
       ↓
RELEASE_NOTES.md（按里程碑组织）
       ↓
relnotes/*.md 被清除
```

## Markdown 编写规范

1. **不要引用本地文件**: 不能使用 `![Tooltip](image.png)` 等本地引用，
   但可以使用 URL 引用
2. **不要使用标题**: 不要使用 `#`、`##` 等标题标记（里程碑标题由工具自动添加）
3. **不要以星号开头**: 不要以 `*` 或其他列表标记开头（工具会自动添加）
4. **不要使用水平线**: 里程碑之间的分隔线由工具自动插入

## 关键文件

- **README.md**: 发布说明编写规范（不会被汇总到发布说明中）
- ***.md**: 各个发布说明条目（每个文件一个功能/变更说明）

## 依赖关系

- 发布分支工具: https://skia.googlesource.com/buildbot/+/refs/heads/main/sk/

## 相关文档与参考

- 顶层发布说明: `RELEASE_NOTES.md`
- Skia 发布流程: Skia buildbot 仓库中的 sk 工具
