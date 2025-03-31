from typing import Dict, Any, List, Optional
import logging

from django.contrib.auth.models import User

from .models import Interaction, ProgressRecord, StudentProfile

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Tracks and analyzes user's learning progress."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.user = User.objects.get(id=user_id)
    
    def analyze_progress(self, timeframe: str = "week") -> Dict[str, Any]:
        """Analyze progress for a given timeframe (day, week, month)."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Determine date range
        now = timezone.now()
        if timeframe == "day":
            start_date = now - timedelta(days=1)
        elif timeframe == "week":
            start_date = now - timedelta(days=7)
        elif timeframe == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=7)  # Default to week
        
        # Get recent interactions
        interactions = Interaction.objects.filter(
            user=self.user,
            created_at__gte=start_date
        ).order_by('-created_at')
        
        # Group by subject
        subjects = {}
        for interaction in interactions:
            subject = interaction.subject
            if subject not in subjects:
                subjects[subject] = {
                    "subject": subject,
                    "count": 0,
                    "interactions": []
                }
            subjects[subject]["count"] += 1
            subjects[subject]["interactions"].append({
                "question": interaction.question,
                "created_at": interaction.created_at
            })
        
        # Convert to list and sort by count
        subject_list = list(subjects.values())
        subject_list.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "timeframe": timeframe,
            "total_interactions": interactions.count(),
            "subjects": subject_list
        }
    
    def identify_knowledge_gaps(self) -> Dict[str, List[Dict[str, Any]]]:
        """Identify knowledge gaps based on progress records."""
        # Get progress records
        records = ProgressRecord.objects.filter(user=self.user)
        
        # Find low mastery topics
        low_mastery = []
        for record in records:
            if record.mastery_level < 3:  # Below average mastery
                low_mastery.append({
                    "subject": record.subject,
                    "topic": record.topic,
                    "mastery_level": record.mastery_level,
                    "confidence_score": record.confidence_score
                })
        
        # Find struggling subjects
        subjects = {}
        for record in records:
            if record.subject not in subjects:
                subjects[record.subject] = {
                    "subject": record.subject,
                    "records": [],
                    "avg_mastery": 0
                }
            subjects[record.subject]["records"].append(record)
        
        # Calculate average mastery per subject
        struggling_subjects = []
        for subject, data in subjects.items():
            if data["records"]:
                avg_mastery = sum(r.mastery_level for r in data["records"]) / len(data["records"])
                data["avg_mastery"] = avg_mastery
                if avg_mastery < 3:
                    struggling_subjects.append({
                        "subject": subject,
                        "avg_mastery": avg_mastery
                    })
        
        return {
            "low_mastery_topics": low_mastery,
            "struggling_subjects": struggling_subjects
        }

class PersonalizedTutor:
    """Provides personalized tutoring based on user's learning profile."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        # Load user's learning profile
        self.learning_profile = self._load_learning_profile()
        
        # Import here to avoid circular imports
        from .services.ai_provider import get_ai_provider
        self.ai_provider = get_ai_provider()
    
    def _load_learning_profile(self) -> Dict[str, Any]:
        """Load user's learning profile from progress data."""
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

        try:
            # Get user object
            user = User.objects.get(id=self.user_id)

            # Get or create student profile for context
            profile, created = StudentProfile.objects.get_or_create(user=user)

            # Set up context for AI provider
            ai_context = {
                'subject': context.get("subject", "general") if context else "general",
                'profile': {
                    'learning_style': profile.learning_style,
                    'difficulty_preference': context.get('difficulty', profile.difficulty_preference),
                    'response_length': profile.response_length,
                    'include_examples': profile.include_examples,
                    'include_visuals': profile.include_visuals,
                },
                'user': {
                    'username': user.username,
                }
            }

            # Generate response directly using AI provider
            response_text = self.ai_provider.generate_response(enhanced_prompt, ai_context)

            return {
                'text': response_text,
                'personalized': True,
            }
        except Exception as e:
            # Log the error
            logger.error(f"Error in personalized tutor: {str(e)}")
            
            # Fallback to a simpler response if the AI provider fails
            fallback_response = f"I apologize, but I encountered an issue while processing your question about {context.get('subject', 'this topic') if context else 'this topic'}. Please try again with a simpler question or check your connection."
            
            return {
                'text': fallback_response,
                'personalized': False,
                'error': str(e)
            }
    
    def _enhance_prompt(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Enhance the question with user's learning profile and context."""
        prompt_parts = [
            f"As a personalized tutor for {self.learning_profile['user_name']}, please answer the following question.",
            f"The student has recently been studying: {', '.join(self.learning_profile['recent_subjects'][:3]) if self.learning_profile['recent_subjects'] else 'various subjects'}."
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
