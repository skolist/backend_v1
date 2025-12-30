from ai.schemas.questions import MCQ4, MSQ4, FillInTheBlank, TrueFalse, ShortAnswer, LongAnswer

def generate_mcq(*args, **kwargs):
    return MCQ4(
        question="What is the capital of France?",
        option1="Paris",
        option2="London",
        option3="Berlin",
        option4="Madrid",
        answer=1,
        explanation="Paris is the capital of France."
    )

def generate_msq(*args, **kwargs):
    return MSQ4(
        question="What is the capital of France?",
        option1="Paris",
        option2="London",
        option3="Berlin",
        option4="Madrid",
        answers=[1, 2],
        explanation="Paris is the capital of France."
    )

def generate_fill_in_the_blank(*args, **kwargs):
    return FillInTheBlank(
        question="What is the capital of France?",
        answer="Paris",
        explanation="Paris is the capital of France."
    )

def generate_true_false(*args, **kwargs):
    return TrueFalse(
        question="What is the capital of France?",
        answer=True,
        explanation="Paris is the capital of France."
    )

def generate_short_answer(*args, **kwargs):
    return ShortAnswer(
        question="What is the capital of France?",
        answer="Paris",
        explanation="Paris is the capital of France."
    )

def generate_long_answer(*args, **kwargs):
    return LongAnswer(
        question="What is the capital of France?",
        answer="Paris",
        explanation="Paris is the capital of France."
    )