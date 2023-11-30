let data = [...Array(26).keys()].map(i => String.fromCharCode(i + 97)).concat([" ", "⌫", ",", "↵"]);
let text = "";
let grid = document.getElementById('grid');
let rowIndex = 0;
let cellIndex = 0;

const textDisplay = document.getElementById('textDisplay');

// get DOM elements
var iceConnectionLog = document.getElementById('ice-connection-state'),
    iceGatheringLog = document.getElementById('ice-gathering-state'),
    signalingLog = document.getElementById('signaling-state');

// peer connection
var pc = null;
// data channel
var dc = null, dcInterval = null;

//---------------------------------------------------

function createPeerConnection() {
    var config = {
        sdpSemantics: 'unified-plan'
    };

    config.iceServers = [{urls: ['stun:stun.l.google.com:19302']}];

    pc = new RTCPeerConnection(config);

    // register some listeners to help debugging
    pc.addEventListener('icegatheringstatechange', function() {
        iceGatheringLog.textContent += ' -> ' + pc.iceGatheringState;
    }, false);
    iceGatheringLog.textContent = pc.iceGatheringState;

    pc.addEventListener('iceconnectionstatechange', function() {
        iceConnectionLog.textContent += ' -> ' + pc.iceConnectionState;
    }, false);
    iceConnectionLog.textContent = pc.iceConnectionState;

    pc.addEventListener('signalingstatechange', function() {
        signalingLog.textContent += ' -> ' + pc.signalingState;
    }, false);
    signalingLog.textContent = pc.signalingState;

    // connect audio / video
    pc.addEventListener('track', function(evt) {
        if (evt.track.kind == 'video')
            document.getElementById('video').srcObject = evt.streams[0];
        // else
        //     document.getElementById('audio').srcObject = evt.streams[0];
    });

    return pc;
}


function negotiate() {
    return pc.createOffer().then(function(offer) {
        return pc.setLocalDescription(offer);
    }).then(function() {
        // wait for ICE gathering to complete
        return new Promise(function(resolve) {
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                function checkState() {
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                }
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(function() {
        var offer = pc.localDescription;
        var codec;

        // codec = document.getElementById('audio-codec').value;
        // if (codec !== 'default') {
        //     offer.sdp = sdpFilterCodec('audio', codec, offer.sdp);
        // }

        // codec = document.getElementById('video-codec').value;
        // if (codec !== 'default') {
        //     offer.sdp = sdpFilterCodec('video', codec, offer.sdp);
        // }

        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then(function(response) {
        return response.json();
    }).then(function(answer) {
        return pc.setRemoteDescription(answer);
    });

    //.catch(function(e) {
    //     alert(e);
    // })
}


function start_cam(){
    pc = createPeerConnection();

    var constraints = {
        audio: false,
        video: false
    };


    var resolution = "1280x720"
    if (resolution) {
        resolution = resolution.split('x');
        constraints.video = {
            width: parseInt(resolution[0], 0),
            height: parseInt(resolution[1], 0)
        };
    } else {
        constraints.video = true;
    }


    if (constraints.audio || constraints.video) {

        navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {
            stream.getTracks().forEach(function(track) {
                pc.addTrack(track, stream);
            });
            
            return negotiate();

        }, function(err) {
            alert('Could not acquire media: ' + err);
        });

    } else {
        negotiate();
    }

}


function sdpFilterCodec(kind, codec, realSdp) {
    var allowed = []
    var rtxRegex = new RegExp('a=fmtp:(\\d+) apt=(\\d+)\r$');
    var codecRegex = new RegExp('a=rtpmap:([0-9]+) ' + escapeRegExp(codec))
    var videoRegex = new RegExp('(m=' + kind + ' .*?)( ([0-9]+))*\\s*$')
    
    var lines = realSdp.split('\n');

    var isKind = false;
    for (var i = 0; i < lines.length; i++) {
        if (lines[i].startsWith('m=' + kind + ' ')) {
            isKind = true;
        } else if (lines[i].startsWith('m=')) {
            isKind = false;
        }

        if (isKind) {
            var match = lines[i].match(codecRegex);
            if (match) {
                allowed.push(parseInt(match[1]));
            }

            match = lines[i].match(rtxRegex);
            if (match && allowed.includes(parseInt(match[2]))) {
                allowed.push(parseInt(match[1]));
            }
        }
    }

    var skipRegex = 'a=(fmtp|rtcp-fb|rtpmap):([0-9]+)';
    var sdp = '';

    isKind = false;
    for (var i = 0; i < lines.length; i++) {
        if (lines[i].startsWith('m=' + kind + ' ')) {
            isKind = true;
        } else if (lines[i].startsWith('m=')) {
            isKind = false;
        }

        if (isKind) {
            var skipMatch = lines[i].match(skipRegex);
            if (skipMatch && !allowed.includes(parseInt(skipMatch[2]))) {
                continue;
            } else if (lines[i].match(videoRegex)) {
                sdp += lines[i].replace(videoRegex, '$1 ' + allowed.join(' ')) + '\n';
            } else {
                sdp += lines[i] + '\n';
            }
        } else {
            sdp += lines[i] + '\n';
        }
    }

    return sdp;
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
}


//---------------------------------------------------

async function start() {
  start_cam();

  const res = await fetch("/words");
  const words = await res.json();
  data = words.concat(data);

  for (const datum of data) {
    let cell = document.createElement('div');
    cell.classList.add('cell');
    cell.textContent = datum;
    grid.appendChild(cell);
  }

  textDisplay.textContent = text;
  setInterval(() => highlightAndMoveRight(), 2000);
}

async function highlightAndMoveRight() {
  [...grid.children].forEach((cell, index) => {
    if (Math.floor(index / 4) === rowIndex) {
      cell.classList.add('highlight-row');
      if (index % 4 === cellIndex) {
        cell.classList.add('highlight-cell');
      } else {
        cell.classList.remove('highlight-cell');
      }
    } else {
      cell.classList.remove('highlight-row');
      cell.classList.remove('highlight-cell');
    }
  });

  const res = await fetch("/twitch");
  const twitch = await res.json();

  if (twitch) {
    text += grid.children[rowIndex*4 + cellIndex].textContent;
    textDisplay.textContent = text;
    if (text.endsWith("↵")) {
      await fetch('/text', {
        method: 'POST',
        body: text,
        headers: { "Content-Type": "text/plain" }
      });
      text = "";
    }
  }

  cellIndex++;

  // After a complete row traverse, move to next row
  if (cellIndex >= 4) {
    cellIndex = 0;
    rowIndex++;

    // After the last row traverse, move back to the top row
    if (rowIndex >= 8) {
      rowIndex = 0;
    }
  }
}


start();