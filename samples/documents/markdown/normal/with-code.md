# 代码示例文档

## Python 示例

下面是一个简单的 FastAPI 路由示例：

```python
from fastapi import FastAPI, Depends
from app.common.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.get("/api/v1/users")
async def get_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表"""
    offset = (page - 1) * page_size
    result = await db.execute(
        "SELECT id, username, display_name FROM users LIMIT :limit OFFSET :offset",
        {"limit": page_size, "offset": offset}
    )
    return {"items": result.fetchall(), "page": page, "page_size": page_size}
```

## JavaScript 示例

前端使用 Composition API 和 TypeScript：

```typescript
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';

export function useAuth() {
  const isLoggedIn = ref(false);
  const currentUser = ref(null);

  const isAdmin = computed(() => {
    return currentUser.value?.permissions?.includes('admin.dashboard.view');
  });

  async function login(username: string, password: string) {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    return response.json();
  }

  return { isLoggedIn, currentUser, isAdmin, login };
}
```

## SQL 示例

```sql
-- 创建用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_status ON users(status);
```