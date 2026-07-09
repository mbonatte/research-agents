def print_token_usage(result):
    usage = getattr(getattr(result, "context_wrapper", None), "usage", None)

    if not usage:
        print("\n[token usage] Not available from this provider/model response.")
        return None

    print("\n=== Token usage ===")
    print(f"Requests:      {usage.requests}")
    print(f"Input tokens:  {usage.input_tokens}")
    print(f"Output tokens: {usage.output_tokens}")
    print(f"Total tokens:  {usage.total_tokens}")

    if getattr(usage, "request_usage_entries", None):
        print("\nPer request:")
        for i, req in enumerate(usage.request_usage_entries, start=1):
            print(
                f"  {i}. input={req.input_tokens}, "
                f"output={req.output_tokens}, "
                f"total={req.total_tokens}"
            )

    return usage


def serialize_usage(result):
    usage = getattr(getattr(result, "context_wrapper", None), "usage", None)

    if not usage:
        return None

    return {
        "requests": usage.requests,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "request_usage_entries": [
            {
                "input_tokens": req.input_tokens,
                "output_tokens": req.output_tokens,
                "total_tokens": req.total_tokens,
            }
            for req in getattr(usage, "request_usage_entries", [])
        ],
    }