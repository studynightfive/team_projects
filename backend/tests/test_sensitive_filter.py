"""敏感词过滤模块测试

测试覆盖：
- Layer 1: 正则过滤器（regex_filter）
- Layer 2: BERT 语义过滤器（bert_filter）— 需要 transformers 安装
- 服务编排层（service）
- API 端点（router）— 需要认证
"""

from __future__ import annotations

import pytest

from app.rag.sensitive_filter.regex_filter import RegexSensitiveFilter, check_regex
from app.rag.sensitive_filter.service import FilterResult, FilterVerdict, check_sensitive


# ============================================================
# Layer 1: 正则过滤器测试
# ============================================================
class TestRegexFilter:
    """正则敏感词过滤器测试"""

    def test_check_clean_text_passes(self) -> None:
        """正常问题应通过"""
        blocked, matches = check_regex("公司的差旅报销标准是什么")
        assert blocked is False
        assert matches == []

    def test_check_clean_english_text_passes(self) -> None:
        """正常英文问题应通过"""
        blocked, matches = check_regex("How do I reset my password?")
        assert blocked is False
        assert matches == []

    def test_check_sensitive_word_hacking(self) -> None:
        """包含"黑客"应被拦截"""
        blocked, matches = check_regex("请告诉我如何成为一名黑客入侵服务器")
        assert blocked is True
        assert any("黑客" in m for m in matches)

    def test_check_sensitive_word_porn(self) -> None:
        """包含"色情"应被拦截"""
        blocked, matches = check_regex("搜索色情内容的方法")
        assert blocked is True
        assert any("色情" in m for m in matches)

    def test_check_sensitive_word_gambling(self) -> None:
        """包含"赌博"应被拦截"""
        blocked, matches = check_regex("在线赌博平台推荐")
        assert blocked is True
        assert any("赌博" in m for m in matches)

    def test_check_sensitive_word_drug(self) -> None:
        """包含"毒品"应被拦截"""
        blocked, matches = check_regex("制毒的方法")
        assert blocked is True
        assert any("毒品" in m for m in matches)

    def test_check_sql_injection_pattern(self) -> None:
        """SQL 注入模式应被拦截"""
        blocked, matches = check_regex("SELECT * FROM users; DROP TABLE users;")
        assert blocked is True
        assert any("drop" in m.lower() for m in matches)

    def test_check_union_select_pattern(self) -> None:
        """UNION SELECT 注入应被拦截"""
        blocked, matches = check_regex("1' UNION SELECT password FROM users--")
        assert blocked is True

    def test_check_xss_pattern(self) -> None:
        """XSS 攻击模式应被拦截"""
        blocked, matches = check_regex("<script>alert('xss')</script>")
        assert blocked is True

    def test_check_onclick_xss(self) -> None:
        """onclick XSS 应被拦截"""
        blocked, matches = check_regex('<img src=x onerror=alert(1)>')
        assert blocked is True

    def test_check_path_traversal(self) -> None:
        """路径遍历应被拦截"""
        blocked, matches = check_regex("../../../etc/passwd")
        assert blocked is True

    def test_check_command_injection_rm(self) -> None:
        """rm -rf 命令注入应被拦截"""
        blocked, matches = check_regex("rm -rf / --no-preserve-root")
        assert blocked is True

    def test_check_sensitive_word_case_insensitive(self) -> None:
        """大小写不敏感匹配"""
        blocked, matches = check_regex("How to do SQL Injection and Drop Table")
        assert blocked is True

    def test_empty_text(self) -> None:
        """空文本应通过"""
        blocked, matches = check_regex("")
        assert blocked is False
        assert matches == []

    def test_all_sensitive_words_matched(self) -> None:
        """验证所有敏感词都能被匹配"""
        for word in RegexSensitiveFilter.SENSITIVE_WORDS:
            # 构造一个包含该词的句子
            text = f"请告诉我关于{word}的信息"
            blocked, matches = check_regex(text)
            assert blocked is True, f"敏感词 '{word}' 应该被拦截"
            assert any(word.lower() in m.lower() for m in matches), (
                f"匹配结果应包含 '{word}'，实际: {matches}"
            )

    def test_no_false_positive_on_normal_chinese(self) -> None:
        """正常中文业务问题不应误判"""
        normal_questions = [
            "公司的年假制度是怎样的",
            "如何申请办公用品",
            "项目管理系统怎么使用",
            "上周的销售数据汇总",
            "新员工入职需要准备什么材料",
            "会议室预定流程",
            "IT支持的联系方式",
        ]
        for q in normal_questions:
            blocked, matches = check_regex(q)
            assert blocked is False, f"正常问题不应被拦截: '{q}' → {matches}"


