import os
import logging
import zipfile
import json
from google import genai
from tests import ppt_reader_test  # type: ignore
from dotenv import load_dotenv

# ------------- Variables ------------- #
debugger = False
ppt_reader = ppt_reader_test.ppt_reader
lesson_references = [
    "chapter3.txt",
    "Managing-Work-Goal-Development-Ch-1.pptx"

    # Add more references as needed
]
result_name = "Supplementary_Quiz.txt"
references_path = "./references"
activities_path = "./activities"

# Load sensitive info from .env
load_dotenv()

# API keys and model from environment variables
gemini_keys = {
    "lhourdeiansube7": os.getenv("GEMINI_KEY_1"),
    "li.sube": os.getenv("GEMINI_KEY_2"),
    "holeeshet68": os.getenv("GEMINI_KEY_3"),
}
gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ------------- Error Logger (append mode) ------------- #
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

# ------------- AI Generation ------------- #
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

def generate_activity(tagged_lesson_content):
    prompt = f"""
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
    -Each question = 1 point. Include only the GIFT text, no explanations.
    - Do not use icons or emoji
    - Do not use multiple responses or answers since each question must only amount to 1 point i.e.
        Question 4 (Drag and Drop - Multiple Response)
            Select all the taxes that are specifically categorized as 'Niche Taxes' in the module.
                ~%100%Wine Equalisation Tax (WET)
                ~Corporate Income Tax
                ~%100%Luxury Car Tax (LCT)
                ~Goods and Services Tax (GST)
                ~%100%Fringe Benefits Tax (FBT)
    - Use this format when generating an activity:
        Question {{Current question number}} ({{Question set type i.e. True or False, Drag and Drop, etc.}})
        Question contents....

> Lesson references:
{tagged_lesson_content}
"""
    return get_gemini_response_with_keys(prompt, gemini_keys, gemini_model)

# ------------- Main Function ------------- #
def main():
    print("[STEP] Initializing script...")
    print(f"[INFO] Output file will be: {os.path.join(activities_path, result_name)}")

    tagged_content_blocks = []

    for idx, ref_name in enumerate(lesson_references, start=1):
        full_path = os.path.join(references_path, ref_name)
        print(f"[STEP] Reading reference: {full_path}")

        if not os.path.exists(full_path):
            msg = f"Lesson file not found: {full_path}"
            print(f"[ERROR] {msg}")
            log_error_to_file(msg)
            continue

        try:
            if ref_name.lower().endswith(".h5p"):
                with zipfile.ZipFile(full_path, "r") as zip_ref:
                    if "content/content.json" not in zip_ref.namelist():
                        raise ValueError("No content/content.json found in the H5P file.")
                    with zip_ref.open("content/content.json") as f:
                        lesson_content_dict = json.load(f)
                        content = json.dumps(lesson_content_dict, indent=2)

            elif ref_name.lower().endswith(".pptx"):
                content = ppt_reader(full_path)

            else:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

            tagged_block = f"Reference {idx} ({ref_name}):\n{content}"
            tagged_content_blocks.append(tagged_block)

        except Exception as e:
            msg = f"Error reading {ref_name}: {e}"
            print(f"[ERROR] {msg}")
            log_error_to_file(msg)

    combined_content = "\n\n".join(tagged_content_blocks)

    if not combined_content.strip():
        print("[ERROR] No valid lesson content found.")
        log_error_to_file("No valid lesson content found from provided references.")
        return

    # Generate quiz
    try:
        print("[STEP] Sending request to LLM...")
        gemini_response = generate_activity(combined_content)
        print("[INFO] LLM response received.")

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
