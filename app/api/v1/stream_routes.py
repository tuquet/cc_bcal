from flask import Blueprint, Response, request
from app.tasks import redis_client, REDIS_CHANNEL
import structlog

stream_bp = Blueprint('stream', __name__)
log = structlog.get_logger()

def event_stream():
    """
    Subscribes to the Redis channel and yields server-sent events.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)
    
    # Send a confirmation message to the client
    log.info("sse.client.connected", remote_addr=request.remote_addr)
    yield 'data: {"message": "Connection established. Waiting for job updates..."}\n\n'
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                # Format the data as a server-sent event
                log.debug("sse.message.published", data=message['data'])
                yield f"data: {message['data']}\n\n"
    except GeneratorExit:
        # This block is executed when the client disconnects
        log.info("sse.client.disconnected", remote_addr=request.remote_addr)
    finally:
        pubsub.close()

@stream_bp.route('/stream')
def stream():
    """Stream real-time job updates using Server-Sent Events (SSE).
    This endpoint maintains a long-lived connection and pushes job status
    updates as they happen on the server. Clients should use the `EventSource`
    API to connect.
    ---
    tags:
      - Real-time
    produces:
      - text/event-stream
    responses:
      200:
        description: >
          An event stream of JSON objects. Each event is a job update.
          The connection remains open.
        schema:
          type: string
          example: |
            data: {"job_id": "some-uuid", "status": "running", ...}

            data: {"job_id": "another-uuid", "status": "done", ...}
    """
    # The mimetype 'text/event-stream' is crucial for SSE
    return Response(event_stream(), mimetype='text/event-stream')