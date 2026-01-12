"""
Logs Router - Real-time log streaming via SSE
"""
import asyncio
import subprocess
import time
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import structlog

logger = structlog.get_logger()
router = APIRouter()


def _escape_sse(text: str) -> str:
    return text.replace("\n", "\\n").replace("\r", "")


def _try_get_docker_client():
    try:
        import docker  # type: ignore
        return docker.from_env()
    except Exception:
        return None


async def stream_docker_logs(container: str, lines: int = 100):
    """Stream Docker container logs via SSE"""
    docker_client = _try_get_docker_client()

    if docker_client is not None:
        try:
            c = docker_client.containers.get(container)
            yield f"data: [Connected to {container} logs]\n\n"

            initial = c.logs(tail=lines)
            if initial:
                for raw_line in initial.decode("utf-8", errors="replace").splitlines():
                    if raw_line:
                        yield f"data: {_escape_sse(raw_line)}\n\n"

            stream = c.logs(stream=True, follow=True, tail=0, since=int(time.time()))
            it = iter(stream)
            while True:
                chunk = await asyncio.to_thread(next, it)
                if not chunk:
                    await asyncio.sleep(0.1)
                    continue
                text = chunk.decode("utf-8", errors="replace")
                for raw_line in text.splitlines():
                    if raw_line:
                        yield f"data: {_escape_sse(raw_line)}\n\n"
        except Exception as e:
            yield f"data: [Error: {str(e)}]\n\n"
        return

    try:
        # Start docker logs process with follow
        process = await asyncio.create_subprocess_exec(
            'docker', 'logs', '-f', '--tail', str(lines), container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        # Send initial event
        yield f"data: [Connected to {container} logs]\n\n"
        
        # Stream logs
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            # Escape special characters for SSE
            text = line.decode('utf-8', errors='replace').rstrip()
            if text:
                # Escape newlines and format for SSE
                yield f"data: {_escape_sse(text)}\n\n"
                
    except Exception as e:
        yield f"data: [Error: {str(e)}]\n\n"
    finally:
        if process:
            process.terminate()
            await process.wait()


async def stream_all_logs(services: list, lines: int = 50):
    """Stream logs from multiple Docker containers"""
    try:
        # Build docker compose logs command
        cmd = ['docker', 'compose', 'logs', '-f', '--tail', str(lines)] + services
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd='/home/tom/github/founder-pl/br'
        )
        
        yield f"data: [Connected to logs: {', '.join(services)}]\n\n"
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            text = line.decode('utf-8', errors='replace').rstrip()
            if text:
                yield f"data: {_escape_sse(text)}\n\n"
                
    except Exception as e:
        yield f"data: [Error: {str(e)}]\n\n"
    finally:
        if process:
            process.terminate()
            await process.wait()


@router.get("/stream")
async def stream_logs(
    service: Optional[str] = Query(default=None, description="Service name (api, ocr, llm, web, postgres, redis)"),
    lines: int = Query(default=100, ge=10, le=1000, description="Number of initial lines")
):
    """
    Stream real-time logs via Server-Sent Events (SSE).
    
    Services: api, ocr, llm, web, postgres, redis, celery-worker, celery-beat
    """
    container_map = {
        'api': 'br-api',
        'ocr': 'br-ocr', 
        'llm': 'br-llm',
        'web': 'br-web',
        'postgres': 'br-postgres',
        'redis': 'br-redis',
        'celery-worker': 'br-celery-worker',
        'celery-beat': 'br-celery-beat',
        'flower': 'br-flower'
    }
    
    if service:
        container = container_map.get(service)
        if not container:
            return {"error": f"Unknown service: {service}. Available: {list(container_map.keys())}"}
        
        return StreamingResponse(
            stream_docker_logs(container, lines),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # Stream all main services
        services = ['api', 'ocr-service', 'llm-service']
        return StreamingResponse(
            stream_all_logs(services, lines),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache", 
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )


@router.get("/snapshot")
async def get_logs_snapshot(
    service: str = Query(..., description="Service name"),
    lines: int = Query(default=100, ge=10, le=1000)
):
    """Get a snapshot of recent logs (non-streaming)"""
    container_map = {
        'api': 'br-api',
        'ocr': 'br-ocr',
        'llm': 'br-llm', 
        'web': 'br-web',
        'postgres': 'br-postgres',
        'redis': 'br-redis'
    }
    
    container = container_map.get(service)
    if not container:
        return {"error": f"Unknown service: {service}"}
    
    try:
        docker_client = _try_get_docker_client()
        if docker_client is not None:
            c = docker_client.containers.get(container)
            out = c.logs(tail=lines)
            text_out = out.decode("utf-8", errors="replace") if out else ""
            return {
                "service": service,
                "container": container,
                "lines": text_out.split('\n') if text_out else [],
                "errors": []
            }

        result = subprocess.run(
            ['docker', 'logs', '--tail', str(lines), container],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return {
            "service": service,
            "container": container,
            "lines": result.stdout.split('\n') if result.stdout else [],
            "errors": result.stderr.split('\n') if result.stderr else []
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/services")
async def list_services():
    """List available services for log streaming"""
    return {
        "services": [
            {"id": "api", "name": "API Backend", "container": "br-api"},
            {"id": "ocr", "name": "OCR Service", "container": "br-ocr"},
            {"id": "llm", "name": "LLM Service", "container": "br-llm"},
            {"id": "web", "name": "Web Frontend", "container": "br-web"},
            {"id": "postgres", "name": "PostgreSQL", "container": "br-postgres"},
            {"id": "redis", "name": "Redis", "container": "br-redis"},
            {"id": "celery-worker", "name": "Celery Worker", "container": "br-celery-worker"},
            {"id": "flower", "name": "Flower", "container": "br-flower"}
        ]
    }
