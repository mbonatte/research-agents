import asyncio

from dotenv import load_dotenv
from agents import set_tracing_disabled

from app.config import load_model_config
from app.models import create_configured_model
from app.chat import interactive_chat
from app.logging import save_local_run_log

from agents_config.registry import create_agent_registry, choose_agent


async def main():
    load_dotenv()
    set_tracing_disabled(True)

    model = create_configured_model(load_model_config())

    agent_registry = create_agent_registry(model)
    agent = choose_agent(agent_registry)

    result = await interactive_chat(agent)

    if result is not None:
        log_file = save_local_run_log(result)
        print(f"Run log saved to: {log_file}")


if __name__ == "__main__":
    asyncio.run(main())
