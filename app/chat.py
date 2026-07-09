import time
import asyncio
import httpx

from openai import RateLimitError, InternalServerError, APIConnectionError, APITimeoutError

from agents import Agent, Runner, ItemHelpers


from app.usage import print_token_usage


async def generate_agent_intro(agent):
    intro_agent = Agent(
        name=agent.name,
        instructions=agent.instructions,
        model=agent.model,
        model_settings=getattr(agent, "model_settings", None),
        tools=[],
    )

    intro_prompt = (
        "Introduce yourself to the user before the chat starts. "
        "Use your agent name and your instructions to explain what you do. "
        "Mention the kinds of requests you can handle. "
        "Give 3 short example requests. "
        "Keep it concise, friendly, and practical. "
        "End by inviting the user to write their request."
    )

    result = await Runner.run(
        intro_agent,
        intro_prompt,
        max_turns=1,
    )

    return result.final_output


async def run_with_live_updates(agent, user_input, write_tool_output=False):
    started_at = time.perf_counter()

    result = Runner.run_streamed(
        agent,
        input=user_input,
        max_turns=30,
    )

    print("\n=== Agent run started ===\n")

    async for event in result.stream_events():
        elapsed = time.perf_counter() - started_at

        if event.type == "raw_response_event":
            continue

        if event.type == "agent_updated_stream_event":
            print(f"[agent] Switched to: {event.new_agent.name}")
            continue

        if event.type == "run_item_stream_event":
            item = event.item

            if item.type == "tool_call_item":
                raw = getattr(item, "raw_item", None)
                tool_name = getattr(raw, "name", "unknown_tool")
                arguments = getattr(raw, "arguments", "{}")

                print(f"\n[{elapsed:.1f}s] [tool called] {tool_name}")
                print(f"[arguments] {arguments}")

            elif item.type == "tool_call_output_item":
                if write_tool_output:
                    output = str(item.output)
                    if len(output) > 200: 
                        output = output[:200] + "\n...[tool output truncated]" 
                        print(f"\n[{elapsed:.1f}s] [tool] Tool output") 
                        print(output)

            elif item.type == "message_output_item":
                if write_tool_output:
                    print(f"[{elapsed:.1f}s] [agent message]")
                    print(ItemHelpers.text_message_output(item))

            else:
                print(f"[{elapsed:.1f}s] [event] {item.type}")

    total_elapsed = time.perf_counter() - started_at

    print(f"\n=== Agent run completed in {total_elapsed:.1f}s ===")
    print_token_usage(result)

    return result


async def run_with_retry(agent, user_input, retries: int = 3):
    for attempt in range(retries):
        try:
            return await run_with_live_updates(agent, user_input)

        except RateLimitError:
            wait_seconds = 20 * (attempt + 1)
            print(f"\n[rate limit] Waiting {wait_seconds} seconds before retrying...")
            await asyncio.sleep(wait_seconds)

        except (
            InternalServerError,
            APIConnectionError,
            APITimeoutError,
            httpx.ReadTimeout,
        ) as e:
            wait_seconds = 10 * (attempt + 1)
            print(f"\n[model/backend timeout] {type(e).__name__}: {e}")
            print(f"[retry] Waiting {wait_seconds} seconds before retrying...")
            await asyncio.sleep(wait_seconds)

    raise RuntimeError("Model/backend timeout persisted after retries.")


async def interactive_chat(agent, show_intro: bool = True):
    conversation = []
    last_result = None

    print(f"Interactive {agent.name} agent started.")
    print("Type 'exit' or 'quit' to stop.\n")

    if show_intro:
        try:
            started_at = time.perf_counter()
            intro_message = await generate_agent_intro(agent)
            elapsed = time.perf_counter() - started_at
            print(f"[{elapsed:.1f}s] [intro message]")
            print(intro_message)
            print()
        except APITimeoutError:
            return "Hello! I’m ready to help. Note: the initial model request timed out, but you can try sending a message."
        except APIConnectionError:
            return "Hello! I’m ready to help. Note: there seems to be a connection issue with the model API."

    while True:
        user_input = input("You > ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        conversation.append({
            "role": "user",
            "content": user_input,
        })

        result = await run_with_retry(agent, conversation)
        last_result = result

        print("\nAgent >")
        print(result.final_output)
        print()

        conversation = result.to_input_list()

    return last_result