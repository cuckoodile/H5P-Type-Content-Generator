import os
import logging
import zipfile
import json
from google import genai

# ------------- Variables ------------- #
debugger = False
lesson_reference_name = "chapter3.txt"  # can be .txt or .h5p
result_name = "Supplementary_Quiz.txt"
references_path = "./references"
activities_path = "./activities"


# Load sensitive info from .env
from dotenv import load_dotenv

load_dotenv()

# API keys and model from environment variables
gemini_key = [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"),
    os.getenv("GEMINI_KEY_3"),
]
gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ------------- Error Logger (append mode) ------------- #
def log_error_to_file(message):
    os.makedirs(activities_path, exist_ok=True)
    log_path = os.path.join(activities_path, "h5p_generator.log")
    logging.basicConfig(
        filename=log_path,
        filemode="a",  # append mode
        format="%(asctime)s | %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.ERROR,
    )
    logging.error(message)


# ------------- AI Generation ------------- #
def get_gemini_response_with_keys(prompt, keys, model):
    exhausted_keys = set()
    last_exception = None
    for key in keys:
        if key in exhausted_keys:
            continue
        try:
            client = genai.Client(api_key=key)
            print(f"[INFO] Using Gemini key: {key[:6]}...")  # partial key for debug
            response = client.models.generate_content(model=model, contents=prompt)
            if not response.text:
                raise ValueError("Empty response from API")
            return response.text
        except Exception as e:
            exhausted_keys.add(key)
            last_exception = e
            print(f"[WARN] Key failed: {key[:6]}... Reason: {e}")
    raise RuntimeError(f"All given keys are exhausted: {last_exception}")


def generate_activity(lesson_content):
    prompt = f"""
You are a helpful assistant that generates H5P activities based on a given lesson content.

Generate a TXT file containing GIFT content for an H5P Question Set quiz.
The quiz should have 10 questions, mixing:
- Multiple Choice
- True/False
- Fill in the Blanks
- Drag and Drop
- Mark the Words
- Drag the Words

Each question = 1 point. Include only the GIFT text, no explanations.
Lesson content:
{lesson_content}
"""
    return get_gemini_response_with_keys(prompt, gemini_key, gemini_model)


# ------------- Main Function ------------- #
def main():
    print("[STEP] Initializing script...")
    full_lesson_path = os.path.join(references_path, lesson_reference_name)
    print(f"[INFO] Lesson reference path: {full_lesson_path}")
    print(f"[INFO] Output file will be: {os.path.join(activities_path, result_name)}")

    if not os.path.exists(full_lesson_path):
        msg = f"Lesson file not found: {full_lesson_path}"
        print(f"[ERROR] {msg}")
        log_error_to_file(msg)
        return

    # Read lesson content
    try:
        print("[STEP] Reading lesson content...")
        if lesson_reference_name.lower().endswith(".h5p"):
            with zipfile.ZipFile(full_lesson_path, "r") as zip_ref:
                if "content/content.json" not in zip_ref.namelist():
                    raise ValueError("No content/content.json found in the H5P file.")
                with zip_ref.open("content/content.json") as f:
                    lesson_content_dict = json.load(f)
                    lesson_content_str = json.dumps(lesson_content_dict, indent=2)
        else:
            with open(full_lesson_path, "r", encoding="utf-8") as f:
                lesson_content_str = f.read()
    except Exception as e:
        msg = f"Error reading lesson file: {e}"
        print(f"[ERROR] {msg}")
        log_error_to_file(msg)
        return

    # Generate quiz
    try:
        print("[STEP] Sending request to LLM...")
        gemini_response = generate_activity(lesson_content_str)
        print("[INFO] LLM response received.")

        # Save directly to TXT file
        os.makedirs(activities_path, exist_ok=True)
        output_path = os.path.join(activities_path, result_name)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(gemini_response.strip())

        print(f"[SUCCESS] Quiz saved to: {output_path}")

    except Exception as e:
        msg = f"Error generating quiz: {e}"
        print(f"[ERROR] {msg}")
        log_error_to_file(msg)
        return

    print("[DONE] Script completed successfully.")


if __name__ == "__main__":
    main()
