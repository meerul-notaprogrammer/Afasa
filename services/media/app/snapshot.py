"""
AFASA 2.0 - Snapshot Capture
FFmpeg-based RTSP snapshot extraction
"""
import asyncio
import subprocess
import tempfile
from typing import Dict, Any
from PIL import Image
import io


async def capture_snapshot(rtsp_url: str) -> Dict[str, Any]:
    """
    Capture a single frame from RTSP stream using FFmpeg.
    Returns dict with 'data' (bytes), 'width', 'height'.
    """
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    
    # FFmpeg command to capture single frame
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-frames:v", "1",
        "-q:v", "2",
        "-y",
        tmp_path
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")
        
        # Read the captured image
        with open(tmp_path, "rb") as f:
            data = f.read()
        
        # Get dimensions
        img = Image.open(io.BytesIO(data))
        width, height = img.size
        
        return {
            "data": data,
            "width": width,
            "height": height
        }
    
    except asyncio.TimeoutError:
        raise Exception("Snapshot capture timeout")
    
    finally:
        # Cleanup
        import os
        try:
            os.unlink(tmp_path)
        except:
            pass
