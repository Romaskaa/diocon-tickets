from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from ...core.ai import YANDEX_GPT_CONFIG, get_llm, load_prompt
from ..schemas import PredictionResponse, TicketPredict

model = get_llm(YANDEX_GPT_CONFIG)


async def suggest_ticket_fields(data: TicketPredict) -> PredictionResponse:
    """
    Предлагает оптимальные значения для полей тикета (приоритет, теги и.т.д)
    с помощью ИИ на основе заголовка и описания.
    """

    prompt = load_prompt("suggest_ticket_fields")
    agent = create_agent(
        model=model,
        system_prompt=prompt["system"],
        response_format=ToolStrategy(PredictionResponse)
    )
    human_message = (
        "human", prompt["user_template"].format(title=data.title, description=data.description)
    )
    result = await agent.ainvoke({"messages": [human_message]})
    return result["structured_response"]
