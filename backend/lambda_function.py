import base64
import json
import math
import os
import re
import string
import time  # NEW: for response timing
import ast
import operator

import boto3


def load_env_file():
    env_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env")
    ]

    for env_path in env_paths:
        normalized_path = os.path.normpath(env_path)
        if not os.path.exists(normalized_path):
            continue

        try:
            with open(normalized_path, "r", encoding="utf-8") as env_file:
                for raw_line in env_file:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue

                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception as error:
            print(f"env_load_failed path={normalized_path} error={error}")


load_env_file()

# ================================================================
# REGION / MODEL
# ================================================================

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")
NOVA_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "apac.amazon.nova-pro-v1:0")
LLAMA_MODEL_ID = os.getenv("LLAMA_MODEL_ID", "us.meta.llama3-1-70b-instruct-v1:0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "1"))
PARTIAL_RETRIES = int(os.getenv("PARTIAL_RETRIES", "1"))

# NEW: Batch size — never ask AI for more than this many questions at once.
# If user requests 10 → 2 batches of 5. If 15 → 3 batches of 5.
# This prevents the AI from truncating its response and losing questions.
BATCH_SIZE = 5

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

QUESTION_BANK_CACHE = None

# ================================================================
# EXAM PATTERNS
# ================================================================

EXAM_PATTERNS = {
    "RRB NTPC": {
        "timer_minutes": 90,
        "total_questions": 100,
        "sections": {
            "Mathematics": 30,
            "General Intelligence & Reasoning": 30,
            "General Awareness": 40
        }
    },
    "RRB Group D": {
        "timer_minutes": 90,
        "total_questions": 100,
        "sections": {
            "Mathematics": 25,
            "General Intelligence & Reasoning": 30,
            "General Science": 25,
            "General Awareness & Current Affairs": 20
        }
    },
    "RRB ALP": {
        "timer_minutes": 60,
        "total_questions": 75,
        "sections": {
            "Mathematics": 20,
            "Mental Ability & Reasoning": 25,
            "General Science": 20,
            "Current Affairs & General Awareness": 10
        }
    },
    "RRB Technician Grade 3": {
        "timer_minutes": 90,
        "total_questions": 100,
        "sections": {
            "Mathematics": 30,
            "General Intelligence & Reasoning": 30,
            "General Science": 20,
            "General Awareness": 20
        }
    },
    "RRB Technician Grade 1": {
        "timer_minutes": 90,
        "total_questions": 100,
        "sections": {
            "Mathematics": 30,
            "General Intelligence & Reasoning": 25,
            "General Awareness": 10,
            "Physics & Chemistry": 15,
            "Technical": 20
        }
    }
}

# ================================================================
# NEW: RRB SYLLABUS MAP
# Each subject maps to its exact subtopics so the AI covers
# varied content instead of repeating the same concept.
# ================================================================

RRB_SYLLABUS = {
    "Mathematics": {
        "subtopics": [
            "Number System", "HCF and LCM", "Simplification", "Fractions and Decimals",
            "Ratio and Proportion", "Percentage", "Profit and Loss", "Simple Interest",
            "Compound Interest", "Time and Work", "Time Speed Distance", "Trains",
            "Pipes and Cisterns", "Averages", "Mixtures and Alligation",
            "Mensuration 2D", "Mensuration 3D", "Algebra", "Trigonometry",
            "Data Interpretation", "Boats and Streams", "Partnership"
        ],
        "rules": "Generate numerical MCQs with exact calculations. Wrong options must be common calculation mistakes (wrong formula, unit conversion error). Show full step-by-step in explanation.",
        "style": "calculation-based"
    },
    "General Intelligence & Reasoning": {
        "subtopics": [
            "Analogies", "Alphabetical Series", "Number Series", "Coding-Decoding",
            "Blood Relations", "Direction Sense", "Ranking and Order",
            "Syllogisms", "Venn Diagrams", "Statement and Conclusions",
            "Odd One Out", "Missing Numbers", "Calendar", "Clock",
            "Seating Arrangement", "Mathematical Operations", "Mirror Images",
            "Paper Cutting and Folding"
        ],
        "rules": "Generate pattern-based logical reasoning questions. All 4 options must look plausible at first glance. Explanation must show exact pattern or rule used step by step.",
        "style": "pattern-based"
    },
    "General Awareness": {
        "subtopics": [
            "Indian History", "Indian Geography", "Indian Constitution",
            "Indian Polity", "Indian Economy", "Sports", "Awards and Honours",
            "Books and Authors", "Important Days", "Science and Technology",
            "Inventions and Discoveries", "Famous Personalities",
            "Countries Capitals Currencies", "Railway Knowledge",
            "UNESCO Heritage Sites", "National Parks"
        ],
        "rules": "Generate direct factual GK questions. Wrong options must be REAL entities (real countries, real people, real years), not made-up names. One clearly correct answer only.",
        "style": "fact-based"
    },
    "General Science": {
        "Physics": [
            "Laws of Motion", "Work Energy Power", "Gravitation",
            "Light and Optics", "Sound Waves", "Current Electricity",
            "Magnetism", "Heat and Temperature", "Modern Physics", "Units and Measurement"
        ],
        "Chemistry": [
            "Matter and States", "Atoms and Molecules", "Chemical Reactions",
            "Acids Bases and Salts", "Metals and Non-metals", "Carbon Compounds",
            "Periodic Table", "Fuels and Combustion"
        ],
        "Biology": [
            "Cell Biology", "Human Digestive System", "Human Respiratory System",
            "Human Circulatory System", "Nervous System", "Plant Biology",
            "Diseases and Prevention", "Nutrition and Vitamins", "Ecology"
        ],
        "rules": "Mix definition, application, and real-world example questions. Explanation must include the scientific principle. Wrong options must be scientifically related terms.",
        "style": "concept-based"
    }
}

# ================================================================
# NEW: DIFFICULTY DEFINITIONS
# Clearly tells the AI what each difficulty level means.
# ================================================================

DIFFICULTY_DEFINITIONS = {
    "basic":        "Class 8-10 level. Direct recall. Single concept. No tricks. Student should answer in under 30 seconds.",
    "medium":       "Requires 1-2 step thinking. Apply formula or concept. Slightly tricky options that test understanding. 30-60 seconds.",
    "intermediate": "Requires 1-2 step thinking. Standard RRB exam difficulty. 30-60 seconds.",
    "advanced":     "Multi-step problems. Combine 2+ concepts. Options are very close. Designed to confuse — only deep understanding leads to correct answer. 60-90 seconds.",
    "hard":         "Multi-step problems. Tricky distractors. Advanced level."
}

# ================================================================
# NEW: FEW-SHOT EXAMPLES PER SUBJECT
# One example per subject shows the AI exactly what format to follow.
# ================================================================

FEW_SHOT_EXAMPLES = {
    "Mathematics": '{"q": "A train travels 360 km in 4 hours. What is its speed in m/s?", "opts": ["A) 20 m/s", "B) 25 m/s", "C) 30 m/s", "D) 15 m/s"], "ans": 1, "exp": "Step 1: Speed = Distance/Time = 360/4 = 90 km/h. Step 2: Convert to m/s: 90 x 1000/3600 = 25 m/s. Step 3: Therefore, the correct answer is 25 m/s which matches option B."}',

    "General Intelligence & Reasoning": '{"q": "If MANGO is coded as NBOHP, then APPLE is coded as?", "opts": ["A) BQQMF", "B) BQPMF", "C) BRQMF", "D) BQQNF"], "ans": 0, "exp": "Step 1: Each letter shifts +1 in the alphabet. Step 2: A→B, P→Q, P→Q, L→M, E→F. Step 3: Therefore, APPLE = BQQMF which matches option A."}',

    "General Awareness": '{"q": "Who was the first woman to become the President of India?", "opts": ["A) Indira Gandhi", "B) Sarojini Naidu", "C) Pratibha Patil", "D) Sonia Gandhi"], "ans": 2, "exp": "Step 1: India has had one female President so far. Step 2: Pratibha Patil served as the 12th President from 2007 to 2012. Step 3: Therefore, Pratibha Patil was the first female President, which matches option C."}',

    "General Science": '{"q": "Which part of the human eye controls the amount of light entering it?", "opts": ["A) Cornea", "B) Retina", "C) Lens", "D) Iris"], "ans": 3, "exp": "Step 1: The question asks about light regulation in the eye. Step 2: The Iris is the colored ring that controls pupil size — it contracts in bright light and expands in dim light. Step 3: Therefore, the correct answer is Iris which matches option D."}'
}

# ================================================================
# QUESTION BANKS (UNCHANGED)
# ================================================================

CODING_DECODE_WORD_BANK = [
    "RAIL", "TRACK", "BOOK", "PAGE", "SIGN", "BOARD", "CAMP", "TRAIN",
    "MIND", "BRAIN", "CLOCK", "TIMER", "PLANT", "GARDEN", "STONE", "BRIDGE",
    "LIGHT", "SIGNAL", "MOTOR", "ENGINE", "CHAIR", "TABLE", "FRAME", "WINDOW",
    "PAPER", "MARKS", "POINT", "SCORE", "FIELD", "MATCH", "LEVEL", "SHIFT",
    "ROUND", "STAGE", "COACH", "METAL", "SOLVE", "LOGIC", "BASIC", "SKILL"
]

PERCENTAGE_PRACTICE_BANK = [
    {
        "q": "A student scores 72 marks out of 90 in an exam. What percentage of marks did the student score?",
        "opts": ["A) 70%", "B) 75%", "C) 80%", "D) 85%"],
        "ans": 2,
        "exp": "Step 1: Use percentage = (obtained marks / total marks) x 100. Step 2: Here, percentage = (72 / 90) x 100 = 0.8 x 100. Step 3: Therefore, the percentage scored is 80%."
    },
    {
        "q": "Out of 500 railway applicants, 320 cleared Stage 1. What percent cleared the stage?",
        "opts": ["A) 60%", "B) 62%", "C) 64%", "D) 68%"],
        "ans": 2,
        "exp": "Step 1: Use percentage = (successful applicants / total applicants) x 100. Step 2: Here, percentage = (320 / 500) x 100 = 0.64 x 100. Step 3: Therefore, 64% applicants cleared the stage."
    },
    {
        "q": "If 25% of a number is 36, what is the number?",
        "opts": ["A) 144", "B) 120", "C) 136", "D) 150"],
        "ans": 0,
        "exp": "Step 1: Let the number be x, so 25% of x = 36. Step 2: This gives 0.25x = 36, so x = 36 / 0.25. Step 3: Therefore, the number is 144."
    },
    {
        "q": "If the price of a product is first increased by 20% and then decreased by 20%, what is the net change in the price?",
        "opts": ["A) No change", "B) 2% decrease", "C) 4% decrease", "D) 6% increase"],
        "ans": 2,
        "exp": "Step 1: Assume the original price is 100. Step 2: After a 20% increase, the price becomes 120, and after a 20% decrease on 120, the price becomes 96. Step 3: Therefore, the net result is a 4% decrease."
    },
    {
        "q": "The price of an article is reduced by 25%. By what percentage must the reduced price be increased to restore the original price?",
        "opts": ["A) 30%", "B) 33.33%", "C) 37.5%", "D) 40%"],
        "ans": 1,
        "exp": "Step 1: Assume the original price is 100, so the reduced price becomes 75. Step 2: Required increase percentage = (25 / 75) x 100. Step 3: Therefore, the reduced price must be increased by 33.33%."
    },
    {
        "q": "In an examination, a student scored 60% in the first paper of 200 marks and 80% in the second paper of 300 marks. What is the student's overall percentage?",
        "opts": ["A) 72%", "B) 74%", "C) 70%", "D) 76%"],
        "ans": 0,
        "exp": "Step 1: First paper marks = 60% of 200 = 120, and second paper marks = 80% of 300 = 240. Step 2: Total marks obtained = 120 + 240 = 360 out of 500. Step 3: Therefore, the overall percentage is (360 / 500) x 100 = 72%."
    },
    {
        "q": "A man saves Rs. 22,000 which is 40% of his monthly salary. What is his monthly salary?",
        "opts": ["A) Rs. 55,000", "B) Rs. 60,000", "C) Rs. 50,000", "D) Rs. 52,000"],
        "ans": 0,
        "exp": "Step 1: If Rs. 22,000 is 40% of the salary, then salary = 22000 x 100 / 40. Step 2: This gives salary = 2200000 / 40 = 55000. Step 3: Therefore, the monthly salary is Rs. 55,000."
    },
    {
        "q": "If 40% of a number is 28 more than 20% of the same number, what is the number?",
        "opts": ["A) 140", "B) 160", "C) 280", "D) 100"],
        "ans": 0,
        "exp": "Step 1: Let the number be x, then 40% of x = 20% of x + 28. Step 2: This gives 0.4x = 0.2x + 28, so 0.2x = 28. Step 3: Therefore, x = 28 / 0.2 = 140."
    }
]

ARITHMETIC_PRACTICE_BANK = [
    {
        "q": "If the simple interest on a sum for 2 years at 5% per annum is Rs. 50, what is the principal amount?",
        "opts": ["A) Rs. 500", "B) Rs. 550", "C) Rs. 600", "D) Rs. 650"],
        "ans": 0,
        "exp": "Step 1: Use SI = PRT / 100. Step 2: Here, 50 = P x 5 x 2 / 100. Step 3: Solving gives P = 500."
    },
    {
        "q": "If Rs. 8000 amounts to Rs. 9200 in 3 years at simple interest, what is the rate of interest per annum?",
        "opts": ["A) 5%", "B) 6%", "C) 7%", "D) 8%"],
        "ans": 0,
        "exp": "Step 1: Interest = 9200 - 8000 = 1200. Step 2: Use SI = PRT / 100, so 1200 = 8000 x R x 3 / 100. Step 3: Therefore, R = 5%."
    },
    {
        "q": "A trader marks his goods 20% above cost price and gives a 10% discount on the marked price. What is the profit percentage?",
        "opts": ["A) 6%", "B) 8%", "C) 10%", "D) 12%"],
        "ans": 1,
        "exp": "Step 1: Let cost price be 100, so marked price becomes 120. Step 2: After 10% discount, selling price = 120 - 12 = 108. Step 3: Therefore, profit percentage = 8%."
    },
    {
        "q": "If the price of an article is increased by 20% and then decreased by 20%, what is the net change in price?",
        "opts": ["A) No change", "B) 2% decrease", "C) 4% decrease", "D) 6% increase"],
        "ans": 2,
        "exp": "Step 1: Let the original price be 100. Step 2: After 20% increase it becomes 120, and after 20% decrease it becomes 96. Step 3: So the net change is a 4% decrease."
    },
    {
        "q": "A sum amounts to Rs. 6000 in 5 years and Rs. 6600 in 7 years at simple interest. What is the annual interest?",
        "opts": ["A) Rs. 250", "B) Rs. 300", "C) Rs. 350", "D) Rs. 400"],
        "ans": 1,
        "exp": "Step 1: Interest for 2 years = 6600 - 6000 = 600. Step 2: Therefore, interest for 1 year = 600 / 2. Step 3: So the annual interest is Rs. 300."
    },
    {
        "q": "If the circumference of a circle is 88 cm, what is its area?",
        "opts": ["A) 616 cm2", "B) 600 cm2", "C) 566 cm2", "D) 666 cm2"],
        "ans": 0,
        "exp": "Step 1: Circumference = 2 x 22/7 x r = 88. Step 2: Solving gives r = 14 cm. Step 3: Therefore, area = 22/7 x 14 x 14 = 616 cm2."
    },
    {
        "q": "A train 150 meters long crosses a signal post in 15 seconds. What is the speed of the train in km/hr?",
        "opts": ["A) 36 km/hr", "B) 42 km/hr", "C) 32 km/hr", "D) 30 km/hr"],
        "ans": 0,
        "exp": "Step 1: Speed = distance / time = 150 / 15 = 10 m/s. Step 2: Convert m/s to km/hr by multiplying by 18/5. Step 3: Therefore, speed = 10 x 18/5 = 36 km/hr."
    },
    {
        "q": "If the diagonal of a rectangle is 13 cm and its length is 12 cm, what is the breadth?",
        "opts": ["A) 5 cm", "B) 6 cm", "C) 7 cm", "D) 8 cm"],
        "ans": 0,
        "exp": "Step 1: By Pythagoras theorem, diagonal2 = length2 + breadth2. Step 2: So 13 x 13 = 12 x 12 + breadth2, which gives breadth2 = 25. Step 3: Therefore, breadth = 5 cm."
    },
    {
        "q": "A train running at the speed of 60 km/hr crosses a pole in 18 seconds. Find the length of the train.",
        "opts": ["A) 300 m", "B) 320 m", "C) 330 m", "D) 350 m"],
        "ans": 0,
        "exp": "Step 1: Convert speed to m/s: 60 x 5/18 = 50/3 m/s. Step 2: Distance = speed x time = 50/3 x 18. Step 3: Therefore, the length of the train is 300 m."
    }
]

RATIO_PROPORTION_PRACTICE_BANK = [
    {
        "q": "If A:B = 2:3 and B:C = 4:5, what is the ratio A:B:C?",
        "opts": ["A) 8:12:15", "B) 12:8:10", "C) 8:12:10", "D) 16:24:30"],
        "ans": 0,
        "exp": "Step 1: Make the common term B equal in both ratios. Step 2: Multiply 2:3 by 4 to get 8:12 and multiply 4:5 by 3 to get 12:15. Step 3: Therefore, A:B:C = 8:12:15."
    },
    {
        "q": "In a mixture of 45 litres, the ratio of milk to water is 4:1. How much water must be added to make the ratio 3:2?",
        "opts": ["A) 15 litres", "B) 10 litres", "C) 12 litres", "D) 18 litres"],
        "ans": 0,
        "exp": "Step 1: Milk = 4/5 of 45 = 36 litres and water = 9 litres. Step 2: Let x litres of water be added, so 36:(9 + x) = 3:2. Step 3: Solving gives 72 = 27 + 3x, so x = 15 litres."
    },
    {
        "q": "The ratio of ages of A and B is 3:4. If the sum of their ages is 28 years, what is the age of B?",
        "opts": ["A) 10 years", "B) 12 years", "C) 16 years", "D) 18 years"],
        "ans": 2,
        "exp": "Step 1: Total ratio parts = 3 + 4 = 7. Step 2: One part = 28 / 7 = 4. Step 3: Therefore, B's age = 4 x 4 = 16 years."
    },
    {
        "q": "A sum of money is divided between Ram and Shyam in the ratio 5:7. If Shyam gets Rs. 840, what is the total sum?",
        "opts": ["A) Rs. 1200", "B) Rs. 1320", "C) Rs. 1440", "D) Rs. 1560"],
        "ans": 2,
        "exp": "Step 1: Shyam's 7 parts equal Rs. 840, so 1 part = 840 / 7 = 120. Step 2: Total parts = 5 + 7 = 12. Step 3: Therefore, total sum = 12 x 120 = Rs. 1440."
    },
    {
        "q": "If 40% of a class are girls and the number of boys is 36, what is the total number of students in the class?",
        "opts": ["A) 54", "B) 60", "C) 72", "D) 90"],
        "ans": 1,
        "exp": "Step 1: If 40% are girls, then 60% are boys. Step 2: So 60% of the class = 36, which means total students = 36 x 100 / 60. Step 3: Therefore, the total number of students is 60."
    }
]

TIME_WORK_PRACTICE_BANK = [
    {
        "q": "A can complete a piece of work in 10 days and B can complete it in 15 days. In how many days will they finish the work together?",
        "opts": ["A) 5 days", "B) 6 days", "C) 7 days", "D) 8 days"],
        "ans": 1,
        "exp": "Step 1: A's one day work = 1/10 and B's one day work = 1/15. Step 2: Together, one day work = 1/10 + 1/15 = 1/6. Step 3: Therefore, they will finish the work in 6 days."
    },
    {
        "q": "A alone can finish a work in 12 days. B alone can finish the same work in 18 days. How much time will they take together?",
        "opts": ["A) 6.2 days", "B) 7.2 days", "C) 8 days", "D) 9 days"],
        "ans": 1,
        "exp": "Step 1: A's one day work = 1/12 and B's one day work = 1/18. Step 2: Together, one day work = 1/12 + 1/18 = 5/36. Step 3: Therefore, total time = 36/5 = 7.2 days."
    },
    {
        "q": "If 8 men can complete a work in 15 days, how many men are needed to complete the same work in 10 days?",
        "opts": ["A) 10", "B) 12", "C) 14", "D) 16"],
        "ans": 1,
        "exp": "Step 1: For the same work, men x days remains constant. Step 2: So required men = (8 x 15) / 10. Step 3: Therefore, 12 men are needed."
    },
    {
        "q": "12 workers can complete a job in 18 days. After 6 days, 6 more workers join them. In how many more days will the remaining work be completed?",
        "opts": ["A) 6 days", "B) 7 days", "C) 8 days", "D) 9 days"],
        "ans": 2,
        "exp": "Step 1: Total work = 12 x 18 = 216 worker-days. Step 2: Work done in first 6 days = 12 x 6 = 72, so remaining work = 144. Step 3: With 18 workers, time needed = 144 / 18 = 8 days."
    },
    {
        "q": "A can do a work in 20 days and B can do it in 30 days. If they work together for 5 days, what fraction of the work remains?",
        "opts": ["A) 1/6", "B) 1/4", "C) 5/12", "D) 7/12"],
        "ans": 3,
        "exp": "Step 1: Together, one day work = 1/20 + 1/30 = 1/12. Step 2: In 5 days they complete 5/12 of the work. Step 3: Therefore, remaining work = 1 - 5/12 = 7/12."
    }
]

NUMBER_SYSTEM_PRACTICE_BANK = [
    {
        "q": "What is the largest 4-digit number exactly divisible by 75?",
        "opts": ["A) 9975", "B) 9950", "C) 9900", "D) 9750"],
        "ans": 0,
        "exp": "Step 1: The largest 4-digit number is 9999. Step 2: 9999 divided by 75 leaves remainder 24. Step 3: Subtract 24 from 9999 to get 9975, so the answer is 9975."
    },
    {
        "q": "Find the HCF of 180 and 216.",
        "opts": ["A) 18", "B) 24", "C) 36", "D) 54"],
        "ans": 2,
        "exp": "Step 1: Use Euclid's method: 216 - 180 = 36. Step 2: 180 is exactly divisible by 36 and 216 is also divisible by 36. Step 3: Therefore, the HCF is 36."
    },
    {
        "q": "Simplify: 3/4 of 4/5 of 5/6 of 540.",
        "opts": ["A) 180", "B) 240", "C) 270", "D) 300"],
        "ans": 2,
        "exp": "Step 1: Cancel common factors in 3/4 x 4/5 x 5/6 x 540. Step 2: This becomes 3/6 x 540 = 1/2 x 540. Step 3: Therefore, the value is 270."
    },
    {
        "q": "What is the decimal form of 7/16?",
        "opts": ["A) 0.4375", "B) 0.375", "C) 0.4675", "D) 0.4175"],
        "ans": 0,
        "exp": "Step 1: To convert 7/16 into decimal, divide 7 by 16. Step 2: 16 goes into 70 four times and the decimal division continues to 0.4375. Step 3: Therefore, 7/16 = 0.4375."
    }
]

PROFIT_LOSS_INTEREST_PRACTICE_BANK = [
    {
        "q": "A shopkeeper buys an article for Rs. 800 and sells it for Rs. 920. What is the profit percentage?",
        "opts": ["A) 10%", "B) 12%", "C) 15%", "D) 20%"],
        "ans": 2,
        "exp": "Step 1: Profit = 920 - 800 = Rs. 120. Step 2: Profit percentage = 120 x 100 / 800. Step 3: Therefore, the profit percentage is 15%."
    },
    {
        "q": "What is the simple interest on Rs. 7000 at 5% per annum for 2 years?",
        "opts": ["A) Rs. 600", "B) Rs. 650", "C) Rs. 700", "D) Rs. 750"],
        "ans": 2,
        "exp": "Step 1: Simple interest = P x R x T / 100. Step 2: Substitute values: 7000 x 5 x 2 / 100. Step 3: Therefore, the simple interest is Rs. 700."
    },
    {
        "q": "What is the compound interest on Rs. 10000 at 10% per annum for 2 years compounded annually?",
        "opts": ["A) Rs. 2000", "B) Rs. 2100", "C) Rs. 2200", "D) Rs. 2300"],
        "ans": 1,
        "exp": "Step 1: Amount after 2 years = 10000 x 1.10 x 1.10 = 12100. Step 2: Compound interest = 12100 - 10000. Step 3: Therefore, the compound interest is Rs. 2100."
    },
    {
        "q": "An article is sold for Rs. 960 at a loss of 20%. What is its cost price?",
        "opts": ["A) Rs. 1000", "B) Rs. 1100", "C) Rs. 1200", "D) Rs. 1300"],
        "ans": 2,
        "exp": "Step 1: At 20% loss, selling price is 80% of cost price. Step 2: So 0.8 x cost price = 960. Step 3: Therefore, cost price = 960 / 0.8 = Rs. 1200."
    }
]

REASONING_PRACTICE_BANK = [
    {
        "q": "Pointing to a girl, Ravi said, 'She is the daughter of the only son of my mother.' How is the girl related to Ravi?",
        "opts": ["A) Sister", "B) Daughter", "C) Niece", "D) Cousin"],
        "ans": 1,
        "exp": "Step 1: The only son of Ravi's mother is Ravi himself. Step 2: So the girl is the daughter of Ravi. Step 3: Therefore, the girl is Ravi's daughter."
    },
    {
        "q": "If in a series each number increases by consecutive even numbers, what comes next: 2, 6, 12, 20, 30, ?",
        "opts": ["A) 42", "B) 40", "C) 44", "D) 46"],
        "ans": 0,
        "exp": "Step 1: The differences are 4, 6, 8 and 10. Step 2: The next difference should be 12. Step 3: Therefore, the next number is 30 + 12 = 42."
    },
    {
        "q": "Pointing to a photograph, Meena said, 'His brother's father is my grandfather's only son.' How is the man in the photograph related to Meena?",
        "opts": ["A) Brother", "B) Father", "C) Cousin", "D) Uncle"],
        "ans": 0,
        "exp": "Step 1: Meena's grandfather's only son is Meena's father. Step 2: So the father of the man's brother is Meena's father. Step 3: Therefore, the man is Meena's brother."
    },
    {
        "q": "Find the missing number in the series: 5, 10, 20, 40, ?",
        "opts": ["A) 60", "B) 70", "C) 80", "D) 90"],
        "ans": 2,
        "exp": "Step 1: Each term is double the previous term. Step 2: So after 40, the next term is 40 x 2. Step 3: Therefore, the missing number is 80."
    },
    {
        "q": "A is taller than B but shorter than C. D is shorter than B. Who is the tallest?",
        "opts": ["A) A", "B) B", "C) C", "D) D"],
        "ans": 2,
        "exp": "Step 1: From the statement, C is taller than A and A is taller than B. Step 2: D is shorter than B, so D is the shortest. Step 3: Therefore, C is the tallest."
    },
    {
        "q": "In a class of 30 students, Ravi secured the 7th rank. How many students ranked below him?",
        "opts": ["A) 21", "B) 22", "C) 23", "D) 24"],
        "ans": 2,
        "exp": "Step 1: Ravi is 7th, so 6 students are above him. Step 2: Students below him = total students - rank = 30 - 7. Step 3: Therefore, 23 students ranked below Ravi."
    },
    {
        "q": "If a person walks 10 meters east, then turns left and walks 10 meters, then turns left again and walks 10 meters, in which direction is the person from the starting point?",
        "opts": ["A) North", "B) South", "C) East", "D) West"],
        "ans": 0,
        "exp": "Step 1: The person first moves 10 meters east. Step 2: A left turn from east faces north, so the person moves 10 meters north. Step 3: A left turn from north faces west, and moving 10 meters west cancels the earlier east movement. Step 4: Therefore, the person is north of the starting point."
    },
    {
        "q": "Statements: All flowers are plants. Some plants are trees. Conclusions: I. Some flowers are trees. II. Some plants are flowers. Which conclusion follows?",
        "opts": ["A) Only I", "B) Only II", "C) Both I and II", "D) Neither I nor II"],
        "ans": 1,
        "exp": "Step 1: All flowers are plants, so some plants are definitely flowers. Step 2: Some plants are trees does not prove that flowers and trees overlap. Step 3: Therefore, only conclusion II follows."
    },
    {
        "q": "Find the odd one out: 17, 19, 23, 29, 33.",
        "opts": ["A) 17", "B) 19", "C) 33", "D) 23"],
        "ans": 2,
        "exp": "Step 1: Check whether each number is prime. Step 2: 17, 19, 23 and 29 are prime numbers, while 33 is divisible by 3 and 11. Step 3: Therefore, 33 is the odd one out."
    },
    {
        "q": "If 3rd March 2024 was a Sunday, what day was 10th March 2024?",
        "opts": ["A) Monday", "B) Saturday", "C) Sunday", "D) Friday"],
        "ans": 2,
        "exp": "Step 1: 10th March is exactly 7 days after 3rd March. Step 2: After 7 days, the day of the week remains the same. Step 3: Therefore, 10th March 2024 was also Sunday."
    },
    {
        "q": "At what angle are the hands of a clock at 3:00?",
        "opts": ["A) 60 degrees", "B) 75 degrees", "C) 90 degrees", "D) 120 degrees"],
        "ans": 2,
        "exp": "Step 1: At 3:00, the minute hand is at 12 and the hour hand is at 3. Step 2: Each hour mark represents 30 degrees. Step 3: The angle is 3 x 30 = 90 degrees."
    },
    {
        "q": "Complete the analogy: Doctor is to Hospital as Teacher is to?",
        "opts": ["A) Court", "B) School", "C) Bank", "D) Station"],
        "ans": 1,
        "exp": "Step 1: A doctor commonly works in a hospital. Step 2: A teacher commonly works in a school. Step 3: Therefore, Teacher is to School."
    },
    {
        "q": "A person faces north, turns right, then turns right again. Which direction is the person facing now?",
        "opts": ["A) North", "B) East", "C) South", "D) West"],
        "ans": 2,
        "exp": "Step 1: Facing north, a right turn makes the person face east. Step 2: Another right turn from east makes the person face south. Step 3: Therefore, the person is facing south."
    }
]

GENERAL_SCIENCE_PRACTICE_BANK = [
    {
        "q": "What is the SI unit of force?",
        "opts": ["A) Joule", "B) Newton", "C) Watt", "D) Pascal"],
        "ans": 1,
        "exp": "Step 1: Force is measured in the SI system. Step 2: The SI unit assigned to force is named after Isaac Newton. Step 3: Therefore, the SI unit of force is Newton."
    },
    {
        "q": "Which law explains why a body at rest remains at rest unless acted upon by an external force?",
        "opts": ["A) Newton's First Law", "B) Newton's Second Law", "C) Newton's Third Law", "D) Law of Gravitation"],
        "ans": 0,
        "exp": "Step 1: This question asks about inertia and rest. Step 2: Newton's First Law states that a body remains at rest or in uniform motion unless acted upon by an external force. Step 3: Therefore, the correct answer is Newton's First Law."
    },
    {
        "q": "Which gas is most abundant in the Earth's atmosphere?",
        "opts": ["A) Oxygen", "B) Carbon dioxide", "C) Nitrogen", "D) Hydrogen"],
        "ans": 2,
        "exp": "Step 1: The atmosphere contains several gases. Step 2: Nitrogen makes up the largest percentage, around 78 percent. Step 3: Therefore, nitrogen is the most abundant gas."
    },
    {
        "q": "What is the chemical formula of water?",
        "opts": ["A) CO2", "B) H2O", "C) O2", "D) H2SO4"],
        "ans": 1,
        "exp": "Step 1: Water is made of hydrogen and oxygen. Step 2: Two hydrogen atoms combine with one oxygen atom. Step 3: Therefore, the chemical formula is H2O."
    },
    {
        "q": "Which part of the plant prepares food by photosynthesis?",
        "opts": ["A) Root", "B) Stem", "C) Leaf", "D) Flower"],
        "ans": 2,
        "exp": "Step 1: Photosynthesis mainly occurs where chlorophyll is present. Step 2: Leaves contain chlorophyll and prepare food for the plant. Step 3: Therefore, the correct answer is leaf."
    },
    {
        "q": "Which vitamin is produced in the human body when skin is exposed to sunlight?",
        "opts": ["A) Vitamin A", "B) Vitamin B12", "C) Vitamin C", "D) Vitamin D"],
        "ans": 3,
        "exp": "Step 1: Sunlight helps the body synthesize a particular vitamin. Step 2: That vitamin is Vitamin D. Step 3: Therefore, the correct answer is Vitamin D."
    },
    {
        "q": "Which organ in the human body purifies blood?",
        "opts": ["A) Heart", "B) Kidney", "C) Lung", "D) Stomach"],
        "ans": 1,
        "exp": "Step 1: Blood filtration and removal of waste is the main function asked here. Step 2: Kidneys filter blood and remove waste as urine. Step 3: Therefore, the correct answer is kidney."
    },
    {
        "q": "Which force pulls objects toward the Earth?",
        "opts": ["A) Magnetic force", "B) Frictional force", "C) Gravitational force", "D) Electrostatic force"],
        "ans": 2,
        "exp": "Step 1: The Earth attracts objects toward its center. Step 2: This attraction is called gravity. Step 3: Therefore, the force is gravitational force."
    },
    {
        "q": "What happens to the boiling point of water at high altitude?",
        "opts": ["A) It increases", "B) It decreases", "C) It remains unchanged", "D) It becomes zero"],
        "ans": 1,
        "exp": "Step 1: At high altitude, atmospheric pressure is lower. Step 2: Lower pressure causes water to boil at a lower temperature. Step 3: Therefore, the boiling point decreases."
    },
    {
        "q": "Which metal is liquid at room temperature?",
        "opts": ["A) Iron", "B) Aluminium", "C) Mercury", "D) Copper"],
        "ans": 2,
        "exp": "Step 1: Most metals are solid at room temperature. Step 2: Mercury is the common metal that remains liquid at room temperature. Step 3: Therefore, the correct answer is mercury."
    },
    {
        "q": "Which blood cells help in clotting of blood?",
        "opts": ["A) Red blood cells", "B) White blood cells", "C) Platelets", "D) Plasma"],
        "ans": 2,
        "exp": "Step 1: Blood has different components with different functions. Step 2: Platelets help stop bleeding by forming clots. Step 3: Therefore, platelets help in clotting of blood."
    },
    {
        "q": "Which organ helps in pumping blood throughout the human body?",
        "opts": ["A) Liver", "B) Heart", "C) Kidney", "D) Lungs"],
        "ans": 1,
        "exp": "Step 1: The circulatory system depends on one muscular organ to push blood through the body. Step 2: That organ is the heart. Step 3: Therefore, the organ that pumps blood is the heart."
    },
    {
        "q": "Which layer of the atmosphere contains the ozone layer?",
        "opts": ["A) Troposphere", "B) Stratosphere", "C) Mesosphere", "D) Thermosphere"],
        "ans": 1,
        "exp": "Step 1: The ozone layer is located in one of the upper layers of the atmosphere. Step 2: It is found mainly in the stratosphere. Step 3: Therefore, the correct answer is stratosphere."
    },
    {
        "q": "Which part of the cell is known as the powerhouse of the cell?",
        "opts": ["A) Nucleus", "B) Ribosome", "C) Mitochondria", "D) Vacuole"],
        "ans": 2,
        "exp": "Step 1: Cells need energy to perform their functions. Step 2: Mitochondria release energy from food and are called the powerhouse of the cell. Step 3: Therefore, the correct answer is mitochondria."
    },
    {
        "q": "Which device is used to measure electric current?",
        "opts": ["A) Voltmeter", "B) Ammeter", "C) Barometer", "D) Thermometer"],
        "ans": 1,
        "exp": "Step 1: Different instruments are used to measure different physical quantities. Step 2: Electric current is measured using an ammeter. Step 3: Therefore, the correct answer is ammeter."
    },
    {
        "q": "What is the main source of energy for the Earth?",
        "opts": ["A) Moon", "B) Wind", "C) Sun", "D) Volcanoes"],
        "ans": 2,
        "exp": "Step 1: Most natural processes on Earth depend on one primary energy source. Step 2: That source is the Sun. Step 3: Therefore, the main source of energy for the Earth is the Sun."
    }
]

GA_HISTORY_PRACTICE_BANK = [
    {
        "q": "Who was the founder of the Maurya Empire?",
        "opts": ["A) Ashoka", "B) Chandragupta Maurya", "C) Bindusara", "D) Harshavardhana"],
        "ans": 1,
        "exp": "Step 1: The Maurya Empire was established in ancient India before Ashoka's rule. Step 2: Chandragupta Maurya founded the Maurya Empire. Step 3: Therefore, the correct answer is Chandragupta Maurya."
    },
    {
        "q": "In which year did the Revolt of 1857 begin?",
        "opts": ["A) 1856", "B) 1857", "C) 1858", "D) 1860"],
        "ans": 1,
        "exp": "Step 1: The First War of Independence is also called the Revolt of 1857. Step 2: It began in the year 1857. Step 3: Therefore, the correct answer is 1857."
    },
    {
        "q": "Who gave the call 'Do or Die' during the Indian freedom struggle?",
        "opts": ["A) Subhas Chandra Bose", "B) Jawaharlal Nehru", "C) Mahatma Gandhi", "D) Sardar Patel"],
        "ans": 2,
        "exp": "Step 1: 'Do or Die' is associated with the Quit India Movement. Step 2: This call was given by Mahatma Gandhi. Step 3: Therefore, the correct answer is Mahatma Gandhi."
    },
    {
        "q": "Which movement was launched by Mahatma Gandhi in 1942?",
        "opts": ["A) Non-Cooperation Movement", "B) Civil Disobedience Movement", "C) Quit India Movement", "D) Swadeshi Movement"],
        "ans": 2,
        "exp": "Step 1: The year 1942 is linked with a major freedom movement. Step 2: Gandhi launched the Quit India Movement in 1942. Step 3: Therefore, the correct answer is Quit India Movement."
    },
    {
        "q": "Who was the first President of independent India?",
        "opts": ["A) Dr. Rajendra Prasad", "B) Dr. S. Radhakrishnan", "C) Jawaharlal Nehru", "D) B. R. Ambedkar"],
        "ans": 0,
        "exp": "Step 1: After India became a republic, the first President was elected. Step 2: Dr. Rajendra Prasad became the first President of India. Step 3: Therefore, the correct answer is Dr. Rajendra Prasad."
    }
]

TIME_DISTANCE_PRACTICE_BANK = [
    {
        "q": "A train running at 60 km/hr crosses a pole in 18 seconds. What is the length of the train?",
        "opts": ["A) 300 meters", "B) 250 meters", "C) 200 meters", "D) 180 meters"],
        "ans": 0,
        "exp": "Step 1: Convert speed into m/s: 60 x 5 / 18 = 50 / 3 m/s. Step 2: Length = speed x time = (50 / 3) x 18. Step 3: Therefore, the length of the train is 300 meters."
    },
    {
        "q": "A train 200 meters long is running at 36 km/hr. In what time will it cross a bridge 100 meters long?",
        "opts": ["A) 20 seconds", "B) 25 seconds", "C) 30 seconds", "D) 35 seconds"],
        "ans": 2,
        "exp": "Step 1: Total distance = 200 + 100 = 300 meters. Step 2: Speed = 36 x 5 / 18 = 10 m/s. Step 3: Therefore, time = 300 / 10 = 30 seconds."
    },
    {
        "q": "If a man walks at 5 km/hr, how much distance will he cover in 2 hours 24 minutes?",
        "opts": ["A) 10 km", "B) 11 km", "C) 12 km", "D) 13 km"],
        "ans": 2,
        "exp": "Step 1: Convert 2 hours 24 minutes into hours: 2.4 hours. Step 2: Distance = speed x time = 5 x 2.4. Step 3: Therefore, the distance covered is 12 km."
    },
    {
        "q": "A car covers 150 km in 3 hours. What is its average speed?",
        "opts": ["A) 40 km/hr", "B) 45 km/hr", "C) 50 km/hr", "D) 55 km/hr"],
        "ans": 2,
        "exp": "Step 1: Average speed = total distance / total time. Step 2: Here, speed = 150 / 3. Step 3: Therefore, the average speed is 50 km/hr."
    },
    {
        "q": "A boat travels 30 km downstream in 2 hours. What is its downstream speed?",
        "opts": ["A) 12 km/hr", "B) 15 km/hr", "C) 18 km/hr", "D) 20 km/hr"],
        "ans": 1,
        "exp": "Step 1: Speed = distance / time. Step 2: Here, speed = 30 / 2. Step 3: Therefore, the downstream speed is 15 km/hr."
    }
]


# ================================================================
# MAIN HANDLER
# CHANGED: Added start_time tracking and meta in response
# ================================================================

def lambda_handler(event, context):
    # NEW: track how long the whole request takes
    start_time = time.time()

    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers(), "body": ""}

    try:
        raw_body = event.get("body")
        if isinstance(raw_body, (bytes, bytearray)):
            raw_body = raw_body.decode("utf-8", "ignore")

        if event.get("isBase64Encoded") and isinstance(raw_body, str):
            raw_body = base64.b64decode(raw_body).decode("utf-8", "ignore")

        if isinstance(raw_body, str) and raw_body.strip():
            body = json.loads(raw_body)
        elif isinstance(event, dict) and any(key in event for key in ["exam", "subject", "topic", "count", "mode", "difficulty"]):
            body = event
        else:
            body = {}

        exam = body.get("exam", "RRB NTPC")
        subject = body.get("subject", "Mathematics")
        topic = body.get("topic", "Percentage")
        count = int(body.get("count", 10))
        mode = body.get("mode", "practice")
        difficulty = body.get("difficulty", "medium")
        selected_chapters = body.get("selectedChapters", [])
        chapter_mode = body.get("chapterQuestionMode", "random_mix")
        drill_topics = body.get("drillTopics", [])
        exclude_questions = body.get("excludeQuestions", [])
        practice_type = body.get("practiceType", "topic-practice")

        pipeline_result = generate_validated_questions(
            exam=exam,
            subject=subject,
            topic=topic,
            count=count,
            mode=mode,
            difficulty=difficulty,
            selected_chapters=selected_chapters,
            chapter_mode=chapter_mode,
            drill_topics=drill_topics,
            exclude_questions=exclude_questions,
            practice_type=practice_type
        )

        questions = pipeline_result["questions"]
        if not questions:
            return error_response(pipeline_result["error"])

        elapsed = round(time.time() - start_time, 2)
        delivered = len(questions)

        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps({
                "questions": questions,
                # NEW: meta tells frontend exactly what happened
                "meta": {
                    "exam": exam,
                    "subject": subject,
                    "topic": topic,
                    "mode": mode,
                    "difficulty": difficulty,
                    "model": "Multi-Model-Router",
                    "requested": count,
                    "delivered": delivered,
                    "shortfall": count - delivered,       # 0 = perfect
                    "complete": delivered == count,        # true/false
                    "time_seconds": elapsed,
                    "errors": pipeline_result.get("errors", [])
                }
            })
        }

    except Exception as error:
        print(f"Lambda error: {error}")
        return error_response(str(error))


