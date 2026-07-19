# AI 搜索跳转修正记录

## 背景

真实 API 模式下，用户在 AI 搜索首页输入问题后点击“开始搜索”，页面会跳转到 `/search`，但结果页没有立即使用首次输入的问题发起检索，用户需要再次输入同一问题。

## 原因

搜索结果页为了避免刷新后恢复上一条问题，只读取一次性 `history.state.initialSearch`。首页跳转仍使用 URL 查询参数 `q`、`mode`、`sources` 和 `model` 传递搜索条件，真实 API 模式进入结果页时会被结果页清理，因此首次问题丢失。

## 修正

- `frontend/web/src/views/UserHomeView.vue` 在真实 API 模式下改用 `history.state.initialSearch` 传递问题、搜索模式和搜索范围。
- 首页“最近搜索”在真实 API 模式下也改用同样的一次性 state 传参。
- Mock 模式继续保留 URL 查询参数行为，避免影响现有前端样例和测试路径。

## 验收

- 从 AI 搜索首页输入问题并点击“开始搜索”，跳转到 `/search` 后会直接发起 RAG 检索。
- 从首页“最近搜索”进入 `/search` 后会直接发起检索。
- 刷新 `/search` 页面不会恢复上一条问题，仍满足真实 API 模式不把问题持久留在 URL 的要求。
