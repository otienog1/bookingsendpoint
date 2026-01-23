"""
Itinerary Agent - AI assistant for itinerary management

Provides conversational assistance for:
- Answering questions about itineraries
- Validating itinerary completeness
- Suggesting improvements
- Generating summaries and reports
"""

import os
from typing import Optional, List, Dict
from datetime import datetime


class ItineraryAgent:
    """AI agent for itinerary assistance and management."""

    def __init__(self, mongo, llm_provider: str = 'gemini'):
        """
        Initialize the itinerary agent.

        Args:
            mongo: Flask-PyMongo instance
            llm_provider: 'gemini' or 'anthropic' (default: gemini)
        """
        self.mongo = mongo
        self.llm_provider = llm_provider
        self.collection = mongo.db['itineraries']

        # Configure LLM
        if llm_provider == 'gemini':
            from google import genai
            self.gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
            # Models to try in order of preference
            self.gemini_models = [
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
            ]
        else:
            import anthropic
            self.anthropic_client = anthropic.Anthropic(
                api_key=os.getenv('ANTHROPIC_API_KEY')
            )

    def chat(
        self,
        message: str,
        itinerary_id: Optional[str] = None,
        conversation_history: List[Dict] = None
    ) -> Dict:
        """
        Chat with the agent about an itinerary.

        Args:
            message: User's message/question
            itinerary_id: Optional itinerary document ID for context
            conversation_history: Optional list of previous messages

        Returns:
            Dictionary with agent response and metadata
        """
        # Get itinerary context if ID provided
        itinerary_context = None
        if itinerary_id:
            from .itinerary_model import ItineraryModel
            model = ItineraryModel(self.mongo)
            itinerary_context = model.find_by_id(itinerary_id)

        # Build prompt with context
        prompt = self._build_chat_prompt(
            message,
            itinerary_context,
            conversation_history
        )

        # Get LLM response
        if self.llm_provider == 'gemini':
            response = self._chat_with_gemini(prompt)
        else:
            response = self._chat_with_anthropic(prompt)

        return {
            'message': response,
            'timestamp': datetime.utcnow().isoformat(),
            'itinerary_id': itinerary_id
        }

    def validate_itinerary(self, itinerary_id: str) -> Dict:
        """
        Validate an itinerary for completeness and consistency.

        Args:
            itinerary_id: Document ID

        Returns:
            Validation report with issues and suggestions
        """
        from .itinerary_model import ItineraryModel
        model = ItineraryModel(self.mongo)
        itinerary = model.find_by_id(itinerary_id)

        if not itinerary:
            return {'error': 'Itinerary not found'}

        # Build validation prompt
        prompt = self._build_validation_prompt(itinerary)

        # Get LLM analysis
        if self.llm_provider == 'gemini':
            analysis = self._chat_with_gemini(prompt)
        else:
            analysis = self._chat_with_anthropic(prompt)

        return {
            'itinerary_id': itinerary_id,
            'validation_report': analysis,
            'timestamp': datetime.utcnow().isoformat()
        }

    def suggest_improvements(self, itinerary_id: str) -> Dict:
        """
        Suggest improvements for an itinerary.

        Args:
            itinerary_id: Document ID

        Returns:
            Suggestions for improvements
        """
        from .itinerary_model import ItineraryModel
        model = ItineraryModel(self.mongo)
        itinerary = model.find_by_id(itinerary_id)

        if not itinerary:
            return {'error': 'Itinerary not found'}

        # Build improvement prompt
        prompt = self._build_improvement_prompt(itinerary)

        # Get LLM suggestions
        if self.llm_provider == 'gemini':
            suggestions = self._chat_with_gemini(prompt)
        else:
            suggestions = self._chat_with_anthropic(prompt)

        return {
            'itinerary_id': itinerary_id,
            'suggestions': suggestions,
            'timestamp': datetime.utcnow().isoformat()
        }

    def generate_summary(self, itinerary_id: str, summary_type: str = 'overview') -> Dict:
        """
        Generate a summary of an itinerary.

        Args:
            itinerary_id: Document ID
            summary_type: 'overview', 'daily', 'highlights', or 'logistics'

        Returns:
            Generated summary
        """
        from .itinerary_model import ItineraryModel
        model = ItineraryModel(self.mongo)
        itinerary = model.find_by_id(itinerary_id)

        if not itinerary:
            return {'error': 'Itinerary not found'}

        # Build summary prompt
        prompt = self._build_summary_prompt(itinerary, summary_type)

        # Get LLM summary
        if self.llm_provider == 'gemini':
            summary = self._chat_with_gemini(prompt)
        else:
            summary = self._chat_with_anthropic(prompt)

        return {
            'itinerary_id': itinerary_id,
            'summary_type': summary_type,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _build_chat_prompt(
        self,
        message: str,
        itinerary_context: Optional[Dict],
        conversation_history: Optional[List[Dict]]
    ) -> str:
        """Build chat prompt with context."""
        prompt_parts = [
            "You are an expert safari itinerary assistant. You help users understand, plan, and optimize safari itineraries.",
            "You have deep knowledge of East African and Southern African safari destinations, accommodations, wildlife, and travel logistics.",
            ""
        ]

        if itinerary_context:
            prompt_parts.extend([
                "CURRENT ITINERARY CONTEXT:",
                f"Tour Name: {itinerary_context.get('trip_overview', {}).get('tour_name', 'Unknown')}",
                f"Client: {itinerary_context.get('trip_overview', {}).get('client_group', 'Unknown')}",
                f"Dates: {itinerary_context.get('trip_overview', {}).get('dates', 'Unknown')}",
                f"Duration: {itinerary_context.get('trip_overview', {}).get('duration', 'Unknown')}",
                "",
                "Full itinerary data:",
                str(itinerary_context),
                ""
            ])

        if conversation_history:
            prompt_parts.append("CONVERSATION HISTORY:")
            for entry in conversation_history[-5:]:  # Last 5 messages
                prompt_parts.append(f"User: {entry.get('user', '')}")
                prompt_parts.append(f"Agent: {entry.get('agent', '')}")
            prompt_parts.append("")

        prompt_parts.extend([
            "USER QUESTION:",
            message,
            "",
            "INSTRUCTIONS:",
            "- Provide helpful, accurate, and concise responses",
            "- Reference specific details from the itinerary when relevant",
            "- If you don't have enough information, say so clearly",
            "- Use friendly, professional tone",
            "- Format responses with bullet points or sections when appropriate",
            "",
            "YOUR RESPONSE:"
        ])

        return "\n".join(prompt_parts)

    def _build_validation_prompt(self, itinerary: Dict) -> str:
        """Build validation prompt."""
        return f"""You are an expert safari itinerary validator. Analyze the following itinerary for completeness, consistency, and potential issues.

ITINERARY DATA:
{itinerary}

VALIDATION CHECKLIST:
1. **Trip Overview Completeness**
   - Tour name, dates, duration present and formatted correctly
   - Client information complete
   - Contact details present
   - Countries visited listed

2. **Daily Itinerary Consistency**
   - All days numbered sequentially
   - Dates are consecutive and match duration
   - Each day has location and accommodation
   - Meal plans are consistent with accommodation basis
   - Activities are described adequately

3. **Inclusions Accuracy**
   - Accommodations: Check nights total matches duration, room types specified
   - Meals: Verify meal plans match accommodation basis for each property
   - Flights: All flights have origin, destination, and timing details
   - Transportation: Transfers have origin, destination, and vehicle type
   - Activities: All activities clearly described
   - Services: Guide information, park fees, etc. included

4. **Data Quality Issues**
   - Missing required information
   - Inconsistent formatting
   - Contradictory information
   - Unclear or vague descriptions

PROVIDE A STRUCTURED VALIDATION REPORT:
- **Status**: Pass / Pass with warnings / Fail
- **Critical Issues**: List any blocking problems
- **Warnings**: List any concerns that should be addressed
- **Suggestions**: List recommended improvements
- **Data Quality Score**: Rate 1-10

Format your response clearly with sections and bullet points."""

    def _build_improvement_prompt(self, itinerary: Dict) -> str:
        """Build improvement prompt."""
        overview = itinerary.get('trip_overview', {})
        daily = itinerary.get('daily_itinerary', [])

        return f"""You are an expert safari travel planner. Review this itinerary and suggest improvements.

ITINERARY OVERVIEW:
Tour: {overview.get('tour_name', 'Unknown')}
Duration: {overview.get('duration', 'Unknown')}
Countries: {', '.join(overview.get('countries_visited', []))}
Days: {len(daily)}

FULL ITINERARY DATA:
{itinerary}

PROVIDE IMPROVEMENT SUGGESTIONS FOR:

1. **Pacing and Flow**
   - Is the itinerary well-paced or too rushed/slow?
   - Are travel days balanced with activity days?
   - Suggested timing adjustments

2. **Accommodation Selection**
   - Quality and appropriateness of lodges/camps
   - Better alternatives if any
   - Strategic positioning for wildlife viewing

3. **Activities and Experiences**
   - Missing must-see attractions or experiences
   - Optimal timing for game drives
   - Seasonal considerations
   - Unique experiences to add

4. **Logistics Optimization**
   - More efficient routing
   - Better flight connections
   - Transfer timing improvements

5. **Client Experience Enhancement**
   - Special touches to add
   - Photography opportunities
   - Cultural experiences
   - Dietary or special needs considerations

Format your response with clear sections, priorities (High/Medium/Low), and specific actionable recommendations."""

    def _build_summary_prompt(self, itinerary: Dict, summary_type: str) -> str:
        """Build summary prompt based on type."""
        overview = itinerary.get('trip_overview', {})

        base_prompt = f"""Generate a {summary_type} summary for this safari itinerary:

ITINERARY DATA:
{itinerary}

"""

        type_instructions = {
            'overview': """Create a compelling OVERVIEW summary (2-3 paragraphs) that includes:
- Destination highlights and countries visited
- Duration and key dates
- Accommodation types and standards
- Main activities and experiences
- What makes this itinerary special

Write in engaging, professional style suitable for client presentation.""",

            'daily': """Create a DAILY BREAKDOWN summary with:
- Day-by-day highlights (1-2 sentences per day)
- Key locations and movements
- Main activities each day
- Accommodation each night

Format as a numbered list, concise and scannable.""",

            'highlights': """Create a HIGHLIGHTS summary featuring:
- Top 5-7 experiences in this itinerary
- Wildlife viewing opportunities
- Unique activities or cultural experiences
- Special accommodations or locations
- Photography opportunities

Format as bullet points with brief descriptions.""",

            'logistics': """Create a LOGISTICS summary covering:
- Flight details and connections
- Transfer arrangements
- Accommodation check-in/out patterns
- Meal plan overview
- Important timing considerations
- Documents or preparations needed

Format as organized sections with clear information."""
        }

        return base_prompt + type_instructions.get(summary_type, type_instructions['overview'])

    def _chat_with_gemini(self, prompt: str) -> str:
        """Get response from Gemini with model fallback."""
        from google.genai import types

        last_error = None
        for model_name in self.gemini_models:
            try:
                response = self.gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=2000,
                    )
                )
                return response.text
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                # If model is unavailable, try next one
                if "404" in error_str or "not found" in error_str or "unavailable" in error_str:
                    continue
                else:
                    # For other errors, return immediately
                    return f"Error generating response: {str(e)}"

        return f"Error generating response: All models failed. Last error: {str(last_error)}"

    def _chat_with_anthropic(self, prompt: str) -> str:
        """Get response from Claude."""
        try:
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            return f"Error generating response: {str(e)}"
