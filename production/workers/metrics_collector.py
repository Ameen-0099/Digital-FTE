"""
NexusFlow Customer Success Digital FTE - Metrics Collector
===========================================================
Exercise 2.6: Daily Reports & Metrics Collection

Background worker that generates daily customer sentiment reports
and stores aggregated metrics in the agent_metrics table.

Features:
- Calculates average sentiment per channel
- Tracks escalation rates
- Measures resolution times
- Identifies top topics
- Stores daily/hourly aggregates

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from decimal import Decimal

# Async scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Database
import asyncpg

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.message_processor import DatabasePool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """
    Collects and aggregates metrics for the Digital FTE.
    
    Runs as a background task and generates daily/hourly reports.
    """
    
    def __init__(self, db_pool=None):
        """
        Initialize metrics collector.
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self._scheduler: Optional[AsyncIOScheduler] = None
    
    async def initialize(self):
        """Initialize database pool and scheduler."""
        if self.db_pool is None:
            self.db_pool = DatabasePool()
            await self.db_pool.create_pool(
                os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nexusflow')
            )
        
        # Initialize scheduler
        self._scheduler = AsyncIOScheduler()
        
        # Schedule daily report generation at midnight
        self._scheduler.add_job(
            self.generate_daily_report,
            CronTrigger(hour=0, minute=0),  # Run at midnight
            id='daily_report',
            name='Generate Daily Sentiment Report',
            replace_existing=True
        )
        
        # Schedule hourly metrics aggregation
        self._scheduler.add_job(
            self.aggregate_hourly_metrics,
            CronTrigger(minute=5),  # Run at 5 minutes past each hour
            id='hourly_metrics',
            name='Aggregate Hourly Metrics',
            replace_existing=True
        )
        
        logger.info("Metrics Collector initialized")
    
    async def start(self):
        """Start the metrics collector scheduler."""
        if self._scheduler:
            self._scheduler.start()
            logger.info("Metrics Collector scheduler started")
    
    async def stop(self):
        """Stop the metrics collector scheduler."""
        if self._scheduler:
            self._scheduler.shutdown()
            logger.info("Metrics Collector scheduler stopped")
        
        if self.db_pool:
            await self.db_pool.close_pool()
    
    async def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate daily sentiment report and store in agent_metrics.
        
        Args:
            date: Date to generate report for (default: yesterday)
            
        Returns:
            Report data dictionary
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        report_date = date.date()
        
        logger.info(f"Generating daily report for {report_date}")
        
        async with self.db_pool.acquire() as conn:
            # Calculate metrics for the day
            metrics = await self._calculate_daily_metrics(conn, report_date)
            
            # Insert into agent_metrics table
            await conn.execute("""
                INSERT INTO agent_metrics (
                    metric_date, metric_hour,
                    total_conversations, total_messages, total_tickets, total_escalations,
                    conversations_by_channel, messages_by_channel,
                    sentiment_distribution,
                    ai_resolved_count, human_resolved_count, ai_resolution_rate,
                    avg_first_response_time, p50_first_response_time,
                    p95_first_response_time, p99_first_response_time,
                    avg_resolution_time, p50_resolution_time,
                    p95_resolution_time, p99_resolution_time,
                    sla_breach_count, sla_compliance_rate,
                    escalations_by_level, escalation_rate,
                    avg_csat_score, csat_response_count,
                    avg_ai_confidence, low_confidence_count,
                    created_at, updated_at
                ) VALUES (
                    $1, NULL, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18, $19, $20, $21,
                    $22, $23, $24, $25, $26, $27, NOW(), NOW()
                )
                ON CONFLICT (metric_date, metric_hour) DO UPDATE SET
                    total_conversations = EXCLUDED.total_conversations,
                    total_messages = EXCLUDED.total_messages,
                    updated_at = NOW()
            """,
                report_date,
                metrics['total_conversations'],
                metrics['total_messages'],
                metrics['total_tickets'],
                metrics['total_escalations'],
                jsonb(metrics['conversations_by_channel']),
                jsonb(metrics['messages_by_channel']),
                jsonb(metrics['sentiment_distribution']),
                metrics['ai_resolved_count'],
                metrics['human_resolved_count'],
                metrics['ai_resolution_rate'],
                metrics['avg_first_response_time'],
                metrics['p50_first_response_time'],
                metrics['p95_first_response_time'],
                metrics['p99_first_response_time'],
                metrics['avg_resolution_time'],
                metrics['p50_resolution_time'],
                metrics['p95_resolution_time'],
                metrics['p99_resolution_time'],
                metrics['sla_breach_count'],
                metrics['sla_compliance_rate'],
                jsonb(metrics['escalations_by_level']),
                metrics['escalation_rate'],
                metrics['avg_csat_score'],
                metrics['csat_response_count'],
                metrics['avg_ai_confidence'],
                metrics['low_confidence_count']
            )
            
            logger.info(f"Daily report generated for {report_date}")
            return metrics
    
    async def aggregate_hourly_metrics(self):
        """Aggregate metrics for the previous hour."""
        now = datetime.now()
        previous_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        hour = previous_hour.hour
        
        logger.info(f"Aggregating hourly metrics for hour {hour}")
        
        async with self.db_pool.acquire() as conn:
            metrics = await self._calculate_hourly_metrics(conn, previous_hour.date(), hour)
            
            # Insert hourly metrics
            await conn.execute("""
                INSERT INTO agent_metrics (
                    metric_date, metric_hour,
                    total_conversations, total_messages,
                    conversations_by_channel, messages_by_channel,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                ON CONFLICT (metric_date, metric_hour) DO UPDATE SET
                    total_conversations = EXCLUDED.total_conversations,
                    total_messages = EXCLUDED.total_messages,
                    updated_at = NOW()
            """,
                previous_hour.date(),
                hour,
                metrics['total_conversations'],
                metrics['total_messages'],
                jsonb(metrics['conversations_by_channel']),
                jsonb(metrics['messages_by_channel'])
            )
    
    async def _calculate_daily_metrics(
        self,
        conn: asyncpg.Connection,
        report_date: datetime.date
    ) -> Dict[str, Any]:
        """
        Calculate daily metrics from database.
        
        Args:
            conn: Database connection
            report_date: Date to calculate metrics for
            
        Returns:
            Metrics dictionary
        """
        # Total conversations
        total_conversations = await conn.fetchval("""
            SELECT COUNT(*) FROM conversations
            WHERE DATE(created_at) = $1
        """, report_date)
        
        # Total messages
        total_messages = await conn.fetchval("""
            SELECT COUNT(*) FROM messages
            WHERE DATE(created_at) = $1
        """, report_date)
        
        # Total tickets
        total_tickets = await conn.fetchval("""
            SELECT COUNT(*) FROM tickets
            WHERE DATE(created_at) = $1
        """, report_date)
        
        # Total escalations
        total_escalations = await conn.fetchval("""
            SELECT COUNT(*) FROM escalations
            WHERE DATE(created_at) = $1
        """, report_date)
        
        # Conversations by channel
        conv_by_channel = await conn.fetch("""
            SELECT original_channel as channel, COUNT(*) as count
            FROM conversations
            WHERE DATE(created_at) = $1
            GROUP BY original_channel
        """, report_date)
        conversations_by_channel = {r['channel']: r['count'] for r in conv_by_channel}
        
        # Messages by channel
        msg_by_channel = await conn.fetch("""
            SELECT channel, COUNT(*) as count
            FROM messages
            WHERE DATE(created_at) = $1
            GROUP BY channel
        """, report_date)
        messages_by_channel = {r['channel']: r['count'] for r in msg_by_channel}
        
        # Sentiment distribution
        sentiment_dist = await conn.fetch("""
            SELECT sentiment, COUNT(*) as count
            FROM messages
            WHERE DATE(created_at) = $1 AND direction = 'inbound'
            GROUP BY sentiment
        """, report_date)
        sentiment_distribution = {r['sentiment']: r['count'] for r in sentiment_dist}
        
        # Resolution metrics (AI vs Human)
        resolution_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE resolved_by LIKE '%AI%' OR resolved_by IS NULL) as ai_resolved,
                COUNT(*) FILTER (WHERE resolved_by NOT LIKE '%AI%') as human_resolved,
                COUNT(*) as total
            FROM tickets
            WHERE DATE(resolved_at) = $1
        """, report_date)
        
        ai_resolved = resolution_stats['ai_resolved'] or 0
        human_resolved = resolution_stats['human_resolved'] or 0
        total_resolved = resolution_stats['total'] or 1
        ai_resolution_rate = round((ai_resolved / total_resolved) * 100, 2)
        
        # Response time percentiles
        response_times = await conn.fetch("""
            SELECT EXTRACT(EPOCH FROM (first_response_at - created_at)) as response_time
            FROM tickets
            WHERE DATE(created_at) = $1 AND first_response_at IS NOT NULL
        """, report_date)
        
        response_time_values = [r['response_time'] for r in response_times if r['response_time']]
        response_time_values.sort()
        
        avg_first_response = sum(response_time_values) / len(response_time_values) if response_time_values else 0
        p50_first_response = self._percentile(response_time_values, 50)
        p95_first_response = self._percentile(response_time_values, 95)
        p99_first_response = self._percentile(response_time_values, 99)
        
        # Resolution time percentiles
        resolution_times = await conn.fetch("""
            SELECT EXTRACT(EPOCH FROM (resolved_at - created_at)) as resolution_time
            FROM tickets
            WHERE DATE(resolved_at) = $1 AND resolved_at IS NOT NULL
        """, report_date)
        
        resolution_time_values = [r['resolution_time'] for r in resolution_times if r['resolution_time']]
        resolution_time_values.sort()
        
        avg_resolution = sum(resolution_time_values) / len(resolution_time_values) if resolution_time_values else 0
        p50_resolution = self._percentile(resolution_time_values, 50)
        p95_resolution = self._percentile(resolution_time_values, 95)
        p99_resolution = self._percentile(resolution_time_values, 99)
        
        # SLA metrics
        sla_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE sla_breached = TRUE) as breaches,
                COUNT(*) as total
            FROM tickets
            WHERE DATE(created_at) = $1
        """, report_date)
        
        sla_breaches = sla_stats['breaches'] or 0
        sla_total = sla_stats['total'] or 1
        sla_compliance_rate = round(((sla_total - sla_breaches) / sla_total) * 100, 2)
        
        # Escalation metrics
        esc_by_level = await conn.fetch("""
            SELECT escalation_level, COUNT(*) as count
            FROM escalations
            WHERE DATE(created_at) = $1
            GROUP BY escalation_level
        """, report_date)
        escalations_by_level = {r['escalation_level']: r['count'] for r in esc_by_level}
        
        escalation_rate = round((total_escalations / total_conversations) * 100, 2) if total_conversations else 0
        
        # CSAT metrics
        csat_stats = await conn.fetchrow("""
            SELECT
                AVG(csat_score) as avg_score,
                COUNT(*) FILTER (WHERE csat_score IS NOT NULL) as count
            FROM tickets
            WHERE DATE(resolved_at) = $1
        """, report_date)
        
        avg_csat = float(csat_stats['avg_score']) if csat_stats['avg_score'] else 0
        csat_count = csat_stats['count'] or 0
        
        # AI confidence metrics
        ai_stats = await conn.fetchrow("""
            SELECT
                AVG(ai_confidence) as avg_confidence,
                COUNT(*) FILTER (WHERE ai_confidence < 0.5) as low_confidence
            FROM messages
            WHERE DATE(created_at) = $1 AND is_ai_generated = TRUE
        """, report_date)
        
        avg_ai_confidence = float(ai_stats['avg_confidence']) if ai_stats['avg_confidence'] else 0
        low_confidence_count = ai_stats['low_confidence'] or 0
        
        return {
            'total_conversations': total_conversations or 0,
            'total_messages': total_messages or 0,
            'total_tickets': total_tickets or 0,
            'total_escalations': total_escalations or 0,
            'conversations_by_channel': conversations_by_channel,
            'messages_by_channel': messages_by_channel,
            'sentiment_distribution': sentiment_distribution,
            'ai_resolved_count': ai_resolved,
            'human_resolved_count': human_resolved,
            'ai_resolution_rate': ai_resolution_rate,
            'avg_first_response_time': round(avg_first_response, 2),
            'p50_first_response_time': round(p50_first_response, 2),
            'p95_first_response_time': round(p95_first_response, 2),
            'p99_first_response_time': round(p99_first_response, 2),
            'avg_resolution_time': round(avg_resolution, 2),
            'p50_resolution_time': round(p50_resolution, 2),
            'p95_resolution_time': round(p95_resolution, 2),
            'p99_resolution_time': round(p99_resolution, 2),
            'sla_breach_count': sla_breaches,
            'sla_compliance_rate': sla_compliance_rate,
            'escalations_by_level': escalations_by_level,
            'escalation_rate': escalation_rate,
            'avg_csat_score': round(avg_csat, 2),
            'csat_response_count': csat_count,
            'avg_ai_confidence': round(avg_ai_confidence, 2),
            'low_confidence_count': low_confidence_count
        }
    
    async def _calculate_hourly_metrics(
        self,
        conn: asyncpg.Connection,
        report_date: datetime.date,
        hour: int
    ) -> Dict[str, Any]:
        """Calculate hourly metrics."""
        # Similar to daily but for specific hour
        total_conversations = await conn.fetchval("""
            SELECT COUNT(*) FROM conversations
            WHERE DATE(created_at) = $1 AND EXTRACT(HOUR FROM created_at) = $2
        """, report_date, hour)
        
        total_messages = await conn.fetchval("""
            SELECT COUNT(*) FROM messages
            WHERE DATE(created_at) = $1 AND EXTRACT(HOUR FROM created_at) = $2
        """, report_date, hour)
        
        conv_by_channel = await conn.fetch("""
            SELECT original_channel as channel, COUNT(*) as count
            FROM conversations
            WHERE DATE(created_at) = $1 AND EXTRACT(HOUR FROM created_at) = $2
            GROUP BY original_channel
        """, report_date, hour)
        conversations_by_channel = {r['channel']: r['count'] for r in conv_by_channel}
        
        msg_by_channel = await conn.fetch("""
            SELECT channel, COUNT(*) as count
            FROM messages
            WHERE DATE(created_at) = $1 AND EXTRACT(HOUR FROM created_at) = $2
            GROUP BY channel
        """, report_date, hour)
        messages_by_channel = {r['channel']: r['count'] for r in msg_by_channel}
        
        return {
            'total_conversations': total_conversations or 0,
            'total_messages': total_messages or 0,
            'conversations_by_channel': conversations_by_channel,
            'messages_by_channel': messages_by_channel
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of a sorted list."""
        if not values:
            return 0
        
        k = (len(values) - 1) * (percentile / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(values) else f
        
        if f == c:
            return values[f]
        
        return values[f] * (c - k) + values[c] * (k - f)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def jsonb(data: Any) -> Any:
    """Convert data to JSONB format for PostgreSQL."""
    import json
    return json.dumps(data)


# =============================================================================
# MAIN (Testing)
# =============================================================================

async def main():
    """Test metrics collector."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - METRICS COLLECTOR")
    print("=" * 80)
    
    collector = MetricsCollector()
    
    try:
        await collector.initialize()
        await collector.start()
        
        print("\n✅ Metrics Collector started")
        print("Daily reports will be generated at midnight")
        print("Hourly metrics will be aggregated at 5 minutes past each hour")
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await collector.stop()


if __name__ == "__main__":
    asyncio.run(main())
