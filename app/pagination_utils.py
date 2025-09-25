"""
Pagination utilities for Flask MongoDB applications
"""
from typing import Dict, Any, List, Optional
from flask import request
import math


def get_pagination_params() -> Dict[str, int]:
    """
    Extract and validate pagination parameters from request

    Returns:
        Dict containing page and limit with defaults applied
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        # Validate ranges
        page = max(1, page)
        limit = max(1, min(limit, 100))  # Cap at 100 items per page

        return {'page': page, 'limit': limit}
    except (ValueError, TypeError):
        return {'page': 1, 'limit': 20}


def calculate_skip(page: int, limit: int) -> int:
    """Calculate MongoDB skip value for pagination"""
    return (page - 1) * limit


def create_pagination_meta(page: int, limit: int, total_count: int) -> Dict[str, Any]:
    """
    Create pagination metadata for API responses

    Args:
        page: Current page number
        limit: Items per page
        total_count: Total number of items

    Returns:
        Dict containing pagination metadata
    """
    total_pages = math.ceil(total_count / limit) if limit > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    return {
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_count,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'next_page': page + 1 if has_next else None,
            'prev_page': page - 1 if has_prev else None
        }
    }


def paginate_mongo_query(
    collection,
    query: Dict[str, Any] = None,
    sort_field: str = 'created_at',
    sort_order: int = -1,
    page: Optional[int] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Paginate a MongoDB query with standardized response format

    Args:
        collection: MongoDB collection object
        query: MongoDB query dict
        sort_field: Field to sort by
        sort_order: Sort order (1 for asc, -1 for desc)
        page: Page number (if None, extracts from request)
        limit: Items per page (if None, extracts from request)

    Returns:
        Dict containing paginated data and metadata
    """
    if query is None:
        query = {}

    # Get pagination params
    if page is None or limit is None:
        pagination_params = get_pagination_params()
        page = page or pagination_params['page']
        limit = limit or pagination_params['limit']

    # Calculate skip
    skip = calculate_skip(page, limit)

    # Get total count
    total_count = collection.count_documents(query)

    # Get paginated results
    cursor = collection.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
    items = list(cursor)

    # Create response
    return {
        'items': items,
        'meta': create_pagination_meta(page, limit, total_count)
    }


def paginate_aggregation(
    collection,
    pipeline: List[Dict[str, Any]],
    page: Optional[int] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Paginate a MongoDB aggregation pipeline

    Args:
        collection: MongoDB collection object
        pipeline: Aggregation pipeline (without $skip and $limit)
        page: Page number (if None, extracts from request)
        limit: Items per page (if None, extracts from request)

    Returns:
        Dict containing paginated data and metadata
    """
    # Get pagination params
    if page is None or limit is None:
        pagination_params = get_pagination_params()
        page = page or pagination_params['page']
        limit = limit or pagination_params['limit']

    # Calculate skip
    skip = calculate_skip(page, limit)

    # Create count pipeline
    count_pipeline = pipeline + [
        {'$count': 'total'}
    ]

    # Get total count
    count_result = list(collection.aggregate(count_pipeline))
    total_count = count_result[0]['total'] if count_result else 0

    # Create paginated pipeline
    paginated_pipeline = pipeline + [
        {'$skip': skip},
        {'$limit': limit}
    ]

    # Get paginated results
    items = list(collection.aggregate(paginated_pipeline))

    # Create response
    return {
        'items': items,
        'meta': create_pagination_meta(page, limit, total_count)
    }


class PaginationHelper:
    """Helper class for pagination operations"""

    def __init__(self, collection):
        self.collection = collection

    def paginate(
        self,
        query: Dict[str, Any] = None,
        sort_field: str = 'created_at',
        sort_order: int = -1,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Paginate a standard query"""
        return paginate_mongo_query(
            self.collection,
            query,
            sort_field,
            sort_order,
            page,
            limit
        )

    def paginate_aggregation(
        self,
        pipeline: List[Dict[str, Any]],
        page: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Paginate an aggregation pipeline"""
        return paginate_aggregation(self.collection, pipeline, page, limit)

    def search_and_paginate(
        self,
        search_term: Optional[str] = None,
        search_fields: List[str] = None,
        additional_filters: Dict[str, Any] = None,
        sort_field: str = 'created_at',
        sort_order: int = -1,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search and paginate with text search capability

        Args:
            search_term: Text to search for
            search_fields: Fields to search in (for regex search)
            additional_filters: Additional MongoDB filters
            sort_field: Field to sort by
            sort_order: Sort order
            page: Page number
            limit: Items per page
        """
        query = additional_filters or {}

        if search_term and search_fields:
            # Create regex search for multiple fields
            search_conditions = []
            for field in search_fields:
                search_conditions.append({
                    field: {'$regex': search_term, '$options': 'i'}
                })

            if search_conditions:
                if len(search_conditions) == 1:
                    query.update(search_conditions[0])
                else:
                    query['$or'] = search_conditions

        return self.paginate(query, sort_field, sort_order, page, limit)