# ================================================================
# GENERATION PIPELINE
# ================================================================

# CHANGED: Fixed token math — old formula caused AI to truncate
# mid-response, losing 5-8 questions out of 10.
# Old: min(3200, 180*count+700) → 2500 for 10 questions (too low)
# New: min(6000, 300*count+800) → 3800 for 10 questions (enough)
def calculate_max_tokens(count, mode="", practice_type=""):
    normalized_mode = normalize_text(mode).lower()
    normalized_practice_type = normalize_text(practice_type).lower()
    requested_count = max(int(count), 1)

    if normalized_mode == "final-mock" or normalized_practice_type == "final-mock":
        return min(6000, 320 * requested_count + 1000)

    if normalized_mode in {"mock", "subject-test"} or normalized_practice_type in {"mock", "subject-test"}:
        return min(6000, 300 * requested_count + 800)

    return min(6000, 300 * requested_count + 800)


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_for_dedupe(value):
    lowered = normalize_text(value).lower()
    return lowered.translate(str.maketrans("", "", string.punctuation))


def load_question_bank_entries():
    global QUESTION_BANK_CACHE

    if QUESTION_BANK_CACHE is not None:
        return QUESTION_BANK_CACHE

    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "..", "frontend", "data", "question-bank.json"),
        os.path.join(os.path.dirname(__file__), "question-bank.json")
    ]

    for path in candidate_paths:
        normalized_path = os.path.normpath(path)
        if not os.path.exists(normalized_path):
            continue

        try:
            with open(normalized_path, "r", encoding="utf-8") as bank_file:
                QUESTION_BANK_CACHE = json.load(bank_file)
                return QUESTION_BANK_CACHE
        except Exception as error:
            print(f"question_bank_load_failed path={normalized_path} error={error}")

    QUESTION_BANK_CACHE = []
    return QUESTION_BANK_CACHE


