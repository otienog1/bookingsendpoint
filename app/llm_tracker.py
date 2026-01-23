"""
LLM Performance Tracking System

Tracks success rates, failures, and response times for different LLM models
to automatically prioritize the most reliable models for future requests.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import json


class LLMPerformanceTracker:
    """Track and analyze LLM model performance"""

    def __init__(self, mongo_client=None):
        """Initialize the tracker with optional MongoDB client"""
        self.mongo_client = mongo_client
        self.collection_name = 'llm_performance'

        # In-memory cache for quick access
        self.stats_cache = defaultdict(lambda: {
            'total_attempts': 0,
            'successes': 0,
            'failures': 0,
            'avg_response_time': 0.0,
            'recent_failures': [],
            'last_success': None,
            'last_failure': None
        })

    def get_collection(self):
        """Get the MongoDB collection"""
        if self.mongo_client:
            return self.mongo_client.db[self.collection_name]
        return None

    def record_attempt(self, provider: str, model: str, success: bool,
                      response_time: float = None, error_message: str = None,
                      tokens_used: int = None):
        """
        Record an LLM attempt (success or failure)

        Args:
            provider: Provider name (e.g., 'gemini', 'openrouter', 'anthropic')
            model: Model name (e.g., 'gemini-2.0-flash-exp')
            success: Whether the attempt succeeded
            response_time: Response time in seconds
            error_message: Error message if failed
            tokens_used: Number of tokens used (prompt + completion)
        """
        model_key = f"{provider}/{model}"
        timestamp = datetime.now(timezone.utc)

        # Update in-memory cache
        stats = self.stats_cache[model_key]
        stats['total_attempts'] += 1

        if success:
            stats['successes'] += 1
            stats['last_success'] = timestamp

            # Update average response time
            if response_time:
                current_avg = stats['avg_response_time']
                total = stats['successes']
                stats['avg_response_time'] = (current_avg * (total - 1) + response_time) / total
        else:
            stats['failures'] += 1
            stats['last_failure'] = timestamp
            stats['recent_failures'].append({
                'timestamp': timestamp,
                'error': error_message
            })
            # Keep only last 10 failures
            stats['recent_failures'] = stats['recent_failures'][-10:]

        # Persist to MongoDB
        collection = self.get_collection()
        if collection:
            attempt_doc = {
                'provider': provider,
                'model': model,
                'model_key': model_key,
                'success': success,
                'timestamp': timestamp,
                'response_time': response_time,
                'error_message': error_message,
                'tokens_used': tokens_used
            }
            collection.insert_one(attempt_doc)

            # Update aggregated stats
            self._update_aggregated_stats(model_key)

    def _update_aggregated_stats(self, model_key: str):
        """Update aggregated statistics in MongoDB"""
        collection = self.get_collection()
        if not collection:
            return

        stats = self.stats_cache[model_key]

        # Calculate success rate
        success_rate = (stats['successes'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0

        # Update or insert aggregated stats
        aggregated_collection = self.mongo_client.db['llm_aggregated_stats']
        aggregated_collection.update_one(
            {'model_key': model_key},
            {
                '$set': {
                    'model_key': model_key,
                    'provider': model_key.split('/')[0],
                    'model': '/'.join(model_key.split('/')[1:]),
                    'total_attempts': stats['total_attempts'],
                    'successes': stats['successes'],
                    'failures': stats['failures'],
                    'success_rate': success_rate,
                    'avg_response_time': stats['avg_response_time'],
                    'last_success': stats['last_success'],
                    'last_failure': stats['last_failure'],
                    'updated_at': datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

    def get_model_stats(self, provider: str = None, model: str = None) -> Dict:
        """
        Get statistics for a specific model or all models

        Args:
            provider: Filter by provider (optional)
            model: Filter by model (optional)

        Returns:
            Dictionary with model statistics
        """
        collection = self.get_collection()
        if not collection:
            # Return from cache if no MongoDB
            if provider and model:
                model_key = f"{provider}/{model}"
                return {model_key: self.stats_cache.get(model_key)}
            return dict(self.stats_cache)

        # Query aggregated stats from MongoDB
        aggregated_collection = self.mongo_client.db['llm_aggregated_stats']
        query = {}

        if provider:
            query['provider'] = provider
        if model:
            query['model'] = model

        stats = list(aggregated_collection.find(query).sort('success_rate', -1))

        # Convert to dictionary
        result = {}
        for stat in stats:
            model_key = stat['model_key']
            result[model_key] = {
                'provider': stat['provider'],
                'model': stat['model'],
                'total_attempts': stat['total_attempts'],
                'successes': stat['successes'],
                'failures': stat['failures'],
                'success_rate': stat['success_rate'],
                'avg_response_time': stat['avg_response_time'],
                'last_success': stat.get('last_success'),
                'last_failure': stat.get('last_failure')
            }

        return result

    def get_recent_failures(self, hours: int = 24) -> List[Dict]:
        """
        Get recent failures across all models

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent failures
        """
        collection = self.get_collection()
        if not collection:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        failures = list(collection.find({
            'success': False,
            'timestamp': {'$gte': cutoff_time}
        }).sort('timestamp', -1).limit(100))

        return failures

    def get_optimal_model_order(self, available_models: List[tuple]) -> List[tuple]:
        """
        Reorder models based on recent performance

        Args:
            available_models: List of (provider, model, max_tokens) tuples

        Returns:
            Reordered list prioritizing best-performing models
        """
        collection = self.get_collection()
        if not collection:
            # No data, return original order
            return available_models

        # Get recent stats (last 7 days)
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)

        model_scores = {}
        for provider, model, max_tokens in available_models:
            model_key = f"{provider}/{model}"

            # Get recent attempts
            recent_attempts = collection.count_documents({
                'model_key': model_key,
                'timestamp': {'$gte': cutoff_time}
            })

            if recent_attempts == 0:
                # No recent data, keep original position (neutral score)
                model_scores[model_key] = (0.5, 0, max_tokens, available_models.index((provider, model, max_tokens)))
                continue

            # Get recent successes
            recent_successes = collection.count_documents({
                'model_key': model_key,
                'success': True,
                'timestamp': {'$gte': cutoff_time}
            })

            # Calculate success rate
            success_rate = recent_successes / recent_attempts

            # Get average response time for recent successes
            pipeline = [
                {
                    '$match': {
                        'model_key': model_key,
                        'success': True,
                        'timestamp': {'$gte': cutoff_time},
                        'response_time': {'$ne': None}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'avg_time': {'$avg': '$response_time'}
                    }
                }
            ]

            result = list(collection.aggregate(pipeline))
            avg_time = result[0]['avg_time'] if result else 10.0

            # Calculate score (prioritize success rate, then speed)
            # Normalize response time (assume max 60 seconds)
            time_score = max(0, 1 - (avg_time / 60))

            # Combined score: 70% success rate, 30% speed
            score = (success_rate * 0.7) + (time_score * 0.3)

            model_scores[model_key] = (score, recent_attempts, max_tokens, available_models.index((provider, model, max_tokens)))

        # Sort by score (descending), then by original index
        sorted_models = sorted(
            available_models,
            key=lambda x: model_scores[f"{x[0]}/{x[1]}"][0],
            reverse=True
        )

        return sorted_models

    def get_summary_report(self) -> Dict:
        """
        Generate a summary report of all LLM performance

        Returns:
            Dictionary with summary statistics
        """
        stats = self.get_model_stats()

        total_attempts = sum(s['total_attempts'] for s in stats.values())
        total_successes = sum(s['successes'] for s in stats.values())
        total_failures = sum(s['failures'] for s in stats.values())

        # Sort by success rate
        sorted_models = sorted(
            stats.items(),
            key=lambda x: x[1]['success_rate'],
            reverse=True
        )

        return {
            'total_attempts': total_attempts,
            'total_successes': total_successes,
            'total_failures': total_failures,
            'overall_success_rate': (total_successes / total_attempts * 100) if total_attempts > 0 else 0,
            'models': [
                {
                    'model_key': model_key,
                    'provider': stats[model_key]['provider'],
                    'model': stats[model_key]['model'],
                    'success_rate': stats[model_key]['success_rate'],
                    'total_attempts': stats[model_key]['total_attempts'],
                    'avg_response_time': stats[model_key]['avg_response_time']
                }
                for model_key, _ in sorted_models
            ]
        }
