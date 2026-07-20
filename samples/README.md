# 测试样本库说明

> 版本：1.0
> 负责人：员工6（测试与平台工程）
> 用途：为文档处理、OCR、检索和导出功能提供回归测试样本

---

## 一、用途

本样本库是知识库平台文档处理功能的测试基础。每个样本用于验证：

1. **文档处理**：解析器能否正确识别格式、提取文本、生成 Markdown
2. **OCR**：图片和扫描件能否正确识别文字
3. **检索**：关键词/向量/混合检索能否返回正确结果
4. **导出**：五种导出格式（PDF/DOCX/Markdown/CSV/TXT）是否可读

---

## 二、目录结构

```
samples/
├── README.md                    # 本文件
├── manifest.json                # 样本清单（机器可读）
├── documents/                   # 文档样本
│   ├── pdf/                     # PDF 类
│   │   ├── normal/              #   正常样本
│   │   ├── scanned/             #   扫描件
│   │   └── abnormal/            #   异常样本
│   ├── word/                    # Word 类
│   │   ├── normal/              #   正常样本（.docx）
│   │   ├── legacy/              #   旧格式（.doc）
│   │   └── abnormal/            #   异常样本
│   ├── excel/                   # Excel 类
│   ├── powerpoint/              # PowerPoint 类
│   ├── markdown/                # Markdown 类
│   ├── text/                    # 纯文本类
│   ├── csv/                     # CSV 类
│   ├── html/                    # HTML 类
│   ├── epub/                    # EPUB 电子书类
│   ├── images/                  # 图片类
│   ├── email/                   # 邮件类
│   └── open-documents/          # 开放文档格式（ODT/ODS/RTF）
├── exports/                     # 导出验证样本
│   ├── source-test-document.md  #   导出测试源文档
│   ├── expected/                #   期望输出文件
│   └── validation/              #   验证脚本
└── retrieval/                   # 检索测试集
    ├── queries/                 #   查询集
    └── expected-results/        #   期望结果
```

---

## 三、样本命名规范

1. 使用小写英文和连字符，如 `simple-text.pdf`、`with-table.docx`
2. 正常样本用描述性名称，如 `中文含表格.pdf`
3. 异常样本以 `abnormal-` 或 `corrupted-` 开头，如 `corrupted.docx`
4. 同一格式的不同样本使用数字后缀，如 `sample-001.pdf`、`sample-002.pdf`

---

## 四、样本内容限制

**禁止以下内容出现在任何样本中：**

- 真实个人信息（姓名、身份证号、手机号、邮箱地址、家庭住址）
- 商业 Secret（公司内部文档、客户数据、合同条款）
- 受版权保护的内容（书籍章节、论文全文、商业图片）
- 真实的 API Key、Token、密码或数据库连接字符串

**允许的内容：**

- 使用假数据（"张三"、"示例项目"、"test@example.com"）
- 公开领域文本（政府公告、维基百科开放内容）
- 自行编写的中英文测试内容

**文件大小限制：**
- 单个正常样本不超过 10MB
- 扫描件可适当放宽至 20MB
- 超过 50MB 的文件使用 Git LFS 管理

---

## 五、如何添加新样本

### 1. 创建样本文件

将样本文件放入对应的 `samples/documents/<格式>/<类别>/` 目录。

### 2. 更新 manifest.json

在 `manifest.json` 的 `samples` 数组中添加条目：

```json
{
  "id": "pdf-004",
  "path": "documents/pdf/normal/new-sample.pdf",
  "format": "pdf",
  "category": "normal",
  "language": "zh-CN",
  "features": ["text", "tables"],
  "page_count": 5,
  "file_size_bytes": 123456,
  "sha256": "abc123...",
  "description": "新样本的描述"
}
```

### 3. 计算 SHA256

```bash
sha256sum samples/documents/pdf/normal/new-sample.pdf
```

### 4. 运行验证

```bash
uv run python scripts/validate_samples.py
```

---

## 六、如何更新样本

1. 替换样本文件
2. 更新 `manifest.json` 中对应条目的 `file_size_bytes` 和 `sha256`
3. 如果样本内容发生实质性变化，更新 `description`
4. 运行验证脚本确认一致性

---

## 七、样本库版本管理

- 样本库的变更与 Git 提交绑定
- 每次添加或修改样本，commit message 使用 `test(samples):` 前缀
- 如：`test(samples): 添加 PDF 扫描件样本`
- 样本文件本身进入 Git，大文件（>10MB）使用 Git LFS

---

## 八、禁止事项

- 不提交真实敏感数据
- 不提交超过 50MB 的单个文件（使用 Git LFS）
- 不提交受版权保护的内容
- 不提交 `.env`、密钥或证书文件
- 不修改他人负责的样本（如需修改，提交 Issue 或 PR）