def rotate_list(values, steps):
    if not values:
        return values

    offset = steps % len(values)
    return values[offset:] + values[:offset]


def interleave_lists(*lists):
    interleaved = []
    max_length = max((len(values) for values in lists if values), default=0)
    for index in range(max_length):
        for values in lists:
            if index < len(values):
                interleaved.append(values[index])
    return interleaved


def dedupe_signature(question):
    question_text = normalize_for_dedupe(question.get("q", ""))
    options = [normalize_for_dedupe(option) for option in question.get("opts", [])]
    return "|".join([question_text, *options])


def question_pattern_signature(question_text):
    normalized = normalize_text(question_text).lower()
    if "largest" in normalized and "digit" in normalized and "divisible" in normalized:
        return "pattern_largest_digit_divisible"
    compact = normalized.replace(" ", "")
    if "a:b" in compact and "b:c" in compact and "a:b:c" in compact:
        return "pattern_combined_ratio_abc"
    normalized = re.sub(r"\d+(?:\.\d+)?", "<n>", normalized)
    normalized = re.sub(
        r"\b(rs|rupees|km|cm|m|meters|metres|hours|hour|minutes|minute|days|day|percent|percentage)\b",
        "<u>",
        normalized
    )
    return normalize_for_dedupe(normalized)


def normalize_numeric_token(token):
    return normalize_text(token).replace(",", "")


def extract_numbers(text):
    matches = re.findall(r"-?\d[\d,]*(?:\.\d+)?", normalize_text(text))
    return [normalize_numeric_token(match) for match in matches]

def option_text_without_label(text):
    return re.sub(r"^\s*[A-D][\)\.\:\-]\s*", "", normalize_text(text), flags=re.IGNORECASE)


def explanation_has_enough_steps(explanation):
    steps = split_explanation_steps(explanation)
    return 3 <= len(steps) <= 6


def get_selected_option_label(question):
    return ["A", "B", "C", "D"][question["ans"]]


def split_explanation_steps(explanation):
    text = normalize_text(explanation)
    if not text:
        return []

    text = re.sub(r"\bRs\.\s*", "Rs ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bDr\.\s*", "Dr ", text, flags=re.IGNORECASE)
    text = re.sub(r"Step\s*\d+\s*:\s*", "", text, flags=re.IGNORECASE)
    parts = re.split(r"(?<=[.!?])\s+|\s*;\s*", text)
    return [part.strip(" -") for part in parts if part.strip(" -")]


def format_explanation_steps(steps):
    cleaned = []
    for step in steps:
        normalized = normalize_text(step).rstrip(".")
        if normalized:
            cleaned.append(normalized)

    if len(cleaned) < 3:
        return ""

    trimmed = cleaned[:6]
    return " ".join([f"Step {index + 1}: {step}." for index, step in enumerate(trimmed)])


def build_fallback_options(question_text):
    stem = normalize_text(question_text).rstrip(" ?.")
    if not stem:
        stem = "RRB topic"
    return [
        f"A) {stem} - option 1",
        f"B) {stem} - option 2",
        f"C) {stem} - option 3",
        f"D) {stem} - option 4"
    ]


def coerce_answer_index(answer_index, options):
    if isinstance(answer_index, bool):
        return 0

    if isinstance(answer_index, int):
        return max(0, min(answer_index, 3))

    if isinstance(answer_index, str):
        stripped = answer_index.strip().upper()
        if stripped.isdigit():
            numeric = int(stripped)
            if 0 <= numeric <= 3:
                return numeric
            if 1 <= numeric <= 4:
                return numeric - 1
        if stripped in ["A", "B", "C", "D"]:
            return ["A", "B", "C", "D"].index(stripped)
        for index, option in enumerate(options):
            if stripped and stripped in str(option).upper():
                return index

    return 0


def ensure_explanation(question_text, explanation, answer_index, options=None, trusted_bank=False):
    steps = split_explanation_steps(explanation)
    formatted = format_explanation_steps(steps)
    if formatted:
        return formatted

    if trusted_bank and normalize_text(explanation):
        answer_label = ["A", "B", "C", "D"][answer_index]
        answer_text = option_text_without_label((options or ["", "", "", ""])[answer_index])
        bank_steps = [
            f"Use the trusted bank explanation for this question: {normalize_text(explanation)}",
            f"Check the computed or stated result against the selected option value {answer_text}",
            f"Therefore, the correct answer is {answer_text}, which matches option {answer_label}"
        ]
        trusted_formatted = format_explanation_steps(bank_steps)
        if trusted_formatted:
            return trusted_formatted

    answer_label = ["A", "B", "C", "D"][answer_index]
    fallback_steps = [
        f"Read the question carefully and identify what is being asked in {question_text}",
        "Compare all four options and remove the choices that do not satisfy the requirement",
        f"Confirm that option {answer_label} is the correct answer after checking the final remaining choice"
    ]
    return format_explanation_steps(fallback_steps)


def subject_requires_numeric_alignment(subject, topic, question_text=""):
    combined = f"{subject} {topic} {question_text}".lower()
    numeric_keywords = [
        "math", "mathematics", "number system", "percentage", "ratio",
        "profit", "loss", "interest", "average", "time", "distance",
        "work", "algebra", "speed", "velocity", "acceleration", "force",
        "mass", "height", "gravity", "deceleration", "motion"
    ]
    return any(keyword in combined for keyword in numeric_keywords)


def is_high_risk_math_question(subject="", topic="", question_text=""):
    combined = f"{subject} {topic} {question_text}".lower()
    high_risk_keywords = [
        "ratio", "age", "ages", "work", "simple interest", "compound interest",
        "interest", "train", "distance", "equation", "piece of work"
    ]
    return ("math" in combined or "mathematics" in combined) and any(
        keyword in combined for keyword in high_risk_keywords
    )


def reasoning_is_high_risk(subject, topic):
    combined = f"{subject} {topic}".lower()
    risk_keywords = [
        "reasoning", "intelligence", "coding", "decoding", "code", "pattern",
        "series", "analogy", "ranking", "order", "blood", "relation",
        "direction", "syllogism"
    ]
    return any(keyword in combined for keyword in risk_keywords)


def is_coding_decoding_topic(subject="", topic="", selected_chapters=None, drill_topics=None):
    text_parts = [subject, topic] + list(selected_chapters or []) + list(drill_topics or [])
    combined = " ".join(normalize_text(part).lower() for part in text_parts if part)
    return "coding" in combined and "decoding" in combined


def split_planned_topic_names(topic=""):
    return [
        normalize_text(part)
        for part in re.split(r"[,;/|]+", normalize_text(topic))
        if normalize_text(part)
    ]


def is_dedicated_coding_decoding_request(subject="", topic="", selected_chapters=None, drill_topics=None):
    topic_names = []
    topic_names.extend(get_drill_topic_names(drill_topics))
    topic_names.extend(normalize_text(item) for item in (selected_chapters or []) if normalize_text(item))

    if not topic_names:
        topic_names = split_planned_topic_names(topic)

    if len(topic_names) != 1:
        return False

    normalized_topic = topic_names[0].lower()
    return "coding" in normalized_topic and "decoding" in normalized_topic


def is_percentage_topic(subject="", topic="", selected_chapters=None, drill_topics=None):
    text_parts = [subject, topic] + list(selected_chapters or []) + list(drill_topics or [])
    combined = " ".join(normalize_text(part).lower() for part in text_parts if part)
    return "math" in combined and "percentage" in combined


def should_use_percentage_bank_fallback(subject="", topic="", mode="", practice_type="", selected_chapters=None, drill_topics=None):
    if not is_percentage_topic(subject, topic, selected_chapters, drill_topics):
        return False

    normalized_mode = normalize_text(mode).lower()
    normalized_practice_type = normalize_text(practice_type).lower()
    normalized_topic = normalize_text(topic).lower()

    if normalized_mode == "practice" and normalized_practice_type in {"", "topic-practice"}:
        return normalized_topic == "percentage"

    if normalized_mode == "weak-drill" or normalized_practice_type == "weak-drill":
        normalized_drill_topics = [normalize_text(item).lower() for item in (drill_topics or [])]
        return any("percentage" in item for item in normalized_drill_topics)

    return False


def is_subject_test_flow(mode="", practice_type=""):
    normalized_mode = normalize_text(mode).lower()
    normalized_practice_type = normalize_text(practice_type).lower()
    return normalized_mode == "subject-test" or normalized_practice_type == "subject-test"


def is_weak_drill_flow(mode="", practice_type=""):
    normalized_mode = normalize_text(mode).lower()
    normalized_practice_type = normalize_text(practice_type).lower()
    return normalized_mode == "weak-drill" or normalized_practice_type == "weak-drill"


def get_drill_topic_names(drill_topics):
    topic_names = []
    for item in drill_topics or []:
        if isinstance(item, dict):
            topic_name = item.get("topic") or item.get("name") or item.get("subject")
        else:
            topic_name = item
        normalized = normalize_text(topic_name)
        if normalized:
            topic_names.append(normalized)
    return topic_names


def is_mixed_weak_drill(mode="", practice_type="", drill_topics=None):
    return is_weak_drill_flow(mode, practice_type) and len(get_drill_topic_names(drill_topics)) > 1


def get_weak_drill_batch_topics(drill_topics, batch_count, start_index=0):
    topic_names = get_drill_topic_names(drill_topics)
    if not topic_names or batch_count <= 0:
        return []
    rotated_topics = rotate_list(topic_names, start_index)
    selected_topics = []
    index = 0
    while len(selected_topics) < batch_count:
        selected_topics.append(rotated_topics[index % len(rotated_topics)])
        index += 1
    return selected_topics


def get_subject_test_topic_order(subject):
    normalized_subject = normalize_text(subject).lower()

    subject_alias_map = {
        "mathematics": "Mathematics",
        "math": "Mathematics",
        "general intelligence & reasoning": "General Intelligence & Reasoning",
        "reasoning": "General Intelligence & Reasoning",
        "mental ability & reasoning": "General Intelligence & Reasoning",
        "mental ability": "General Intelligence & Reasoning",
        "general awareness": "General Awareness",
        "general awareness & current affairs": "General Awareness",
        "current affairs & general awareness": "General Awareness",
        "current affairs": "General Awareness",
        "general science": "General Science",
        "physics & chemistry": "General Science"
    }

    resolved_subject = subject_alias_map.get(normalized_subject, subject)

    if resolved_subject == "General Science":
        science_data = RRB_SYLLABUS.get("General Science", {})
        return interleave_lists(
            science_data.get("Physics", []),
            science_data.get("Chemistry", []),
            science_data.get("Biology", [])
        )

    subject_data = RRB_SYLLABUS.get(resolved_subject, {})
    if isinstance(subject_data, dict) and "subtopics" in subject_data:
        return list(subject_data.get("subtopics", []))

    return []


def get_subject_test_batch_topics(subject, batch_count, start_index=0):
    topic_order = get_subject_test_topic_order(subject)
    if not topic_order or batch_count <= 0:
        return []

    rotated_topics = rotate_list(topic_order, start_index)
    selected_topics = []
    index = 0
    while len(selected_topics) < batch_count:
        selected_topics.append(rotated_topics[index % len(rotated_topics)])
        index += 1

    return selected_topics


def is_practice_flow(mode="", practice_type=""):
    normalized_mode = normalize_text(mode).lower()
    normalized_practice_type = normalize_text(practice_type).lower()
    practice_mode_values = {
        "practice", "topic-practice", "chapter-practice", "weak-drill",
        "subject-test", "mock", "previous-year", "final-mock"
    }
    return normalized_mode in practice_mode_values or normalized_practice_type in practice_mode_values


