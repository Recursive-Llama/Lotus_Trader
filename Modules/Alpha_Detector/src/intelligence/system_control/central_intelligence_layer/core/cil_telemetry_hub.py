"""
CIL-TelemetryHub: Housekeeping and Metrics

Role: Housekeeping for IDs, versions, metrics; no "thinking".
- Keeps detector versions, dq flags, time lattice metrics
- Publishes light dashboards for Orchestrator decisions
- Maintains system health metrics and performance tracking

Think: the mechanical housekeeper that tracks everything.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


@dataclass
class SystemMetrics:
    """System metrics data structure"""
    timestamp: datetime
    active_experiments: int
    completed_experiments: int
    active_hypotheses: int
    completed_hypotheses: int
    motif_cards: int
    confluence_events: int
    doctrine_entries: int
    lessons_count: int
    system_health: float
    performance_score: float


@dataclass
class DetectorVersion:
    """Detector version data structure"""
    detector_name: str
    version: str
    last_updated: datetime
    status: str  # active, deprecated, error
    performance_metrics: Dict[str, Any]


@dataclass
class DataQualityFlag:
    """Data quality flag data structure"""
    flag_id: str
    flag_type: str  # missing_data, corrupted_data, stale_data, anomaly
    severity: str  # low, medium, high, critical
    description: str
    affected_components: List[str]
    created_at: datetime
    resolved_at: Optional[datetime] = None


class CILTelemetryHub:
    """
    CIL-TelemetryHub: Housekeeping and Metrics
    
    Responsibilities:
    - Keeps detector versions, dq flags, time lattice metrics
    - Publishes light dashboards for Orchestrator decisions
    - Maintains system health metrics and performance tracking
    - No "thinking" - pure mechanical housekeeping
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Telemetry Management
        self.system_metrics: Dict[str, SystemMetrics] = {}
        self.detector_versions: Dict[str, DetectorVersion] = {}
        self.data_quality_flags: Dict[str, DataQualityFlag] = {}
        
        # Telemetry Configuration
        self.metrics_collection_interval_minutes = 5
        self.dashboard_update_interval_minutes = 15
        self.health_check_interval_minutes = 10
        
    async def initialize(self):
        """Initialize the telemetry hub"""
        try:
            # Load existing telemetry data
            await self._load_existing_telemetry()
            
            # Start telemetry collection loop
            asyncio.create_task(self._telemetry_collection_loop())
            
            # Start dashboard update loop
            asyncio.create_task(self._dashboard_update_loop())
            
            # Start health check loop
            asyncio.create_task(self._health_check_loop())
            
            print("✅ CIL-TelemetryHub initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ CIL-TelemetryHub initialization failed: {e}")
            return False
    
    async def _telemetry_collection_loop(self):
        """Main telemetry collection loop"""
        while True:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Update detector versions
                await self._update_detector_versions()
                
                # Check data quality
                await self._check_data_quality()
                
                # Wait before next iteration
                await asyncio.sleep(self.metrics_collection_interval_minutes * 60)
                
            except Exception as e:
                print(f"Error in telemetry collection loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _dashboard_update_loop(self):
        """Dashboard update loop"""
        while True:
            try:
                # Update dashboard metrics
                await self._update_dashboard_metrics()
                
                # Wait before next iteration
                await asyncio.sleep(self.dashboard_update_interval_minutes * 60)
                
            except Exception as e:
                print(f"Error in dashboard update loop: {e}")
                await asyncio.sleep(900)  # Wait 15 minutes on error
    
    async def _health_check_loop(self):
        """Health check loop"""
        while True:
            try:
                # Perform health checks
                await self._perform_health_checks()
                
                # Wait before next iteration
                await asyncio.sleep(self.health_check_interval_minutes * 60)
                
            except Exception as e:
                print(f"Error in health check loop: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error
    
    async def _collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # Query for current system state
            queries = {
                'active_experiments': "SELECT COUNT(*) as count FROM AD_strands WHERE kind = 'experiment' AND status = 'active'",
                'completed_experiments': "SELECT COUNT(*) as count FROM AD_strands WHERE kind = 'experiment' AND status = 'completed'",
                'active_hypotheses': "SELECT COUNT(*) as count FROM AD_strands WHERE kind = 'hypothesis' AND status = 'active'",
                'completed_hypotheses': "SELECT COUNT(*) as count FROM AD_strands WHERE kind = 'hypothesis' AND status = 'completed'",
                'motif_cards': "SELECT COUNT(*) as count FROM AD_strands WHERE kind = 'motif'",
                'confluence_events': "SELECT COUNT(*) as count FROM AD_strands WHERE kind = 'confluence_event'",
                'doctrine_entries': "SELECT COUNT(*) as count FROM AD_strands WHERE doctrine_status IS NOT NULL",
                'lessons_count': "SELECT COUNT(*) as count FROM AD_strands WHERE kind = 'lesson'"
            }
            
            metrics_data = {}
            for metric_name, query in queries.items():
                try:
                    result = await self.supabase_manager.execute_query(query)
                    metrics_data[metric_name] = result[0]['count'] if result else 0
                except Exception as e:
                    print(f"Error collecting {metric_name}: {e}")
                    metrics_data[metric_name] = 0
            
            # Calculate system health and performance
            system_health = await self._calculate_system_health(metrics_data)
            performance_score = await self._calculate_performance_score(metrics_data)
            
            # Create system metrics
            timestamp = datetime.now(timezone.utc)
            metrics = SystemMetrics(
                timestamp=timestamp,
                active_experiments=metrics_data['active_experiments'],
                completed_experiments=metrics_data['completed_experiments'],
                active_hypotheses=metrics_data['active_hypotheses'],
                completed_hypotheses=metrics_data['completed_hypotheses'],
                motif_cards=metrics_data['motif_cards'],
                confluence_events=metrics_data['confluence_events'],
                doctrine_entries=metrics_data['doctrine_entries'],
                lessons_count=metrics_data['lessons_count'],
                system_health=system_health,
                performance_score=performance_score
            )
            
            # Store metrics
            metrics_key = timestamp.strftime('%Y%m%d_%H%M%S')
            self.system_metrics[metrics_key] = metrics
            
            print(f"✅ Collected system metrics (health: {system_health:.2f}, performance: {performance_score:.2f})")
            
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
    
    async def _calculate_system_health(self, metrics_data: Dict[str, int]) -> float:
        """Calculate system health score"""
        try:
            # Simple health calculation based on activity
            total_activity = sum(metrics_data.values())
            
            if total_activity == 0:
                return 0.0
            
            # Health based on balance of activities
            active_ratio = metrics_data['active_experiments'] / max(metrics_data['completed_experiments'], 1)
            hypothesis_ratio = metrics_data['active_hypotheses'] / max(metrics_data['completed_hypotheses'], 1)
            
            # Normalize to 0-1 range
            health_score = min(1.0, (active_ratio + hypothesis_ratio) / 2.0)
            
            return health_score
            
        except Exception as e:
            print(f"Error calculating system health: {e}")
            return 0.5
    
    async def _calculate_performance_score(self, metrics_data: Dict[str, int]) -> float:
        """Calculate performance score"""
        try:
            # Performance based on completion rates
            total_experiments = metrics_data['active_experiments'] + metrics_data['completed_experiments']
            total_hypotheses = metrics_data['active_hypotheses'] + metrics_data['completed_hypotheses']
            
            if total_experiments == 0 and total_hypotheses == 0:
                return 0.0
            
            experiment_completion_rate = metrics_data['completed_experiments'] / max(total_experiments, 1)
            hypothesis_completion_rate = metrics_data['completed_hypotheses'] / max(total_hypotheses, 1)
            
            # Average completion rate
            performance_score = (experiment_completion_rate + hypothesis_completion_rate) / 2.0
            
            return performance_score
            
        except Exception as e:
            print(f"Error calculating performance score: {e}")
            return 0.5
    
    async def _update_detector_versions(self):
        """Update detector versions"""
        try:
            # Query for detector versions
            query = """
                SELECT 
                    detector_name,
                    version,
                    last_updated,
                    status,
                    performance_metrics
                FROM detector_versions
                ORDER BY last_updated DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                detector_version = DetectorVersion(
                    detector_name=row['detector_name'],
                    version=row['version'],
                    last_updated=row['last_updated'],
                    status=row['status'],
                    performance_metrics=row.get('performance_metrics', {})
                )
                
                self.detector_versions[detector_version.detector_name] = detector_version
                
        except Exception as e:
            print(f"Error updating detector versions: {e}")
    
    async def _check_data_quality(self):
        """Check data quality and flag issues"""
        try:
            # Check for missing data
            await self._check_missing_data()
            
            # Check for stale data
            await self._check_stale_data()
            
            # Check for anomalies
            await self._check_data_anomalies()
            
        except Exception as e:
            print(f"Error checking data quality: {e}")
    
    async def _check_missing_data(self):
        """Check for missing data"""
        try:
            # Check for missing market data
            query = """
                SELECT COUNT(*) as count
                FROM alpha_market_data_1m
                WHERE created_at > NOW() - INTERVAL '1 hour'
            """
            
            result = await self.supabase_manager.execute_query(query)
            recent_data_count = result[0]['count'] if result else 0
            
            if recent_data_count == 0:
                # Flag missing data
                flag_id = f"missing_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                flag = DataQualityFlag(
                    flag_id=flag_id,
                    flag_type='missing_data',
                    severity='high',
                    description='No market data received in the last hour',
                    affected_components=['market_data_collection', 'signal_generation'],
                    created_at=datetime.now(timezone.utc)
                )
                
                self.data_quality_flags[flag_id] = flag
                print(f"⚠️ Data quality flag: {flag.description}")
                
        except Exception as e:
            print(f"Error checking missing data: {e}")
    
    async def _check_stale_data(self):
        """Check for stale data"""
        try:
            # Check for stale strands
            query = """
                SELECT COUNT(*) as count
                FROM AD_strands
                WHERE created_at < NOW() - INTERVAL '24 hours'
                AND status = 'active'
            """
            
            result = await self.supabase_manager.execute_query(query)
            stale_count = result[0]['count'] if result else 0
            
            if stale_count > 100:  # Threshold for stale data
                # Flag stale data
                flag_id = f"stale_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                flag = DataQualityFlag(
                    flag_id=flag_id,
                    flag_type='stale_data',
                    severity='medium',
                    description=f'{stale_count} active strands are older than 24 hours',
                    affected_components=['strand_management', 'experiment_tracking'],
                    created_at=datetime.now(timezone.utc)
                )
                
                self.data_quality_flags[flag_id] = flag
                print(f"⚠️ Data quality flag: {flag.description}")
                
        except Exception as e:
            print(f"Error checking stale data: {e}")
    
    async def _check_data_anomalies(self):
        """Check for data anomalies"""
        try:
            # Check for unusual signal volumes
            query = """
                SELECT COUNT(*) as count
                FROM AD_strands
                WHERE kind = 'signal'
                AND created_at > NOW() - INTERVAL '1 hour'
            """
            
            result = await self.supabase_manager.execute_query(query)
            recent_signals = result[0]['count'] if result else 0
            
            # Compare with historical average (simplified)
            if recent_signals > 1000:  # Threshold for anomaly
                # Flag anomaly
                flag_id = f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                flag = DataQualityFlag(
                    flag_id=flag_id,
                    flag_type='anomaly',
                    severity='medium',
                    description=f'Unusually high signal volume: {recent_signals} signals in last hour',
                    affected_components=['signal_generation', 'pattern_detection'],
                    created_at=datetime.now(timezone.utc)
                )
                
                self.data_quality_flags[flag_id] = flag
                print(f"⚠️ Data quality flag: {flag.description}")
                
        except Exception as e:
            print(f"Error checking data anomalies: {e}")
    
    async def _update_dashboard_metrics(self):
        """Update dashboard metrics for Orchestrator"""
        try:
            # Get latest system metrics
            if not self.system_metrics:
                return
            
            latest_metrics = max(self.system_metrics.values(), key=lambda m: m.timestamp)
            
            # Create dashboard data
            dashboard_data = {
                'timestamp': latest_metrics.timestamp.isoformat(),
                'system_health': latest_metrics.system_health,
                'performance_score': latest_metrics.performance_score,
                'active_experiments': latest_metrics.active_experiments,
                'active_hypotheses': latest_metrics.active_hypotheses,
                'motif_cards': latest_metrics.motif_cards,
                'confluence_events': latest_metrics.confluence_events,
                'doctrine_entries': latest_metrics.doctrine_entries,
                'lessons_count': latest_metrics.lessons_count,
                'data_quality_flags': len(self.data_quality_flags),
                'detector_versions': len(self.detector_versions)
            }
            
            # Publish dashboard metrics
            await self._publish_dashboard_metrics(dashboard_data)
            
        except Exception as e:
            print(f"Error updating dashboard metrics: {e}")
    
    async def _publish_dashboard_metrics(self, dashboard_data: Dict[str, Any]):
        """Publish dashboard metrics to database"""
        try:
            strand_data = {
                'kind': 'dashboard_metrics',
                'module': 'alpha',
                'tags': [f"agent:central_intelligence:telemetry_hub:dashboard_updated"],
                'dashboard_data': dashboard_data,
                'team_member': 'telemetry_hub'
            }
            
            await self.supabase_manager.insert_strand(strand_data)
            
        except Exception as e:
            print(f"Error publishing dashboard metrics: {e}")
    
    async def _perform_health_checks(self):
        """Perform system health checks"""
        try:
            # Check database connectivity
            await self._check_database_connectivity()
            
            # Check LLM connectivity
            await self._check_llm_connectivity()
            
            # Check system resources
            await self._check_system_resources()
            
        except Exception as e:
            print(f"Error performing health checks: {e}")
    
    async def _check_database_connectivity(self):
        """Check database connectivity"""
        try:
            # Simple connectivity test
            query = "SELECT 1 as test"
            result = await self.supabase_manager.execute_query(query)
            
            if result and result[0]['test'] == 1:
                print("✅ Database connectivity: OK")
            else:
                print("❌ Database connectivity: FAILED")
                
        except Exception as e:
            print(f"❌ Database connectivity: ERROR - {e}")
    
    async def _check_llm_connectivity(self):
        """Check LLM connectivity"""
        try:
            # Simple LLM test
            response = await self.llm_client.generate_response(
                prompt="Test connectivity",
                model="anthropic/claude-3.5-sonnet",
                max_tokens=10,
                temperature=0.1
            )
            
            if response:
                print("✅ LLM connectivity: OK")
            else:
                print("❌ LLM connectivity: FAILED")
                
        except Exception as e:
            print(f"❌ LLM connectivity: ERROR - {e}")
    
    async def _check_system_resources(self):
        """Check system resources"""
        try:
            # Check memory usage (simplified)
            import psutil
            
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent()
            
            if memory_percent > 90:
                print(f"⚠️ High memory usage: {memory_percent}%")
            else:
                print(f"✅ Memory usage: {memory_percent}%")
            
            if cpu_percent > 90:
                print(f"⚠️ High CPU usage: {cpu_percent}%")
            else:
                print(f"✅ CPU usage: {cpu_percent}%")
                
        except Exception as e:
            print(f"Error checking system resources: {e}")
    
    async def _load_existing_telemetry(self):
        """Load existing telemetry data"""
        try:
            # Load existing metrics
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'dashboard_metrics'
                ORDER BY created_at DESC
                LIMIT 100
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                # Parse dashboard data
                dashboard_data = row.get('dashboard_data', {})
                if dashboard_data:
                    timestamp = datetime.fromisoformat(dashboard_data['timestamp'].replace('Z', '+00:00'))
                    
                    metrics = SystemMetrics(
                        timestamp=timestamp,
                        active_experiments=dashboard_data.get('active_experiments', 0),
                        completed_experiments=dashboard_data.get('completed_experiments', 0),
                        active_hypotheses=dashboard_data.get('active_hypotheses', 0),
                        completed_hypotheses=dashboard_data.get('completed_hypotheses', 0),
                        motif_cards=dashboard_data.get('motif_cards', 0),
                        confluence_events=dashboard_data.get('confluence_events', 0),
                        doctrine_entries=dashboard_data.get('doctrine_entries', 0),
                        lessons_count=dashboard_data.get('lessons_count', 0),
                        system_health=dashboard_data.get('system_health', 0.0),
                        performance_score=dashboard_data.get('performance_score', 0.0)
                    )
                    
                    metrics_key = timestamp.strftime('%Y%m%d_%H%M%S')
                    self.system_metrics[metrics_key] = metrics
                    
        except Exception as e:
            print(f"Warning: Could not load existing telemetry: {e}")
    
    async def get_telemetry_status(self) -> Dict[str, Any]:
        """Get current telemetry status"""
        return {
            'system_metrics_count': len(self.system_metrics),
            'detector_versions_count': len(self.detector_versions),
            'data_quality_flags_count': len(self.data_quality_flags),
            'metrics_collection_interval_minutes': self.metrics_collection_interval_minutes,
            'dashboard_update_interval_minutes': self.dashboard_update_interval_minutes,
            'health_check_interval_minutes': self.health_check_interval_minutes
        }
    
    async def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get latest system metrics"""
        if not self.system_metrics:
            return None
        
        return max(self.system_metrics.values(), key=lambda m: m.timestamp)
    
    async def get_data_quality_flags(self) -> List[DataQualityFlag]:
        """Get current data quality flags"""
        return list(self.data_quality_flags.values())
    
    async def resolve_data_quality_flag(self, flag_id: str):
        """Resolve a data quality flag"""
        try:
            if flag_id in self.data_quality_flags:
                flag = self.data_quality_flags[flag_id]
                flag.resolved_at = datetime.now(timezone.utc)
                print(f"✅ Resolved data quality flag: {flag_id}")
                
        except Exception as e:
            print(f"Error resolving data quality flag: {e}")

