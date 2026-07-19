"""临时脚本：修复 LoginView.vue 接入真实登录 API"""
import re

with open("frontend/web/src/views/LoginView.vue", "r", encoding="utf-8") as f:
    content = f.read()

old = 'void message.info("当前仅验证界面交互，认证接口将在 M02 里程碑接入");'

new = """loading.value = true;
  try {
    const { apiClient } = await import("../api/client");
    const resp = await apiClient.post("/v1/auth/login", {
      username: account.value.trim(),
      password: password.value,
    });
    const token = resp.data?.data?.access_token;
    if (token) {
      localStorage.setItem("access_token", token);
      message.success("登录成功");
      const router = (await import("../router")).default;
      router.replace("/");
    } else {
      message.error("登录失败，未获取到 Token");
    }
  } catch (err) {
    const msg = err?.response?.data?.message ?? "登录失败，请重试";
    message.error(msg);
  } finally {
    loading.value = false;
  }"""

content = content.replace(old, new)
print("替换:", "成功" if old not in content else "失败")

with open("frontend/web/src/views/LoginView.vue", "w", encoding="utf-8") as f:
    f.write(content)
print("文件已保存")