def score_question_bank_entry(entry, exam, subject, topic):
    score = 0
    entry_exam = normalize_for_dedupe(entry.get("exam", ""))
    entry_subject = normalize_for_dedupe(entry.get("subject", ""))
    entry_topic = normalize_for_dedupe(entry.get("topic", ""))
    requested_exam = normalize_for_dedupe(exam)
    requested_subject = normalize_for_dedupe(subject)
    requested_topic = normalize_for_dedupe(topic)

    if entry_exam and entry_exam == requested_exam:
        score += 2
    if entry_subject and entry_subject == requested_subject:
        score += 3
    if requested_topic in {"", "all topics", "all"}:
        if entry_subject == requested_subject:
            score += 1
        return score
    if entry_topic == requested_topic:
        score += 5
    elif requested_topic and (requested_topic in entry_topic or entry_topic in requested_topic):
        score += 2

    return score


def to_bank_question(entry):
    return {
        "q": entry.get("question", ""),
        "opts": entry.get("options", []),
        "ans": entry.get("answer", 0),
        "exp": entry.get("explanation", "")
    }


def extract_final_numeric_candidates(explanation):
    lowered = normalize_text(explanation).lower()
    patterns = [
        r"(?:therefore|hence|thus|so|final answer is|answer is|correct answer is)\s*(?:rs\.?\s*)?(-?\d[\d,]*(?:\.\d+)?)",
        r"(?:younger person's age is|cost price is|net percentage change is|distance is|length is|principal is)\s*(?:rs\.?\s*)?(-?\d[\d,]*(?:\.\d+)?)",
        r"=\s*(?:rs\.?\s*)?(-?\d[\d,]*(?:\.\d+)?)\s*$"
    ]

    candidates = []
    for pattern in patterns:
        matches = re.findall(pattern, lowered)
        candidates.extend(normalize_numeric_token(match) for match in matches)

    return candidates


def extract_equation_result_candidates(explanation):
    tokens = re.findall(r"=\s*(?:rs\.?\s*)?(-?\d[\d,]*(?:/\d[\d,]*)?(?:\.\d+)?)", normalize_text(explanation).lower())
    return [normalize_numeric_token(token) for token in tokens]


