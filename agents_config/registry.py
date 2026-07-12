from agents_config.thesis_diagnostic import create_thesis_diagnostic_agent
from agents_config.literature_fit_reviewer import create_literature_reviewer_agent
from agents_config.literature_searcher import create_literature_searcher_agent
# from agents_config.thesis_writer import create_thesis_writer_agent
# from agents_config.methodology_reviewer import create_methodology_reviewer_agent


def create_agent_registry(model):
    return {
        "diagnostic": create_thesis_diagnostic_agent(model),
        "searcher": create_literature_searcher_agent(model),
        "reviewer": create_literature_reviewer_agent(model),
        # "writer": create_thesis_writer_agent(model),
    }


def choose_agent(agent_registry):
    print("Available agents:\n")

    for key, agent in agent_registry.items():
        print(f"- {key}: {agent.name}")

    print()

    while True:
        selected = input("Choose agent > ").strip().lower()

        if selected in agent_registry:
            return agent_registry[selected]

        print(f"Unknown agent: {selected}")
        print("Please choose one of:", ", ".join(agent_registry.keys()))
