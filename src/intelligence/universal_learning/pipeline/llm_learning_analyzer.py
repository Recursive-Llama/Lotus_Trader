"""
LLM Learning Analyzer

Provides LLM-based analysis for learning and braid creation.
This analyzer uses LLM capabilities to analyze clusters and create intelligent braids.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class LLMLearningAnalyzer:
    """
    LLM Learning Analyzer
    
    Provides LLM-based analysis for learning and braid creation.
    This analyzer uses LLM capabilities to analyze clusters and create intelligent braids.
    """
    
    def __init__(self, llm_client, prompt_manager=None):
        """
        Initialize LLM learning analyzer
        
        Args:
            llm_client: LLM client for analysis
            prompt_manager: Prompt manager for template handling
        """
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(__name__)
    
    async def analyze_cluster(
        self, 
        cluster_strands: List[Dict[str, Any]], 
        cluster_type: str,
        strand_type: str
    ) -> Dict[str, Any]:
        """
        Analyze a cluster of strands using LLM
        
        Args:
            cluster_strands: List of strands in the cluster
            cluster_type: Type of cluster
            strand_type: Type of strands
            
        Returns:
            Analysis results dictionary
        """
        try:
            if not cluster_strands:
                return {'error': 'Empty cluster'}
            
            self.logger.info(f"Analyzing cluster of {len(cluster_strands)} {strand_type} strands")
            
            # Prepare cluster data for analysis
            cluster_data = self._prepare_cluster_data(cluster_strands, cluster_type, strand_type)
            
            # Generate analysis prompt
            prompt = self._generate_analysis_prompt(cluster_data, strand_type)
            
            # Get LLM analysis
            analysis = await self._get_llm_analysis(prompt)
            
            # Parse and structure the analysis
            structured_analysis = self._parse_analysis(analysis, cluster_data)
            
            self.logger.info(f"Completed cluster analysis for {strand_type}")
            return structured_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing cluster: {e}")
            return {'error': str(e)}
    
    def _prepare_cluster_data(
        self, 
        cluster_strands: List[Dict[str, Any]], 
        cluster_type: str,
        strand_type: str
    ) -> Dict[str, Any]:
        """Prepare cluster data for LLM analysis"""
        try:
            # Calculate cluster statistics
            scores = {
                'persistence': [s.get('persistence_score', 0.5) for s in cluster_strands],
                'novelty': [s.get('novelty_score', 0.5) for s in cluster_strands],
                'surprise': [s.get('surprise_rating', 0.5) for s in cluster_strands],
                'resonance': [s.get('resonance_score', 0.5) for s in cluster_strands]
            }
            
            avg_scores = {
                metric: sum(values) / len(values) if values else 0.5
                for metric, values in scores.items()
            }
            
            # Extract key information from strands
            strand_summaries = []
            for strand in cluster_strands:
                summary = {
                    'id': strand.get('id', 'unknown'),
                    'created_at': strand.get('created_at', 'unknown'),
                    'scores': {
                        'persistence': strand.get('persistence_score', 0.5),
                        'novelty': strand.get('novelty_score', 0.5),
                        'surprise': strand.get('surprise_rating', 0.5),
                        'resonance': strand.get('resonance_score', 0.5)
                    }
                }
                
                # Add module-specific data
                if strand_type == 'pattern':
                    summary['pattern_data'] = strand.get('module_intelligence', {})
                elif strand_type == 'prediction_review':
                    summary['prediction_data'] = strand.get('content', {})
                elif strand_type == 'conditional_trading_plan':
                    summary['plan_data'] = strand.get('content', {})
                elif strand_type == 'trading_decision':
                    summary['decision_data'] = strand.get('content', {})
                elif strand_type == 'trade_outcome':
                    summary['outcome_data'] = strand.get('content', {})
                
                strand_summaries.append(summary)
            
            return {
                'cluster_type': cluster_type,
                'strand_type': strand_type,
                'strand_count': len(cluster_strands),
                'average_scores': avg_scores,
                'strands': strand_summaries,
                'score_distributions': scores
            }
            
        except Exception as e:
            self.logger.error(f"Error preparing cluster data: {e}")
            return {'error': str(e)}
    
    def _generate_analysis_prompt(self, cluster_data: Dict[str, Any], strand_type: str) -> str:
        """Generate analysis prompt for LLM"""
        try:
            if self.prompt_manager:
                # Use prompt manager if available
                context = {
                    'cluster_data': cluster_data,
                    'strand_type': strand_type,
                    'analysis_type': 'cluster_learning'
                }
                return self.prompt_manager.format_prompt('cluster_analysis', context)
            else:
                # Generate basic prompt
                return self._generate_basic_analysis_prompt(cluster_data, strand_type)
                
        except Exception as e:
            self.logger.error(f"Error generating analysis prompt: {e}")
            return self._generate_basic_analysis_prompt(cluster_data, strand_type)
    
    def _generate_basic_analysis_prompt(self, cluster_data: Dict[str, Any], strand_type: str) -> str:
        """Generate basic analysis prompt without prompt manager"""
        prompt = f"""