def extract_code_example_pair(question_text):
    text = normalize_text(question_text)
    patterns = [
        r"'([A-Z]+)'\s+is\s+written\s+as\s+'([A-Z0-9]+)'",
        r"'([A-Z]+)'\s+is\s+coded\s+as\s+'([A-Z0-9]+)'"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper(), match.group(2).upper()

    return "", ""


def extract_target_code_word(question_text):
    text = normalize_text(question_text)
    patterns = [
        r"how\s+(?:is|will)\s+'([A-Z]+)'",
        r"then\s+how\s+(?:is|will)\s+'([A-Z]+)'"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    quoted_words = re.findall(r"'([A-Z]+)'", text, flags=re.IGNORECASE)
    return quoted_words[-1].upper() if len(quoted_words) >= 3 else ""


def extract_final_code_candidate(explanation):
    text = normalize_text(explanation)
    patterns = [
        r"coded\s+as\s+'?([A-Z0-9]+)'?",
        r"written\s+as\s+'?([A-Z0-9]+)'?",
        r"therefore,\s*'?[A-Z]+'?\s+is\s+(?:coded|written)\s+as\s+'?([A-Z0-9]+)'?",
        r"therefore,\s*'?[A-Z]+'?\s*=\s*'?([A-Z0-9]+)'?"
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return candidates[-1].upper() if candidates else ""


def shift_alpha_letter(character, offset):
    if not ("A" <= character <= "Z"):
        return character
    return chr(((ord(character) - ord("A") + offset) % 26) + ord("A"))


def encode_word_by_shift(word, offset=1):
    return "".join(shift_alpha_letter(character, offset) for character in word.upper() if "A" <= character <= "Z")


def detect_uniform_alpha_shift(source_word, sample_code):
    source = re.sub(r"[^A-Z]", "", normalize_text(source_word).upper())
    code = re.sub(r"[^A-Z]", "", normalize_text(sample_code).upper())
    if not source or len(source) != len(code):
        return None
    offsets = [((ord(encoded) - ord(original)) % 26) for original, encoded in zip(source, code)]
    if len(set(offsets)) != 1:
        return None
    return offsets[0]


def mutate_code_variant(code, index, delta):
    characters = list(code)
    if not characters:
        return code
    target_index = index % len(characters)
    characters[target_index] = shift_alpha_letter(characters[target_index], delta)
    return "".join(characters)


def format_bank_explanation(base_explanation, selected_code, answer_label):
    base_text = normalize_text(base_explanation).rstrip(".")
    return format_explanation_steps([
        "Use the same coding rule shown in the example pair",
        base_text,
        f"Therefore, the required code is {selected_code}, which matches option {answer_label}"
    ])


def build_coding_decoding_bank_questions(count, exclude_questions=None):
    questions = []
    seen_signatures = set()
    seen_questions = {normalize_for_dedupe(item) for item in (exclude_questions or [])}
    rotation_seed = 0
    word_count = len(CODING_DECODE_WORD_BANK)

    for index in range(word_count * 2):
        if len(questions) >= count:
            break

        sample_word = CODING_DECODE_WORD_BANK[index % word_count]
        target_word = CODING_DECODE_WORD_BANK[(index * 3 + 5) % word_count]
        if target_word == sample_word:
            target_word = CODING_DECODE_WORD_BANK[(index * 3 + 6) % word_count]

        sample_code = encode_word_by_shift(sample_word, 1)
        target_code = encode_word_by_shift(target_word, 1)

        question_text = (
            f"If in a certain code '{sample_word}' is written as '{sample_code}' by moving each letter "
            f"one step forward alphabetically, how will '{target_word}' be written in the same code?"
        )
        normalized_question = normalize_for_dedupe(question_text)
        if normalized_question in seen_questions:
            continue

        raw_codes = [
            target_code,
            mutate_code_variant(target_code, 0, 1),
            mutate_code_variant(target_code, 1, -1),
            mutate_code_variant(target_code, len(target_code) - 1, 1)
        ]

        unique_codes = []
        for code in raw_codes:
            if code not in unique_codes:
                unique_codes.append(code)

        if len(unique_codes) < 4:
            continue

        rotated_codes = rotate_list(unique_codes[:4], rotation_seed)
        answer_index = rotated_codes.index(target_code)
        answer_label = ["A", "B", "C", "D"][answer_index]
        options = [f"{label}) {code}" for label, code in zip(["A", "B", "C", "D"], rotated_codes)]
        explanation = format_bank_explanation(
            f"Apply the same +1 alphabet shift to {target_word}: "
            + ", ".join(
                f"{character}->{shift_alpha_letter(character, 1)}"
                for character in target_word
            ),
            target_code,
            answer_label
        )

        candidate = {
            "q": question_text,
            "opts": options,
            "ans": answer_index,
            "exp": explanation
        }

        signature = dedupe_signature(candidate)
        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        seen_questions.add(normalized_question)
        questions.append(candidate)
        rotation_seed += 1

    return questions


def build_percentage_bank_questions(count, exclude_questions=None, existing_questions=None):
    questions = []
    seen_signatures = {dedupe_signature(question) for question in (existing_questions or [])}
    seen_questions = {normalize_for_dedupe(item) for item in (exclude_questions or [])}

    for candidate in PERCENTAGE_PRACTICE_BANK:
        if len(questions) >= count:
            break
        normalized_question = normalize_for_dedupe(candidate["q"])
        if normalized_question in seen_questions:
            continue
        signature = dedupe_signature(candidate)
        if signature in seen_signatures:
            continue
        seen_questions.add(normalized_question)
        seen_signatures.add(signature)
        questions.append(dict(candidate))

    return questions


def build_local_practice_bank_questions(bank, count, exclude_questions=None, existing_questions=None):
    questions = []
    seen_signatures = {dedupe_signature(question) for question in (existing_questions or [])}
    seen_questions = {normalize_for_dedupe(item) for item in (exclude_questions or [])}
    seen_concepts = {final_concept_signature(question) for question in (existing_questions or [])}

    for candidate in bank:
        if len(questions) >= count:
            break
        normalized_question = normalize_for_dedupe(candidate["q"])
        if normalized_question in seen_questions:
            continue
        signature = dedupe_signature(candidate)
        concept_signature = final_concept_signature(candidate)
        if signature in seen_signatures or concept_signature in seen_concepts:
            continue
        seen_questions.add(normalized_question)
        seen_signatures.add(signature)
        seen_concepts.add(concept_signature)
        questions.append(dict(candidate))

    return questions


def build_topic_bank_questions(exam, subject, topic, count, exclude_questions=None, existing_questions=None):
    bank_entries = load_question_bank_entries()
    if not bank_entries:
        return []

    questions = []
    seen_signatures = {dedupe_signature(question) for question in (existing_questions or [])}
    seen_questions = {normalize_for_dedupe(item) for item in (exclude_questions or [])}

    ranked_entries = sorted(
        (
            (score_question_bank_entry(entry, exam, subject, topic), entry)
            for entry in bank_entries
        ),
        key=lambda item: (item[0], item[1].get("year", 0)),
        reverse=True
    )

    for score, entry in ranked_entries:
        if len(questions) >= count:
            break
        if score <= 0:
            continue
        candidate = to_bank_question(entry)
        normalized_question = normalize_for_dedupe(candidate["q"])
        if normalized_question in seen_questions:
            continue
        signature = dedupe_signature(candidate)
        if signature in seen_signatures:
            continue
        seen_questions.add(normalized_question)
        seen_signatures.add(signature)
        questions.append(candidate)

    return questions


def build_subject_bank_questions(exam, subject, count, exclude_questions=None, existing_questions=None, preferred_topics=None):
    bank_entries = load_question_bank_entries()
    if not bank_entries:
        return []

    preferred_topic_tokens = [
        normalize_for_dedupe(topic_name)
        for topic_name in (preferred_topics or [])
        if normalize_for_dedupe(topic_name)
    ]

    questions = []
    seen_signatures = {dedupe_signature(question) for question in (existing_questions or [])}
    seen_questions = {normalize_for_dedupe(item) for item in (exclude_questions or [])}
    requested_exam = normalize_for_dedupe(exam)
    requested_subject = normalize_for_dedupe(subject)

    ranked_entries = []
    for entry in bank_entries:
        entry_exam = normalize_for_dedupe(entry.get("exam", ""))
        entry_subject = normalize_for_dedupe(entry.get("subject", ""))
        if entry_subject != requested_subject:
            continue
        entry_topic = normalize_for_dedupe(entry.get("topic", ""))
        score = 0
        if entry_exam == requested_exam:
            score += 3
        if entry_subject == requested_subject:
            score += 3
        if preferred_topic_tokens and any(token and (token in entry_topic or entry_topic in token) for token in preferred_topic_tokens):
            score += 4
        ranked_entries.append((score, entry))

    ranked_entries.sort(key=lambda item: (item[0], item[1].get("year", 0)), reverse=True)

    for score, entry in ranked_entries:
        if len(questions) >= count:
            break
        if score <= 0:
            continue
        candidate = to_bank_question(entry)
        normalized_question = normalize_for_dedupe(candidate["q"])
        if normalized_question in seen_questions:
            continue
        signature = dedupe_signature(candidate)
        if signature in seen_signatures:
            continue
        seen_questions.add(normalized_question)
        seen_signatures.add(signature)
        questions.append(candidate)

    return questions


def alphabetical_position_code(word):
    return "".join(str(ord(character) - 64) for character in word if "A" <= character <= "Z")


def explanation_claims_direct_alphabet_code(explanation):
    lowered = normalize_text(explanation).lower()
    if re.search(r"\b[A-Z]\s*=\s*\d{1,2}\b", normalize_text(explanation)):
        return True
    claim_markers = [
        "alphabetical position", "positional value in the alphabet",
        "position in the alphabet", "letter is replaced by its positional value",
        "letter is replaced by its alphabetical position"
    ]
    return any(marker in lowered for marker in claim_markers)


def text_claims_direct_alphabet_code(text):
    lowered = normalize_text(text).lower()
    return (
        explanation_claims_direct_alphabet_code(text)
        or "based on the position of the letters" in lowered
        or "position of the letters in the english alphabet" in lowered
    )


def explanation_has_final_conclusion(explanation):
    lowered = normalize_text(explanation).lower()
    final_markers = [
        "therefore", "hence", "thus", "so,", "so ", "so the correct answer",
        "final answer", "answer is", "correct answer is"
    ]
    return any(marker in lowered for marker in final_markers)


def explanation_is_generic_template(explanation):
    lowered = normalize_text(explanation).lower()
    generic_patterns = [
        "read the question carefully", "identify what is being asked",
        "compare all four options", "remove the choices",
        "confirm that option", "final remaining choice"
    ]
    return any(pattern in lowered for pattern in generic_patterns)


def explanation_has_revision_language(explanation):
    lowered = normalize_text(explanation).lower()
    revision_patterns = [
        "however", "assuming", "assume that", "recheck", "re-evaluating",
        "reevaluating", "correcting", "fits better", "plausible",
        "closest plausible", "closest answer", "closest given option",
        "can be inferred", "match the pattern", "rounds to", "closest option",
        "options provided", "minor calculation difference", "question design",
        "commonly used principal"
    ]
    return any(pattern in lowered for pattern in revision_patterns)


def explanation_has_incomplete_numeric_formatting(explanation):
    lowered = normalize_text(explanation).lower()
    incomplete_patterns = [
        r"rs\.\s*(?:step\s*\d+|$)",
        r"=\s*(?:rs\.)?\s*$"
    ]
    return any(re.search(pattern, lowered) for pattern in incomplete_patterns)


def explanation_has_unstable_equation_chain(explanation):
    for step in split_explanation_steps(explanation):
        if step.count("=") >= 4:
            return True
    return False


def has_conflicting_final_numeric_candidates(question, explanation):
    selected_option = question["opts"][question["ans"]]
    option_numbers = set(extract_numbers(option_text_without_label(selected_option)))
    final_candidates = {candidate for candidate in extract_final_numeric_candidates(explanation)}
    if not final_candidates:
        return False
    return final_candidates.isdisjoint(option_numbers)


def has_mismatched_computed_final_value(question, explanation):
    selected_option = question["opts"][question["ans"]]
    option_numbers = set(extract_numbers(option_text_without_label(selected_option)))
    equation_results = extract_equation_result_candidates(explanation)
    if not equation_results:
        return False
    last_result_numbers = set(extract_numbers(equation_results[-1]))
    if not last_result_numbers:
        return False
    return last_result_numbers.isdisjoint(option_numbers)


SAFE_ARITHMETIC_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos
}


def safe_eval_arithmetic_expression(expression):
    parsed = ast.parse(expression, mode="eval")

    def eval_node(node):
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in SAFE_ARITHMETIC_OPERATORS:
            left = eval_node(node.left)
            right = eval_node(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("division by zero")
            return SAFE_ARITHMETIC_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_ARITHMETIC_OPERATORS:
            return SAFE_ARITHMETIC_OPERATORS[type(node.op)](eval_node(node.operand))
        raise ValueError("unsupported arithmetic expression")

    return eval_node(parsed)


def extract_simplify_expression(question_text):
    text = normalize_text(question_text)
    match = re.search(r"simplify\s*:?\s*(.+?)(?:\?|$)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    expression = match.group(1).strip()
    if not re.fullmatch(r"[0-9\.\s\+\-\*\/\(\)]+", expression):
        return ""
    return expression


def has_mismatched_simplify_answer(question):
    expression = extract_simplify_expression(question.get("q", ""))
    if not expression:
        return False

    try:
        computed_value = safe_eval_arithmetic_expression(expression)
    except Exception:
        return False

    selected_option = question["opts"][question["ans"]]
    option_numbers = extract_numbers(option_text_without_label(selected_option))
    if not option_numbers:
        return False

    for option_number in option_numbers:
        try:
            if abs(float(option_number.replace(",", "")) - computed_value) <= 0.001:
                return False
        except ValueError:
            continue

    return True


def has_invalid_ratio_solution(question):
    text = normalize_text(f"{question.get('q', '')} {question.get('exp', '')}").lower()
    if "ratio" not in text:
        return False

    if re.search(r"\bx\s*=\s*-\d", text):
        return True

    if "smaller number" in text or "larger number" in text or "numbers be" in text:
        selected_option = question["opts"][question["ans"]]
        selected_numbers = [float(number.replace(",", "")) for number in extract_numbers(option_text_without_label(selected_option))]
        if selected_numbers and any(number <= 0 for number in selected_numbers):
            return True
        if re.search(r"\d+x\s*=\s*\d+\s*\(-\d", text):
            return True

    return False


def lcm_numbers(values):
    result = 1
    for value in values:
        result = abs(result * value) // math.gcd(result, value)
    return result


def has_invalid_same_remainder_lcm_answer(question):
    question_text = normalize_text(question.get("q", "")).lower()
    if "divided by" not in question_text or "remainder" not in question_text:
        return False

    divisor_match = re.search(r"divided\s+by\s+(.+?)\s+leaves?", question_text)
    remainder_match = re.search(
        r"leaves?\s+(?:a\s+)?remainders?\s+(?:of\s+)?(\d+)|remainders?\s+of\s+(\d+)",
        question_text
    )
    if not divisor_match or not remainder_match:
        return False

    divisors = [int(number) for number in re.findall(r"\d+", divisor_match.group(1))]
    remainder = int(next(group for group in remainder_match.groups() if group))
    if len(divisors) < 2:
        return False

    selected_numbers = [int(number) for number in selected_option_numbers(question)]
    option_numbers = [
        int(number)
        for option in question.get("opts", [])
        for number in extract_numbers(option_text_without_label(option))
    ]
    if not selected_numbers or not option_numbers:
        return False

    base_lcm = lcm_numbers(divisors)
    expected = base_lcm + remainder if min(option_numbers) > max(divisors) else remainder
    return selected_numbers[0] != expected


def selected_option_numbers(question):
    selected_option = question["opts"][question["ans"]]
    return [
        float(number.replace(",", ""))
        for number in extract_numbers(option_text_without_label(selected_option))
    ]


def has_invalid_ranking_answer(question):
    text = normalize_text(question.get("q", "")).lower()
    if "interchange" in text and "from the left" in text and "from the right" in text:
        left_positions = [int(value) for value in re.findall(r"(\d+)(?:st|nd|rd|th)?\s+from\s+the\s+left", text)]
        right_positions = [int(value) for value in re.findall(r"(\d+)(?:st|nd|rd|th)?\s+from\s+the\s+right", text)]
        if len(left_positions) >= 2 and right_positions:
            expected_total = left_positions[-1] + right_positions[0] - 1
            return expected_total not in [int(number) for number in selected_option_numbers(question)]

    if "rank" not in text or "from the bottom" not in text or "from the top" not in text:
        return False

    total_match = re.search(r"(?:class|row|group)\s+of\s+(\d+)", text)
    rank_match = re.search(r"rank(?:s|ed)?\s+(\d+)(?:st|nd|rd|th)?\s+from\s+the\s+top", text)
    if not total_match or not rank_match:
        return False

    total = int(total_match.group(1))
    top_rank = int(rank_match.group(1))
    expected_rank = total - top_rank + 1
    return expected_rank not in [int(number) for number in selected_option_numbers(question)]


def extract_series_numbers(question_text):
    text = normalize_text(question_text)
    match = re.search(r"(?:series|next|missing number)[^:]*:\s*([0-9,\s\-]+)\?", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r":\s*([0-9,\s\-]+),\s*\?", text)
    if not match:
        return []
    return [int(number) for number in re.findall(r"-?\d+", match.group(1))]


def predicted_next_series_value(numbers):
    if len(numbers) < 4:
        return None

    differences = [numbers[index + 1] - numbers[index] for index in range(len(numbers) - 1)]
    if len(differences) >= 2:
        second_differences = [differences[index + 1] - differences[index] for index in range(len(differences) - 1)]
        if second_differences and len(set(second_differences)) == 1:
            return numbers[-1] + differences[-1] + second_differences[-1]
        if len(set(differences)) == 1:
            return numbers[-1] + differences[-1]

    if all(number != 0 for number in numbers[:-1]):
        ratios = [numbers[index + 1] / numbers[index] for index in range(len(numbers) - 1)]
        if len(set(ratios)) == 1:
            return int(numbers[-1] * ratios[-1])
        ratio_steps = [ratios[index + 1] - ratios[index] for index in range(len(ratios) - 1)]
        if ratio_steps and len(set(ratio_steps)) == 1 and all(float(ratio).is_integer() for ratio in ratios):
            return int(numbers[-1] * (ratios[-1] + ratio_steps[-1]))

    return None


def has_invalid_number_series_answer(question):
    text = normalize_text(question.get("q", "")).lower()
    if "series" not in text and "missing number" not in text:
        return False

    numbers = extract_series_numbers(question.get("q", ""))
    expected_value = predicted_next_series_value(numbers)
    if expected_value is None:
        return False

    selected_numbers = [int(number) for number in selected_option_numbers(question)]
    return expected_value not in selected_numbers


def has_invalid_odd_one_out_answer(question):
    question_text = normalize_text(question.get("q", ""))
    explanation = normalize_text(question.get("exp", "")).lower()
    if "odd one out" not in question_text.lower():
        return False

    question_numbers = [int(number) for number in extract_numbers(question_text)]
    selected_numbers = [int(number) for number in selected_option_numbers(question)]
    if not question_numbers or not selected_numbers:
        return False

    selected_number = selected_numbers[0]
    other_numbers = [number for number in question_numbers if number != selected_number]

    if "multiple of 5" in explanation:
        if selected_number % 5 == 0 and all(number % 5 == 0 for number in other_numbers):
            return True

    if "even" in explanation and "odd" in explanation:
        selected_parity = selected_number % 2
        if other_numbers and all(number % 2 == selected_parity for number in other_numbers):
            return True

    return False


def has_invalid_simple_direction_answer(question):
    question_text = normalize_text(question.get("q", "")).lower()
    if "walk" not in question_text or "direction" not in question_text:
        return False

    compact = re.sub(r"\s+", " ", question_text)
    if not (
        "towards the east" in compact
        and compact.count("turns left") >= 2
        and re.search(r"10\s+meters?", compact)
    ):
        return False

    selected_option = option_text_without_label(question["opts"][question["ans"]]).lower()
    if "east" in selected_option or "west" in selected_option or "south" in selected_option:
        return True
    return "north" not in selected_option


def has_invalid_blood_relation_answer(question):
    normalized_question = normalize_text(question.get("q", "")).lower()
    selected_answer_text = option_text_without_label(question["opts"][question["ans"]]).lower()
    if "her only brother is the father of my son" in normalized_question and "uncle" in normalized_question:
        return "aunt" not in selected_answer_text
    text = normalize_text(question.get("q", "")).lower().replace("’", "'")
    selected_option = option_text_without_label(question["opts"][question["ans"]]).lower()

    if "her only brother is the father of my son's uncle" in text:
        return "aunt" not in selected_option

    if "her only brother is the father of my son" in text and "sister" in text:
        return False

    return False


def explanation_supports_numeric_answer(question, explanation):
    selected_option = question["opts"][question["ans"]]
    option_numbers = extract_numbers(option_text_without_label(selected_option))
    if not option_numbers:
        return False
    final_candidates = extract_final_numeric_candidates(explanation)
    if final_candidates:
        return any(option_number in final_candidates for option_number in option_numbers)
    explanation_numbers = extract_numbers(explanation)
    return any(option_number in explanation_numbers for option_number in option_numbers)


def explanation_has_numeric_solution_steps(explanation):
    lowered = normalize_text(explanation).lower()
    numbers = extract_numbers(lowered)
    solution_markers = ["=", "formula", "using", "calculate", "rearranging", "substituting", "convert", "becomes"]
    return len(numbers) >= 3 and any(marker in lowered for marker in solution_markers)


def explanation_supports_non_numeric_answer(question, explanation):
    selected_option = question["opts"][question["ans"]]
    selected_body = option_text_without_label(selected_option).lower()
    selected_label = get_selected_option_label(question).lower()
    explanation_lower = normalize_text(explanation).lower()

    explicit_label_patterns = [
        rf"\boption\s+{selected_label}\b",
        rf"\b{selected_label}\s+is correct\b",
        rf"\bcorrect answer is\s+{selected_label}\b"
    ]
    if any(re.search(pattern, explanation_lower) for pattern in explicit_label_patterns) and explanation_has_final_conclusion(explanation):
        return True
    if selected_body and selected_body in explanation_lower and explanation_has_final_conclusion(explanation):
        return True
    return False


def explanation_supports_selected_option(question, subject="", topic=""):
    explanation = normalize_text(question["exp"])
    if not explanation:
        return False
    if subject_requires_numeric_alignment(subject, topic, question["q"]):
        return explanation_supports_numeric_answer(question, explanation)
    if reasoning_is_high_risk(subject, topic):
        return explanation_supports_non_numeric_answer(question, explanation)
    return explanation_supports_non_numeric_answer(question, explanation)


def explanation_contradicts_selected_option(question):
    selected_label = ["A", "B", "C", "D"][question["ans"]]
    explanation = normalize_text(question["exp"]).lower()

    for index, option in enumerate(question["opts"]):
        option_label = ["A", "B", "C", "D"][index]
        if option_label == selected_label:
            continue
        option_body = option_text_without_label(option).lower()
        if re.search(rf"\boption\s+{option_label.lower()}\b", explanation):
            return True
        if option_body and option_body in explanation and option_body != option_text_without_label(question["opts"][question["ans"]]).lower():
            return True
    return False


def explanation_has_award_or_medal_mismatch(question):
    question_text = normalize_text(question.get("q", "")).lower()
    explanation = normalize_text(question.get("exp", "")).lower()
    selected_option = option_text_without_label(question["opts"][question["ans"]]).lower()

    question_terms = {
        "gold": ["silver", "bronze"],
        "silver": ["gold", "bronze"],
        "bronze": ["gold", "silver"],
    }
    for expected_term, conflicting_terms in question_terms.items():
        if expected_term in question_text and any(term in explanation for term in conflicting_terms):
            return True

    if "bharat ratna" in question_text and "2019" in question_text:
        known_2019_recipients = ["pranab mukherjee", "nanaji deshmukh", "bhupen hazarika"]
        if selected_option not in known_2019_recipients:
            return True

    return False


def is_confidently_bad_reasoning(question, subject="", topic=""):
    if not reasoning_is_high_risk(subject, topic):
        return False
    explanation = normalize_text(question["exp"]).lower()
    bad_signals = [
        "assume", "probably", "guess", "seems", "may be", "might be",
        "pattern unclear", "use given", "following the given pattern"
    ]
    return any(signal in explanation for signal in bad_signals)
def has_invalid_syllogism_overlap_inference(question):
    question_text = normalize_text(question.get("q", "")).lower()
    selected_option = option_text_without_label(question["opts"][question["ans"]]).lower()
    explanation = normalize_text(question.get("exp", "")).lower()

    if "all pens are pencils" in question_text and "some pencils are erasers" in question_text:
        if "some pens are erasers" in selected_option:
            return True
        if "some pens are erasers" in explanation:
            return True

    if "all flowers are plants" in question_text and "some plants are trees" in question_text:
        if "some flowers are trees" in selected_option:
            return True
        if "some flowers are trees" in explanation:
            return True

    return False


def reasoning_pattern_is_consistent(question, subject="", topic=""):
    if not reasoning_is_high_risk(subject, topic):
        return True
    explanation = normalize_text(question["exp"])
    if not explanation:
        return False
    if not explanation_supports_non_numeric_answer(question, explanation):
        return False
    if explanation_claims_direct_alphabet_code(explanation) or text_claims_direct_alphabet_code(question["q"]):
        source_word, sample_code = extract_code_example_pair(question["q"])
        if source_word and sample_code:
            expected_code = alphabetical_position_code(source_word)
            if expected_code != sample_code:
                return False
        target_word_for_direct_code = extract_target_code_word(question["q"])
        if target_word_for_direct_code:
            selected_direct_code = option_text_without_label(question["opts"][question["ans"]]).upper()
            if alphabetical_position_code(target_word_for_direct_code) != selected_direct_code:
                return False
    source_word, sample_code = extract_code_example_pair(question["q"])
    target_word = extract_target_code_word(question["q"])
    selected_body = option_text_without_label(question["opts"][question["ans"]]).upper()
    final_code_candidate = extract_final_code_candidate(explanation)
    if final_code_candidate and target_word and selected_body != final_code_candidate:
        return False
    if source_word and sample_code and target_word and sample_code.isalpha():
        shift = detect_uniform_alpha_shift(source_word, sample_code)
        if shift is None:
            return False
        if encode_word_by_shift(target_word, shift) != selected_body:
            return False
    if "syllogism" in normalize_text(topic).lower() or "conclusion" in normalize_text(question["q"]).lower():
        lowered_explanation = explanation.lower()
        if "can be" in lowered_explanation or "may be" in lowered_explanation:
            return False
        if has_invalid_syllogism_overlap_inference(question):
            return False
    if has_invalid_ranking_answer(question):
        return False
    if has_invalid_number_series_answer(question):
        return False
    if has_invalid_odd_one_out_answer(question):
        return False
    if has_invalid_simple_direction_answer(question):
        return False
    if has_invalid_blood_relation_answer(question):
        return False
    return True


def validate_relaxed_practice_correctness(question, subject="", topic=""):
    if reasoning_is_high_risk(subject, topic):
        return False
    if is_high_risk_math_question(subject, topic, question["q"]):
        return False
    if explanation_is_generic_template(question["exp"]):
        return False
    if subject_requires_numeric_alignment(subject, topic, question["q"]):
        if explanation_has_revision_language(question["exp"]):
            return False
        if explanation_has_incomplete_numeric_formatting(question["exp"]):
            return False
        if explanation_has_unstable_equation_chain(question["exp"]):
            return False
    if explanation_contradicts_selected_option(question):
        return False
    if explanation_has_award_or_medal_mismatch(question):
        return False
    if is_confidently_bad_reasoning(question, subject, topic):
        return False
    if not explanation_supports_selected_option(question, subject, topic):
        return False
    if not reasoning_pattern_is_consistent(question, subject, topic):
        return False
    return True


def validate_broad_mode_correctness(question, subject="", topic=""):
    is_numeric_question = subject_requires_numeric_alignment(subject, topic, question["q"])
    is_high_risk_math = is_high_risk_math_question(subject, topic, question["q"])
    if not explanation_has_enough_steps(question["exp"]):
        return False
    if explanation_is_generic_template(question["exp"]):
        return False
    if is_numeric_question:
        if explanation_has_revision_language(question["exp"]):
            return False
        if explanation_has_incomplete_numeric_formatting(question["exp"]):
            return False
        if explanation_has_unstable_equation_chain(question["exp"]):
            return False
        if not (explanation_has_final_conclusion(question["exp"]) or explanation_has_numeric_solution_steps(question["exp"])):
            return False
    if explanation_contradicts_selected_option(question):
        return False
    if explanation_has_award_or_medal_mismatch(question):
        return False
    if is_confidently_bad_reasoning(question, subject, topic):
        return False
    if not explanation_supports_selected_option(question, subject, topic):
        return False
    if is_numeric_question and has_conflicting_final_numeric_candidates(question, question["exp"]):
        return False
    if has_mismatched_simplify_answer(question):
        return False
    if has_invalid_ratio_solution(question):
        return False
    if has_invalid_same_remainder_lcm_answer(question):
        return False
    if (is_numeric_question or is_high_risk_math) and has_mismatched_computed_final_value(question, question["exp"]):
        return False
    if not reasoning_pattern_is_consistent(question, subject, topic):
        return False
    return True


def validate_question_correctness(question, subject="", topic=""):
    is_numeric_question = subject_requires_numeric_alignment(subject, topic, question["q"])
    is_high_risk_math = is_high_risk_math_question(subject, topic, question["q"])
    if not explanation_has_enough_steps(question["exp"]):
        return False
    if explanation_is_generic_template(question["exp"]):
        return False
    if is_numeric_question:
        if explanation_has_revision_language(question["exp"]):
            return False
        if explanation_has_incomplete_numeric_formatting(question["exp"]):
            return False
        if explanation_has_unstable_equation_chain(question["exp"]):
            return False
    if is_numeric_question:
        if not (explanation_has_final_conclusion(question["exp"]) or explanation_has_numeric_solution_steps(question["exp"])):
            return False
    elif not explanation_has_final_conclusion(question["exp"]):
        return False
    if explanation_contradicts_selected_option(question):
        return False
    if explanation_has_award_or_medal_mismatch(question):
        return False
    if is_confidently_bad_reasoning(question, subject, topic):
        return False
    if not explanation_supports_selected_option(question, subject, topic):
        return False
    if is_numeric_question and has_conflicting_final_numeric_candidates(question, question["exp"]):
        return False
    if has_mismatched_simplify_answer(question):
        return False
    if has_invalid_ratio_solution(question):
        return False
    if has_invalid_same_remainder_lcm_answer(question):
        return False
    if (is_numeric_question or is_high_risk_math) and has_mismatched_computed_final_value(question, question["exp"]):
        return False
    if not reasoning_pattern_is_consistent(question, subject, topic):
        return False
    return True


def get_relaxed_practice_rejection_reason(question, subject="", topic=""):
    if reasoning_is_high_risk(subject, topic):
        return "relaxed_reject_high_risk_reasoning"
    if is_high_risk_math_question(subject, topic, question["q"]):
        return "relaxed_reject_high_risk_math"
    if explanation_is_generic_template(question["exp"]):
        return "generic_explanation"
    if subject_requires_numeric_alignment(subject, topic, question["q"]):
        if explanation_has_revision_language(question["exp"]):
            return "revision_language"
        if explanation_has_incomplete_numeric_formatting(question["exp"]):
            return "incomplete_numeric_formatting"
        if explanation_has_unstable_equation_chain(question["exp"]):
            return "unstable_equation_chain"
    if explanation_contradicts_selected_option(question):
        return "contradicts_selected_option"
    if explanation_has_award_or_medal_mismatch(question):
        return "award_or_medal_mismatch"
    if is_confidently_bad_reasoning(question, subject, topic):
        return "bad_reasoning_language"
    if not explanation_supports_selected_option(question, subject, topic):
        return "explanation_not_supporting_answer"
    if has_invalid_ratio_solution(question):
        return "invalid_ratio_solution"
    if has_invalid_same_remainder_lcm_answer(question):
        return "same_remainder_lcm_mismatch"
    if not reasoning_pattern_is_consistent(question, subject, topic):
        return "reasoning_pattern_inconsistent"
    return None


def get_broad_mode_rejection_reason(question, subject="", topic=""):
    is_numeric_question = subject_requires_numeric_alignment(subject, topic, question["q"])
    is_high_risk_math = is_high_risk_math_question(subject, topic, question["q"])
    if not explanation_has_enough_steps(question["exp"]):
        return "explanation_step_count"
    if explanation_is_generic_template(question["exp"]):
        return "generic_explanation"
    if is_numeric_question:
        if explanation_has_revision_language(question["exp"]):
            return "revision_language"
        if explanation_has_incomplete_numeric_formatting(question["exp"]):
            return "incomplete_numeric_formatting"
        if explanation_has_unstable_equation_chain(question["exp"]):
            return "unstable_equation_chain"
        if not (explanation_has_final_conclusion(question["exp"]) or explanation_has_numeric_solution_steps(question["exp"])):
            return "missing_numeric_conclusion"
    if explanation_contradicts_selected_option(question):
        return "contradicts_selected_option"
    if explanation_has_award_or_medal_mismatch(question):
        return "award_or_medal_mismatch"
    if is_confidently_bad_reasoning(question, subject, topic):
        return "bad_reasoning_language"
    if not explanation_supports_selected_option(question, subject, topic):
        return "explanation_not_supporting_answer"
    if is_numeric_question and has_conflicting_final_numeric_candidates(question, question["exp"]):
        return "conflicting_final_numbers"
    if has_mismatched_simplify_answer(question):
        return "simplify_answer_mismatch"
    if has_invalid_ratio_solution(question):
        return "invalid_ratio_solution"
    if has_invalid_same_remainder_lcm_answer(question):
        return "same_remainder_lcm_mismatch"
    if (is_numeric_question or is_high_risk_math) and has_mismatched_computed_final_value(question, question["exp"]):
        return "computed_value_mismatch"
    if not reasoning_pattern_is_consistent(question, subject, topic):
        return "reasoning_pattern_inconsistent"
    return None


def get_strict_practice_rejection_reason(question, subject="", topic=""):
    is_numeric_question = subject_requires_numeric_alignment(subject, topic, question["q"])
    is_high_risk_math = is_high_risk_math_question(subject, topic, question["q"])
    if not explanation_has_enough_steps(question["exp"]):
        return "explanation_step_count"
    if explanation_is_generic_template(question["exp"]):
        return "generic_explanation"
    if is_numeric_question:
        if explanation_has_revision_language(question["exp"]):
            return "revision_language"
        if explanation_has_incomplete_numeric_formatting(question["exp"]):
            return "incomplete_numeric_formatting"
        if explanation_has_unstable_equation_chain(question["exp"]):
            return "unstable_equation_chain"
        if not (explanation_has_final_conclusion(question["exp"]) or explanation_has_numeric_solution_steps(question["exp"])):
            return "missing_numeric_conclusion"
    elif not explanation_has_final_conclusion(question["exp"]):
        return "missing_final_conclusion"
    if explanation_contradicts_selected_option(question):
        return "contradicts_selected_option"
    if explanation_has_award_or_medal_mismatch(question):
        return "award_or_medal_mismatch"
    if is_confidently_bad_reasoning(question, subject, topic):
        return "bad_reasoning_language"
    if not explanation_supports_selected_option(question, subject, topic):
        return "explanation_not_supporting_answer"
    if is_numeric_question and has_conflicting_final_numeric_candidates(question, question["exp"]):
        return "conflicting_final_numbers"
    if has_mismatched_simplify_answer(question):
        return "simplify_answer_mismatch"
    if has_invalid_ratio_solution(question):
        return "invalid_ratio_solution"
    if has_invalid_same_remainder_lcm_answer(question):
        return "same_remainder_lcm_mismatch"
    if (is_numeric_question or is_high_risk_math) and has_mismatched_computed_final_value(question, question["exp"]):
        return "computed_value_mismatch"
    if not reasoning_pattern_is_consistent(question, subject, topic):
        return "reasoning_pattern_inconsistent"
    return None


def get_validation_rejection_reason(question, subject="", topic="", relaxed=False, mode="", practice_type=""):
    if not is_practice_flow(mode, practice_type):
        return None
    if relaxed:
        if uses_broad_mode_validation(mode, practice_type):
            return get_broad_mode_rejection_reason(question, subject, topic)
        return get_relaxed_practice_rejection_reason(question, subject, topic)
    if uses_broad_mode_validation(mode, practice_type):
        return get_broad_mode_rejection_reason(question, subject, topic)
    return get_strict_practice_rejection_reason(question, subject, topic)


def add_rejection_reason(reason_counts, reason):
    reason_counts[reason] = reason_counts.get(reason, 0) + 1


def log_validation_rejections(reason_counts):
    if not reason_counts:
        return
    summary = " ".join(
        f"{reason}={count}"
        for reason, count in sorted(reason_counts.items())
    )
    print(f"validation_rejections {summary}")


def uses_broad_mode_validation(mode="", practice_type=""):
    normalized_mode = normalize_text(mode).lower()
    normalized_practice_type = normalize_text(practice_type).lower()
    broad_modes = {"chapter-practice", "subject-test", "mock"}
    return normalized_mode in broad_modes or normalized_practice_type in broad_modes


def get_generation_temperature(mode="", practice_type=""):
    if uses_broad_mode_validation(mode, practice_type):
        return 0.35
    normalized_mode = normalize_text(mode).lower()
    normalized_practice_type = normalize_text(practice_type).lower()
    if normalized_mode == "final-mock" or normalized_practice_type == "final-mock":
        return 0.45
    return 0.55


def sanitize_options(raw_options, question_text):
    options = raw_options if isinstance(raw_options, list) else []
    cleaned = [normalize_text(option) for option in options if normalize_text(option)]
    if len(cleaned) < 4:
        for fallback in build_fallback_options(question_text):
            if len(cleaned) >= 4:
                break
            cleaned.append(fallback)
    return cleaned[:4]


def fix_question(raw_question, trusted_bank=False):
    if not isinstance(raw_question, dict):
        return None
    question_text = normalize_text(raw_question.get("q") or raw_question.get("question"))
    if len(question_text) < 10:
        return None
    options = sanitize_options(raw_question.get("opts") or raw_question.get("options"), question_text)
    if len(options) != 4:
        return None
    option_bodies = [normalize_for_dedupe(option_text_without_label(option)) for option in options]
    if len(set(option_bodies)) != 4:
        return None
    answer_index = coerce_answer_index(raw_question.get("ans"), options)
    explanation = ensure_explanation(
        question_text, raw_question.get("exp"), answer_index,
        options=options, trusted_bank=trusted_bank
    )
    return {
        "q": question_text,
        "opts": options,
        "ans": answer_index,
        "exp": explanation
    }


def extract_json_array(raw_text):
    decoder = json.JSONDecoder()
    stripped = (raw_text or "").strip()

    if not stripped:
        raise ValueError("Empty Bedrock response")

    def repair_common_json_issues(text):
        repaired = text.strip()
        repaired = re.sub(r",\s*(\]|\})", r"\1", repaired)
        repaired = re.sub(r"(\})\s*(\{)", r"\1,\2", repaired)
        repaired = re.sub(r'("|\]|\})\s*("(?=[^"]+"\s*:))', r"\1,\2", repaired)
        last_object_end = repaired.rfind("}")
        last_array_end = repaired.rfind("]")
        if last_object_end != -1 and last_object_end > last_array_end:
            repaired = repaired[:last_object_end + 1]
        open_braces = repaired.count("{")
        close_braces = repaired.count("}")
        if open_braces > close_braces:
            repaired += "}" * (open_braces - close_braces)
        open_brackets = repaired.count("[")
        close_brackets = repaired.count("]")
        if open_brackets > close_brackets:
            repaired += "]" * (open_brackets - close_brackets)
        return repaired

    def try_parse(text):
        try:
            parsed, _ = decoder.raw_decode(text)
            return parsed
        except json.JSONDecodeError:
            repaired = repair_common_json_issues(text)
            parsed, _ = decoder.raw_decode(repaired)
            return parsed

    array_start = stripped.find("[")
    if array_start == -1:
        raise ValueError("No JSON array found in model response")

    candidate = stripped[array_start:]
    try:
        return try_parse(candidate)
    except (json.JSONDecodeError, ValueError):
        match = re.search(r"\[[\s\S]*\]", stripped)
        if match:
            try:
                return try_parse(match.group(0))
            except (json.JSONDecodeError, ValueError):
                pass
        raise ValueError("Incomplete or invalid JSON array in model response")


def call_bedrock(prompt, count, mode="", practice_type="", max_tokens_override=None, subject=""):
    import urllib.request
    
    max_tokens = max_tokens_override or calculate_max_tokens(count, mode, practice_type)
    temperature = get_generation_temperature(mode, practice_type)

    # Normalize subject for routing
    subj_lower = (subject or "").lower()
    is_general_awareness = "awareness" in subj_lower or "current affairs" in subj_lower
    is_math_or_reasoning = "math" in subj_lower or "reasoning" in subj_lower or "mental ability" in subj_lower

    if is_general_awareness and GEMINI_API_KEY:
        # Route to Gemini API (100% Free)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                try:
                    return extract_json_array(raw_text)
                except Exception as parse_err:
                    print(f"Gemini API Parser Error: {parse_err}. Raw text was:\n{raw_text}")
                    raise parse_err
        except Exception as e:
            if hasattr(e, "read"):
                try:
                    print(f"Gemini API Error Response Body: {e.read().decode('utf-8')}")
                except Exception:
                    pass
            print(f"Gemini API Error: {e}. Falling back to Bedrock.")
    
    # Route to Bedrock models (Free with AWS Credits)
    active_model_id = LLAMA_MODEL_ID if is_math_or_reasoning else NOVA_MODEL_ID
    
    # Format payload depending on the model chosen
    if "llama3" in active_model_id.lower():
        body = json.dumps({
            "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
            "max_gen_len": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        })
    else:
        body = json.dumps({
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ],
            "inferenceConfig": {
                "max_new_tokens": max_tokens,
                "temperature": temperature
            }
        })

    response = bedrock.invoke_model(
        modelId=active_model_id,
        body=body
    )

    result = json.loads(response["body"].read())
    
    if "llama3" in active_model_id.lower():
        raw_text = result.get("generation", "").strip()
    else:
        raw_text = result["output"]["message"]["content"][0]["text"].strip()
        
    return extract_json_array(raw_text)


def call_bedrock_with_truncation_retry(prompt, count, mode="", practice_type="", subject=""):
    try:
        return call_bedrock(prompt, count, mode=mode, practice_type=practice_type, subject=subject)
    except ValueError as error:
        if "Incomplete or invalid JSON array" not in str(error):
            raise
        print("Truncation retry: 1")
        retry_tokens = min(6000, calculate_max_tokens(count, mode, practice_type) + 1200)
        return call_bedrock(
            prompt, count, mode=mode, practice_type=practice_type,
            max_tokens_override=retry_tokens, subject=subject
        )


def validate_and_fix_questions(questions, exclude_questions=None, existing_signatures=None, subject="", topic="", relaxed=False, mode="", practice_type="", trusted_bank=False):
    if not isinstance(questions, list):
        print("before_validation=0")
        print("after_validation=0")
        print("after_deduplication=0")
        return []

    print(f"before_validation={len(questions)}")

    fixed_questions = []
    rejection_counts = {}
    for question in questions:
        fixed = fix_question(question, trusted_bank=trusted_bank)
        if fixed:
            fixed_questions.append(fixed)
        else:
            add_rejection_reason(rejection_counts, "malformed_question")

    print(f"after_validation={len(fixed_questions)}")

    valid = []
    seen = set(existing_signatures or set())
    seen_patterns = set()

    for excluded_question in (exclude_questions or []):
        normalized_excluded = normalize_for_dedupe(excluded_question)
        seen.add(normalized_excluded)
        seen_patterns.add(question_pattern_signature(excluded_question))

    for fixed in fixed_questions:
        signature = dedupe_signature(fixed)
        question_text_signature = normalize_for_dedupe(fixed["q"])
        pattern_signature = question_pattern_signature(fixed["q"])
        if signature in seen or question_text_signature in seen or pattern_signature in seen_patterns:
            add_rejection_reason(rejection_counts, "duplicate_or_repeated_pattern")
            continue
        if trusted_bank:
            seen.add(signature)
            seen.add(question_text_signature)
            seen_patterns.add(pattern_signature)
            valid.append(fixed)
            continue
        if is_practice_flow(mode, practice_type):
            rejection_reason = get_validation_rejection_reason(
                fixed,
                subject=subject,
                topic=topic,
                relaxed=relaxed,
                mode=mode,
                practice_type=practice_type
            )
            if rejection_reason:
                add_rejection_reason(rejection_counts, rejection_reason)
                continue
        seen.add(signature)
        seen.add(question_text_signature)
        seen_patterns.add(pattern_signature)
        valid.append(fixed)

    print(f"after_deduplication={len(valid)}")
    log_validation_rejections(rejection_counts)
    return valid


def build_logging_context(exam, subject, topic, mode, difficulty, practice_type):
    return f"exam={exam} subject={subject} topic={topic} mode={mode} difficulty={difficulty} practiceType={practice_type}"


def generate_batch(exam, subject, topic, count, mode, difficulty,
                   selected_chapters, chapter_mode, drill_topics, exclude_questions, practice_type):
    prompt = build_prompt(
        exam, subject, topic, count, mode, difficulty,
        selected_chapters, chapter_mode, drill_topics, exclude_questions, practice_type
    )
    return call_bedrock_with_truncation_retry(prompt, count, mode=mode, practice_type=practice_type, subject=subject)


def build_deterministic_math_fallbacks(topic):
    normalized_topic = normalize_text(topic).lower()

    if any(keyword in normalized_topic for keyword in ["time", "speed", "distance", "train", "boat"]):
        return [
            {
                "q": "A bus travels 180 km in 3 hours. What is its average speed?",
                "opts": ["A) 45 km/h", "B) 50 km/h", "C) 60 km/h", "D) 75 km/h"],
                "ans": 2,
                "exp": "Step 1: Average speed = distance / time. Step 2: Speed = 180 / 3 = 60 km/h. Step 3: Therefore, the correct answer is 60 km/h."
            },
            {
                "q": "A train runs at 72 km/h. How far will it travel in 25 minutes?",
                "opts": ["A) 24 km", "B) 30 km", "C) 36 km", "D) 40 km"],
                "ans": 1,
                "exp": "Step 1: Convert 25 minutes into hours: 25/60 = 5/12 hour. Step 2: Distance = speed x time = 72 x 5/12 = 30 km. Step 3: Therefore, the train travels 30 km."
            },
            {
                "q": "A cyclist covers 48 km at a speed of 16 km/h. How much time does he take?",
                "opts": ["A) 2 hours", "B) 3 hours", "C) 4 hours", "D) 5 hours"],
                "ans": 1,
                "exp": "Step 1: Time = distance / speed. Step 2: Time = 48 / 16 = 3 hours. Step 3: Therefore, the correct answer is 3 hours."
            },
            {
                "q": "A train 150 meters long crosses a pole in 10 seconds. What is its speed in km/h?",
                "opts": ["A) 36 km/h", "B) 45 km/h", "C) 54 km/h", "D) 60 km/h"],
                "ans": 2,
                "exp": "Step 1: Speed = distance / time = 150 / 10 = 15 m/s. Step 2: Convert m/s to km/h: 15 x 18/5 = 54 km/h. Step 3: Therefore, the speed is 54 km/h."
            },
            {
                "q": "Two trains move in opposite directions at 50 km/h and 70 km/h. What is their relative speed?",
                "opts": ["A) 20 km/h", "B) 100 km/h", "C) 110 km/h", "D) 120 km/h"],
                "ans": 3,
                "exp": "Step 1: For opposite directions, relative speed is the sum of speeds. Step 2: Relative speed = 50 + 70 = 120 km/h. Step 3: Therefore, the correct answer is 120 km/h."
            },
            {
                "q": "A boat covers 36 km downstream in 3 hours. What is its downstream speed?",
                "opts": ["A) 9 km/h", "B) 12 km/h", "C) 15 km/h", "D) 18 km/h"],
                "ans": 1,
                "exp": "Step 1: Speed = distance / time. Step 2: Downstream speed = 36 / 3 = 12 km/h. Step 3: Therefore, the downstream speed is 12 km/h."
            }
        ]

    if "percentage" in normalized_topic or "percent" in normalized_topic:
        return [
            {
                "q": "What is 28% of 250?",
                "opts": ["A) 60", "B) 65", "C) 70", "D) 75"],
                "ans": 2,
                "exp": "Step 1: 28% of 250 = 28/100 x 250. Step 2: This equals 70. Step 3: Therefore, the correct answer is 70."
            },
            {
                "q": "A number is increased from 400 to 460. What is the percentage increase?",
                "opts": ["A) 12%", "B) 15%", "C) 18%", "D) 20%"],
                "ans": 1,
                "exp": "Step 1: Increase = 460 - 400 = 60. Step 2: Percentage increase = 60/400 x 100 = 15%. Step 3: Therefore, the correct answer is 15%."
            }
        ]

    if any(keyword in normalized_topic for keyword in ["profit", "loss", "interest"]):
        return [
            {
                "q": "An article is bought for Rs. 600 and sold for Rs. 750. What is the profit percentage?",
                "opts": ["A) 20%", "B) 25%", "C) 30%", "D) 35%"],
                "ans": 1,
                "exp": "Step 1: Profit = 750 - 600 = Rs. 150. Step 2: Profit percentage = 150/600 x 100 = 25%. Step 3: Therefore, the correct answer is 25%."
            },
            {
                "q": "What is the simple interest on Rs. 4000 at 6% per annum for 2 years?",
                "opts": ["A) Rs. 420", "B) Rs. 460", "C) Rs. 480", "D) Rs. 520"],
                "ans": 2,
                "exp": "Step 1: Simple Interest = P x R x T / 100. Step 2: SI = 4000 x 6 x 2 / 100 = Rs. 480. Step 3: Therefore, the correct answer is Rs. 480."
            }
        ]

    if "time" in normalized_topic and "work" in normalized_topic:
        return [
            {
                "q": "A can complete a work in 12 days and B can complete it in 18 days. In how many days will they complete it together?",
                "opts": ["A) 6.5 days", "B) 7.2 days", "C) 8 days", "D) 9 days"],
                "ans": 1,
                "exp": "Step 1: A's one day work = 1/12 and B's one day work = 1/18. Step 2: Together = 1/12 + 1/18 = 5/36. Step 3: Time = 36/5 = 7.2 days."
            }
        ]

    return [
        {
            "q": "Find the HCF of 84 and 126.",
            "opts": ["A) 21", "B) 28", "C) 42", "D) 63"],
            "ans": 2,
            "exp": "Step 1: Prime factors of 84 are 2 x 2 x 3 x 7. Step 2: Prime factors of 126 are 2 x 3 x 3 x 7. Step 3: Common factors are 2, 3 and 7, so HCF = 42."
        },
        {
            "q": "Simplify: 18 + 6 x 4 - 12.",
            "opts": ["A) 24", "B) 30", "C) 36", "D) 42"],
            "ans": 1,
            "exp": "Step 1: Multiply first: 6 x 4 = 24. Step 2: Now calculate 18 + 24 - 12 = 30. Step 3: Therefore, the correct answer is 30."
        }
    ]


def build_deterministic_fallback_bank(exam, subject, topic):
    normalized_subject = normalize_text(subject).lower()

    if "math" in normalized_subject:
        return build_deterministic_math_fallbacks(topic)
    if "reason" in normalized_subject or "intelligence" in normalized_subject:
        return choose_local_reasoning_bank(topic)
    if "science" in normalized_subject:
        return GENERAL_SCIENCE_PRACTICE_BANK
    if "awareness" in normalized_subject or "current affairs" in normalized_subject:
        return GA_HISTORY_PRACTICE_BANK

    return []


def build_safe_fallback_questions(exam, subject, topic, count, existing_questions):
    questions = []
    seen = {dedupe_signature(question) for question in existing_questions}
    seen_concepts = {final_concept_signature(question) for question in existing_questions}
    normalized_subject = normalize_text(subject).lower()
    bank = []
    if "math" in normalized_subject:
        bank = choose_local_math_bank(topic=topic)
    elif "reason" in normalized_subject or "intelligence" in normalized_subject:
        bank = choose_local_reasoning_bank(topic=topic)
    elif "science" in normalized_subject:
        bank = GENERAL_SCIENCE_PRACTICE_BANK
    elif "awareness" in normalized_subject or "current affairs" in normalized_subject:
        bank = GA_HISTORY_PRACTICE_BANK

    if bank:
        for candidate in bank:
            if len(questions) >= count:
                break
            signature = dedupe_signature(candidate)
            concept_signature = final_concept_signature(candidate)
            if signature in seen or concept_signature in seen_concepts:
                continue
            seen.add(signature)
            seen_concepts.add(concept_signature)
            questions.append(dict(candidate))

    if len(questions) >= count:
        return questions[:count]

    for candidate in build_deterministic_fallback_bank(exam, subject, topic):
        if len(questions) >= count:
            break
        signature = dedupe_signature(candidate)
        concept_signature = final_concept_signature(candidate)
        if signature not in seen and concept_signature not in seen_concepts:
            seen.add(signature)
            seen_concepts.add(concept_signature)
            questions.append(dict(candidate))

    return questions


def top_off_with_safe_fallback(exam, subject, topic, count, questions):
    missing_count = max(count - len(questions), 0)
    if missing_count <= 0:
        return questions[:count]

    safe_fallback = build_safe_fallback_questions(exam, subject, topic, missing_count, questions)
    if safe_fallback:
        print(f"safe_fallback_used remaining={missing_count} exam={exam} subject={subject} topic={topic}")
        questions.extend(safe_fallback)

    return questions[:count]


def combined_exclusions(exclude_questions, questions):
    return list(exclude_questions or []) + [question["q"] for question in questions]


def extend_with_validated_bank_questions(
    questions, bank_questions, count, subject, topic, mode, practice_type,
    exclude_questions=None, trusted_bank=True
):
    exclusions = combined_exclusions(exclude_questions, questions)
    validated_bank_questions = validate_and_fix_questions(
        bank_questions,
        exclude_questions=exclusions,
        existing_signatures={dedupe_signature(question) for question in questions},
        subject=subject, topic=topic, mode=mode, practice_type=practice_type,
        trusted_bank=trusted_bank
    )

    if validated_bank_questions:
        questions.extend(validated_bank_questions)
        questions = questions[:count]

    missing_count = max(count - len(questions), 0)
    return questions, missing_count, len(validated_bank_questions)


def choose_local_math_bank(mode="", practice_type="", topic=""):
    normalized_topic = normalize_text(topic).lower()

    selected_banks = []

    def add_bank(bank):
        if bank not in selected_banks:
            selected_banks.append(bank)

    if any(keyword in normalized_topic for keyword in ["number system", "hcf", "lcm", "simplification", "fraction", "decimal"]):
        add_bank(NUMBER_SYSTEM_PRACTICE_BANK)

    if "percentage" in normalized_topic:
        add_bank(PERCENTAGE_PRACTICE_BANK)

    if "ratio" in normalized_topic or "proportion" in normalized_topic:
        add_bank(RATIO_PROPORTION_PRACTICE_BANK)

    if any(keyword in normalized_topic for keyword in ["profit", "loss", "simple interest", "compound interest", "interest"]):
        add_bank(PROFIT_LOSS_INTEREST_PRACTICE_BANK)

    if "time" in normalized_topic and "work" in normalized_topic:
        add_bank(TIME_WORK_PRACTICE_BANK)

    if (
        "time speed distance" in normalized_topic
        or ("time" in normalized_topic and "distance" in normalized_topic)
        or "train" in normalized_topic
        or mode == "previous-year"
        or practice_type == "previous-year"
    ):
        add_bank(TIME_DISTANCE_PRACTICE_BANK)

    if not selected_banks:
        selected_banks = [ARITHMETIC_PRACTICE_BANK]

    mixed_bank = []
    max_length = max(len(bank) for bank in selected_banks)
    for index in range(max_length):
        for bank in selected_banks:
            if index < len(bank):
                mixed_bank.append(bank[index])

    return mixed_bank


def split_planned_topics(topic):
    return [item.strip() for item in str(topic or "").split(",") if item.strip()]


CODING_DECODING_PRACTICE_BANK = [
    {
        "q": "If in a certain code 'RAIL' is written as 'SBJM' by moving each letter one step forward alphabetically, how will 'BOARD' be written in the same code?",
        "opts": ["A) CPBSE", "B) DPBSE", "C) COBSE", "D) CPBSF"],
        "ans": 0,
        "exp": "Step 1: Each letter is shifted one step forward. Step 2: BOARD becomes B->C, O->P, A->B, R->S, D->E. Step 3: Therefore, BOARD is written as CPBSE."
    },
    {
        "q": "If in a certain code 'TRACK' is written as 'USBDL' by moving each letter one step forward alphabetically, how will 'MIND' be written in the same code?",
        "opts": ["A) OJOE", "B) NJOE", "C) NIOE", "D) NJOF"],
        "ans": 1,
        "exp": "Step 1: Each letter is shifted one step forward. Step 2: MIND becomes M->N, I->J, N->O, D->E. Step 3: Therefore, MIND is written as NJOE."
    }
]


def choose_local_reasoning_bank(topic=""):
    normalized_topic = normalize_text(topic).lower()
    planned_topics = [normalize_text(item).lower() for item in split_planned_topics(topic)]
    if not planned_topics:
        planned_topics = [normalized_topic]

    def matches_question(candidate, keywords):
        question_text = normalize_text(candidate.get("q", "")).lower()
        return any(keyword in question_text for keyword in keywords)

    topic_rules = [
        (["coding", "decoding", "alphabetical"], CODING_DECODING_PRACTICE_BANK),
        (["number series", "series", "missing number"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["series", "missing number"])]),
        (["blood", "relation"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["pointing", "related"])]),
        (["direction"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["direction", "walk", "faces", "turn"])]),
        (["ranking", "order"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["rank", "taller", "shorter"])]),
        (["syllogism", "statement", "conclusion", "venn"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["statements", "conclusion", "cricket", "football"])]),
        (["odd"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["odd one out"])]),
        (["calendar"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["march", "day"])]),
        (["clock"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["clock", "angle"])]),
        (["analogy"], [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["analogy", "doctor", "teacher"])]),
    ]

    selected_banks = []
    for planned_topic in planned_topics:
        for keywords, bank in topic_rules:
            if any(keyword in planned_topic for keyword in keywords) and bank:
                selected_banks.append(bank)

    if not selected_banks:
        selected_banks = [
            CODING_DECODING_PRACTICE_BANK,
            [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["series", "missing number"])],
            [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["pointing", "related"])],
            [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["direction", "walk", "faces", "turn"])],
            [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["rank", "taller", "shorter"])],
            [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["statements", "conclusion", "cricket", "football"])],
            [q for q in REASONING_PRACTICE_BANK if matches_question(q, ["odd one out", "march", "clock", "analogy"])],
        ]

    mixed_bank = []
    max_length = max((len(bank) for bank in selected_banks if bank), default=0)
    for index in range(max_length):
        for bank in selected_banks:
            if index < len(bank):
                candidate = bank[index]
                if dedupe_signature(candidate) not in {dedupe_signature(item) for item in mixed_bank}:
                    mixed_bank.append(candidate)

    return mixed_bank or REASONING_PRACTICE_BANK


