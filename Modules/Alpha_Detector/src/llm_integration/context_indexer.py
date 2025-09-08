"""
ContextIndexer: Creates vector embeddings and categorizes database content
Converts database records into searchable context vectors
"""

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

class ContextIndexer:
    """
    Creates vector embeddings and categorizes database content
    Converts database records into searchable context vectors
    """
    
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the context indexer
        
        Args:
            embedding_model_name: Name of the sentence transformer model to use
        """
        self.embedding_model_name = embedding_model_name
        self.embedding_model = None
        self.column_categories = self._analyze_column_categories()
        self._initialize_embedding_model()
    
    def _initialize_embedding_model(self):
        """Initialize the sentence transformer model"""
        try:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _analyze_column_categories(self) -> Dict[str, List[str]]:
        """Analyze database columns and categorize them"""
        
        return {
            'market_data': ['symbol', 'timeframe', 'regime', 'volatility', 'session_bucket'],
            'signal_data': ['sig_direction', 'sig_confidence', 'sig_sigma', 'kind'],
            'pattern_data': ['patterns', 'breakouts', 'divergences', 'support_levels', 'resistance_levels'],
            'performance_data': ['outcome', 'performance_score', 'execution_quality', 'accumulated_score'],
            'context_data': ['market_conditions', 'event_context', 'regime_context'],
            'learning_data': ['lesson', 'source_strands', 'clustering_columns', 'braid_level']
        }
    
    def create_context_vector(self, analysis_data: Dict) -> np.ndarray:
        """
        Create vector embedding for current analysis
        
        Args:
            analysis_data: Dictionary containing analysis data
            
        Returns:
            Vector embedding as numpy array
        """
        try:
            # Convert analysis to context string
            context_string = self._create_context_string(analysis_data)
            
            # Generate embedding
            embedding = self.embedding_model.encode(context_string)
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to create context vector: {e}")
            raise
    
    def _create_context_string(self, data: Dict) -> str:
        """
        Convert data to searchable context string
        
        Args:
            data: Dictionary containing data to convert
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add key analysis components
        if 'symbol' in data:
            context_parts.append(f"Symbol: {data['symbol']}")
        if 'timeframe' in data:
            context_parts.append(f"Timeframe: {data['timeframe']}")
        if 'regime' in data:
            context_parts.append(f"Regime: {data['regime']}")
        if 'sig_direction' in data:
            context_parts.append(f"Direction: {data['sig_direction']}")
        if 'sig_confidence' in data:
            context_parts.append(f"Confidence: {data['sig_confidence']:.2f}")
        if 'sig_sigma' in data:
            context_parts.append(f"Strength: {data['sig_sigma']:.2f}")
        
        # Add patterns if available
        if 'patterns' in data:
            if isinstance(data['patterns'], dict):
                pattern_list = []
                for key, value in data['patterns'].items():
                    if value:
                        pattern_list.append(key)
                if pattern_list:
                    context_parts.append(f"Patterns: {', '.join(pattern_list)}")
            elif isinstance(data['patterns'], list):
                context_parts.append(f"Patterns: {', '.join(data['patterns'])}")
        
        # Add features if available
        if 'features' in data:
            key_features = self._extract_key_features(data['features'])
            if key_features:
                context_parts.append(f"Features: {key_features}")
        
        # Add market conditions
        if 'market_conditions' in data:
            conditions = data['market_conditions']
            if isinstance(conditions, dict):
                condition_parts = []
                for key, value in conditions.items():
                    if value:
                        condition_parts.append(f"{key}: {value}")
                if condition_parts:
                    context_parts.append(f"Market: {', '.join(condition_parts)}")
        
        # Add learning context if available
        if 'lesson' in data and data['lesson']:
            context_parts.append(f"Lesson: {str(data['lesson'])[:100]}...")
        
        return " | ".join(context_parts)
    
    def _extract_key_features(self, features: Dict) -> str:
        """
        Extract key features from feature dictionary
        
        Args:
            features: Dictionary of features
            
        Returns:
            String of key features
        """
        key_features = []
        
        # Look for important technical indicators
        important_indicators = ['rsi', 'macd', 'bb_position', 'volume_ratio', 'volatility']
        
        for indicator in important_indicators:
            if indicator in features:
                value = features[indicator]
                if isinstance(value, (int, float)):
                    key_features.append(f"{indicator}: {value:.2f}")
                elif isinstance(value, bool):
                    key_features.append(f"{indicator}: {value}")
        
        return ", ".join(key_features)
    
    def create_database_context_vectors(self, database_records: List[Dict]) -> List[Dict]:
        """
        Create context vectors for multiple database records
        
        Args:
            database_records: List of database records
            
        Returns:
            List of records with added context vectors
        """
        enhanced_records = []
        
        for record in database_records:
            try:
                # Create context vector
                context_vector = self.create_context_vector(record)
                
                # Add vector to record
                enhanced_record = record.copy()
                enhanced_record['context_vector'] = context_vector.tolist()
                enhanced_record['context_string'] = self._create_context_string(record)
                enhanced_record['vector_created_at'] = datetime.now(timezone.utc).isoformat()
                
                enhanced_records.append(enhanced_record)
                
            except Exception as e:
                logger.warning(f"Failed to create context vector for record: {e}")
                # Add record without vector
                enhanced_record = record.copy()
                enhanced_record['context_vector'] = None
                enhanced_record['context_string'] = self._create_context_string(record)
                enhanced_record['vector_created_at'] = datetime.now(timezone.utc).isoformat()
                enhanced_records.append(enhanced_record)
        
        return enhanced_records
    
    def categorize_record(self, record: Dict) -> Dict[str, Any]:
        """
        Categorize a database record by column types
        
        Args:
            record: Database record to categorize
            
        Returns:
            Categorized record with column categories
        """
        categorized = {
            'record_id': record.get('id', 'unknown'),
            'categories': {}
        }
        
        for category, columns in self.column_categories.items():
            categorized['categories'][category] = {}
            for column in columns:
                if column in record:
                    categorized['categories'][category][column] = record[column]
        
        return categorized
    
    def get_similarity_score(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vector1: First vector
            vector2: Second vector
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Calculate cosine similarity
            dot_product = np.dot(vector1, vector2)
            norm1 = np.linalg.norm(vector1)
            norm2 = np.linalg.norm(vector2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))  # Clamp between 0 and 1
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def batch_create_vectors(self, records: List[Dict], batch_size: int = 32) -> List[Dict]:
        """
        Create context vectors for multiple records in batches
        
        Args:
            records: List of database records
            batch_size: Number of records to process at once
            
        Returns:
            List of records with context vectors
        """
        enhanced_records = []
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            try:
                # Create context strings for batch
                context_strings = [self._create_context_string(record) for record in batch]
                
                # Generate embeddings for batch
                embeddings = self.embedding_model.encode(context_strings)
                
                # Add vectors to records
                for j, record in enumerate(batch):
                    enhanced_record = record.copy()
                    enhanced_record['context_vector'] = embeddings[j].tolist()
                    enhanced_record['context_string'] = context_strings[j]
                    enhanced_record['vector_created_at'] = datetime.now(timezone.utc).isoformat()
                    enhanced_records.append(enhanced_record)
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}")
                
            except Exception as e:
                logger.error(f"Failed to process batch {i//batch_size + 1}: {e}")
                # Add records without vectors
                for record in batch:
                    enhanced_record = record.copy()
                    enhanced_record['context_vector'] = None
                    enhanced_record['context_string'] = self._create_context_string(record)
                    enhanced_record['vector_created_at'] = datetime.now(timezone.utc).isoformat()
                    enhanced_records.append(enhanced_record)
        
        return enhanced_records
