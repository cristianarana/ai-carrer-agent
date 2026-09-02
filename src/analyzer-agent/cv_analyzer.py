from google import genai
from google.genai import errors
from mistralai.client import Mistral
from dotenv import load_dotenv
import os

load_dotenv()

genai_client = genai.Client(
    api_key = os.getenv('GENAI_API_KEY')
)

mistral_client = Mistral(
    api_key = os.getenv('MISTRAL_API_KEY')
)

with open("data-source/cv_ENG.md", "r", encoding="utf-8") as file:
    resume=file.read()

prompt = f"""
You are a technology recruiter with 15 years of experience specializing in recruiting Software Engineers, Backend Engineers, Full Stack Engineers, and AI Engineers.

Analyze the candidate's resume as if you were evaluating it for real job opportunities.

Provide a detailed recruitment report covering the following:

1. BEST-FIT JOB POSITIONS
Identify 20 job positions that match the candidate's current professional profile, ranked from the strongest match to the weakest. For each position, briefly explain why the candidate is a good fit.

2. ATS KEYWORDS
Identify the most important technical and professional keywords that should be included in the resume to improve its ATS compatibility for the recommended positions.

Separate them into:
- Technical skills
- Tools and technologies
- Professional skills
- AI / Data keywords

3. 10-SECOND RECRUITER TEST
Imagine you are reviewing this resume for less than 10 seconds.

Identify:
- What immediately stands out positively
- What is unclear or weak
- What could cause a recruiter to reject the resume

4. RESUME SCORE
Rate the resume from 1 to 10 based on:
- Relevance to target positions
- Technical skills
- Professional experience
- Achievement-oriented descriptions
- ATS optimization
- Clarity and structure
- Seniority positioning

Explain the score.

5. HOW TO REACH 10/10
Provide specific and actionable changes that would improve the resume and bring it as close as possible to a 10/10.

IMPORTANT RULES:
- Only use information explicitly provided in the resume.
- Do not invent experience, technologies, projects, responsibilities, certifications, or achievements.
- If important information is missing, explicitly state that it is missing.
- Evaluate the candidate based on their current profile, not on skills they should have in the future.
- Distinguish between professional experience and knowledge or learning mentioned in the resume.

CANDIDATE RESUME:

{resume}
"""
try:
    response = mistral_client.chat.complete(
        model = "mistral-small-latest",
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    print(response.choices[0].message.content)

except Exception as e:
    print(f"Mistral API error: {e}")

