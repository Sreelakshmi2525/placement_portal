# jobs/services.py
import json
import random
from transformers import pipeline, set_seed

class QuestionGenerationService:
    def __init__(self):
        # Initialize the text generation pipeline with GPT-2
        try:
            self.generator = pipeline('text-generation', model='gpt2')
            set_seed(42)  # For reproducibility
        except Exception as e:
            print(f"Error initializing text generation: {str(e)}")
            self.generator = None
    
    def generate_questions(self, job_type, num_questions=5):
        """
        Generate assessment questions using local GPT-2 model
        """
        # If model initialization failed, return fallback questions
        if self.generator is None:
            return self._get_fallback_questions(job_type)
        
        # Define job-specific prompts
        prompts = {
            "developer": "Create assessment questions about programming, software development, coding languages, and web development frameworks.",
            "designer": "Create assessment questions about UI/UX design, wireframing, prototyping, and design software tools.",
            "analyst": "Create assessment questions about data analysis, business intelligence, reporting, and analytical tools.",
            "manager": "Create assessment questions about project management, team leadership, agile methodologies, and stakeholder communication.",
            "data_scientist": "Create assessment questions about machine learning, statistical modeling, data mining, and data visualization."
        }
        
        prompt = prompts.get(job_type, f"Create assessment questions for a {job_type} role.")
        
        try:
            # Generate text using GPT-2
            result = self.generator(prompt, max_length=500, num_return_sequences=1)
            generated_text = result[0]['generated_text']
            
            # Parse the generated text to create questions
            questions_data = self._extract_questions_from_text(generated_text, job_type, num_questions)
            
            return questions_data
            
        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            return self._get_fallback_questions(job_type)
    
    def _extract_questions_from_text(self, text, job_type, num_questions):
        """Extract structured questions from generated text"""
        # This is a simple parser - in production, you'd use more sophisticated NLP
        lines = text.split('\n')
        questions = []
        
        for line in lines:
            if '?' in line and len(questions) < num_questions:
                question_text = line.strip()
                
                # Randomly decide if it's MCQ or rating
                q_type = random.choice(['mcq', 'rating'])
                
                if q_type == 'mcq':
                    # Create options based on job type
                    options = self._generate_options_for_job_type(job_type, question_text)
                    questions.append({
                        'text': question_text,
                        'type': q_type,
                        'options': options
                    })
                else:
                    questions.append({
                        'text': question_text,
                        'type': q_type
                    })
        
        # If we couldn't extract enough questions, add some fallback ones
        while len(questions) < num_questions:
            fallback = self._get_fallback_questions(job_type, 1)[0]
            questions.append(fallback)
        
        return questions[:num_questions]
    
    def _generate_options_for_job_type(self, job_type, question_text):
        """Generate appropriate options based on job type and question"""
        options = []
        
        if job_type == "developer":
            if "language" in question_text.lower() or "programming" in question_text.lower():
                options = [
                    {"text": "Python", "skills": ["Python"]},
                    {"text": "JavaScript", "skills": ["JavaScript"]},
                    {"text": "Java", "skills": ["Java"]},
                    {"text": "C#", "skills": ["C#"]},
                    {"text": "None of the above", "skills": []}
                ]
            elif "framework" in question_text.lower():
                options = [
                    {"text": "React", "skills": ["React", "JavaScript"]},
                    {"text": "Django", "skills": ["Django", "Python"]},
                    {"text": "Angular", "skills": ["Angular", "JavaScript"]},
                    {"text": "Spring", "skills": ["Spring", "Java"]},
                    {"text": "None of the above", "skills": []}
                ]
            else:
                options = [
                    {"text": "Very experienced", "skills": ["Software Development"]},
                    {"text": "Somewhat experienced", "skills": ["Software Development"]},
                    {"text": "Beginner level", "skills": []},
                    {"text": "No experience", "skills": []}
                ]
        elif job_type == "designer":
            options = [
                {"text": "Figma", "skills": ["Figma", "UI Design"]},
                {"text": "Adobe XD", "skills": ["Adobe XD", "UI Design"]},
                {"text": "Sketch", "skills": ["Sketch", "UI Design"]},
                {"text": "None of the above", "skills": []}
            ]
        # Add similar option sets for other job types
        
        return options
    
    def _get_fallback_questions(self, job_type, count=2):
        """Fallback questions if generation fails"""
        developer_questions = [
            {
                "text": "How would you rate your programming skills?",
                "type": "rating"
            },
            {
                "text": "Which programming language are you most comfortable with?",
                "type": "mcq",
                "options": [
                    {"text": "Python", "skills": ["Python"]},
                    {"text": "JavaScript", "skills": ["JavaScript"]},
                    {"text": "Java", "skills": ["Java"]},
                    {"text": "I'm not comfortable with any yet", "skills": []}
                ]
            }
        ]
        
        designer_questions = [
            {
                "text": "How would you rate your design skills?",
                "type": "rating"
            },
            {
                "text": "Which design tool do you use most often?",
                "type": "mcq",
                "options": [
                    {"text": "Figma", "skills": ["Figma", "UI Design"]},
                    {"text": "Adobe XD", "skills": ["Adobe XD", "UI Design"]},
                    {"text": "Sketch", "skills": ["Sketch", "UI Design"]},
                    {"text": "I don't use design tools regularly", "skills": []}
                ]
            }
        ]
        
        # Add similar question sets for other job types
        
        job_questions = {
            "developer": developer_questions,
            "designer": designer_questions,
            # Add other job types here
        }
        
        # Return questions for the specified job type, or generic questions if not found
        return job_questions.get(job_type, [
            {
                "text": f"How would you rate your experience with {job_type} roles?",
                "type": "rating"
            },
            {
                "text": f"Are you interested in pursuing a career as a {job_type}?",
                "type": "mcq",
                "options": [
                    {"text": "Yes, definitely", "skills": []},
                    {"text": "I'm considering it", "skills": []},
                    {"text": "Not sure yet", "skills": []},
                    {"text": "No, I'm exploring options", "skills": []}
                ]
            }
        ])[:count]