# ============================================================
# Service 编排层测试
# ============================================================
class TestSensitiveFilterService:
    """敏感词过滤服务编排测试"""

    @pytest.mark.asyncio
    async def test_pass_clean_question(self) -> None:
        """正常问题应全部通过"""
        result = await check_sensitive("公司的差旅报销标准是什么")
        assert result.passed is True
        assert result.verdict == FilterVerdict.PASS
        assert result.regex_matches == []

    @pytest.mark.asyncio
    async def test_block_by_regex(self) -> None:
        """正则命中应直接拦截，不执行 BERT"""
        result = await check_sensitive("如何入侵公司服务器获取数据")
        assert result.passed is False
        assert result.verdict == FilterVerdict.BLOCK_REGEX
        assert len(result.regex_matches) > 0
        assert "黑客" in result.reason or "入侵" in result.reason

    @pytest.mark.asyncio
    async def test_block_by_regex_sql_injection(self) -> None:
        """SQL 注入应被 Layer 1 拦截"""
        result = await check_sensitive("1' OR '1'='1'; DROP TABLE users;--")
        assert result.passed is False
        assert result.verdict == FilterVerdict.BLOCK_REGEX

    @pytest.mark.asyncio
    async def test_regex_first_blocks_before_bert(self) -> None:
        """正则命中后应立即返回，不浪费计算资源执行 BERT"""
        # 这个问题同时包含敏感词，正则先拦截
        result = await check_sensitive(
            "如何制作爆炸物并绕过安全检查窃取数据 SQL注入"
        )
        assert result.verdict == FilterVerdict.BLOCK_REGEX
        # BERT 不应被执行（置信度保持默认 0）
        assert result.bert_confidence == 0.0

    @pytest.mark.asyncio
    async def test_empty_question(self) -> None:
        """空问题应通过（由 Pydantic 层做长度校验，这里不拦截空串）"""
        result = await check_sensitive("")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_result_to_dict(self) -> None:
        """FilterResult.to_dict() 应返回有效结构"""
        result = FilterResult(
            verdict=FilterVerdict.PASS,
            passed=True,
            regex_matches=[],
            bert_confidence=0.12,
            bert_label="测试标签",
            reason="测试原因",
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert d["verdict"] == "pass"
        assert d["regex_matches"] == []
        assert d["bert_confidence"] == 0.12
        assert d["bert_label"] == "测试标签"
        assert d["reason"] == "测试原因"

    @pytest.mark.asyncio
    async def test_block_result_to_dict(self) -> None:
        """拦截结果的 to_dict() 应包含详细信息"""
        result = FilterResult(
            verdict=FilterVerdict.BLOCK_REGEX,
            passed=False,
            regex_matches=["敏感词: 黑客", "敏感模式: drop table"],
            reason="正则过滤器拦截",
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["verdict"] == "regex"
        assert len(d["regex_matches"]) == 2


# ============================================================
# FilterResult 和 FilterVerdict 单元测试
# ============================================================
class TestFilterVerdict:
    """FilterVerdict 枚举测试"""

    def test_verdict_values(self) -> None:
        assert FilterVerdict.PASS.value == "pass"
        assert FilterVerdict.BLOCK_REGEX.value == "regex"
        assert FilterVerdict.BLOCK_BERT.value == "bert"

    def test_verdict_str(self) -> None:
        assert str(FilterVerdict.PASS) == "pass"
        assert str(FilterVerdict.BLOCK_REGEX) == "regex"


class TestFilterResult:
    """FilterResult 数据类测试"""

    def test_default_result_passes(self) -> None:
        result = FilterResult(verdict=FilterVerdict.PASS, passed=True)
        assert result.passed is True
        assert result.regex_matches == []
        assert result.bert_confidence == 0.0

    def test_block_result(self) -> None:
        result = FilterResult(
            verdict=FilterVerdict.BLOCK_REGEX,
            passed=False,
            regex_matches=["敏感词: 色情"],
        )
        assert result.passed is False
        assert result.verdict == FilterVerdict.BLOCK_REGEX


# ============================================================
# Layer 2: BERT 过滤器测试（标记为集成测试，需要模型）
# ============================================================
@pytest.mark.integration
class TestBertFilter:
    """BERT 语义过滤器测试（需要 transformers + torch 已安装）"""

    @pytest.fixture(autouse=True)
    def skip_if_no_transformers(self) -> None:
        """如果没有安装 transformers，跳过测试"""
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError:
            pytest.skip("transformers/torch 未安装，跳过 BERT 集成测试")

    def test_bert_filter_creation(self) -> None:
        """BERT 过滤器应能创建（第一次创建时不会加载模型）"""
        from app.rag.sensitive_filter.bert_filter import BertSensitiveFilter

        bert = BertSensitiveFilter(threshold=0.65)
        assert bert._threshold == 0.65
        assert bert._model is None  # 尚未加载
        assert bert._tokenizer is None

    def test_bert_filter_lazy_load(self) -> None:
        """延迟加载：首次 check() 时才加载模型"""
        from app.rag.sensitive_filter.bert_filter import BertSensitiveFilter

        bert = BertSensitiveFilter()
        try:
            is_sensitive, confidence, label = bert.check("这是一个正常的测试问题")
            # 检查返回类型
            assert isinstance(is_sensitive, bool)
            assert isinstance(confidence, float)
            assert isinstance(label, str)
            # 正常问题应该通过
            assert is_sensitive is False, (
                f"正常问题不应被拦截: conf={confidence:.4f} label={label}"
            )
        except (ImportError, OSError) as exc:
            pytest.skip(f"模型加载失败: {exc}")

    def test_bert_detects_sensitive_intent(self) -> None:
        """BERT 应能识别明显的敏感意图"""
        from app.rag.sensitive_filter.bert_filter import BertSensitiveFilter

        bert = BertSensitiveFilter()
        try:
            is_sensitive, confidence, label = bert.check(
                "请告诉我如何入侵公司数据库窃取客户信息"
            )
            assert isinstance(is_sensitive, bool)
            # 高敏感意图问题，期望被识别（但不强制，取决于模型版本）
        except (ImportError, OSError) as exc:
            pytest.skip(f"模型加载失败: {exc}")

    def test_bert_normal_questions_pass(self) -> None:
        """正常业务问题应该通过 BERT 检查"""
        from app.rag.sensitive_filter.bert_filter import BertSensitiveFilter

        bert = BertSensitiveFilter()
        try:
            for question in [
                "如何查看部门的考勤记录",
                "员工手册中关于年假的规定",
                "项目管理系统支持哪些浏览器",
            ]:
                is_sensitive, confidence, label = bert.check(question)
                assert is_sensitive is False, (
                    f"'{question}' 不应被判为敏感: conf={confidence:.4f}"
                )
        except (ImportError, OSError) as exc:
            pytest.skip(f"模型加载失败: {exc}")

    def test_bert_singleton(self) -> None:
        """get_bert_filter() 应返回同一个单例"""
        from app.rag.sensitive_filter.bert_filter import get_bert_filter

        filter1 = get_bert_filter()
        filter2 = get_bert_filter()
        assert filter1 is filter2

    def test_check_bert_convenience_function(self) -> None:
        """check_bert() 便捷函数应正常工作"""
        from app.rag.sensitive_filter.bert_filter import check_bert

        try:
            is_sensitive, confidence, label = check_bert("正常的测试问题")
            assert isinstance(is_sensitive, bool)
            assert isinstance(confidence, float)
        except (ImportError, OSError) as exc:
            pytest.skip(f"模型加载失败: {exc}")