def choose_local_math_bank_for_topic(topic):
    normalized_topic = normalize_text(topic).lower()

    if any(keyword in normalized_topic for keyword in ["number system", "hcf", "lcm", "simplification", "fraction", "decimal"]):
        return NUMBER_SYSTEM_PRACTICE_BANK
    if "percentage" in normalized_topic:
        return PERCENTAGE_PRACTICE_BANK
    if "ratio" in normalized_topic or "proportion" in normalized_topic:
        return RATIO_PROPORTION_PRACTICE_BANK
    if any(keyword in normalized_topic for keyword in ["profit", "loss", "simple interest", "compound interest", "interest"]):
        return PROFIT_LOSS_INTEREST_PRACTICE_BANK
    if "time" in normalized_topic and "work" in normalized_topic:
        return TIME_WORK_PRACTICE_BANK
    if "time speed distance" in normalized_topic or "train" in normalized_topic or ("time" in normalized_topic and "distance" in normalized_topic):
        return TIME_DISTANCE_PRACTICE_BANK
    return []


def question_matches_planned_topic(question, planned_topic):
    question_text = normalize_text(question.get("q", "")).lower()
    normalized_topic = normalize_text(planned_topic).lower()

    if "number system" in normalized_topic:
        return any(keyword in question_text for keyword in ["largest", "smallest", "divisible", "remainder", "number"])
    if "hcf" in normalized_topic or "lcm" in normalized_topic:
        return "hcf" in question_text or "lcm" in question_text
    if "simplification" in normalized_topic:
        return "simplify" in question_text or "decimal" in question_text or "fraction" in question_text
    if "percentage" in normalized_topic:
        return any(keyword in question_text for keyword in ["percentage", "percent", "increased", "decreased"])
    if "ratio" in normalized_topic or "proportion" in normalized_topic:
        return "ratio" in question_text or "proportion" in question_text
    if "compound interest" in normalized_topic:
        return "compound interest" in question_text or "compounded" in question_text
    if "simple interest" in normalized_topic:
        return "simple interest" in question_text
    if "profit" in normalized_topic or "loss" in normalized_topic:
        return any(keyword in question_text for keyword in ["profit", "loss", "cost price", "selling price", "shopkeeper"])
    if "time" in normalized_topic and "work" in normalized_topic:
        return "work" in question_text or "complete" in question_text
    if "time speed distance" in normalized_topic:
        return any(keyword in question_text for keyword in ["train", "speed", "distance", "km/hr", "pole"])

    return normalized_topic in question_text


