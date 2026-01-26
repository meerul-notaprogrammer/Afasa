"""
AFASA 2.0 - Snapshot Event Subscriber
Auto-runs inference on new snapshots
"""
import sys
sys.path.insert(0, '/app/services')

from common import get_event_bus, EventEnvelope, Subjects, get_storage_client
from app.infer import get_detector


async def handle_snapshot_created(envelope: EventEnvelope):
    """Handle incoming snapshot events and run inference"""
    data = envelope.data
    tenant_id = envelope.tenant_id
    
    snapshot_id = data.get("snapshot_id")
    camera_id = data.get("camera_id")
    s3_key = data.get("s3_key")
    
    if not all([snapshot_id, camera_id, s3_key]):
        print("Missing required fields in snapshot event")
        return
    
    print(f"Processing snapshot {snapshot_id} for tenant {tenant_id}")
    
    try:
        storage = get_storage_client()
        detector = get_detector()
        
        # Get image
        image_data = storage.get_object(s3_key)
        
        # Run inference
        result = detector.infer(image_data, threshold=0.5)
        
        # Upload annotated if detections found
        annotated_s3_key = None
        if result["detections"] and result["annotated_data"]:
            annotated_s3_key = storage.upload_annotated(
                tenant_id,
                snapshot_id,
                result["annotated_data"]
            )
        
        # Publish detection event
        event_bus = await get_event_bus()
        await event_bus.publish(
            Subjects.DETECTION_CREATED,
            tenant_id,
            {
                "detection_batch_id": snapshot_id,
                "snapshot_id": snapshot_id,
                "camera_id": camera_id,
                "model": "yolov8n",
                "threshold": 0.5,
                "detections": result["detections"],
                "annotated_s3_key": annotated_s3_key
            },
            producer="afasa-vision-yolo",
            correlation_id=envelope.correlation_id
        )
        
        print(f"Detected {len(result['detections'])} objects in snapshot {snapshot_id}")
        
    except Exception as e:
        print(f"Error processing snapshot {snapshot_id}: {e}")


async def start_snapshot_subscriber():
    """Start listening for snapshot events"""
    event_bus = await get_event_bus()
    await event_bus.subscribe(
        Subjects.SNAPSHOT_CREATED,
        handle_snapshot_created,
        queue="yolo-workers"
    )
    print("Vision YOLO subscriber started")
