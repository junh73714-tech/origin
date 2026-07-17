"""
生成示例文档数据

生成5种格式的测试文档（PDF/DOCX/TXT/MD/HTML），用于演示和测试。
内容为模拟的企业管理制度文档，包含标题、段落、列表、表格和条款。
"""
import os
import sys


def generate_txt(filepath: str) -> None:
    """生成TXT格式示例文档 -- 员工考勤管理制度"""
    content = """员工考勤管理制度

第一章 总则

第一条 目的
为规范公司考勤管理，维护正常工作秩序，保障员工合法权益，特制定本制度。

第二条 适用范围
本制度适用于公司全体员工，包括试用期员工和实习生。

第二章 工作时间

第三条 标准工时
公司实行每周五天工作制，周一至周五为工作日。
上午工作时间：9:00 - 12:00
下午工作时间：13:30 - 18:00

第四条 弹性工时
经部门负责人批准，员工可申请弹性工作时间，但必须满足核心工作时段（10:00 - 16:00）在岗。

第三章 考勤管理

第五条 打卡要求
1. 员工每日上下班均需通过公司指定考勤系统打卡。
2. 忘记打卡的，应在当日内在系统中提交补卡申请，经直属上级审批。
3. 每月补卡次数不得超过5次，超出部分按缺勤处理。

第六条 迟到与早退
1. 迟到30分钟以内，扣除当日绩效分数2分。
2. 迟到30分钟以上2小时以内，按半天事假处理。
3. 迟到2小时以上，按全天事假处理。
4. 早退30分钟以上，按半天事假处理。

第四章 请假制度

第七条 请假类型
公司提供以下请假类型：
- 年假：工作满1年享有5天，逐年递增，上限15天。
- 事假：需提前1天申请，按日扣除工资。
- 病假：需提供医院证明，每月累计不超过3天带薪。
- 婚假：3天，需提前1周申请。
- 产假：女性员工享有98天产假，男性员工享有7天陪产假。
- 丧假：直系亲属3天，旁系亲属1天。

第八条 请假流程
1. 员工在OA系统中提交请假申请。
2. 直属上级在1个工作日内审批。
3. 3天以上假期需部门负责人审批。
4. 5天以上假期需人力资源部审批。

第五章 加班管理

第九条 加班申请
加班需提前在系统中申请，经部门负责人批准后方可执行。
工作日加班按1.5倍工资计算，休息日加班按2倍计算，法定节假日加班按3倍计算。

第十条 加班时长限制
每月加班总时长不得超过36小时，每日加班不得超过3小时。

第六章 附则

第十一条 解释权
本制度由人力资源部负责解释和修订。

第十二条 生效时间
本制度自2026年1月1日起生效，原考勤制度同时废止。
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [OK] {filepath}")


def generate_md(filepath: str) -> None:
    """生成Markdown格式示例文档 -- 技术架构说明"""
    content = """# 企业知识问答平台技术架构说明

## 1. 系统概述

企业级混合检索 RAG 知识问答平台是一套基于检索增强生成（RAG）技术的智能问答系统。

### 1.1 核心能力

- **多源知识管理**：支持 PDF、DOCX、TXT、Markdown、HTML 等多种文档格式的上传和解析。
- **混合检索**：结合关键词检索（BM25）和向量检索（pgvector），通过 RRF 融合和 Reranker 重排提升召回质量。
- **权限隔离**：基于 RBAC 和 ABAC 的严格权限控制，确保用户只能检索被授权的知识。
- **标准问答**：支持高频问题的标准问答生成、审核和发布，直接命中时跳过检索流程。

### 1.2 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | Python 3.10 + FastAPI |
| 数据库 | PostgreSQL + pgvector |
| 搜索引擎 | OpenSearch (BM25) |
| 缓存 | Redis |
| 任务队列 | Celery |
| 文件存储 | MinIO |
| 前端 | React + TypeScript + Ant Design |
| 容器化 | Docker Compose |

