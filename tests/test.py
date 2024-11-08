def test():
    import openai, os
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    api_base = "https://openrouter.ai/api/v1/"
    model_name = "nousresearch/hermes-3-llama-3.1-405b:free"
    messages_dict = [{"role": "user", "content": "Say hello!"}]

    client = openai.OpenAI(
        base_url=api_base,
        api_key=api_key,
        # max_retries=
        #         timeout=WORKER_API_TIMEOUT,
        # timeout=5,
        #     timeout=httpx.Timeout(5, read=5, write=5, connect=2
        # )
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=messages_dict,
        temperature=1,
        max_tokens=100,
        stream=True,
        stream_options={"include_usage": True},
        # Not available like this
        # top_p=top_p,
    )
    # Verify the response
    text = ""
    output_tokens = None
    for chunk in response:
        if "output_tokens" in chunk:
            print(
                f"reported output tokens for api test:"
                + str(chunk["output_tokens"])
            )
            output_tokens = chunk["output_tokens"]
        
        if len(chunk.choices) > 0:
            text += chunk.choices[0].delta.content or ""


    if output_tokens:
        print(output_tokens)

    # Check if the response is successful
    if text:
        print(text)
    else:
        print("Argh!")
    return text


if __name__ == "__main__":
    print("This script is being executed directly")
    test()