# H5P GIFT Quiz Generator

## Overview
This Python script generates H5P Question Set quizzes in GIFT format from a given lesson reference file. It uses the Google Generative AI (Gemini) API to create a 10-question quiz that can include a mix of question types. The generated quiz is saved as a `.txt` file, ready for import into H5P or compatible LMS platforms.

The script supports both `.txt` plain text lesson files and `.h5p` lesson packages. For `.h5p` files, it extracts the `content/content.json` file to use as the lesson source.

## Features
- Reads lesson content from `.txt` or `.h5p` files.
- Generates 10-question quizzes in GIFT format.
- Supports multiple question types:
  - Multiple Choice
  - True/False
  - Fill in the Blanks
  - Drag and Drop
  - Mark the Words
  - Drag the Words
- Saves the quiz to a specified output file in the `./activities` directory.
- Logs errors only, appending them to a log file without overwriting previous entries.

Code
## Configuration
The following variables can be adjusted at the top of the script:

| Variable               | Description |
|------------------------|-------------|
| `lesson_reference_name`| Name of the lesson file inside `./references` (can be `.txt` or `.h5p`) |
| `result_name`          | Name of the generated quiz file (e.g., `Supplementary_Quiz.txt`) |
| `references_path`      | Path to the folder containing lesson reference files |
| `activities_path`      | Path to the folder where generated quizzes and logs will be saved |
| `gemini_key`           | List of Gemini API keys to use (script will try them in order) |
| `gemini_model`         | Gemini model to use (default: `gemini-2.5-flash`) |
| `debugger`             | Set to `True` to enable debug output for API key usage and failures |

## Installation
1. Ensure Python 3.8 or higher is installed.
2. Install the required dependency:
   ```bash
   pip install google-generativeai
   ```