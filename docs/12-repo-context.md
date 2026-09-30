# 12. Repo Context：大型代码仓库里，Agent 怎么找到该看的代码

## 1. Coding Agent 找代码，不等于“做一个 RAG”

一个真实代码仓库里，可以有多种检索方式：

```text
Repo Map
Keyword Search
Semantic Retrieval / RAG
Bounded Read
```

它们不是互相替代，而是解决不同问题。

---

## 2. Keyword Search

例如：

```text
search_code("refresh_token")
```

适合：

- 已知函数名；
- 错误字符串；
- 类名；
- 配置键；
- 明确变量名。

优点：

- 简单；
- 准；
- 便宜；
- 无需 Embedding。

缺点：

> 用户说的是“登录状态丢失”，代码可能叫 `create_session`，字面不一致。

---

## 3. RAG / Semantic Retrieval（语义检索）

RAG 在 Repo 场景中大致：

```text
代码
↓
切块
↓
Embedding
↓
Vector DB

自然语言问题
↓
Embedding Query
↓
相似度检索
↓
相关代码块
↓
主 LLM
```

它解决：

> **我知道问题的语义，但不知道代码里到底叫什么。**

例如：

```text
“登录状态丢失”
```

可能检索到：

```text
session_manager.py
auth_middleware.py
token.py
```

但 Retriever 只负责：

> 这些片段“可能相关”。

真正判断 Bug 仍由 LLM + read_file 验证。

---

## 4. Repo Map

Repo Map 更像仓库地图：

```text
src/api/auth.py
  - login()
  - logout()

src/service/auth_service.py
  - authenticate_user()
  - create_session()

src/utils/token.py
  - encode_token()
  - decode_token()
```

它解决：

> **这个仓库大概有什么，重要结构在哪里？**

所以：

```text
Repo Map
→ 导航

Keyword / Semantic Search
→ 定位

Bounded Read
→ 获取真正细节
```

---

## 5. Retrieval 从粗到细

不用背 “Retrieval Ladder” 这个英文词。

记住中文意思：

> **从粗到细地找代码。**

可以理解为：

```text
目录 / Repo Overview
↓
文件
↓
Symbol（类 / 函数 / 方法）
↓
关键词 / 语义检索
↓
局部读取真实代码
```

---

## 6. Python AST

Python 自带：

```python
import ast
```

可以确定性解析代码结构。

例如：

```python
class UserService:
    def login(self):
        pass

def create_user():
    pass
```

AST 大概：

```text
Module
├── ClassDef: UserService
│   └── FunctionDef: login
└── FunctionDef: create_user
```

这意味着：

> 提取函数 / 类名这种确定信息，不需要浪费 LLM。

---

## 7. 最小 Symbol 提取

概念代码：

```python
tree = ast.parse(code)

for node in tree.body:
    if isinstance(node, ast.ClassDef):
        print(node.name)

    elif isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    ):
        print(node.name)
```

类的方法可以继续遍历：

```python
for child in node.body:
    ...
```

Repo Map 第一版只需要：

```text
文件
+
class
+
function
+
method
```

---

## 8. 为什么返回结构化数据

优先：

```python
{
    "type": "class",
    "name": "AuthService",
    "methods": ["login", "logout"],
}
```

而不是直接拼成不可复用字符串。

这样以后可以：

- 格式化给 LLM；
- 输出 JSON；
- 做缓存；
- 做搜索；
- 进一步构图。

---

## 9. AST Parse 失败怎么办

Agent 正在修的代码可能本来就有 SyntaxError。

所以：

```text
单个文件 parse 失败
→ 不应该让整个 Repo Map 构建失败
```

可单独记录：

```text
a.py → parse failed
```

第一版也可以跳过。

---

## 10. Repo Map 也会太大

如果：

```text
5000 文件
20000 symbols
```

把完整 Repo Map 每轮塞给模型，又会制造 Context 问题。

所以要做：

### 渐进式展开（Progressive Disclosure）

```text
Level 1：目录
↓
Level 2：文件
↓
Level 3：Symbols
↓
Level 4：具体代码
```

模型需要时再继续展开。

---

## 11. Tool 设计

可以提供：

```text
list_directory(path)
list_symbols(path)
search_code(keyword)
read_file(path, start_line, end_line)
```

于是 LLM 可以：

```text
list_directory(".")
↓
list_directory("src/service")
↓
list_symbols("src/service/auth.py")
↓
read_file(...)
```

如果用户直接给出：

```text
“auth.py 第 120 行报错”
```

模型也可以直接 read，不必被 Workflow 强迫走完整地图流程。

> 我们提供探索能力，不强迫每次固定探索顺序。

---

## 12. Repo Map 应该做 Tool 还是自动注入 Context

小 Repo：

```text
非常短的 Repo Overview
→ 可以每轮注入
```

细节：

```text
Symbol / 文件内部结构
→ 更适合按需 Tool
```

强模型 + 薄 Harness 下，不需要每轮无脑注入完整 Repo。

---

## 13. Repo Map 会过期

Agent 修改代码后：

- 新函数可能出现；
- 文件可能新增；
- import 关系可能变化。

旧 Repo Map 可能 stale。

第一版最简单：

```text
list_directory
→ 实时读

list_symbols
→ 实时 AST parse
```

不缓存就没有 Cache Invalidation（缓存失效）问题。

以后性能真的不够，再考虑：

```text
path + mtime / hash
→ 缓存 AST 结果
```

---

## 14. Coding Agent V1 要不要做完整 RAG

不强制。

V1 推荐：

```text
必须：
- list_directory / list_files
- search_code
- bounded read

建议：
- list_symbols / 简单 Repo Map

进阶：
- Semantic RAG
```

不要为了“看起来高级”过早加入：

- Vector DB；
- 全 Repo Embedding；
- 复杂 Chunking；
- Incremental Index。

---

## 15. 本章核心

```text
Repo Map
→ 这个仓库有什么

Keyword Search
→ 我知道要找什么名字

Semantic Retrieval / RAG
→ 我知道语义，但不知道代码叫什么

Bounded Read
→ 已经定位，读取真实细节
```

以及：

> **先用低成本、粗粒度信息缩小范围，再按需读取高成本细节。**
