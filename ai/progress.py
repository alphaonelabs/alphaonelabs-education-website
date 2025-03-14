from typing import Dict, List, Any
from datetime import datetime, timedelta
from .models import ProgressRecord, Interaction, User
from django.db.models import Avg, Sum, Count, Q, F
import json

class ProgressTracker:
    """Tracks and visualizes student progress."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.user = User.objects.get(id=user_id)
    
    def record_interaction(self, interaction_data: Dict[str, Any]) -> None:
        """Record a learning interaction."""
        # Create interaction record
        Interaction.objects.create(
            user=self.user,
            question=interaction_data.get('question', ''),
            answer=interaction_data.get('answer', ''),
            subject=interaction_data.get('subject', 'general'),
            ai_provider=interaction_data.get('provider', 'gemini'),
            feedback_rating=interaction_data.get('feedback_rating'),
            duration=interaction_data.get('duration', 0)
        )
        
        # Update progress if applicable
        if 'topic' in interaction_data and 'mastery_delta' in interaction_data:
            self.update_progress(
                subject=interaction_data['subject'],
                topic=interaction_data['topic'],
                mastery_delta=interaction_data['mastery_delta'],
                study_time=interaction_data.get('duration', 0) // 60,  # convert seconds to minutes
                questions_attempted=1 if interaction_data.get('is_question', False) else 0,
                questions_correct=1 if interaction_data.get('is_correct', False) else 0
            )
    
    def update_progress(self, subject: str, topic: str, mastery_delta: float,
                       study_time: int = 0, questions_attempted: int = 0,
                       questions_correct: int = 0) -> None:
        """Update progress record for a specific topic."""
        progress, created = ProgressRecord.objects.get_or_create(
            user=self.user,
            subject=subject,
            topic=topic,
            defaults={
                'mastery_level': max(0, min(1, mastery_delta)),
                'study_time': study_time,
                'questions_attempted': questions_attempted,
                'questions_correct': questions_correct
            }
        )
        
        if not created:
            # Update existing record
            progress.mastery_level = max(0, min(1, progress.mastery_level + mastery_delta))
            progress.study_time += study_time
            progress.questions_attempted += questions_attempted
            progress.questions_correct += questions_correct
            progress.save()
    
    def analyze_progress(self, timeframe: str = "week") -> Dict[str, Any]:
        """Analyze progress over a given timeframe."""
        # Determine date range based on timeframe
        now = datetime.now()
        if timeframe == "day":
            start_date = now - timedelta(days=1)
        elif timeframe == "week":
            start_date = now - timedelta(days=7)
        elif timeframe == "month":
            start_date = now - timedelta(days=30)
        elif timeframe == "year":
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=7)  # Default to week
        
        # Get recent interactions
        recent_interactions = Interaction.objects.filter(
            user=self.user,
            created_at__gte=start_date
        )
        
        # Get progress records
        progress_records = ProgressRecord.objects.filter(
            user=self.user,
            updated_at__gte=start_date
        )
        
        # Calculate statistics
        total_study_time = progress_records.aggregate(Sum('study_time'))['study_time__sum'] or 0
        total_questions = progress_records.aggregate(Sum('questions_attempted'))['questions_attempted__sum'] or 0
        correct_questions = progress_records.aggregate(Sum('questions_correct'))['questions_correct__sum'] or 0
        accuracy = (correct_questions / total_questions * 100) if total_questions > 0 else 0
        
        # Get subjects studied
        subjects = list(progress_records.values('subject').annotate(
            time_spent=Sum('study_time'),
            avg_mastery=Avg('mastery_level')
        ))
        
        # Get most improved topics
        improved_topics = list(progress_records.filter(
            mastery_level__gt=0.3
        ).order_by('-mastery_level')[:5].values('subject', 'topic', 'mastery_level'))
        
        return {
            "timeframe": timeframe,
            "total_study_time": total_study_time,
            "total_questions": total_questions,
            "correct_questions": correct_questions,
            "accuracy": accuracy,
            "interaction_count": recent_interactions.count(),
            "subjects": subjects,
            "improved_topics": improved_topics
        }
    
    def identify_knowledge_gaps(self) -> Dict[str, List[Dict[str, Any]]]:
        """Identify areas where student needs improvement."""
        # Find topics with low mastery
        low_mastery_topics = list(ProgressRecord.objects.filter(
            user=self.user,
            mastery_level__lt=0.4,
            questions_attempted__gt=0  # Only consider topics the student has attempted
        ).order_by('mastery_level').values('subject', 'topic', 'mastery_level'))
        
        # Find subjects with lower accuracy
        subjects_with_accuracy = list(ProgressRecord.objects.filter(
            user=self.user,
            questions_attempted__gt=0
        ).values('subject').annotate(
            total=Sum('questions_attempted'),
            correct=Sum('questions_correct')
        ).annotate(
            accuracy=100 * F('correct') / F('total')
        ).filter(accuracy__lt=70).order_by('accuracy'))
        
        return {
            "low_mastery_topics": low_mastery_topics,
            "struggling_subjects": subjects_with_accuracy
        }
    
    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate personalized learning recommendations."""
        # Get knowledge gaps
        gaps = self.identify_knowledge_gaps()
        
        # Get strengths (high mastery topics)
        strengths = list(ProgressRecord.objects.filter(
            user=self.user,
            mastery_level__gt=0.8
        ).order_by('-mastery_level')[:5].values('subject', 'topic'))
        
        # Get recently studied topics
        recent = list(ProgressRecord.objects.filter(
            user=self.user
        ).order_by('-updated_at')[:5].values('subject', 'topic'))
        
        # Calculate recommendations based on gaps and recent activity
        recommendations = []
        
        # Add recommendations for low mastery topics
        for topic in gaps.get("low_mastery_topics", [])[:3]:
            recommendations.append({
                "type": "review",
                "subject": topic["subject"],
                "topic": topic["topic"],
                "reason": f"Your mastery level is {int(topic['mastery_level'] * 100)}%. More practice would help.",
                "priority": "high"
            })
        
        # Add recommendations for struggling subjects
        for subject in gaps.get("struggling_subjects", [])[:2]:
            recommendations.append({
                "type": "study_guide",
                "subject": subject["subject"],
                "reason": f"Your accuracy in this subject is {int(subject['accuracy'])}%. A structured review could help.",
                "priority": "medium"
            })
        
        # Add recommendations for building on strengths
        for strength in strengths[:2]:
            recommendations.append({
                "type": "advanced_content",
                "subject": strength["subject"],
                "topic": strength["topic"],
                "reason": "You've mastered this topic. Consider exploring advanced concepts.",
                "priority": "low"
            })
        
        return recommendations
    
    def create_dashboard_data(self) -> Dict[str, Any]:
        """Prepare data for progress dashboard visualization."""
        # Get progress analysis for different timeframes
        week_progress = self.analyze_progress("week")
        month_progress = self.analyze_progress("month")
        
        # Get recommendations
        recommendations = self.generate_recommendations()
        
        # Get subject breakdown
        subjects = list(ProgressRecord.objects.filter(
            user=self.user
        ).values('subject').annotate(
            time_spent=Sum('study_time'),
            topics_count=Count('topic', distinct=True),
            avg_mastery=Avg('mastery_level')
        ))
        
        # Get daily activity data for chart
        last_30_days = [datetime.now().date() - timedelta(days=x) for x in range(30)]
        daily_activity = []
        
        for day in last_30_days:
            day_data = {
                "date": day.strftime("%Y-%m-%d"),
                "interactions": Interaction.objects.filter(
                    user=self.user,
                    created_at__date=day
                ).count(),
                "study_time": ProgressRecord.objects.filter(
                    user=self.user,
                    updated_at__date=day
                ).aggregate(Sum('study_time'))['study_time__sum'] or 0
            }
            daily_activity.append(day_data)
        
        return {
            "week_summary": week_progress,
            "month_summary": month_progress,
            "recommendations": recommendations,
            "subjects": subjects,
            "daily_activity": daily_activity,
            "last_updated": datetime.now().isoformat()
        }
