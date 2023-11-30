import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

import cv2
# from aiohttp import web
from av import VideoFrame

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
pcs = set()
relay = MediaRelay()

class Item(BaseModel):
    sdp: str
    type: str

app = FastAPI()


class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self, track):
        super().__init__()  # don't forget this!
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        
        return frame


# async def index(request):
#     content = open(os.path.join(ROOT, "index.html"), "r").read()
#     return web.Response(content_type="text/html", text=content)


# async def javascript(request):
#     content = open(os.path.join(ROOT, "client.js"), "r").read()
#     return web.Response(content_type="application/javascript", text=content)


@app.post("/offer")
async def offer(item: Item, request: Request):
    # params = await request.json()
    offer = RTCSessionDescription(sdp=item.sdp, type=item.type)

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    # log_info("Created for %s", request.remote)
    log_info("Created for %s", request.client.host)

    # prepare local media
    player = MediaPlayer(os.path.join(ROOT, "demo-instruct.wav"))
    # if args.record_to:
    #     recorder = MediaRecorder(args.record_to)
    # else:
    recorder = MediaBlackhole()

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)

        if track.kind == "audio":
            pc.addTrack(player.audio)
            recorder.addTrack(track)
        elif track.kind == "video":
            pc.addTrack(
                VideoTransformTrack(relay.subscribe(track))
            )
            # if args.record_to:
            #     recorder.addTrack(relay.subscribe(track))

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)
            await recorder.stop()

    # handle offer
    await pc.setRemoteDescription(offer)
    await recorder.start()

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # return web.Response(
    #     content_type="application/json",
    #     text=json.dumps(
    #         {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    #     ),
    # )
    json_compatible_item_data = jsonable_encoder(Item(sdp=pc.localDescription.sdp, type=pc.localDescription.type))
    print("Here Here", json_compatible_item_data)
    return JSONResponse(content=json_compatible_item_data)


@app.on_event("shutdown")
async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


# if __name__ == "__main__":
# parser = argparse.ArgumentParser(
#     description="WebRTC audio / video / data-channels demo"
# )

# parser.add_argument(
#     "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
# )
# parser.add_argument(
#     "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
# )
# parser.add_argument("--record-to", help="Write received media to a file."),
# parser.add_argument("--verbose", "-v", action="count")
# args = parser.parse_args()


logging.basicConfig(level=logging.INFO)

# app = web.Application()
# app = FastAPI() # defined at the top

# app.on_shutdown.append(on_shutdown)
# app.router.add_get("/", index)
# app.router.add_get("/client.js", javascript)
# app.router.add_post("/offer", offer)

# web.run_app(
#     app, access_log=None, host=args.host, port=args.port
# )

app.mount("/", StaticFiles(directory="static",html = True), name="static")
