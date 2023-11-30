import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid
import cv2

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from av import VideoFrame

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay


logger = logging.getLogger("pc")
pcs = set()
relay = MediaRelay()

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
        
        img = frame.to_ndarray(format="bgr24")
        print(img.shape)
        # cv2.imshow("yay!!", img)
        # cv2.waitKey(1)


class Item(BaseModel):
    sdp: str
    type: str


app = FastAPI()

@app.post("/offer")
async def rtc_connect(item: Item):
    offer = RTCSessionDescription(sdp=item.sdp, type=item.type)

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    # prepare local media
    # player = MediaPlayer(os.path.join(ROOT, "demo-instruct.wav"))
    # if args.record_to:
    #     recorder = MediaRecorder(args.record_to)
    # else:
    recorder = MediaBlackhole()


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

    json_compatible_item_data = jsonable_encoder(Item(sdp=pc.localDescription.sdp, type=pc.localDescription.type))

    return JSONResponse(content=json_compatible_item_data)



@app.get("/words")
def autocomplete_words():
    return ["hello1", "hello2", "hello3", "hello4"]


@app.get("/twitch")
def detect_twitch():
    return False


app.mount("/", StaticFiles(directory="static",html = True), name="static")