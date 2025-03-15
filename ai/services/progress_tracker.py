import re
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import logging

from ..models import ProgressRecord, Interaction

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Tracks and updates user learning progress based on interactions."""
    
    def __init__(self, user):
        self.user = user
        
        # Initialize NLTK if not already done
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
    
    def extract_topics(self, text, subject):
        """Extract potential topics from text using NLP techniques."""
        # Simple topic extraction based on keywords and phrases
        try:
            # Tokenize text
            sentences = sent_tokenize(text.lower())
            
            # Define subject-specific keywords
            subject_keywords = {
                'mathematics': ['theorem', 'equation', 'formula', 'calculus', 'algebra', 'geometry', 
                               'function', 'variable', 'derivative', 'integral', 'matrix'],
                'science': ['theory', 'experiment', 'hypothesis', 'physics', 'chemistry', 'biology',
                           'molecule', 'atom', 'cell', 'reaction', 'force', 'energy'],
                'programming': ['algorithm', 'function', 'class', 'object', 'variable', 'loop',
                               'condition', 'api', 'database', 'interface', 'library'],
                'history': ['century', 'war', 'revolution', 'empire', 'civilization', 'dynasty',
                           'president', 'king', 'queen', 'monarch', 'government'],
                'languages': ['grammar', 'vocabulary', 'pronunciation', 'conjugation', 'tense',
                             'verb', 'noun', 'adjective', 'adverb', 'preposition']
            }
            
            # Get keywords for the subject
            keywords = subject_keywords.get(subject, [])
            
            # Find sentences with keywords
            topic_sentences = []
            for sentence in sentences:
                if any(keyword in sentence for keyword in keywords):
                    topic_sentences.append(sentence)
            
            # Use the first topic sentence or a generic topic based on subject
            if topic_sentences:
                # Extract a snippet (first 5 words) as the topic
                words = topic_sentences[0].split()
                topic = ' '.join(words[:5]) + '...'
            else:
                # Use a generic topic based on first sentence
                words = sentences[0].split() if sentences else [subject]
                topic = ' '.join(words[:5]) + '...'
            
            return topic.capitalize()
            
        except Exception as e:
            logger.warning(f"Error extracting topics: {str(e)}")
            return subject.capitalize()
    
    def calculate_mastery(self, question, answer, subject, previous_level=None):
        """Calculate mastery level based on the interaction."""
        try:
            # Start with previous level or default to 1
            base_level = previous_level or 1
            
            # Basic factors to consider
            factors = {
                'question_complexity': 0,  # -1 to 1
                'answer_quality': 0,       # -1 to 1
                'follow_up': 0             # -0.5 to 0.5
            }
            
            # Assess question complexity
            question_words = len(question.split())
            if question_words < 10:
                factors['question_complexity'] = -0.5  # Simple question
            elif question_words > 30:
                factors['question_complexity'] = 0.5   # Complex question
            
            # Check for complexity indicators in the question
            complexity_indicators = ['why', 'how', 'explain', 'analyze', 'compare', 'evaluate', 'synthesize']
            if any(indicator in question.lower() for indicator in complexity_indicators):
                factors['question_complexity'] += 0.5
            
            # Assess answer quality based on length and details
            answer_words = len(answer.split())
            if answer_words > 200:
                factors['answer_quality'] = 0.5  # Detailed answer suggests understanding
            
            # Look for follow-up questions from the user (previous interactions)
            recent_interactions = Interaction.objects.filter(
                user=self.user, 
                subject=subject
            ).order_by('-created_at')[:5]
            
            if recent_interactions.count() > 1:
                # User is asking follow-up questions, showing engagement
                factors['follow_up'] = 0.3
            
            # Calculate overall adjustment
            adjustment = sum(factors.values())
            
            # Calculate new mastery level with limits
            new_level = min(max(base_level + adjustment, 1), 5)
            
            # For first few interactions, progress more quickly
            if base_level == 1 and new_level < 2:
                new_level = min(base_level + 0.5, 5)
            
            return new_level
            
        except Exception as e:
            logger.warning(f"Error calculating mastery: {str(e)}")
            return previous_level or 1
    
    def update_progress(self, question, answer, subject):
        """Update the user's progress based on a new interaction."""
        try:
            # Extract topic
            topic = self.extract_topics(question + " " + answer, subject)
            
            # Try to get existing record or create new one
            record, created = ProgressRecord.objects.get_or_create(
                user=self.user,
                subject=subject,
                topic=topic,
                defaults={
                    'mastery_level': 1,
                    'confidence_score': 0.2
                }
            )
            
            # Update mastery level
            if not created:
                new_mastery = self.calculate_mastery(
                    question, answer, subject, record.mastery_level
                )
                record.mastery_level = new_mastery
                
                # Update confidence score (increases slightly with each interaction)
                record.confidence_score = min(1.0, record.confidence_score + 0.05)
                
                record.save()
            
            return record
            
        except Exception as e:
            logger.error(f"Error updating progress: {str(e)}")
            return None