## 2. 系统架构

### 2.1 模块化单体架构

系统采用模块化单体架构，一期不拆分微服务。

运行单元包括：
1. React Web 前端
2. FastAPI 后端应用
3. Celery Worker 异步任务处理
4. PostgreSQL 数据库（含 pgvector 扩展）
5. OpenSearch 搜索引擎
6. Redis 缓存
7. MinIO 对象存储

### 2.2 核心原则

- PostgreSQL 是业务状态的唯一事实来源。
- OpenSearch、pgvector 和缓存均为派生数据。
- 权限过滤必须在检索之前执行。
- 跨模块事件通过 Outbox 模式传递。

## 3. 文档处理流水线

文档进入系统后经过以下处理阶段：

1. **上传与校验**：格式验证、MIME 类型检查、SHA-256 哈希去重。
2. **解析**：提取文本、标题、段落、表格等结构信息。
3. **清洗**：去除页眉页脚、合并断裂行、规范化空白。
4. **切分**：按标题层级、段落、条款等策略切分为 Chunk。
5. **Embedding**：生成向量表示。
6. **双索引写入**：OpenSearch BM25 + pgvector 向量。
7. **发布**：通过审核后发布，进入可检索状态。

## 4. 数据模型

### 4.1 核心实体关系

```text
KnowledgeBase
  └─ Document
      └─ DocumentVersion
          └─ DocumentChunk
              └─ IndexTask
```

### 4.2 文档状态机

- 草稿（draft）→ 处理中（processing）→ 待检查（pending_review）→ 待发布（pending_publish）→ 已发布（published）
- 已发布 → 已暂停（paused）/ 已过期（expired）/ 已下线（offline）/ 已归档（archived）

只有已发布 + 当前版本 + 未过期 + 权限有效的文档可被检索。

## 5. 部署说明

### 5.1 环境要求

- Docker 24.0+
- Docker Compose 2.20+
- Python 3.10+
- Node.js 18+

### 5.2 快速启动

```bash
git clone <repository-url>
cd rag-knowledge
cp .env.example .env
make dev-up
make migrate
make seed
```

服务端口：
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- Grafana：http://localhost:3100
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [OK] {filepath}")


def generate_html(filepath: str) -> None:
    """生成HTML格式示例文档 -- 产品使用手册"""
    content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>知识问答平台用户手册</title>
</head>
<body>

<h1>知识问答平台用户手册</h1>

<h2>1. 快速入门</h2>

<h3>1.1 登录系统</h3>
<p>打开浏览器访问系统地址，输入您的企业账号和密码完成登录。首次登录建议修改初始密码。</p>

<h3>1.2 提问</h3>
<p>在首页搜索框中输入您的问题，按回车键或点击发送按钮。系统将根据您的权限范围检索相关知识并生成回答。</p>

<h2>2. 功能介绍</h2>

<h3>2.1 智能问答</h3>
<p>输入自然语言问题，系统将自动识别意图、检索相关文档并生成答案。回答中会标注引用来源，点击引用编号可查看原文。</p>

<h3>2.2 引用查看</h3>
<p>每个回答会附带引用编号，点击可查看来源文档的名称、版本、页码和原文片段。如无权限查看原文，系统会提示权限不足。</p>

<h3>2.3 反馈</h3>
<p>对回答质量进行评价：</p>
<ul>
    <li>点赞：回答准确、有用</li>
    <li>点踩：回答不准确或有误</li>
    <li>纠错：提供更正的答案和建议</li>
</ul>

<h2>3. 常见问题</h2>

<h3>3.1 为什么没有返回答案？</h3>
<p>可能的原因：</p>
<ol>
    <li>当前知识库中没有相关文档</li>
    <li>您没有访问相关文档的权限</li>
    <li>系统判定证据不足，拒绝生成不确定的答案</li>
</ol>