def find_missing_planned_topics(planned_topics, questions):
    missing_topics = []
    for planned_topic in planned_topics:
        if not any(question_matches_planned_topic(question, planned_topic) for question in questions):
            missing_topics.append(planned_topic)
    return missing_topics


def apply_planned_topic_bank_top_offs(
    questions,
    count,
    subject,
    topic,
    mode,
    practice_type,
    exclude_questions,
    context_log
):
    if not is_subject_test_flow(mode, practice_type) or "math" not in normalize_text(subject).lower():
        return questions, max(count - len(questions), 0)

    planned_topics = split_planned_topics(topic)
    if len(planned_topics) <= 1:
        return questions, max(count - len(questions), 0)

    missing_count = max(count - len(questions), 0)
    if missing_count <= 0:
        return questions, missing_count

    for planned_topic in find_missing_planned_topics(planned_topics, questions):
        if missing_count <= 0:
            break

        topic_bank = choose_local_math_bank_for_topic(planned_topic)
        if not topic_bank:
            continue

        bank_questions = build_local_practice_bank_questions(
            topic_bank,
            1,
            exclude_questions=combined_exclusions(exclude_questions, questions),
            existing_questions=questions
        )
        questions, missing_count, added_count = extend_with_validated_bank_questions(
            questions,
            bank_questions,
            count,
            subject,
            planned_topic,
            mode,
            practice_type,
            exclude_questions=exclude_questions
        )
        if added_count:
            print(f"planned_topic_bank_used topic={planned_topic} count={added_count} {context_log}")

    return questions, missing_count


def apply_practice_flow_top_offs(
    exam, subject, topic, count, mode, practice_type,
    selected_chapters, drill_topics, exclude_questions, questions, context_log
):
    missing_count = max(count - len(questions), 0)
    if missing_count <= 0:
        return questions, missing_count

    bank_questions = build_topic_bank_questions(
        exam, subject, topic, missing_count,
        exclude_questions=combined_exclusions(exclude_questions, questions),
        existing_questions=questions
    )
    questions, missing_count, added_count = extend_with_validated_bank_questions(
        questions, bank_questions, count, subject, topic, mode, practice_type,
        exclude_questions=exclude_questions
    )
    if added_count:
        print(f"topic_bank_used count={added_count} {context_log}")

    if missing_count > 0 and (
        mode == "subject-test" or practice_type == "subject-test"
        or mode == "chapter-practice" or practice_type == "chapter-practice"
    ):
        bank_questions = build_subject_bank_questions(
            exam, subject, missing_count,
            exclude_questions=combined_exclusions(exclude_questions, questions),
            existing_questions=questions,
            preferred_topics=selected_chapters if (mode == "chapter-practice" or practice_type == "chapter-practice") else None
        )
        questions, missing_count, added_count = extend_with_validated_bank_questions(
            questions, bank_questions, count, subject, topic, mode, practice_type,
            exclude_questions=exclude_questions
        )
        if added_count:
            print(f"subject_bank_used count={added_count} {context_log}")

    if missing_count > 0 and should_use_percentage_bank_fallback(
        subject=subject, topic=topic, mode=mode, practice_type=practice_type,
        selected_chapters=selected_chapters, drill_topics=drill_topics
    ):
        bank_questions = build_percentage_bank_questions(
            missing_count,
            exclude_questions=combined_exclusions(exclude_questions, questions),
            existing_questions=questions
        )
        questions, missing_count, added_count = extend_with_validated_bank_questions(
            questions, bank_questions, count, subject, topic, mode, practice_type,
            exclude_questions=exclude_questions
        )
        if added_count:
            print(f"percentage_bank_used count={added_count} {context_log}")

    if missing_count > 0:
        questions, missing_count = apply_planned_topic_bank_top_offs(
            questions=questions,
            count=count,
            subject=subject,
            topic=topic,
            mode=mode,
            practice_type=practice_type,
            exclude_questions=exclude_questions,
            context_log=context_log
        )

    if missing_count > 0 and "math" in normalize_text(subject).lower():
        bank_questions = build_local_practice_bank_questions(
            choose_local_math_bank(mode=mode, practice_type=practice_type, topic=topic),
            missing_count,
            exclude_questions=combined_exclusions(exclude_questions, questions),
            existing_questions=questions
        )
        questions, missing_count, added_count = extend_with_validated_bank_questions(
            questions, bank_questions, count, subject, topic, mode, practice_type,
            exclude_questions=exclude_questions
        )
        if added_count:
            print(f"local_math_bank_used count={added_count} {context_log}")

    if missing_count > 0 and (
        "reason" in normalize_text(subject).lower()
        or "intelligence" in normalize_text(subject).lower()
    ):
        bank_questions = build_local_practice_bank_questions(
            choose_local_reasoning_bank(topic=topic), missing_count,
            exclude_questions=combined_exclusions(exclude_questions, questions),
            existing_questions=questions
        )
        questions, missing_count, added_count = extend_with_validated_bank_questions(
            questions, bank_questions, count, subject, topic, mode, practice_type,
            exclude_questions=exclude_questions
        )
        if added_count:
            print(f"local_reasoning_bank_used count={added_count} {context_log}")

    if missing_count > 0 and "science" in normalize_text(subject).lower():
        bank_questions = build_local_practice_bank_questions(
            GENERAL_SCIENCE_PRACTICE_BANK, missing_count,
            exclude_questions=combined_exclusions(exclude_questions, questions),
            existing_questions=questions
        )
        questions, missing_count, added_count = extend_with_validated_bank_questions(
            questions, bank_questions, count, subject, topic, mode, practice_type,
            exclude_questions=exclude_questions
        )
        if added_count:
            print(f"local_science_bank_used count={added_count} {context_log}")

    if missing_count > 0 and (
        "awareness" in normalize_text(subject).lower()
        or "current affairs" in normalize_text(subject).lower()
        or "history" in normalize_text(topic).lower()
    ):
        bank_questions = build_local_practice_bank_questions(
            GA_HISTORY_PRACTICE_BANK, missing_count,
            exclude_questions=combined_exclusions(exclude_questions, questions),
            existing_questions=questions
        )
        questions, missing_count, added_count = extend_with_validated_bank_questions(
            questions, bank_questions, count, subject, topic, mode, practice_type,
            exclude_questions=exclude_questions
        )
        if added_count:
            print(f"local_ga_bank_used count={added_count} {context_log}")

    return questions, missing_count


# ================================================================
# NEW: HELPER FUNCTIONS
# ================================================================

def get_subtopics_for_subject(subject, topic):
    """
    Returns a list of RRB subtopics for the given subject/topic.
    Used to tell the AI to cover varied content within a topic.
    """
    subject_data = RRB_SYLLABUS.get(subject, {})

    # Handle General Science which has nested Physics/Chemistry/Biology
    if subject == "General Science":
        for key in ["Physics", "Chemistry", "Biology"]:
            if key.lower() in topic.lower() or topic.lower() in key.lower():
                return RRB_SYLLABUS["General Science"].get(key, [])
        # No specific match — return all flattened
        all_subs = []
        for key in ["Physics", "Chemistry", "Biology"]:
            all_subs.extend(RRB_SYLLABUS["General Science"].get(key, []))
        return all_subs

    return subject_data.get("subtopics", [])


def check_answer_distribution(questions):
    """
    Warns in logs if the correct answer index is too skewed
    (e.g. 80% of answers are index 0 = option A).
    Does not modify questions — just logs a warning.
    """
    if len(questions) < 4:
        return

    indices = [q["ans"] for q in questions]
    for i in range(4):
        pct = indices.count(i) / len(indices)
        if pct > 0.6:
            print(
                f"[Warning] Answer distribution skewed: "
                f"index {i} (option {['A','B','C','D'][i]}) "
                f"appears {indices.count(i)}/{len(questions)} times ({round(pct*100)}%)"
            )


# ================================================================
# RENAMED: old generate_validated_questions → _generate_batch_questions
# This runs the full retry/validation/fallback logic for ONE batch.
# ================================================================

def final_concept_signature(question):
    question_text = normalize_text(question.get("q", ""))
    compact_text = re.sub(r"\s+", "", question_text)
    compact_lower = compact_text.lower()
    numbers = extract_series_numbers(question_text)
    if numbers:
        return "series:" + ",".join(str(number) for number in numbers)

    normalized = normalize_for_dedupe(question_text)
    if "backupconceptcheck" in normalized:
        return "fallback:" + normalized
    if "daughteroftheonlysonofmymother" in normalized:
        return "blood:only_son_mother_daughter"
    if "5,10,20,40" in compact_lower:
        return "series:5,10,20,40"
    if "2,6,12,20,30" in compact_lower:
        return "series:2,6,12,20,30"
    if "founder of the maurya empire" in question_text.lower() or "founder of the maurya empire" in normalized:
        return "ga:founder_maurya_empire"
    if "world environment day" in normalized:
        return "ga:world_environment_day"
    if "chief election commissioner of india" in normalized:
        return "ga:chief_election_commissioner_india"

    return question_pattern_signature(question_text)


def remove_final_duplicate_questions(questions):
    filtered = []
    seen = set()
    removed = 0
    for question in questions:
        signature = final_concept_signature(question)
        if signature in seen:
            removed += 1
            continue
        seen.add(signature)
        filtered.append(question)
    if removed:
        print(f"final_duplicate_questions_removed count={removed}")
    return filtered


def finalize_questions_for_delivery(
    questions, count, exam, subject, topic, mode, difficulty, practice_type,
    selected_chapters=None, drill_topics=None, exclude_questions=None
):
    for _ in range(4):
        previous_count = len(questions)
        questions = remove_final_duplicate_questions(questions)
        missing_count = max(count - len(questions), 0)
        if missing_count <= 0:
            break
        context_log = build_logging_context(exam, subject, topic, mode, difficulty, practice_type)
        questions, missing_count = apply_practice_flow_top_offs(
            exam, subject, topic, count, mode, practice_type,
            selected_chapters or [], drill_topics or [], exclude_questions or [],
            questions, context_log
        )
        if len(questions) <= previous_count:
            break
    missing_count = max(count - len(questions), 0)
    if missing_count > 0:
        questions = top_off_with_safe_fallback(exam, subject, topic, count, questions)
    questions = remove_final_duplicate_questions(questions)
    missing_count = max(count - len(questions), 0)
    if missing_count > 0:
        questions = top_off_with_safe_fallback(exam, subject, topic, count, questions)
        questions = remove_final_duplicate_questions(questions)
    return questions[:count]


def strip_option_label(option_text):
    return re.sub(r"^\s*[A-D][\)\.\:\-]\s*", "", normalize_text(option_text), flags=re.IGNORECASE)


def relabel_options(option_values):
    return [
        f"{['A', 'B', 'C', 'D'][index]}) {strip_option_label(value)}"
        for index, value in enumerate(option_values[:4])
    ]


def update_explanation_answer_label(explanation, old_index, new_index):
    old_label = ["A", "B", "C", "D"][old_index]
    new_label = ["A", "B", "C", "D"][new_index]
    return re.sub(
        rf"\boption\s+{old_label}\b",
        f"option {new_label}",
        normalize_text(explanation),
        flags=re.IGNORECASE
    )


