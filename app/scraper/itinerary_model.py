"""
MongoDB Model and Schema for Itineraries

Defines the itinerary document structure and provides
helper methods for CRUD operations.
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId


class ItineraryModel:
    """MongoDB model for itinerary documents."""

    # Collection name
    COLLECTION_NAME = 'itineraries'

    # Schema definition for documentation and validation
    SCHEMA = {
        'booking_id': ObjectId,  # Reference to the booking this itinerary belongs to
        'itinerary_type': str,  # Type: 'option_1', 'option_2', 'extension', 'final', etc.
        'version': int,  # Version number for tracking revisions (1, 2, 3...)
        'is_active': bool,  # Whether this itinerary is currently active/valid
        'trip_overview': {
            'tour_name': str,
            'dates': str,
            'duration': str,
            'client_group': str,
            'tour_operator': str,
            'group_size': int,
            'countries_visited': list,
            'languages': str,
            'contact': {
                'email': str,
                'phone': str,
                'mobile': str
            }
        },
        'logistics': {
            'summary': str,  # Brief overview paragraph
            'flight_details': {
                'overview': str,  # General overview of flight arrangements
                'arrival': {
                    'day': int,
                    'date': str,  # ISO format YYYY-MM-DD
                    'flight_number': str,
                    'airport': str,
                    'arrival_time': str,
                    'notes': str
                },
                'internal_flights': [{
                    'day': int,
                    'date': str,  # ISO format YYYY-MM-DD
                    'flight_number': str,
                    'from_airport': str,
                    'to_airport': str,
                    'departure_time': str,
                    'arrival_time': str,
                    'duration': str,
                    'baggage_limit': str,
                    'notes': str
                }],
                'departure': {
                    'day': int,
                    'date': str,  # ISO format YYYY-MM-DD
                    'flight_number': str,
                    'airport': str,
                    'departure_time': str,
                    'notes': str
                },
                'important_considerations': list  # List of important notes about flights
            },
            'transfer_arrangements': {
                'overview': str,  # General overview of transfer arrangements
                'airport_transfers': str,  # Description of airport transfer arrangements
                'inter_lodge_transfers': str,  # Description of lodge-to-lodge transfers
                'border_crossings': [{
                    'day': int,
                    'date': str,  # ISO format YYYY-MM-DD
                    'from_country': str,
                    'to_country': str,
                    'border_point': str,
                    'estimated_time': str,
                    'procedures': str,
                    'notes': str
                }],
                'vehicle_types': list,  # List of vehicle types used
                'important_considerations': list
            },
            'accommodation_patterns': {
                'overview': str,
                'early_checkouts': [{
                    'day': int,
                    'date': str,  # ISO format YYYY-MM-DD
                    'property': str,
                    'checkout_time': str,
                    'reason': str
                }],
                'late_arrivals': [{
                    'day': int,
                    'date': str,  # ISO format YYYY-MM-DD
                    'property': str,
                    'estimated_arrival_time': str,
                    'reason': str
                }],
                'full_board_properties': list,  # Properties offering full board
                'bed_breakfast_properties': list,  # Properties offering B&B
                'important_considerations': list
            },
            'meal_plan_overview': {
                'summary': str,
                'full_board_locations': list,
                'bed_breakfast_locations': list,
                'special_dining_experiences': list,
                'beverage_policies': str,
                'important_considerations': list
            },
            'timing_considerations': {
                'early_mornings': list,  # Days requiring early starts
                'long_drives': list,  # Days with long drives
                'flight_schedules': str,  # Critical flight timing notes
                'border_crossing_time': str,
                'other_notes': list
            },
            'documents_and_preparations': {
                'passports_and_visas': {
                    'passport_validity': str,
                    'visa_requirements': [{
                        'country': str,
                        'required': bool,
                        'process': str,
                        'notes': str
                    }],
                    'notes': str
                },
                'health_requirements': {
                    'yellow_fever': str,
                    'vaccinations': str,
                    'malaria_prophylaxis': str,
                    'other_precautions': list
                },
                'travel_insurance': str,
                'currency': {
                    'recommendations': str,
                    'restrictions': str,
                    'notes': str
                },
                'clothing_and_packing': {
                    'general_guidance': str,
                    'clothing': list,
                    'gear': list,
                    'accessories': list
                },
                'electrical_adapters': str,
                'luggage_requirements': str,
                'photography_equipment': str
            },
            'emergency_contacts': [{
                'name': str,
                'phone': str,
                'email': str,
                'role': str,
                'availability': str
            }]
        },
        'daily_breakdown_summary': [{
            'day': int,
            'date': str,
            'title': str,  # e.g., "Arrival in Nairobi"
            'summary': str,  # Brief 1-2 sentence summary of the day
            'highlights': list,  # Key highlights/activities
            'distance_traveled': str,  # e.g., "120 km", "2 hour flight"
            'accommodation_type': str,  # e.g., "Lodge", "Tented Camp"
            'meals_included': str  # e.g., "B, L, D" or "Breakfast, Lunch, Dinner"
        }],
        'daily_itinerary': [{
            'day': int,
            'date': str,  # ISO format YYYY-MM-DD
            'location': str,
            'accommodation': {
                'name': str,
                'type': str,
                'description': str,
                'room_type': str,
                'room_description': str,
                'total_rooms': int,
                'distance_from_airport': str
            },
            'meals': {
                'breakfast': bool,
                'lunch': bool,
                'dinner': bool,
                'meal_plan': str
            },
            'activities': [{
                'name': str,
                'type': str,
                'description': str,
                'details': dict,
                'included': bool
            }],
            'optional_activities': [{
                'name': str,
                'description': str
            }],
            'notes': str
        }],
        'inclusions': {
            'accommodation': list,  # List of accommodation objects with name, nights, location, room_type
            'meals': dict,
            'transportation': dict,
            'flights': list,
            'activities': list,
            'services': list
        },
        'exclusions': list,
        'important_information': dict,
        '_metadata': {
            'scraped_at': datetime,
            'version': str,
            'source_url': str,
            'created_by': str
        }
    }

    # Indexes to create on the collection
    INDEXES = [
        {'keys': [('booking_id', 1)], 'name': 'booking_id_idx'},
        {'keys': [('booking_id', 1), ('itinerary_type', 1)], 'name': 'booking_type_idx'},
        {'keys': [('booking_id', 1), ('is_active', 1)], 'name': 'booking_active_idx'},
        {'keys': [('trip_overview.tour_name', 1)], 'name': 'tour_name_idx'},
        {'keys': [('trip_overview.client_group', 1)], 'name': 'client_group_idx'},
        {'keys': [('trip_overview.tour_operator', 1)], 'name': 'tour_operator_idx'},
        {'keys': [('_metadata.scraped_at', -1)], 'name': 'scraped_at_idx'},
        {'keys': [('daily_itinerary.date', 1)], 'name': 'daily_date_idx'},
        {
            'keys': [
                ('trip_overview.tour_name', 'text'),
                ('trip_overview.client_group', 'text'),
                ('daily_itinerary.location', 'text')
            ],
            'name': 'text_search_idx'
        }
    ]

    def __init__(self, mongo):
        """
        Initialize the model with a PyMongo instance.

        Args:
            mongo: Flask-PyMongo instance
        """
        self.mongo = mongo
        self.collection = mongo.db[self.COLLECTION_NAME]

    def ensure_indexes(self):
        """Create indexes if they don't exist."""
        for index in self.INDEXES:
            try:
                self.collection.create_index(
                    index['keys'],
                    name=index['name']
                )
            except Exception as e:
                print(f"Error creating index {index['name']}: {e}")

    def create(self, data: dict, user_id: str = None, source_url: str = None,
               booking_id: str = None, itinerary_type: str = 'option_1', version: int = 1) -> str:
        """
        Create a new itinerary document.

        Args:
            data: Itinerary data
            user_id: ID of user creating the itinerary
            source_url: Source URL that was scraped
            booking_id: ID of the booking this itinerary belongs to
            itinerary_type: Type of itinerary ('option_1', 'option_2', 'extension', 'final', etc.)
            version: Version number for this itinerary (default: 1)

        Returns:
            Inserted document ID
        """
        # Add booking relationship fields
        if booking_id:
            data['booking_id'] = ObjectId(booking_id) if isinstance(booking_id, str) else booking_id

        data['itinerary_type'] = itinerary_type
        data['version'] = version
        data['is_active'] = True  # New itineraries are active by default

        # Ensure metadata exists
        if '_metadata' not in data:
            data['_metadata'] = {}

        data['_metadata'].update({
            'scraped_at': datetime.utcnow(),
            'version': '1.0',
            'source_url': source_url,
            'created_by': user_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })

        result = self.collection.insert_one(data)
        return str(result.inserted_id)

    def find_by_id(self, doc_id: str) -> Optional[dict]:
        """
        Find an itinerary by ID.

        Args:
            doc_id: Document ID

        Returns:
            Itinerary document or None
        """
        try:
            doc = self.collection.find_one({'_id': ObjectId(doc_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception:
            return None

    def find_all(
        self,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = '_metadata.scraped_at',
        sort_order: int = -1,
        search: str = None
    ) -> dict:
        """
        Find all itineraries with pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            sort_by: Field to sort by
            sort_order: 1 for ascending, -1 for descending
            search: Optional text search query

        Returns:
            Dictionary with items and pagination info
        """
        query = {}

        if search:
            query['$text'] = {'$search': search}

        # Get total count
        total = self.collection.count_documents(query)

        # Get paginated results
        skip = (page - 1) * per_page
        cursor = self.collection.find(query).sort(
            sort_by, sort_order
        ).skip(skip).limit(per_page)

        items = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            items.append(doc)

        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }

    def find_by_tour_name(self, tour_name: str) -> list:
        """
        Find itineraries by tour name.

        Args:
            tour_name: Tour name to search

        Returns:
            List of matching itineraries
        """
        cursor = self.collection.find({
            'trip_overview.tour_name': {'$regex': tour_name, '$options': 'i'}
        })

        items = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            items.append(doc)

        return items

    def find_by_client(self, client_group: str) -> list:
        """
        Find itineraries by client group.

        Args:
            client_group: Client group to search

        Returns:
            List of matching itineraries
        """
        cursor = self.collection.find({
            'trip_overview.client_group': {'$regex': client_group, '$options': 'i'}
        })

        items = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            items.append(doc)

        return items

    def find_by_booking(self, booking_id: str, active_only: bool = True) -> list:
        """
        Find all itineraries for a specific booking.

        Args:
            booking_id: Booking ID to search
            active_only: If True, only return active itineraries (default: True)

        Returns:
            List of matching itineraries
        """
        query = {
            'booking_id': ObjectId(booking_id) if isinstance(booking_id, str) else booking_id
        }

        if active_only:
            query['is_active'] = True

        cursor = self.collection.find(query).sort('created_at', -1)

        items = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            if 'booking_id' in doc:
                doc['booking_id'] = str(doc['booking_id'])
            items.append(doc)

        return items

    def find_by_booking_and_type(self, booking_id: str, itinerary_type: str, active_only: bool = True) -> Optional[dict]:
        """
        Find a specific itinerary by booking ID and type.

        Args:
            booking_id: Booking ID
            itinerary_type: Type of itinerary ('option_1', 'option_2', 'extension', 'final', etc.)
            active_only: If True, only return active itinerary (default: True)

        Returns:
            Matching itinerary or None
        """
        query = {
            'booking_id': ObjectId(booking_id) if isinstance(booking_id, str) else booking_id,
            'itinerary_type': itinerary_type
        }

        if active_only:
            query['is_active'] = True

        doc = self.collection.find_one(query, sort=[('version', -1)])

        if doc:
            doc['_id'] = str(doc['_id'])
            if 'booking_id' in doc:
                doc['booking_id'] = str(doc['booking_id'])

        return doc

    def deactivate_itinerary(self, doc_id: str) -> bool:
        """
        Deactivate an itinerary (soft delete).

        Args:
            doc_id: Document ID

        Returns:
            True if deactivated, False otherwise
        """
        result = self.collection.update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'is_active': False,
                '_metadata.updated_at': datetime.utcnow()
            }}
        )

        return result.modified_count > 0

    def update(self, doc_id: str, data: dict) -> bool:
        """
        Update an itinerary document.

        Args:
            doc_id: Document ID
            data: Updated data

        Returns:
            True if updated, False otherwise
        """
        data['_metadata'] = data.get('_metadata', {})
        data['_metadata']['updated_at'] = datetime.utcnow()

        result = self.collection.update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': data}
        )

        return result.modified_count > 0

    def delete(self, doc_id: str) -> bool:
        """
        Delete an itinerary document.

        Args:
            doc_id: Document ID

        Returns:
            True if deleted, False otherwise
        """
        result = self.collection.delete_one({'_id': ObjectId(doc_id)})
        return result.deleted_count > 0

    def get_summary(self, doc_id: str) -> Optional[dict]:
        """
        Get a summary of an itinerary (lightweight).

        Args:
            doc_id: Document ID

        Returns:
            Summary dictionary or None
        """
        doc = self.find_by_id(doc_id)
        if not doc:
            return None

        overview = doc.get('trip_overview', {})
        daily = doc.get('daily_itinerary', [])

        return {
            '_id': doc['_id'],
            'tour_name': overview.get('tour_name', 'Unknown'),
            'client_group': overview.get('client_group', ''),
            'dates': overview.get('dates', ''),
            'duration': overview.get('duration', ''),
            'days': len(daily),
            'countries': overview.get('countries_visited', []),
            'scraped_at': doc.get('_metadata', {}).get('scraped_at')
        }

    def get_daily_summary(self, doc_id: str) -> list:
        """
        Get a daily summary of the itinerary.

        Args:
            doc_id: Document ID

        Returns:
            List of daily summaries
        """
        doc = self.find_by_id(doc_id)
        if not doc:
            return []

        summaries = []
        for day in doc.get('daily_itinerary', []):
            summaries.append({
                'day': day.get('day'),
                'date': day.get('date'),
                'location': day.get('location'),
                'accommodation': day.get('accommodation', {}).get('name'),
                'activities_count': len(day.get('activities', []))
            })

        return summaries


