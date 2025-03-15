import logging

logger = logging.getLogger(__name__)

def initialize_nltk():
    """Initialize NLTK resources if available."""
    try:
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        return True
    except ImportError:
        logger.warning("NLTK not available. Advanced text analysis features will be limited.")
        return False

def extract_topic_from_text(text, subject):
    """Extract a topic from text, with fallback if NLTK is not available."""
    try:
        import nltk
        from nltk.tokenize import sent_tokenize
        
        # Tokenize text
        sentences = sent_tokenize(text)
        
        # Use first sentence for topic extraction
        if sentences:
            words = sentences[0].split()[:5]
            return ' '.join(words) + '...'
        
    except ImportError:
        pass
    
    # Fallback simple extraction
    words = text.split()[:5]
    return ' '.join(words) + '...'