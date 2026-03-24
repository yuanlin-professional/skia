
---
title: "如何回退一个 CL"
linkTitle: "How to revert a CL"

---


使用一键回退 (One-click Revert)
----------------------
*   找到您想回退的 CL 对应的代码审查问题。
*   点击 "revert" 按钮。

使用 Git
---------

更新本地仓库

    git fetch origin main

以 origin/main 为起点创建一个本地分支。

    git checkout -b revert$RANDOM origin/main

找到您想回退的提交的 SHA1 值

    git log origin/main

创建一个回退提交 (Revert Commit)。

    git revert <SHA1>

上传到 Gerrit。

    git cl upload

将回退合入 origin/main。

    git cl land

删除本地回退分支。

    git checkout --detach && git branch -D @{-1}