def move_correct_answer_to_position(question, target_index):
    current_index = int(question.get("ans", 0))
    target_index = max(0, min(int(target_index), 3))
    if current_index == target_index:
        return question

    option_values = [strip_option_label(option) for option in question.get("opts", [])]
    if len(option_values) != 4:
        return question

    correct_option = option_values[current_index]
    remaining_options = [
        option for index, option in enumerate(option_values)
        if index != current_index
    ]
    reordered_options = []
    remaining_index = 0

    for index in range(4):
        if index == target_index:
            reordered_options.append(correct_option)
        else:
            reordered_options.append(remaining_options[remaining_index])
            remaining_index += 1

    return {
        **question,
        "opts": relabel_options(reordered_options),
        "ans": target_index,
        "exp": update_explanation_answer_label(question.get("exp", ""), current_index, target_index)
    }


def rebalance_answer_positions(questions):
    if len(questions) < 4:
        return questions

    rebalanced = []
    changed_count = 0
    for index, question in enumerate(questions):
        target_index = index % 4
        updated_question = move_correct_answer_to_position(question, target_index)
        if updated_question.get("ans") != question.get("ans"):
            changed_count += 1
        rebalanced.append(updated_question)

    if changed_count:
        print(f"answer_positions_rebalanced changed={changed_count} total={len(questions)}")

    return rebalanced


def _generate_batch_questions(exam, subject, topic, count, mode, difficulty,
                              selected_chapters, chapter_mode, drill_topics,
                              exclude_questions, practice_type):
    last_error = None
    context_log = build_logging_context(exam, subject, topic, mode, difficulty, practice_type)

    if (
        is_practice_flow(mode, practice_type)
        and not is_mixed_weak_drill(mode, practice_type, drill_topics)
        and is_dedicated_coding_decoding_request(
            subject, topic, selected_chapters, drill_topics
        )
    ):
        coding_questions = build_coding_decoding_bank_questions(count, exclude_questions=exclude_questions)
        validated_coding_questions = validate_and_fix_questions(
            coding_questions, exclude_questions=exclude_questions,
            subject=subject, topic=topic, mode=mode, practice_type=practice_type,
            trusted_bank=True
        )
        if validated_coding_questions:
            questions = top_off_with_safe_fallback(exam, subject, topic, count, validated_coding_questions[:count])
            print(f"coding_decoding_bank_used count={len(questions)} {context_log}")
            return {"questions": questions, "error": None}
        return {"questions": [], "error": f"Unable to build coding-decoding bank questions. {context_log}"}

    for attempt in range(MAX_RETRIES):
        try:
            raw_questions = generate_batch(
                exam, subject, topic, count, mode, difficulty,
                selected_chapters, chapter_mode, drill_topics,
                exclude_questions, practice_type
            )
            questions = validate_and_fix_questions(
                raw_questions, exclude_questions=exclude_questions,
                subject=subject, topic=topic, mode=mode, practice_type=practice_type
            )

            missing_count = max(count - len(questions), 0)
            for partial_attempt in range(PARTIAL_RETRIES):
                if missing_count <= 0:
                    break
                retry_exclusions = list(exclude_questions or []) + [question["q"] for question in questions]
                refill_raw = generate_batch(
                    exam, subject, topic, missing_count, mode, difficulty,
                    selected_chapters, chapter_mode, drill_topics,
                    retry_exclusions, practice_type
                )
                refill_valid = validate_and_fix_questions(
                    refill_raw, exclude_questions=retry_exclusions,
                    existing_signatures={dedupe_signature(question) for question in questions},
                    subject=subject, topic=topic, mode=mode, practice_type=practice_type
                )
                questions.extend(refill_valid)
                questions = questions[:count]
                missing_count = max(count - len(questions), 0)
                print(f"after_partial_refill={len(questions)}")

            if missing_count > 0:
                print(f"underflow_detected remaining={missing_count} {context_log}")
                retry_exclusions = list(exclude_questions or []) + [question["q"] for question in questions]
                relaxed_raw = generate_batch(
                    exam, subject, topic, missing_count, mode, difficulty,
                    selected_chapters, chapter_mode, drill_topics,
                    retry_exclusions, practice_type
                )
                relaxed_valid = validate_and_fix_questions(
                    relaxed_raw, exclude_questions=retry_exclusions,
                    existing_signatures={dedupe_signature(question) for question in questions},
                    subject=subject, topic=topic, relaxed=True,
                    mode=mode, practice_type=practice_type
                )
                questions.extend(relaxed_valid)
                questions = questions[:count]
                missing_count = max(count - len(questions), 0)

            if missing_count > 0:
                if is_practice_flow(mode, practice_type):
                    questions, missing_count = apply_practice_flow_top_offs(
                        exam=exam, subject=subject, topic=topic, count=count,
                        mode=mode, practice_type=practice_type,
                        selected_chapters=selected_chapters, drill_topics=drill_topics,
                        exclude_questions=exclude_questions, questions=questions,
                        context_log=context_log
                    )
                    print(f"quality_underflow remaining={missing_count} {context_log}")
                    if questions:
                        questions = top_off_with_safe_fallback(exam, subject, topic, count, questions)
                        if len(questions) == count:
                            return {"questions": questions, "error": None}
                    last_error = f"Unable to generate quality practice questions. expected={count} actual={len(questions)} {context_log}"
                    continue

                questions = top_off_with_safe_fallback(exam, subject, topic, count, questions)

            if len(questions) == count:
                return {"questions": questions, "error": None}

            last_error = f"Failed to reach requested count. expected={count} actual={len(questions)} {context_log}"
        except Exception as error:
            last_error = str(error)
            print(f"generation_failure={last_error}")
            fallback_questions = top_off_with_safe_fallback(exam, subject, topic, count, [])
            if fallback_questions:
                print(f"exception_fallback_used count={len(fallback_questions)} {context_log}")
                return {"questions": fallback_questions, "error": None}

    return {"questions": [], "error": f"Failed after {MAX_RETRIES} attempt(s): {last_error}"}


# ================================================================
# NEW: OUTER BATCHING WRAPPER
# If user requests 10 questions → 2 batches of 5
# If user requests 15 questions → 3 batches of 5
# This prevents AI from truncating a big response and losing questions.
# ================================================================

def generate_validated_questions(exam, subject, topic, count, mode, difficulty,
                                 selected_chapters, chapter_mode, drill_topics,
                                 exclude_questions, practice_type):

    # Small request — no batching needed, single call
    if count <= BATCH_SIZE:
        request_topic = topic
        if is_subject_test_flow(mode, practice_type):
            batch_topics = get_subject_test_batch_topics(subject, count)
            if batch_topics:
                request_topic = ", ".join(batch_topics)
                print(f"subject_topic_plan single_batch topics={request_topic}")
        elif is_weak_drill_flow(mode, practice_type):
            batch_topics = get_weak_drill_batch_topics(drill_topics, count)
            if batch_topics:
                request_topic = ", ".join(batch_topics)
                print(f"weak_drill_topic_plan single_batch topics={request_topic}")
        result = _generate_batch_questions(
            exam, subject, request_topic, count, mode, difficulty,
            selected_chapters, chapter_mode, drill_topics,
            exclude_questions, practice_type
        )
        if result.get("questions"):
            result["questions"] = finalize_questions_for_delivery(
                result["questions"], count, exam, subject, request_topic, mode, difficulty, practice_type,
                selected_chapters=selected_chapters, drill_topics=drill_topics, exclude_questions=exclude_questions
            )
            result["questions"] = rebalance_answer_positions(result["questions"])
            check_answer_distribution(result["questions"])
        return result

    # Large request — split into BATCH_SIZE packets
    print(f"batching_started total_requested={count} batch_size={BATCH_SIZE}")
    all_questions = []
    all_errors = []
    batch_number = 0

    while len(all_questions) < count:
        remaining = count - len(all_questions)
        batch_count = min(BATCH_SIZE, remaining)
        batch_number += 1

        # Pass already-collected questions as exclude so no repeats
        batch_excludes = list(exclude_questions or []) + [q["q"] for q in all_questions]
        batch_topic = topic
        if is_subject_test_flow(mode, practice_type):
            batch_topics = get_subject_test_batch_topics(subject, batch_count, start_index=len(all_questions))
            if batch_topics:
                batch_topic = ", ".join(batch_topics)
                print(f"subject_topic_plan batch={batch_number} topics={batch_topic}")
        elif is_weak_drill_flow(mode, practice_type):
            batch_topics = get_weak_drill_batch_topics(drill_topics, batch_count, start_index=len(all_questions))
            if batch_topics:
                batch_topic = ", ".join(batch_topics)
                print(f"weak_drill_topic_plan batch={batch_number} topics={batch_topic}")

        print(f"batch_{batch_number}_start need={batch_count} have={len(all_questions)}/{count}")

        batch_result = _generate_batch_questions(
            exam, subject, batch_topic, batch_count, mode, difficulty,
            selected_chapters, chapter_mode, drill_topics,
            batch_excludes, practice_type
        )

        if batch_result["questions"]:
            all_questions.extend(batch_result["questions"])
            print(f"batch_{batch_number}_done added={len(batch_result['questions'])} total={len(all_questions)}/{count}")
        else:
            err = batch_result.get("error", "Unknown batch error")
            all_errors.append(f"Batch {batch_number}: {err}")
            print(f"batch_{batch_number}_failed error={err}")
            # If a batch completely fails, stop — don't loop forever
            break

    all_questions = finalize_questions_for_delivery(
        all_questions, count, exam, subject, topic, mode, difficulty, practice_type,
        selected_chapters=selected_chapters, drill_topics=drill_topics, exclude_questions=exclude_questions
    )
    all_questions = rebalance_answer_positions(all_questions)

    # Check answer distribution across all batches
    check_answer_distribution(all_questions)

    if all_questions:
        print(f"batching_done total_delivered={len(all_questions)}/{count} batches={batch_number}")
        return {
            "questions": all_questions[:count],
            "error": None,
            "errors": all_errors
        }

    return {
        "questions": [],
        "error": f"All {batch_number} batches failed. Errors: {'; '.join(all_errors)}",
        "errors": all_errors
    }


# ================================================================
# PROMPT BUILDER
# CHANGED: Enhanced with RRB syllabus subtopics, few-shot examples,
# better difficulty descriptions, and stronger generation rules.
# ================================================================

def get_subject_pattern_instruction(subject):
    normalized = str(subject or "").strip().lower()

    if "math" in normalized:
        return """RRB PATTERN FOR MATHEMATICS:
- Use arithmetic, number system, ratio, percentage, profit-loss, SI/CI, time-work, time-distance, algebra, geometry and DI style framing
- Generate numerical MCQs — each question must have a specific calculated answer
- Wrong options must be common calculation mistakes (e.g. forgot to convert units, used wrong formula, arithmetic slip)
- Show full step-by-step calculation in explanation"""

    if "reason" in normalized or "intelligence" in normalized or "mental ability" in normalized:
        return """RRB PATTERN FOR REASONING:
- Use analogy, classification, series, coding-decoding, syllogism, blood relation, direction, ranking, puzzle and statement-based MCQs
- All 4 options must look plausible at first glance — not obviously wrong
- Explanation must show the exact pattern or rule used, step by step
- Keep logic compact and exam-like"""

    if "science" in normalized or "physics" in normalized or "chemistry" in normalized:
        return """RRB PATTERN FOR SCIENCE:
- Mix definition, application, and real-world example questions
- Focus on Class 10 level physics, chemistry and biology concepts
- Wrong options must be scientifically related terms, not random words
- Explanation must include the scientific principle behind the answer"""

    if "awareness" in normalized or "current affairs" in normalized:
        return """RRB PATTERN FOR GENERAL AWARENESS:
- Use static GK: Indian polity, history, geography, economy, awards, sports, railways, science
- Wrong options must be REAL entities (real people, real countries, real years) — not made-up names
- Prefer direct one-answer MCQs
- No opinion-based or essay-style questions"""

    return """RRB PATTERN:
- Keep framing concise, objective and exam-oriented
- Questions should feel like real RRB MCQs, not generic quiz filler"""


def build_prompt(exam, subject, topic, count, mode, difficulty,
                 selected_chapters, chapter_mode, drill_topics, exclude_questions, practice_type):

    # CHANGED: Use richer difficulty descriptions
    diff_desc = DIFFICULTY_DEFINITIONS.get(difficulty, DIFFICULTY_DEFINITIONS["medium"])

    is_chapter_practice = practice_type == "chapter-practice" or mode == "chapter-practice"
    is_weak_drill = practice_type == "weak-drill" or mode == "weak-drill"
    pattern_instruction = get_subject_pattern_instruction(subject)

    # NEW: Get subject subtopics for variety instruction
    subtopics = get_subtopics_for_subject(subject, topic)
    subtopic_note = ""
    if subtopics:
        subtopic_note = f"\nSYLLABUS COVERAGE: Cover varied subtopics from: {', '.join(subtopics[:10])}. Each question must test a DIFFERENT subtopic — no concept repetition within this batch.\n"

    # NEW: Few-shot example for this subject
    example = FEW_SHOT_EXAMPLES.get(subject, FEW_SHOT_EXAMPLES["General Awareness"])
    example_note = f"\nEXAMPLE OF REQUIRED FORMAT (follow this exactly):\n[{example}]\n"

    if is_chapter_practice:
        chapters_str = ", ".join(selected_chapters) if selected_chapters else topic
        if chapter_mode == "fixed_per_topic":
            mode_instruction = f"""SESSION TYPE: Chapter Practice - Fixed Per Topic
- Selected chapters: {chapters_str}
- Generate EXACTLY {count} questions total
- Distribute questions as evenly as possible across the selected chapters
- Every question must come only from these selected chapters"""
        elif chapter_mode == "balanced":
            per_ch = max(1, count // len(selected_chapters)) if selected_chapters else count
            mode_instruction = f"""SESSION TYPE: Chapter Practice - Balanced
- Selected chapters: {chapters_str}
- Generate EXACTLY {count} questions total
- Aim for about {per_ch} questions per selected chapter
- Every question must come only from these selected chapters"""
        else:
            mode_instruction = f"""SESSION TYPE: Chapter Practice - Random Mix
- Selected chapters: {chapters_str}
- Generate EXACTLY {count} questions total
- Mix the selected chapters randomly
- Every question must come only from these selected chapters"""

    elif is_weak_drill:
        weak_topics = get_drill_topic_names(drill_topics)
        weak_str = ", ".join(weak_topics) if weak_topics else topic
        mode_instruction = f"""SESSION TYPE: Weak Topic Drill
- Weak topics: {weak_str}
- Focus on weakest areas with confidence-building but RRB-style questions
- Generate a balanced mix across these weak topics, not only the first topic
- Very detailed step-by-step explanations"""

    elif mode == "practice" and not is_subject_test_flow(mode, practice_type):
        mode_instruction = f"""SESSION TYPE: Topic Practice
- Topic: {topic}
- ALL {count} questions from this exact topic only
- Include shortcut methods in explanations
- Follow actual RRB MCQ framing for this topic"""

    elif mode == "mock":
        mode_instruction = f"""SESSION TYPE: Mock Test
- Subject: {subject}
- Mix questions from multiple topics within {subject}
- Simulate actual exam feel — direct, time-efficient questions"""

    elif mode == "previous-year":
        mode_instruction = f"""SESSION TYPE: Previous Year Style
- Topic: {topic}
- Match style of actual RRB previous year papers exactly
- Focus on commonly repeated patterns in RRB exams"""

    elif mode == "final-mock":
        pattern = EXAM_PATTERNS.get(exam, {})
        sections = pattern.get("sections", {})
        timer = pattern.get("timer_minutes", 90)
        total = pattern.get("total_questions", 100)
        mode_instruction = f"""SESSION TYPE: Final Exam Mock for {exam}
- Timer: {timer} min | Total paper: {total} questions
- Sections: {json.dumps(sections)}
- Generate {count} questions from: {subject}
- Follow exact {exam} exam pattern"""

    elif is_subject_test_flow(mode, practice_type):
        planned_topics = [item.strip() for item in str(topic or "").split(",") if item.strip()]
        syllabus_topics = get_subject_test_topic_order(subject)
        planned_topic_note = ""
        if planned_topics and normalize_text(topic).lower() not in {"all topics", "all", "full subject mix"}:
            planned_topic_note = "\n- This batch topic plan: " + ", ".join(planned_topics)
            topic_assignments = [
                f"Q{index + 1}: {topic_name}"
                for index, topic_name in enumerate(planned_topics[:count])
            ]
            planned_topic_note += "\n- Required per-question topic assignment: " + "; ".join(topic_assignments)
            planned_topic_note += "\n- Generate exactly one question for each assigned topic when possible"
            planned_topic_note += "\n- Do not replace these planned topics with only arithmetic or percentage questions"
            planned_topic_note += "\n- The question text must naturally test its assigned topic"
        elif syllabus_topics:
            planned_topic_note = "\n- Subject syllabus topics available: " + ", ".join(syllabus_topics[:12])
            planned_topic_note += "\n- Distribute questions across different syllabus topics instead of repeating the same concept"
        mode_instruction = f"""SESSION TYPE: Full Subject Test
- Subject: {subject} for {exam}
- Mix from ALL topics in this subject
- Balanced distribution across topics{planned_topic_note}"""

    else:
        mode_instruction = f"""SESSION TYPE: Practice
- Topic: {topic}"""

    exclude_note = ""
    if exclude_questions:
        exclude_note = f"\nDO NOT repeat or closely resemble these questions (already asked): {str(exclude_questions[:3])}"

    return f"""You are an expert MCQ question setter for {exam} railway recruitment exam in India.
This exam tests Class 10 level concepts. Questions are asked by Railway Recruitment Board (RRB) India.

EXAM: {exam}
SUBJECT: {subject}
DIFFICULTY: {diff_desc}

{mode_instruction}
{pattern_instruction}
{subtopic_note}
{example_note}
{exclude_note}

Generate EXACTLY {count} multiple choice questions.

Return ONLY a valid JSON array, no extra text, no markdown:
[
  {{
    "q": "Complete question text here?",
    "opts": ["A) option1", "B) option2", "C) option3", "D) option4"],
    "ans": 0,
    "exp": "Step 1: ... Step 2: ... Step 3: Therefore, the correct answer is option X."
  }}
]

STRICT RULES — FOLLOW ALL:
- ans = 0-indexed: 0=A, 1=B, 2=C, 3=D
- VARY the correct answer position — do not put all answers at index 0 or 1. Spread across 0,1,2,3
- All 4 options must be plausible and related — not obviously wrong
- No "None of the above" or "All of the above"
- No vague questions starting with "Which of the following is correct?" — be direct and specific
- ALL questions and explanations in ENGLISH only
- Each question must end with "?"
- Each question must test a DIFFERENT concept — no repetition within this batch
- Explanation must have minimum 3 steps and must confirm the correct option at the end
- Match real {exam} exam style and difficulty exactly
- Return ONLY the JSON array — absolutely nothing else before or after"""


# ================================================================
# HELPERS
# ================================================================

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Content-Type": "application/json"
    }


def error_response(message):
    return {
        "statusCode": 500,
        "headers": cors_headers(),
        "body": json.dumps({"error": message, "questions": []})
    }








