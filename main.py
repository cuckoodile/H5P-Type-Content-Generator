import os
import logging
import zipfile
import json
from google import genai
from tests import ppt_reader_test  # type: ignore
from dotenv import load_dotenv
import questionary

# ------------- Configuration ------------- #
debugger = False
ppt_reader = ppt_reader_test.ppt_reader
lesson_references = [
    "chapter1.txt",
    "Chapter-1-Digital-Marketing-Create-Multiplatform-Advertisements-for-Mass-Media.pptx",
]
result_name = "Chapter 1"
references_path = "./references/digital_market"
activities_path = "./activities"

# Load environment variables
load_dotenv()
gemini_keys = {
    "holeeshet68": os.getenv("GEMINI_KEY_3"),
    "lhourdeiansube7": os.getenv("GEMINI_KEY_1"),
    "li.sube": os.getenv("GEMINI_KEY_2"),
}
gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ------------- Error Logger ------------- #
def log_error_to_file(message):
    os.makedirs(activities_path, exist_ok=True)
    log_path = os.path.join(activities_path, "h5p_generator.log")
    logging.basicConfig(
        filename=log_path,
        filemode="a",
        format="%(asctime)s | %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.ERROR,
    )
    logging.error(message)


# ------------- Gemini API Handler ------------- #
def get_gemini_response_with_keys(prompt, key_dict, model):
    exhausted_keys = set()
    last_exception = None
    for email, key in key_dict.items():
        if key in exhausted_keys or not key:
            continue
        try:
            client = genai.Client(api_key=key)
            print(f"[INFO] Using Gemini key: {email}")
            response = client.models.generate_content(model=model, contents=prompt)
            if not response.text:
                raise ValueError("Empty response from API")
            return response.text
        except Exception as e:
            exhausted_keys.add(key)
            last_exception = e
            print(f"[WARN] Key failed: {email}. Reason: {e}")
    raise RuntimeError(f"All given keys are exhausted: {last_exception}")


# ------------- Prompt Builder ------------- #
def build_prompt(tagged_lesson_content, difficulty="easy"):
    return f"""
> You are a helpful assistant that generates H5P activities based on a given lesson content.
> Generate a TXT file containing GIFT content for an H5P Question Set quiz.
> The quiz should have 10 questions, mixing:
    - Multiple Choice
    - True/False
    - Fill in the Blanks
    - Drag and Drop
    - Mark the Words
    - Drag the Words
> Notes:
    - Each question = 1 point. Include only the GIFT text, no explanations.
    - Do not use icons or emoji
    - Do not use multiple responses or answers since each question must only amount to 1 point.
    - Do not include markdown formatting or question numbers.
    - Use this format:
        ::{{Question type}}
        ::Question text...
        {{
        ~Wrong answer
        =Correct answer
        ~Wrong answer
        }}
    - Make sure the questions are {difficulty} and answerable.
    - Do not allow any duplications, each question must be unique.

> Lesson references:
{tagged_lesson_content}
"""


# ------------- Lesson Reader ------------- #
def read_lesson_content():
    tagged_blocks = []
    for idx, ref_name in enumerate(lesson_references, start=1):
        full_path = os.path.join(references_path, ref_name)
        print(f"[STEP] Reading reference: {full_path}")
        if not os.path.exists(full_path):
            msg = f"Lesson file not found: {full_path}"
            print(f"[ERROR] {msg}")
            log_error_to_file(msg)
            continue
        try:
            if ref_name.lower().endswith(".pptx"):
                content = ppt_reader(full_path)
            else:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            tagged_blocks.append(f"Reference {idx} ({ref_name}):\n{content}")
        except Exception as e:
            msg = f"Error reading {ref_name}: {e}"
            print(f"[ERROR] {msg}")
            log_error_to_file(msg)
    return "\n\n".join(tagged_blocks)


# ------------- Quiz Generators ------------- #
def generate_main_quiz(content):
    prompt = build_prompt(content, difficulty="medium")
    return get_gemini_response_with_keys(prompt, gemini_keys, gemini_model)


