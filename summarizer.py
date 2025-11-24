# import os
# import sys
# from dotenv import load_dotenv
# from openai import OpenAI

# # Load environment variables from .env
# load_dotenv()

# # Initialize OpenAI client
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def summarize_text(text):
#     prompt = f"""
# You are an expert study-note creator.

# Convert the following raw text into PERFECT study notes:
# - Clear headings and subheadings
# - Bullet points
# - Simplified explanations
# - Bold key terms
# - Definitions separated
# - Examples added if helpful
# - Remove irrelevant or repeated info
# - Make the output clean, neat, and exam-ready

# RAW NOTES:
# {text}
# """
#     response = client.chat.completions.create(
#         model="gpt-4.1",
#         messages=[
#             {"role": "user", "content": prompt}
#         ]
#     )
#     return response.choices[0].message.content

# def main():
#     # Get filename from command line or ask user
#     if len(sys.argv) > 1:
#         filename = sys.argv[1]
#     else:
#         filename = input("Enter path to text file: ")

#     # Read the f
import os
from dotenv import load_dotenv
from openai import OpenAI
import sys

# Load .env
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize_text(text):
    prompt = f"""
    You are an elite university study-note creator.

    Your job is to transform raw lecture notes into EXAM-READY STUDY NOTES.
    
    Produce output with:
    - Clear topic hierarchy (H1, H2, H3)
    - Bullet points AND short explanations
    - Key formulas explained
    - Short examples that illustrate concepts
    - Highlight important warnings, pitfalls, misconceptions
    - Definitions separated and clearly marked
    - Summary boxes at the end of sections
    - Exam tips or memory tricks if relevant
    - No unnecessary text, no fluff

    The final notes must look like a professional study guide.

    RAW NOTES:
    {text}
    """
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4  # keeps it logical and structured
    )
    return response.choices[0].message.content
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python summarizer.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    summary = summarize_text(text)
    print(summary)
