<template>
  <main class="login-page">
    <section
      class="login-card standalone-login-card"
      aria-labelledby="login-title"
    >
      <div class="login-brand">智能知识库平台</div>
      <h1 id="login-title">登录工作区</h1>
      <p class="muted">使用组织账号进入统一工作区。</p>
      <form @submit.prevent>
        <div class="field">
          <label for="account">账号</label>
          <input
            id="account"
            type="text"
            name="account"
            autocomplete="username"
            placeholder="请输入账号"
          />
        </div>
        <div class="field">
          <label for="password">密码</label>
          <input
            id="password"
            type="password"
            name="password"
            autocomplete="current-password"
            placeholder="请输入密码"
          />
        </div>
        <button class="login-button" type="submit">进入工作区</button>
      </form>
      <p class="login-note">M01 只固定视觉，不提交或保存凭据。</p>
    </section>
  </main>
</template>