def generate_supplementary_quiz(content):
    prompt = build_prompt(content, difficulty="easy")
    return get_gemini_response_with_keys(prompt, gemini_keys, gemini_model)


def generate_quiz_package(content):
    prompt_main = build_prompt(content, difficulty="medium")
    prompt_supp = build_prompt(content, difficulty="easy")

    main_quiz = get_gemini_response_with_keys(prompt_main, gemini_keys, gemini_model)
    supp_quiz = get_gemini_response_with_keys(prompt_supp, gemini_keys, gemini_model)

    return main_quiz.strip(), supp_quiz.strip()


# ------------- Supplementary Validator ------------- #
def validate_and_regenerate_supplementary_quiz(main_path, supp_path, lesson_content):
    try:
        with open(main_path, "r", encoding="utf-8") as f:
            main_content = f.read()
        with open(supp_path, "r", encoding="utf-8") as f:
            supp_content = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read quiz files: {e}")
        log_error_to_file(f"Failed to read quiz files: {e}")
        return

    # Build prompt to detect overlap and regenerate if needed
    prompt = f"""
> You are a quiz validator and generator.
> Compare the two GIFT-format quizzes below and identify any overlapping or duplicate questions in concept or phrasing.
> If overlaps are found, regenerate only the overlapping questions using the lesson content.
> Return a clean supplementary quiz with exactly 10 unique questions in GIFT format where each questions are separated by a empty line (/n).
> Do NOT include any analysis, commentary, or explanation—only the final quiz content.
> Use this sample format:
    ::{{Question type}}
    ::Question text...
    {{
    ~Wrong answer
    =Correct answer
    ~Wrong answer
    }}

> Main Quiz:
{main_content}

> Supplementary Quiz:
{supp_content}

> Lesson Content:
{lesson_content}
"""
    print("[STEP] Validating and regenerating supplementary quiz...")
    updated_supp_quiz = get_gemini_response_with_keys(prompt, gemini_keys, gemini_model)

    # Save updated supplementary quiz
    save_quiz(f"{result_name} Supplementary Quiz.txt", updated_supp_quiz.strip())


# ------------- File Writer ------------- #
def save_quiz(filename, content):
    os.makedirs(activities_path, exist_ok=True)
    path = os.path.join(activities_path, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[SUCCESS] Saved: {path}")
    except Exception as e:
        msg = f"Error saving file {path}: {e}"
        print(f"[ERROR] {msg}")
        log_error_to_file(msg)


# ------------- Menu Prompt ------------- #
def display_menu():
    options = [
        "Quiz Package (Main + Supplementary - 20 unique questions)",
        "Main Quiz (10 medium-difficulty questions)",
        "Supplementary Quiz (10 easy questions)",
    ]
    choice = questionary.select(
        "Choose the type of quiz to generate:", choices=options
    ).ask()
    return options.index(choice) if choice in options else None


# ------------- Main Entry Point ------------- #
def main():
    print("[STEP] Initializing script...")
    choice = display_menu()
    lesson_content = read_lesson_content()

    if not lesson_content.strip():
        print("[ERROR] No valid lesson content found.")
        log_error_to_file("No valid lesson content found from provided references.")
        return

    if choice == 0:
        print("[STEP] Generating Quiz Package...")
        main_quiz, supp_quiz = generate_quiz_package(lesson_content)
        main_path = os.path.join(activities_path, f"{result_name} Quiz.txt")
        supp_path = os.path.join(activities_path, f"{result_name} Supplementary Quiz.txt")
        save_quiz(f"{result_name} Quiz.txt", main_quiz)
        save_quiz(f"{result_name} Supplementary Quiz.txt", supp_quiz)
        validate_and_regenerate_supplementary_quiz(main_path, supp_path, lesson_content)

    elif choice == 1:
        print("[STEP] Generating Main Quiz...")
        main_quiz = generate_main_quiz(lesson_content)
        save_quiz(f"{result_name} Quiz.txt", main_quiz)

    elif choice == 2:
        print("[STEP] Generating Supplementary Quiz...")
        supp_quiz = generate_supplementary_quiz(lesson_content)
        save_quiz(f"{result_name} Supplementary Quiz.txt", supp_quiz)

main()