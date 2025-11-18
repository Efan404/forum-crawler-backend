# Testing Documentation

## 测试概览

本项目包含全面的测试套件，验证所有核心功能的正确性。测试覆盖了 API 层、CRUD 操作、RSS 抓取、Celery 任务处理以及完整的集成工作流。

## 测试统计

- **总测试数量**: 46 个
- **测试通过率**: 100%
- **测试文件数**: 8 个

## 测试结构

```
tests/
├── __init__.py                    # 测试包初始化
├── conftest.py                    # pytest 配置和 fixtures
├── test_api.py                    # API 端点基础测试 (5 个测试)
├── test_api_edge_cases.py         # API 边界情况和错误处理 (11 个测试)
├── test_crud.py                   # CRUD 操作测试 (3 个测试)
├── test_fetchers.py               # RSS 抓取器基础测试 (3 个测试)
├── test_fetchers_enhanced.py      # RSS 抓取器增强测试 (12 个测试)
├── test_integration.py            # 集成测试 (4 个测试)
├── test_tasks.py                  # Celery 任务基础测试 (1 个测试)
└── test_tasks_enhanced.py         # Celery 任务增强测试 (7 个测试)
```

## 测试分类

### 1. API 端点测试 (16 个测试)

#### 基础功能测试 (`test_api.py`)
- ✅ 健康检查端点
- ✅ Topics 完整 CRUD 流程
- ✅ 重复话题名称错误处理
- ✅ Posts 列表和过滤（按 topic_id 和 source）
- ✅ Logs 列表和系统统计

#### 边界情况测试 (`test_api_edge_cases.py`)
- ✅ 更新不存在的 topic 返回 404
- ✅ 删除不存在的 topic 返回 404
- ✅ 获取不存在的 topic 返回 404
- ✅ 更新话题时重名错误处理
- ✅ 创建带空关键词列表的话题
- ✅ 分页边界测试（skip > total, limit = 1, 等）
- ✅ 无效过滤器测试
- ✅ 不存在的 source 过滤
- ✅ 无效的 status 过滤
- ✅ 空数据库的系统统计
- ✅ 创建带大量关键词的话题

### 2. CRUD 操作测试 (3 个测试)

- ✅ Topic 的创建、获取、更新、删除
- ✅ Posts 列表过滤（按 topic_id 和 source）
- ✅ Push logs 列表和状态过滤

### 3. RSS 抓取器测试 (15 个测试)

#### 基础测试 (`test_fetchers.py`)
- ✅ RSS 条目标准化处理
- ✅ 关键词匹配行为
- ✅ 不支持的 source 错误处理

#### 增强测试 (`test_fetchers_enhanced.py`)
- ✅ 所有支持的 source 抓取测试（v2ex, nodeseek, linux.do）
- ✅ fetch_feed 工厂函数测试
- ✅ 缺少字段的条目处理
- ✅ content 字段处理（代替 summary）
- ✅ 备用日期字段处理（updated_parsed, created_parsed）
- ✅ 空条目列表处理
- ✅ 多条目处理
- ✅ 关键词匹配边界情况（特殊字符、数字、Unicode）
- ✅ 网络错误处理
- ✅ 大小写不敏感的 source 匹配
- ✅ Unicode 字符支持（中文、emoji）

### 4. Celery 任务测试 (8 个测试)

#### 基础测试 (`test_tasks.py`)
- ✅ fetch_all_topics 创建 posts 和 logs
- ✅ 去重逻辑验证

#### 增强测试 (`test_tasks_enhanced.py`)
- ✅ 无活跃话题时的行为
- ✅ 关键词不匹配时的过滤
- ✅ 空关键词接受所有条目
- ✅ 多条目处理和选择性过滤
- ✅ 为新帖子创建 push logs
- ✅ 多个活跃话题的处理
- ✅ _should_keep_entry 辅助函数测试
- ✅ _uid_exists 去重检查测试

### 5. 集成测试 (4 个测试)

- ✅ 完整工作流测试（创建话题 → 添加帖子 → 检查日志 → 更新话题 → 删除话题）
- ✅ 多个不同来源的话题测试
- ✅ 关键词过滤功能测试
- ✅ 帖子去重测试（UID 唯一性约束）

## 运行测试

### 运行所有测试
```bash
uv run pytest tests/ -v
```

### 运行特定测试文件
```bash
uv run pytest tests/test_api.py -v
```

### 运行特定测试
```bash
uv run pytest tests/test_api.py::test_health_check -v
```

### 显示详细错误信息
```bash
uv run pytest tests/ -v --tb=long
```

### 仅运行失败的测试
```bash
uv run pytest tests/ --lf
```

## 测试覆盖的核心功能

### ✅ API 层
- 所有 REST 端点（GET, POST, PUT, DELETE）
- 请求验证和错误处理
- 分页功能
- 过滤功能
- CORS 配置

### ✅ 数据层
- SQLAlchemy 模型 CRUD 操作
- 关系查询（joins, eager loading）
- 唯一性约束验证
- 事务处理

### ✅ 业务逻辑
- RSS feed 解析和标准化
- 关键词匹配算法
- 帖子去重逻辑
- 定时任务处理

### ✅ 边界情况
- 空数据处理
- 不存在的资源
- 重复数据
- 无效输入
- 网络错误

## 测试最佳实践

1. **使用 Fixtures**: 所有测试使用 `conftest.py` 中定义的共享 fixtures
2. **隔离性**: 每个测试使用独立的数据库实例，测试间互不影响
3. **Mock 外部依赖**: 使用 `monkeypatch` mock 网络请求和外部服务
4. **清晰的测试名称**: 测试名称描述了测试的具体场景
5. **全面的断言**: 每个测试包含多个相关的断言
6. **文档注释**: 每个测试函数都有清晰的文档字符串

## 持续集成建议

在 CI/CD 流程中运行测试：

```yaml
# .github/workflows/test.yml 示例
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install uv
      - run: uv sync
      - run: uv run pytest tests/ -v
```

## 测试数据库

测试使用 SQLite 内存数据库，具有以下优点：
- ✅ 快速（所有数据在内存中）
- ✅ 隔离（每个测试独立的数据库实例）
- ✅ 无需配置（不依赖外部数据库服务）

## 下一步

建议的测试改进方向：

1. **代码覆盖率工具**
   - 安装 pytest-cov: `uv add --dev pytest-cov`
   - 运行: `uv run pytest tests/ --cov=app --cov-report=html`
   - 目标: 达到 90%+ 的代码覆盖率

2. **性能测试**
   - 添加 API 端点的性能基准测试
   - 测试大数据量下的查询性能

3. **端到端测试**
   - 使用真实的 Docker 环境测试
   - 测试完整的 Celery Beat 调度

4. **安全测试**
   - SQL 注入测试
   - XSS 防护测试
   - 输入验证测试

## 维护指南

当添加新功能时，请确保：
1. 为新的 API 端点添加测试
2. 为新的业务逻辑添加单元测试
3. 为边界情况添加测试
4. 更新此文档

## 测试结果

最近一次测试运行结果：

```
============================= test session starts ==============================
platform linux -- Python 3.11.14, pytest-7.4.3, pluggy-1.6.0
plugins: asyncio-0.21.1, anyio-3.7.1
collected 46 items

✅ 46 passed in 0.91s
```

所有测试全部通过！✨
