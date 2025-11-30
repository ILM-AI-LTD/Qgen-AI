def build_generation_prompt(topic, difficulty, fewshots, num_questions):

    fewshot_text = ""
    for fs in fewshots:
        fewshot_text += (
            f"Q: {fs['question']}\n"
            f"Hint: {fs['hint']}\n"
            f"A: {fs['answer']}\n\n"
        )

    prompt = f"""
    You are a math question generator. You must create clear, accurate, logically consistent math questions.

    Topic: {topic}
    Difficulty: {difficulty}
    Number of questions: {num_questions}

    Here are few-shot examples for reference:
    {fewshot_text}

    Now generate {num_questions} NEW questions and their answers.
    Generate answers only. DON'T generate hint.
    You MUST generate questions of {difficulty} level.
    Respond ONLY in strict JSON list format:
    [
    {{"question": "...", "answer": "..."}},
    ...
    ]
    """
    return prompt
