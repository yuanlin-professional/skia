不使用 git-cl 来使用 Gerrit
===========================

设置
-----

以下操作必须在 Skia 源代码仓库中执行。

此命令设置一个 Git 提交消息钩子 (commit-message hook)，用于为每次提交添加一个唯一的 Change-Id。Gerrit 仅接受带有 Change-Id 的变更，并使用它来识别变更对应的评审。

    experimental/tools/set-change-id-hook

如果你是从镜像（如 GitHub）获取的 Skia，你需要将 `origin` 远程仓库指向 googlesource。高级用户会注意到字符串 `origin` 没有什么特殊的，你可以随意命名这个远程仓库，只要在 `git push` 时使用该名称即可。

    git remote set-url origin 'https://skia.googlesource.com/skia.git'


认证
--------------

前往 [skia.googlesource.com/new-password](https://skia.googlesource.com/new-password) 并按照说明操作。


创建变更
-----------------

1.  创建一个主题分支 (Topic Branch)

        git checkout -b TOPIC

    你可能希望此时设置一个跟踪分支：

        git checkout -b TOPIC -t origin/main

2.  进行一次提交。

        echo FOO >> whitespace.txt
        git commit --all --message 'Change Foo'
        git log -1

    `git log` 应显示 Change-Id 行已被添加到你的提交消息中。


3.  如果你的分支中有多个提交，Gerrit 会认为你想要多个相互依赖的变更。如果这不是你想要的，你需要压缩 (squash) 这些提交。

4.  推送到 Gerrit

        git push origin @:refs/for/main

    `@` 是 `HEAD` 的简写，在 git v1.8.5 中引入。

    如果你想要针对 `main` 以外的分支，也可以在此处指定。例如：

        git push origin @:refs/for/chrome/m57

    [Gerrit 上传文档](https://gerrit-review.googlesource.com/Documentation/user-upload.html)

5.  在网页浏览器中打开：

        bin/sysopen https://skia-review.googlesource.com/c/skia/+/$(bin/gerrit-number @)

更新变更
-----------------


1.  继续编辑你的提交。

        echo BAR >> whitespace.txt
        git commit --all --amend

    对提交消息的更改也会随推送一起发送。


2.  如有需要，重新压缩提交。（如果你只修订了原始提交则不需要。）


3.  推送到 Gerrit。

        git push origin @:refs/for/main

    如果你想为此补丁集 (Patch Set) 设置评论消息，请改用以下方式：

        M=$(experimental/tools/gerrit_percent_encode 'This is the patch set comment message!')
        git push origin @:refs/for/main%m=$M

    此补丁集的标题将是 "This is the patch set comment message!"。


在上传补丁时触发提交队列试运行 (Commit-Queue Dry Run)
-------------------------------------------------------

    M=$(experimental/tools/gerrit_percent_encode 'This is the patch set comment message!')
    git push origin @:refs/for/main%l=Commit-Queue+1,m=$M


使用 `git cl try`
------------------

在你的当前分支上，上传到 Gerrit 之后：

    git cl issue $(bin/gerrit-number @)

现在 `git cl try` 和 `bin/try` 将正常工作。


脚本化
---------

你可能想要为常见任务创建 git 别名 (alias)：

    git config alias.gerrit-push 'push origin @:refs/for/main'

以下别名在不编辑提交消息的情况下修订 HEAD：

    git config alias.amend-head 'commit --all --amend --reuse-message=@'

设置 CL 问题编号：

    git config alias.setcl '!git-cl issue $(bin/gerrit-number @)'

以下 shell 脚本将压缩当前分支上的所有提交，假设该分支有一个上游主题分支。

    squash_git_branch() {
        local MESSAGE="$(git log --format=%B ^@{upstream} @)"
        git reset --soft $(git merge-base @ @{upstream})
        git commit -m "$MESSAGE" -e
    }

此 shell 脚本推送到 Gerrit 并为补丁集添加消息：

    gerrit_push_with_message() {
        local REMOTE='origin'
        local REMOTE_BRANCH='main'
        local MESSAGE="$(echo $*|sed 's/[^A-Za-z0-9]/_/g')"
        git push "$REMOTE" "@:refs/for/${REMOTE_BRANCH}%m=${MESSAGE}"
    }

这些 shell 脚本可以通过一个小技巧转换为 Git 别名：

    git config alias.squash-branch '!M="$(git log --format=%B ^@{u} @)";git reset --soft $(git merge-base @ @{u});git commit -m "$M" -e'

    git config alias.gerrit-push-message '!f(){ git push origin @:refs/for/main%m=$(echo $*|sed "s/[^A-Za-z0-9]/_/g");};f'

如果你的分支的上游分支（通过 `git branch --set-upstream-to=...` 设置）已配置，你可以使用它来自动推送到该分支：

    gerrit_push_upstream() {
        local UPSTREAM_FULL="$(git rev-parse --symbolic-full-name @{upstream})"
        case "$UPSTREAM_FULL" in
            (refs/remotes/*);;
            (*) echo "Set your remote upstream branch."; return 2;;
        esac
        local UPSTREAM="${UPSTREAM_FULL#refs/remotes/}"
        local REMOTE="${UPSTREAM%%/*}"
        local REMOTE_BRANCH="${UPSTREAM#*/}"
        local MESSAGE="$(echo $*|sed 's/[^A-Za-z0-9]/_/g')"
        echo git push $REMOTE @:refs/for/${REMOTE_BRANCH}%m=${MESSAGE}
        git push "$REMOTE" "@:refs/for/${REMOTE_BRANCH}%m=${MESSAGE}"
    }

作为 Git 别名：

    git config alias.gerrit-push '!f()(F="$(git rev-parse --symbolic-full-name @{u})";case "$F" in (refs/remotes/*);;(*)echo "Set your remote upstream branch.";return 2;;esac;U="${F#refs/remotes/}";R="${U%%/*}";B="${U#*/}";M="$(echo $*|sed 's/[^A-Za-z0-9]/_/g')";echo git push $R @:refs/for/${B}%m=$M;git push "$R" "@:refs/for/${B}%m=$M");f'
