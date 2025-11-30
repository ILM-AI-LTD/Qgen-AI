from typing import List, Dict, Optional

def build_generation_prompt(
    subject: str,
    curriculam: str,
    topic: str,
    qtype: Optional[str],
    difficulty: str,
    fewshots: List[Dict],
    num_questions: int
):
    s = subject.lower()

    if s in ["math"]:
        return prompt_math(
             curriculam=curriculam,
             topic=topic,
             difficulty=difficulty,
             fewshots=fewshots,
             num_questions=num_questions)

    if s in ["physics", "chemistry"]:
        return prompt_science(
             curriculam=curriculam,
             subject=subject,
             topic=topic,
             qtype=qtype,
             difficulty=difficulty,
             fewshots=fewshots,
             num_questions=num_questions)

    # fallback — at least doesn't crash
    return prompt_default(
         topic=topic,
         difficulty=difficulty,
         fewshots=fewshots,
         num_questions=num_questions)

def prompt_math(curriculam, topic, difficulty, fewshots, num_questions):

    fewshot_text = ""
    for fs in fewshots:
        fewshot_text += (
            f"Q: {fs['question']}\n"
            f"Hint: {fs['hint']}\n"
            f"A: {fs['answer']}\n"
            f"Diff: {fs['difficulty']}\n\n"
        )

    prompt = f"""
    You are a math question generator. You must create clear, accurate, logically consistent math questions.

    Curriculam: {curriculam}
    Topic: {topic}
    Difficulty: {difficulty}
    Number of questions: {num_questions}

    Here are few-shot examples for reference:
    {fewshot_text}

    Now generate {num_questions} NEW questions and their answers of the {curriculam} standard curriculam.
    Generate answers only. DON'T generate hint.
    You MUST generate questions of {difficulty} level.
    Respond ONLY in strict JSON list format:
    [
    {{"question": "...", "answer": "..."}},
    ...
    ]
    """
    return prompt

def prompt_science(curriculam, subject, topic, qtype, difficulty, fewshots, num_questions):

    fewshot_text = ""
    for fs in fewshots:
        fewshot_text += (
            f"Q: {fs['question']}\n"
            f"A: {fs['answer']}\n"
            f"Qtype: {fs['question_type']}\n"
        )

    prompt = f"""
    You are a {subject} question generator. You must create clear, accurate, logically consistent {subject} questions.

    Curriculam: {curriculam}
    Topic: {topic}
    Question Type: {qtype}
    Difficulty: {difficulty}
    Number of questions: {num_questions}

    Here are few-shot examples for reference:
    {fewshot_text}

    Now generate {num_questions} NEW questions and their answers of the {curriculam} standard curriculam.
    Generate answers only. DON'T generate hint.
    You MUST generate questions of {difficulty} level and {qtype} type.
    Respond ONLY in strict JSON list format:
    [
    {{"question": "...", "answer": "..."}},
    ...
    ]
    """
    return prompt

def prompt_default(topic, difficulty, fewshots, num_questions):

        return f"""
        Generate {num_questions} NEW questions and their answers of difficulty level {difficulty} on 
        "{topic}" topic.
        Base your creativity on the examples provided.

        Examples:
        {fewshots}"""