# MongoDB schema for validation (can be used with MongoDB validator)
MONGODB_VALIDATOR = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['trip_overview', 'daily_itinerary'],
        'properties': {
            'trip_overview': {
                'bsonType': 'object',
                'required': ['tour_name'],
                'properties': {
                    'tour_name': {'bsonType': 'string'},
                    'dates': {'bsonType': 'string'},
                    'duration': {'bsonType': 'string'},
                    'client_group': {'bsonType': 'string'},
                    'tour_operator': {'bsonType': 'string'},
                    'group_size': {'bsonType': 'int'},
                    'countries_visited': {
                        'bsonType': 'array',
                        'items': {'bsonType': 'string'}
                    },
                    'languages': {'bsonType': 'string'},
                    'contact': {
                        'bsonType': 'object',
                        'properties': {
                            'email': {'bsonType': 'string'},
                            'phone': {'bsonType': 'string'},
                            'mobile': {'bsonType': 'string'}
                        }
                    }
                }
            },
            'logistics': {
                'bsonType': 'object',
                'properties': {
                    'summary': {'bsonType': 'string'},
                    'flight_details': {'bsonType': 'object'},
                    'transfer_arrangements': {'bsonType': 'object'},
                    'accommodation_patterns': {'bsonType': 'object'},
                    'meal_plan_overview': {'bsonType': 'object'},
                    'timing_considerations': {'bsonType': 'object'},
                    'documents_and_preparations': {'bsonType': 'object'},
                    'emergency_contacts': {'bsonType': 'array'}
                }
            },
            'daily_breakdown_summary': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'properties': {
                        'day': {'bsonType': 'int'},
                        'date': {'bsonType': 'string'},
                        'title': {'bsonType': 'string'},
                        'summary': {'bsonType': 'string'},
                        'highlights': {'bsonType': 'array'},
                        'distance_traveled': {'bsonType': 'string'},
                        'accommodation_type': {'bsonType': 'string'},
                        'meals_included': {'bsonType': 'string'}
                    }
                }
            },
            'daily_itinerary': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'required': ['day', 'location'],
                    'properties': {
                        'day': {'bsonType': 'int'},
                        'date': {'bsonType': 'string'},
                        'location': {'bsonType': 'string'},
                        'accommodation': {'bsonType': 'object'},
                        'meals': {'bsonType': 'object'},
                        'activities': {'bsonType': 'array'},
                        'optional_activities': {'bsonType': 'array'},
                        'notes': {'bsonType': 'string'}
                    }
                }
            },
            'inclusions': {'bsonType': 'object'},
            'exclusions': {'bsonType': 'array'},
            'important_information': {'bsonType': 'object'},
            '_metadata': {
                'bsonType': 'object',
                'properties': {
                    'scraped_at': {'bsonType': 'date'},
                    'version': {'bsonType': 'string'},
                    'source_url': {'bsonType': 'string'},
                    'created_by': {'bsonType': 'string'},
                    'created_at': {'bsonType': 'date'},
                    'updated_at': {'bsonType': 'date'}
                }
            }
        }
    }
}
