from typing import Dict, Any, List, Optional
from .services import AIService

class PersonalizedTutor:
    """Provides personalized tutoring based on user's learning profile."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.ai_service = AIService()
        
        # Load user's learning profile
        self.learning_profile = self._load_learning_profile()
    
    def _load_learning_profile(self) -> Dict[str, Any]:
        """Load user's learning profile from progress data."""
        from .progress import ProgressTracker
        from django.contrib.auth.models import User
        
        # Initialize progress tracker
        tracker = ProgressTracker(self.user_id)
        
        # Get user details
        user = User.objects.get(id=self.user_id)
        
        # Analyze progress
        week_progress = tracker.analyze_progress("week")
        
        # Identify knowledge gaps
        gaps = tracker.identify_knowledge_gaps()
        
        return {
            "user_name": user.get_full_name() or user.username,
            "recent_subjects": [s["subject"] for s in week_progress.get("subjects", [])],
            "knowledge_gaps": gaps.get("low_mastery_topics", []),
            "struggling_subjects": gaps.get("struggling_subjects", [])
        }
    
    def ask(self, question: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Ask the tutor a question."""
        # Prepare enhanced prompt with learning profile
        enhanced_prompt = self._enhance_prompt(question, context)
        
        # Get AI response
        from django.contrib.auth.models import User
        user = User.objects.get(id=self.user_id)
        
        response = self.ai_service.get_response(
            user=user,
            message=enhanced_prompt,
            subject=context.get("subject", "general") if context else "general"
        )
        
        return response
    
    def _enhance_prompt(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Enhance the question with user's learning profile and context."""
        prompt_parts = [
            f"As a personalized tutor for {self.learning_profile['user_name']}, please answer the following question.",
            f"The student has recently been studying: {', '.join(self.learning_profile['recent_subjects'][:3])}."
        ]
        
        # Add knowledge gaps if relevant
        if self.learning_profile['knowledge_gaps']:
            topics = [f"{g['subject']}: {g['topic']}" for g in self.learning_profile['knowledge_gaps'][:3]]
            prompt_parts.append(f"They're working to improve in: {', '.join(topics)}.")
        
        # Add context if provided
        if context:
            if 'subject' in context:
                prompt_parts.append(f"This question is about {context['subject']}.")
            if 'difficulty' in context:
                prompt_parts.append(f"Please provide a {context['difficulty']} level explanation.")
        
        # Add the actual question
        prompt_parts.append(f"Question: {question}")
        
        # Add instructions for response
        prompt_parts.append("Please provide a clear, educational answer that helps them understand the concept deeply. Include examples if appropriate.")
        
        return "\n\n".join(prompt_parts)