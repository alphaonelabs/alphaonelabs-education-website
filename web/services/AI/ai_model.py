import google.generativeai as genai
import json
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=r"../../../.env")  # Relative to ai_model.py in web/services/AI/
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file")
genai.configure(api_key=api_key)

AI_prompt_ai_assignment_corrector = '''
You are an AI-powered assignment corrector. Your task is to evaluate student assignments and provide feedback in a structured JSON format.

**Instructions:**

1.  **Grading:** Assign a numerical grade to the student's assignment on a scale of 0 to 10, where 10 represents
    perfect completion and 0 represents no attempt or completely incorrect work.
2.  **Student Feedback:** Provide concise and constructive feedback to the student, focusing on areas of strength
    and areas for improvement. Be specific and actionable.
3.  **Teacher Feedback:** Offer a brief summary of the student's performance for the teacher. Include observations
    about the student's understanding, effort, and any notable patterns or areas requiring further attention.
4.  **Response Format:** Return your response as a JSON object strictly adhering to the following structure:

    ```json
    {
      "degree": <student_degree>,
      "student_feedback": "<student feedback>",
      "teacher_feedback": "<teacher feedback about student performance>"
    }
    ```

**Additional Considerations:**

* **Contextual Information:** If possible, provide the assignment instructions or the expected answers along with
    the student's submission. This will significantly improve the accuracy of the grading and feedback.
* **Specific Subject:** If the assignments are for a particular subject (e.g., mathematics, history, literature),
    specify it in the prompt. This will help you tailor your responses to the subject's specific requirements.
    Example: "You are an AI-powered mathematics assignment corrector..."
* **Length Constraints:** If you need to limit the length of the feedback, specify it in the prompt. Example: 
    "Student feedback should be no more than 100 words."
* **Tone:** If you want to specify the tone of the feedback (e.g., encouraging, critical, neutral), include it in the prompt.
    Example: "Provide feedback in an encouraging and supportive tone."
* **Error Handling:** Add a instruction to handle cases where the submitted assignment is not related to the expected subject,
    or is completely unreadable. Example: "if the submitted assignment is unrelated to the expected subject, or is unreadable,
    return a degree of 0, and explain the reason in the student and teacher feedback."


**Example of a more complete prompt:**
'''


def ai_assignment_corrector(example_form):
    
    # Construct dynamic user input based on example_form
    user_input = f'''
    instructions: {AI_prompt_ai_assignment_corrector}
    Exam_title: '{example_form["title"]}'
    Exam_description: '{example_form["description"]}'
    Student_answer: "{example_form["student_answer"]}"
    '''

    # Initialize the model with 'gemini-1.5-flash'
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Generate response
    try:
        response = model.generate_content(user_input)
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            response_object = json.loads(json_str)
        else:
            raise ValueError("No JSON object found in response")
        
        # print("Parsed response:", response_object)
        return response_object
    
    except Exception as e:
        print(f"Error in AI processing: {e}")
        return {
            "degree": 0,
            "student_feed_back": "Error: Could not evaluate the answer.",
            "teacher_feed_back": "Error: AI failed to process the response."
        }
    




AI_prompt_ai_quiz_corrector = '''
You are an AI-powered assignment corrector. Your task is to evaluate student assignments and provide feedback in a structured JSON format.

**Instructions:**

1.  **Grading:** Assign a numerical grade to the student's assignment on a scale of 0 to question_max_point, where question_max_point represents
    perfect completion and 0 represents no attempt or completely incorrect work.
2.  **Student Feedback:** Provide concise and constructive feedback to the student, focusing on areas of strength
    and areas for improvement. Be specific and actionable. Feedback for every question if it is correction required or marked as false.
3.  **Teacher Feedback:** Offer a brief summary of the student's performance for the teacher. Include observations
    about the student's understanding, effort, and any notable patterns or areas requiring further attention.
4.  **Response Format:** correction: section must have every question, over all feedback: will be one only for all exam . Return your response as a JSON object strictly adhering to the following structure:

    ```json
    correction: 
    {
        "total degree": total_degree,
        "question_id":{
            "degree": <student_degree from 0 to question_max_point>,
            "student_feedback": "<student feedback>",
            "teacher_feedback": "<teacher feedback about student performance>"
        }
    }
    ...
    "over_all_feedback":
    {
        "student_feedback": "<over all exam student feedback about student performance>",
        "teacher_feedback": "<over all exam teacher feedback about student performance>"
    }
    ```

**Additional Considerations:**

* **Contextual Information:** If possible, provide the assignment instructions or the expected answers along with
    the student's submission. This will significantly improve the accuracy of the grading and feedback.
* **Specific Subject:** If the assignments are for a particular subject (e.g., mathematics, history, literature),
    specify it in the prompt. This will help you tailor your responses to the subject's specific requirements.
    Example: "You are an AI-powered mathematics assignment corrector..."
* **Length Constraints:** If you need to limit the length of the feedback, specify it in the prompt. Example: 
    "Student feedback should be no more than 100 words."
* **Tone:** If you want to specify the tone of the feedback (e.g., encouraging, critical, neutral), include it in the prompt.
    Example: "Provide feedback in an encouraging and supportive tone."
* **Error Handling:** Add a instruction to handle cases where the submitted assignment is not related to the expected subject,
    or is completely unreadable. Example: "if the submitted assignment is unrelated to the expected subject, or is unreadable,
    return a degree of 0, and explain the reason in the student and teacher feedback."


**User exam data:**
'''


def ai_quiz_corrector(Exam_data):
    
    # Construct dynamic user input based on example_form
    user_input = f'''
    instructions: {AI_prompt_ai_quiz_corrector}
    Exam_data: {Exam_data}
    '''
    # print("]]]]]]]]]]]]]]]]", user_input)

    # Initialize the model with 'gemini-1.5-flash'
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Generate response
    try:
        response = model.generate_content(user_input)
        # print(",,,,,,,,,,,,,,,,,,,,,", response.text)
        print(",,,,,,,,,,,,,,,,,,,,,", response.text[7:-4])
        # Try to extract JSON from the response
        # json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        # if json_match:
        #     json_str = json_match.group(0)
        #     response_object = json.loads(json_str)
        # else:
        #     raise ValueError("No JSON object found in response")
        
        # print("Parsed response:", response_object)
        return response.text[7:-4]
    
    except Exception as e:
        print(f"Error in AI processing: {e}")
        return {
            "degree": 0,
            "student_feed_back": "Error: Could not evaluate the answer.",
            "teacher_feed_back": "Error: AI failed to process the response."
        }
