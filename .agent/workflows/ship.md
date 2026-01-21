---
description: 整合變更偵測、智慧 Commit Message 撰寫與自動推送到 GitHub 的完整交付流程。
---

// turbo-all

1. **偵測與暫存變更**
   檢查專案中的所有變更並加入 Git 暫存區。
   ```bash
   git add .
   ```

2. **分析與生成報告**
   - 檢視 `git diff --cached` 以理解變更細節。
   - 參考 `git log -n 5` 以維持專案提交風格。
   - **AI 指引**：撰寫一個道地、精確且符合 Conventional Commits 規範的 Commit Message。

3. **確認步驟 (User Approval)**
   - **AI 指引**：將撰寫好的 Commit Message 展示給使用者。
   - **等待確認**：詢問使用者「是否使用此訊息進行提交？(y/n)」。如果使用者需要修改，根據回饋進行調整。

4. **執行提交 (Commit)**
   ```bash
   # 僅在使用者確認訊息後執行
   git commit -m "[經過確認的專業訊息]"
   ```

5. **智慧推送 (Push)**
   自動處理連線協議並推送到目前的遠端分支。
   ```bash
   # 自動處理 SSH 轉 HTTPS 以確保背景執行順暢
   REMOTE_URL=$(git remote get-url origin)
   if [[ $REMOTE_URL == git@github.com:* ]]; then
     HTTPS_URL=$(echo $REMOTE_URL | sed 's/git@github.com:/https:\/\/github.com\//')
     git remote set-url origin $HTTPS_URL
     echo "已切換至 HTTPS 以進行自動授權推送。"
   fi

   # 推送目前分支至遠端
   CURRENT_BRANCH=$(git branch --show-current)
   git push -u origin $CURRENT_BRANCH
   ```