<h3>3.2 如何申请更多权限？</h3>
<p>在个人中心查看当前权限范围，如需访问更多知识库，请联系部门管理员申请临时授权。</p>

<h2>4. 数据统计</h2>

<table border="1">
    <tr><th>用户角色</th><th>每日提问上限</th><th>可访问知识库</th></tr>
    <tr><td>普通员工</td><td>50次</td><td>公共知识库+部门知识库</td></tr>
    <tr><td>部门管理员</td><td>100次</td><td>全部知识库</td></tr>
    <tr><td>系统管理员</td><td>无限制</td><td>全部知识库+管理后台</td></tr>
</table>

</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [OK] {filepath}")


def generate_pdf(filepath: str) -> None:
    """生成PDF格式示例文档 -- 信息安全管理制度"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4

        y = height - 50
        line_height = 18

        def write_line(text, font_size=12, bold=False):
            nonlocal y
            c.setFont("Helvetica-Bold" if bold else "Helvetica", font_size)
            c.drawString(50, y, text)
            y -= line_height
            if y < 60:
                c.showPage()
                y = height - 50

        write_line("信息安全管理制度", 16, bold=True)
        y -= 10

        write_line("第一章 总则", 14, bold=True)
        write_line("第一条 为加强公司信息安全管理，保护公司核心数据和客户隐私，依据相关法律法规制定本制度。")
        write_line("第二条 本制度适用于公司所有部门和全体员工，包括外包人员和临时工作人员。")
        y -= 5

        write_line("第二章 信息分类与分级", 14, bold=True)
        write_line("第三条 公司信息分为以下等级：")
        write_line("  1. 公开级：可对外公开发布的信息，如产品介绍、新闻公告。")
        write_line("  2. 内部级：仅限公司内部员工访问，如内部通知、培训材料。")
        write_line("  3. 机密级：仅限相关部门和授权人员访问，如财务数据、人事档案。")
        write_line("  4. 绝密级：仅限核心管理层和指定人员访问，如战略规划、商业机密。")
        y -= 5

        write_line("第三章 访问控制", 14, bold=True)
        write_line("第四条 用户访问权限遵循最小权限原则，只授予完成工作所必需的最小权限范围。")
        write_line("第五条 所有系统登录必须使用企业统一认证账号，禁止共享账号和密码。")
        write_line("第六条 离职员工的系统权限应在离职当日全部收回。")
        y -= 5

        write_line("第四章 数据保护", 14, bold=True)
        write_line("第七条 敏感数据在传输过程中必须加密，存储时必须脱敏处理。")
        write_line("第八条 数据库备份至少保留30天，核心数据备份保留90天。")
        write_line("第九条 禁止将公司数据存储到个人设备或未授权的第三方云服务。")
        y -= 5

        write_line("第五章 安全事件处理", 14, bold=True)
        write_line("第十条 发生信息安全事件后，发现人应在1小时内报告信息安全部门。")
        write_line("第十一条 信息安全部门应在24小时内完成初步调查并采取应急措施。")
        y -= 5

        write_line("第六章 附则", 14, bold=True)
        write_line("第十二条 本制度由信息安全部门负责解释和修订。")
        write_line("第十三条 本制度自发布之日起生效。")

        c.save()
        print(f"  [OK] {filepath}")
    except ImportError:
        print(f"  [SKIP] {filepath} (reportlab not installed)")


def generate_docx(filepath: str) -> None:
    """生成DOCX格式示例文档 -- 新员工入职指南"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # 标题
        title = doc.add_heading("新员工入职指南", level=0)

        # 第一章
        doc.add_heading("第一章 入职准备", level=1)
        doc.add_paragraph("欢迎加入公司！为确保顺利入职，请在报到前准备好以下材料：")
        items = [
            "身份证原件及复印件（2份）",
            "最高学历证书原件及复印件",
            "一寸免冠照片（2张）",
            "本人名下的银行卡（用于工资发放）",
        ]
        for item in items:
            doc.add_paragraph(item, style="List Bullet")

        # 第二章
        doc.add_heading("第二章 入职流程", level=1)
        doc.add_heading("2.1 报到", level=2)
        doc.add_paragraph("报到时间：每月1日或15日上午9:00。")
        doc.add_paragraph("报到地点：公司总部大楼3层人力资源部。")

        doc.add_heading("2.2 签订合同", level=2)
        doc.add_paragraph("报到当日签订劳动合同，合同一式两份，公司和员工各执一份。试用期为3个月，表现优异者可提前转正。")

        doc.add_heading("2.3 领取设备", level=2)
        doc.add_paragraph("IT部门将为新员工配置以下设备：")
        doc.add_paragraph("办公电脑（笔记本电脑或台式机）", style="List Bullet")
        doc.add_paragraph("企业邮箱账号", style="List Bullet")
        doc.add_paragraph("OA系统账号", style="List Bullet")
        doc.add_paragraph("门禁卡", style="List Bullet")

        # 第三章
        doc.add_heading("第三章 试用期管理", level=1)
        doc.add_paragraph("试用期为3个月，期间将进行以下评估：")
        doc.add_paragraph("第1个月：熟悉公司文化和业务流程，完成入职培训。")
        doc.add_paragraph("第2个月：在导师指导下独立完成分配的任务。")
        doc.add_paragraph("第3个月：参与部门项目，提交转正述职报告。")

        # 表格：入职培训安排
        doc.add_heading("3.1 入职培训安排", level=2)
        table = doc.add_table(rows=6, cols=3)
        table.style = "Light Grid Accent 1"
        headers = ["培训主题", "时间", "负责人"]
        for i, header in enumerate(headers):
            table.rows[0].cells[i].text = header

        data = [
            ("公司文化与制度", "第1天上午", "人力资源部"),
            ("信息安全培训", "第1天下午", "信息安全部"),
            ("产品与业务介绍", "第2天上午", "产品部"),
            ("技术栈与开发规范", "第2天下午", "技术部"),
            ("合规与职业操守", "第3天上午", "法务部"),
        ]
        for i, (topic, time, person) in enumerate(data, 1):
            table.rows[i].cells[0].text = topic
            table.rows[i].cells[1].text = time
            table.rows[i].cells[2].text = person

        # 第四章
        doc.add_heading("第四章 薪酬福利", level=1)
        doc.add_paragraph("4.1 薪酬结构：基本工资 + 绩效奖金 + 年终奖")
        doc.add_paragraph("4.2 五险一金按国家规定标准缴纳。")
        doc.add_paragraph("4.3 补充福利：商业保险、年度体检、带薪年假、节日福利、员工培训。")

        # 第五章
        doc.add_heading("第五章 常见问题", level=1)
        doc.add_paragraph("Q: 试用期工资如何计算？")
        doc.add_paragraph("A: 试用期工资为转正工资的80%，不低于当地最低工资标准。")
        doc.add_paragraph("Q: 转正需要哪些条件？")
        doc.add_paragraph("A: 试用期评估合格、导师评价良好、无违纪记录。")

        doc.save(filepath)
        print(f"  [OK] {filepath}")
    except ImportError:
        print(f"  [SKIP] {filepath} (python-docx not installed)")


def main():
    sample_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"生成示例文档到: {sample_dir}")
    print("-" * 40)

    generate_txt(os.path.join(sample_dir, "员工考勤管理制度.txt"))
    generate_md(os.path.join(sample_dir, "技术架构说明.md"))
    generate_html(os.path.join(sample_dir, "用户手册.html"))
    generate_pdf(os.path.join(sample_dir, "信息安全管理制度.pdf"))
    generate_docx(os.path.join(sample_dir, "新员工入职指南.docx"))

    print("-" * 40)
    print("示例文档生成完毕。")


if __name__ == "__main__":
    main()
