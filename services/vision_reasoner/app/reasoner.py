"""
AFASA 2.0 - Gemini Reasoning Engine
Multi-modal AI for agricultural analysis
"""
import json
import base64
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import sys
sys.path.insert(0, '/app/services')

from common import get_settings

settings = get_settings()


class GeminiReasoner:
    def __init__(self):
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self._model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self._model = None
    
    async def assess(
        self,
        image_data: bytes,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze crop image with context and return assessment.
        """
        if self._model is None:
            return self._mock_assessment()
        
        # Build prompt
        prompt = self._build_prompt(context)
        
        try:
            # Create image part
            image_part = {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_data).decode()
            }
            
            # Generate response
            response = self._model.generate_content([prompt, image_part])
            
            # Parse structured response
            return self._parse_response(response.text)
            
        except Exception as e:
            print(f"Gemini error: {e}")
            return self._mock_assessment()
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        crop = context.get("crop", "chili")
        location = context.get("farm_location", "Malaysia")
        detections = context.get("recent_detections", [])
        telemetry = context.get("recent_telemetry_summary", {})
        
        detection_summary = ""
        if detections:
            detection_summary = f"\nYOLO detections: {json.dumps(detections)}"
        
        telemetry_summary = ""
        if telemetry:
            telemetry_summary = f"\nSensor readings: {json.dumps(telemetry)}"
        
        return f"""You are an expert agricultural AI assistant analyzing a crop image.

Crop type: {crop}
Location: {location}
{detection_summary}
{telemetry_summary}

Analyze this image and provide:
1. Overall plant health assessment
2. Identify any diseases, pests, or deficiencies visible
3. Severity level (low/medium/high)
4. Confidence in each hypothesis (0-1)
5. Recommended actions with priority (1=urgent, 5=low)

Respond ONLY with valid JSON in this exact format:
{{
    "severity": "low|medium|high",
    "hypotheses": [
        {{"name": "disease_name", "confidence": 0.8, "evidence": "description"}}
    ],
    "recommended_actions": [
        {{"action": "action_description", "priority": 2, "notes": "additional_info"}}
    ],
    "summary": "brief overall assessment"
}}"""
    
    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse Gemini response into structured format"""
        try:
            # Extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        return self._mock_assessment()
    
    def _mock_assessment(self) -> Dict[str, Any]:
        """Return mock assessment when Gemini unavailable"""
        return {
            "severity": "low",
            "hypotheses": [
                {
                    "name": "healthy",
                    "confidence": 0.9,
                    "evidence": "No visible issues detected"
                }
            ],
            "recommended_actions": [
                {
                    "action": "Continue regular monitoring",
                    "priority": 5,
                    "notes": "Maintain current care routine"
                }
            ],
            "summary": "Plants appear healthy with no immediate concerns."
        }


_reasoner: GeminiReasoner = None


def get_reasoner() -> GeminiReasoner:
    global _reasoner
    if _reasoner is None:
        _reasoner = GeminiReasoner()
    return _reasoner