Analyze this cluster of {strand_type} strands for learning insights:

Cluster Type: {cluster_data.get('cluster_type', 'unknown')}
Strand Count: {cluster_data.get('strand_count', 0)}
Average Scores: {json.dumps(cluster_data.get('average_scores', {}), indent=2)}

Strand Data:
{json.dumps(cluster_data.get('strands', [])[:5], indent=2)}  # Show first 5 strands

Please provide:
1. Key patterns and insights from this cluster
2. What makes these strands similar/different
3. Learning recommendations for improvement
4. Quality assessment of the cluster
5. Suggestions for braid creation

Format as JSON with keys: insights, patterns, recommendations, quality_assessment, braid_suggestions
"""
        return prompt
    
    async def _get_llm_analysis(self, prompt: str) -> str:
        """Get LLM analysis for the prompt"""
        try:
            if self.llm_client:
                # Use LLM client if available
                response = await self.llm_client.generate_response(prompt)
                return response
            else:
                # Return mock analysis if no LLM client
                return self._generate_mock_analysis()
                
        except Exception as e:
            self.logger.error(f"Error getting LLM analysis: {e}")
            return self._generate_mock_analysis()
    
    def _generate_mock_analysis(self) -> str:
        """Generate mock analysis for testing"""
        return json.dumps({
            "insights": ["Mock analysis - cluster shows consistent patterns", "High resonance scores indicate quality"],
            "patterns": ["Similar scoring patterns across strands", "Consistent module-specific characteristics"],
            "recommendations": ["Continue monitoring this cluster type", "Consider creating braid for learning"],
            "quality_assessment": {"overall_quality": "high", "consistency": "good", "learning_potential": "excellent"},
            "braid_suggestions": ["Create level 2 braid", "Focus on persistence patterns", "Monitor for improvement"]
        })
    
    def _parse_analysis(self, analysis: str, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM analysis into structured format"""
        try:
            # Try to parse as JSON
            if analysis.strip().startswith('{'):
                parsed = json.loads(analysis)
            else:
                # If not JSON, create structured response
                parsed = {
                    "insights": [analysis],
                    "patterns": ["Analysis provided as text"],
                    "recommendations": ["Review analysis for insights"],
                    "quality_assessment": {"overall_quality": "unknown"},
                    "braid_suggestions": ["Consider creating braid"]
                }
            
            # Add metadata
            parsed['metadata'] = {
                'cluster_type': cluster_data.get('cluster_type'),
                'strand_type': cluster_data.get('strand_type'),
                'strand_count': cluster_data.get('strand_count'),
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return parsed
            
        except Exception as e:
            self.logger.error(f"Error parsing analysis: {e}")
            return {
                "insights": ["Error parsing analysis"],
                "patterns": ["Unable to extract patterns"],
                "recommendations": ["Review analysis manually"],
                "quality_assessment": {"overall_quality": "unknown"},
                "braid_suggestions": ["Manual review required"],
                "metadata": {
                    'cluster_type': cluster_data.get('cluster_type'),
                    'strand_type': cluster_data.get('strand_type'),
                    'strand_count': cluster_data.get('strand_count'),
                    'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                    'error': str(e)
                }
            }
    
    async def create_braid_analysis(
        self, 
        braid_data: Dict[str, Any], 
        source_strands: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create analysis for a braid based on source strands
        
        Args:
            braid_data: Braid data dictionary
            source_strands: List of source strands
            
        Returns:
            Braid analysis dictionary
        """
        try:
            # Prepare braid analysis data
            analysis_data = {
                'braid_id': braid_data.get('id'),
                'braid_level': braid_data.get('braid_level'),
                'source_count': len(source_strands),
                'source_strands': [s.get('id') for s in source_strands],
                'braid_scores': {
                    'persistence': braid_data.get('persistence_score', 0.5),
                    'novelty': braid_data.get('novelty_score', 0.5),
                    'surprise': braid_data.get('surprise_rating', 0.5),
                    'resonance': braid_data.get('resonance_score', 0.5)
                }
            }
            
            # Generate braid analysis prompt
            prompt = f"""
Analyze this braid created from {len(source_strands)} source strands:

Braid ID: {braid_data.get('id')}
Braid Level: {braid_data.get('braid_level')}
Scores: {json.dumps(analysis_data['braid_scores'], indent=2)}

Source Strands: {len(source_strands)} strands

Please provide:
1. Braid quality assessment
2. Learning value of this braid
3. Recommendations for further development
4. Potential applications

Format as JSON with keys: quality_assessment, learning_value, recommendations, applications
"""
            
            # Get LLM analysis
            analysis = await self._get_llm_analysis(prompt)
            parsed_analysis = self._parse_analysis(analysis, analysis_data)
            
            return parsed_analysis
            
        except Exception as e:
            self.logger.error(f"Error creating braid analysis: {e}")
            return {'error': str(e)}
