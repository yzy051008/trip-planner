from evaluation.mocks import MockAmapService, MockLLM, MockRagService


def test_mock_amap_returns_stable_city_data():
    service = MockAmapService()

    first = service.search_poi("历史文化", "上海")
    second = service.search_poi("历史文化", "上海")

    assert first == second
    assert len(first) >= 2
    assert service.get_weather("上海")


def test_mock_rag_returns_deterministic_context():
    service = MockRagService()

    assert service.get_knowledge_attractions("北京")
    assert service.build_rag_context(type("Request", (), {"city": "北京", "travel_days": 1, "preferences": [], "free_text_input": ""})())


def test_mock_llm_counts_calls_and_supports_response_sequence():
    llm = MockLLM(responses=["first", "second"])

    assert llm.invoke("ignored").content == "first"
    assert llm.invoke("ignored").content == "second"
    assert llm.call_count == 2


def test_mock_llm_selects_plan_and_review_by_prompt_stage():
    llm = MockLLM(plan_response="plan", review_response="review")

    assert llm.invoke("planner prompt").content == "plan"
    assert llm.invoke("旅行计划审查员 prompt").content == "review"
