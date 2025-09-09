"""
Learning System Monitoring

This module provides monitoring, metrics, and error handling for the learning system.
It tracks performance, errors, and provides alerting capabilities.

Features:
1. Performance metrics tracking
2. Error monitoring and recovery
3. Learning event logging
4. Alert system for critical issues
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert levels for monitoring"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LearningMetric:
    """Learning system metric"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class LearningEvent:
    """Learning system event"""
    event_type: str
    message: str
    level: AlertLevel
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """Error information for monitoring"""
    error_type: str
    message: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False


class LearningMonitor:
    """Monitors learning system performance and errors"""
    
    def __init__(self, config_manager=None):
        """
        Initialize learning monitor
        
        Args:
            config_manager: Configuration manager for monitoring settings
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Metrics storage
        self.metrics: List[LearningMetric] = []
        self.events: List[LearningEvent] = []
        self.errors: List[ErrorInfo] = []
        
        # Performance tracking
        self.performance_stats = {
            'total_strands_processed': 0,
            'total_braids_created': 0,
            'total_predictions_tracked': 0,
            'total_plans_created': 0,
            'avg_processing_time': 0.0,
            'success_rate': 0.0,
            'error_rate': 0.0
        }
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.metrics_retention_days = 7
        self.max_metrics = 10000
        self.max_events = 1000
        self.max_errors = 500
    
    def track_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Track a metric"""
        try:
            if not self.monitoring_enabled:
                return
            
            metric = LearningMetric(
                name=name,
                value=value,
                timestamp=datetime.now(timezone.utc),
                tags=tags or {}
            )
            
            self.metrics.append(metric)
            
            # Cleanup old metrics
            self._cleanup_old_metrics()
            
            self.logger.debug(f"Tracked metric: {name}={value}")
            
        except Exception as e:
            self.logger.error(f"Error tracking metric: {e}")
    
    def log_event(self, event_type: str, message: str, level: AlertLevel = AlertLevel.INFO, data: Optional[Dict[str, Any]] = None):
        """Log a learning event"""
        try:
            if not self.monitoring_enabled:
                return
            
            event = LearningEvent(
                event_type=event_type,
                message=message,
                level=level,
                timestamp=datetime.now(timezone.utc),
                data=data or {}
            )
            
            self.events.append(event)
            
            # Cleanup old events
            self._cleanup_old_events()
            
            # Check for alerts
            if level in [AlertLevel.WARNING, AlertLevel.ERROR, AlertLevel.CRITICAL]:
                self._trigger_alert(event)
            
            self.logger.info(f"Learning event: {event_type} - {message}")
            
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def track_error(self, error_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Track an error"""
        try:
            error = ErrorInfo(
                error_type=error_type,
                message=message,
                timestamp=datetime.now(timezone.utc),
                context=context or {}
            )
            
            self.errors.append(error)
            
            # Cleanup old errors
            self._cleanup_old_errors()
            
            # Update error rate
            self._update_error_rate()
            
            # Log as critical event
            self.log_event(
                event_type="error",
                message=f"{error_type}: {message}",
                level=AlertLevel.ERROR,
                data=context
            )
            
            self.logger.error(f"Learning error: {error_type} - {message}")
            
        except Exception as e:
            self.logger.error(f"Error tracking error: {e}")
    
    def track_processing_time(self, operation: str, duration: float):
        """Track processing time for an operation"""
        try:
            self.track_metric(f"processing_time_{operation}", duration)
            
            # Update average processing time
            self._update_avg_processing_time(duration)
            
        except Exception as e:
            self.logger.error(f"Error tracking processing time: {e}")
    
    def track_strands_processed(self, count: int, operation: str = "batch"):
        """Track strands processed"""
        try:
            self.performance_stats['total_strands_processed'] += count
            self.track_metric(f"strands_processed_{operation}", count)
            
        except Exception as e:
            self.logger.error(f"Error tracking strands processed: {e}")
    
    def track_braids_created(self, count: int):
        """Track braids created"""
        try:
            self.performance_stats['total_braids_created'] += count
            self.track_metric("braids_created", count)
            
        except Exception as e:
            self.logger.error(f"Error tracking braids created: {e}")
    
    def track_predictions_tracked(self, count: int):
        """Track predictions tracked"""
        try:
            self.performance_stats['total_predictions_tracked'] += count
            self.track_metric("predictions_tracked", count)
            
        except Exception as e:
            self.logger.error(f"Error tracking predictions: {e}")
    
    def track_plans_created(self, count: int):
        """Track conditional plans created"""
        try:
            self.performance_stats['total_plans_created'] += count
            self.track_metric("plans_created", count)
            
        except Exception as e:
            self.logger.error(f"Error tracking plans created: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        try:
            return {
                **self.performance_stats,
                'total_metrics': len(self.metrics),
                'total_events': len(self.events),
                'total_errors': len(self.errors),
                'unresolved_errors': len([e for e in self.errors if not e.resolved])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance stats: {e}")
            return {}
    
    def get_recent_events(self, hours: int = 24) -> List[LearningEvent]:
        """Get recent events"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            return [e for e in self.events if e.timestamp >= cutoff_time]
            
        except Exception as e:
            self.logger.error(f"Error getting recent events: {e}")
            return []
    
    def get_recent_errors(self, hours: int = 24) -> List[ErrorInfo]:
        """Get recent errors"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            return [e for e in self.errors if e.timestamp >= cutoff_time]
            
        except Exception as e:
            self.logger.error(f"Error getting recent errors: {e}")
            return []
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the last N hours"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
            
            # Group metrics by name
            metric_groups = {}
            for metric in recent_metrics:
                if metric.name not in metric_groups:
                    metric_groups[metric.name] = []
                metric_groups[metric.name].append(metric.value)
            
            # Calculate summary statistics
            summary = {}
            for name, values in metric_groups.items():
                summary[name] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'latest': values[-1] if values else 0
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting metrics summary: {e}")
            return {}
    
    def add_alert_handler(self, handler: Callable):
        """Add an alert handler"""
        self.alert_handlers.append(handler)
    
    def _trigger_alert(self, event: LearningEvent):
        """Trigger alert for an event"""
        try:
            for handler in self.alert_handlers:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"Error in alert handler: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error triggering alert: {e}")
    
    def _cleanup_old_metrics(self):
        """Cleanup old metrics"""
        try:
            if len(self.metrics) > self.max_metrics:
                # Keep only the most recent metrics
                self.metrics = self.metrics[-self.max_metrics:]
            
            # Remove metrics older than retention period
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.metrics_retention_days)
            self.metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
            
        except Exception as e:
            self.logger.error(f"Error cleaning up metrics: {e}")
    
    def _cleanup_old_events(self):
        """Cleanup old events"""
        try:
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
            
        except Exception as e:
            self.logger.error(f"Error cleaning up events: {e}")
    
    def _cleanup_old_errors(self):
        """Cleanup old errors"""
        try:
            if len(self.errors) > self.max_errors:
                self.errors = self.errors[-self.max_errors:]
            
        except Exception as e:
            self.logger.error(f"Error cleaning up errors: {e}")
    
    def _update_error_rate(self):
        """Update error rate"""
        try:
            total_events = len(self.events)
            error_events = len([e for e in self.events if e.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]])
            
            if total_events > 0:
                self.performance_stats['error_rate'] = error_events / total_events
                
        except Exception as e:
            self.logger.error(f"Error updating error rate: {e}")
    
    def _update_avg_processing_time(self, duration: float):
        """Update average processing time"""
        try:
            current_avg = self.performance_stats['avg_processing_time']
            total_operations = self.performance_stats['total_strands_processed']
            
            if total_operations > 0:
                new_avg = ((current_avg * (total_operations - 1)) + duration) / total_operations
                self.performance_stats['avg_processing_time'] = new_avg
                
        except Exception as e:
            self.logger.error(f"Error updating average processing time: {e}")
    
    def export_metrics(self, file_path: str) -> bool:
        """Export metrics to file"""
        try:
            export_data = {
                'metrics': [
                    {
                        'name': m.name,
                        'value': m.value,
                        'timestamp': m.timestamp.isoformat(),
                        'tags': m.tags
                    }
                    for m in self.metrics
                ],
                'events': [
                    {
                        'event_type': e.event_type,
                        'message': e.message,
                        'level': e.level.value,
                        'timestamp': e.timestamp.isoformat(),
                        'data': e.data
                    }
                    for e in self.events
                ],
                'errors': [
                    {
                        'error_type': e.error_type,
                        'message': e.message,
                        'timestamp': e.timestamp.isoformat(),
                        'context': e.context,
                        'retry_count': e.retry_count,
                        'resolved': e.resolved
                    }
                    for e in self.errors
                ],
                'performance_stats': self.performance_stats
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Exported metrics to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting metrics: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Test the learning monitor
    monitor = LearningMonitor()
    
    # Track some metrics
    monitor.track_metric("strands_processed", 100)
    monitor.track_metric("braids_created", 5)
    monitor.track_processing_time("clustering", 2.5)
    
    # Log some events
    monitor.log_event("braid_created", "Created new braid from 5 strands", AlertLevel.INFO)
    monitor.log_event("error", "Failed to process strand", AlertLevel.ERROR)
    
    # Track errors
    monitor.track_error("processing_error", "Failed to process strand batch", {"batch_size": 50})
    
    # Get performance stats
    stats = monitor.get_performance_stats()
    print(f"Performance stats: {stats}")
    
    # Get recent events
    events = monitor.get_recent_events(1)
    print(f"Recent events: {len(events)}")
    
    # Export metrics
    success = monitor.export_metrics("learning_metrics.json")
    print(f"Export success: {success}")
