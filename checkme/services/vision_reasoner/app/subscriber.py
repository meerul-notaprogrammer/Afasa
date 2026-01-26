"""
AFASA 2.0 - Detection Event Subscriber
Auto-runs reasoning on significant detections
"""
import sys
sys.path.insert(0, '/app/services')

from common import get_event_bus, EventEnvelope, Subjects, get_storage_client
from app.reasoner import get_reasoner


# Only run reasoning for these detection types
SIGNIFICANT_LABELS = [
    "leaf_blight",
    "powdery_mildew",
    "rust",
    "bacterial_spot",
    "mosaic_virus",
    "anthracnose",
    "pest",
    "wilting"
]


async def handle_detection_created(envelope: EventEnvelope):
    """Handle detection events and run reasoning if significant"""
    data = envelope.data
    tenant_id = envelope.tenant_id
    
    detections = data.get("detections", [])
    
    # Check if any detection warrants reasoning
    significant = [
        d for d in detections 
        if d.get("label", "").lower() in SIGNIFICANT_LABELS
        and d.get("confidence", 0) >= 0.5
    ]
    
    if not significant:
        print(f"No significant detections in snapshot {data.get('snapshot_id')}")
        return
    
    snapshot_id = data.get("snapshot_id")
    camera_id = data.get("camera_id")
    annotated_key = data.get("annotated_s3_key")
    
    # Use annotated image if available, otherwise need original
    s3_key = annotated_key
    if not s3_key:
        print(f"No image available for reasoning on {snapshot_id}")
        return
    
    print(f"Running reasoning for {len(significant)} significant detections")
    
    try:
        storage = get_storage_client()
        reasoner = get_reasoner()
        
        # Get image
        image_data = storage.get_object(s3_key)
        
        # Build context from detections
        context = {
            "crop": "chili",
            "farm_location": "Malaysia",
            "recent_detections": significant
        }
        
        # Run reasoning
        result = await reasoner.assess(image_data, context)
        
        # Publish assessment event
        event_bus = await get_event_bus()
        await event_bus.publish(
            Subjects.ASSESSMENT_CREATED,
            tenant_id,
            {
                "assessment_id": snapshot_id,  # Using snapshot ID as assessment reference
                "snapshot_id": snapshot_id,
                "camera_id": camera_id,
                "severity": result.get("severity", "low"),
                "hypotheses": result.get("hypotheses", []),
                "recommended_actions": result.get("recommended_actions", [])
            },
            producer="afasa-vision-reasoner",
            correlation_id=envelope.correlation_id
        )
        
        print(f"Assessment complete: severity={result.get('severity')}")
        
    except Exception as e:
        print(f"Error in reasoning for {snapshot_id}: {e}")


async def start_detection_subscriber():
    """Start listening for detection events"""
    event_bus = await get_event_bus()
    await event_bus.subscribe(
        Subjects.DETECTION_CREATED,
        handle_detection_created,
        queue="reasoner-workers"
    )
    print("Vision Reasoner subscriber started")
