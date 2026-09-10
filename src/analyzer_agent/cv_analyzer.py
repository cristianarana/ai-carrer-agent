from google import genai
from google.genai import errors
from mistralai.client import Mistral
from dotenv import load_dotenv
import os
import json
from .interfaces.ai_analyzer_response import CVAnalysis
from .validation import CVAnalysisValidator
from pydantic import ValidationError

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
You are a technology recruiter with 15 years of experience specializing
in recruiting Software Engineers, Backend Engineers, Full Stack Engineers,
and AI Engineers.

Analyze the candidate's resume as if you were evaluating it for real
job opportunities.

Generate a structured recruitment report as a JSON object with exactly
the following structure. Do NOT omit any field. Do NOT use alternative
field names.

RECRUITMENT REPORT STRUCTURE:

{{
  "RECRUITMENT_REPORT": {{
    "BEST_FIT_JOB_POSITIONS": [
      {{
        "rank": 1,
        "position": "Job Title",
        "match_explanation": "Explanation"
      }}
    ],
    "ATS_KEYWORDS": {{
      "technical_skills": ["keyword1", "keyword2"],
      "tools_and_technologies": ["tool1", "tool2"],
      "professional_skills": ["skill1", "skill2"],
      "ai_data_keywords": ["keyword1", "keyword2"]
    }},
    "TEN_SECOND_RECRUITER_TEST": {{
      "positive": ["strength1", "strength2"],
      "unclear_or_weak": ["weakness1", "weakness2"],
      "could_cause_rejection": ["rejection_reason1", "rejection_reason2"]
    }},
    "RESUME_SCORE": {{
      "overall_score": 7.5,
      "explanation": "Score explanation",
      "breakdown": {{
        "relevance_to_target_positions": 8,
        "technical_skills": 7,
        "professional_experience": 8,
        "achievement_oriented_descriptions": 7,
        "ats_optimization": 6,
        "clarity_and_structure": 8,
        "seniority_positioning": 7
      }}
    }},
    "HOW_TO_REACH_10": {{
      "immediate_actions": [
        {{
          "priority": "High",
          "impact": "Description of impact"
        }}
      ],
      "technical_enhancements": [
        {{
          "priority": "Medium",
          "impact": "Description of impact"
        }}
      ],
      "ats_optimization": [
        {{
          "priority": "High",
          "impact": "Description of impact"
        }}
      ],
      "professional_and_structural_improvements": [
        {{
          "priority": "Low",
          "impact": "Description of impact"
        }}
      ],
      "long_term_improvements": [
        {{
          "priority": "Medium",
          "impact": "Description of impact"
        }}
      ]
    }}
  }}
}}

INSTRUCTIONS:

1. BEST_FIT_JOB_POSITIONS
   Identify exactly 20 job positions that match the candidate's current
   professional profile. Rank them from the strongest match to the weakest.
   For each position provide rank (1-20), position (job title), and
   match_explanation (concise explanation based only on resume content).

2. ATS_KEYWORDS
   Identify the most important keywords to improve ATS compatibility.
   Organize into: technical_skills, tools_and_technologies,
   professional_skills, ai_data_keywords.
   Only recommend keywords supported by the candidate's existing experience.

3. TEN_SECOND_RECRUITER_TEST
   Imagine reviewing this resume for less than 10 seconds.
   You MUST provide ALL THREE fields as lists of strings:
   - positive: What immediately stands out positively (minimum 3 items)
   - unclear_or_weak: What is unclear or weak (minimum 3 items)
   - could_cause_rejection: What could cause rejection (minimum 3 items)

4. RESUME_SCORE
   Rate the resume from 1 to 10.
   Provide overall_score (float), explanation (string), and breakdown
   object with scores for each of the 7 criteria.

5. HOW_TO_REACH_10
   You MUST provide ALL FIVE categories as lists of objects with
   "priority" (High/Medium/Low) and "impact" (description):
   - immediate_actions: At least 3 items
   - technical_enhancements: At least 3 items
   - ats_optimization: At least 3 items
   - professional_and_structural_improvements: At least 2 items
   - long_term_improvements: At least 2 items

IMPORTANT RULES:

- Only use information explicitly provided in the resume.
- Do not invent experience, technologies, projects, or certifications.
- Do not assume knowledge unless explicitly supported by the resume.
- Distinguish between professional, academic, and personal projects.
- Follow the JSON structure EXACTLY as shown above.
- Do NOT omit any field or category.
- All lists must contain at least the minimum number of items specified.

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
        ],
        response_format={"type": "json_object"}
    )
    response_content = response.choices[0].message.content
    data = json.loads(response_content)
    analysis = CVAnalysis.model_validate(data)
    CVAnalysisValidator.validate(analysis)
    print("Analyzer response is valid")

except json.JSONDecodeError as e:
    print(f"Mistral returned invalid Json: {e}")

except ValueError as e:
    print(f"Business rule violation: {e}")

except Exception as e:
    print(f"Mistral API error: {e}")

