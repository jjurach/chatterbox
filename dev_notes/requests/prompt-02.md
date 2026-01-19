@AGENTS.md create a project plan in dev_notes/project_plans to work more on the TTS and STT features of chatterbox.

Read the background below, and create a detailed checklist of tasks which involve making changes to the chatterbox wyoming service to handle both these audio-start, audio-chunk, and audio-stop packets, as well as the transcribe packets.

In order to complete the TTS and STT workflows, add tasks to implement support for these events:
- STT: transcribe/audio-start/audio-chunk/audio-stop events -> transcript event (from whisper)
- TTS: synchronize event -> audio-start/audio-chunk/audio-stop events (from piper)

Add tasks to fix the wyoming test client to focus on this ha-to-brain interaction. Implement the advice below to arrange for the wyoming test client to think and behave like the ha it emulating -- NOT a satellite it is no longer emulating.

For STT, the test client should transmit audio, and then wait upto 20 seconds
for a transcript event after the audio-stop packet. The client should treat
any such timeout as a failure.

For TTS, the test client should transmit the synchronize event, and then wait
upto 20 seconds for a response.

- create task to configure (e.g. with command-line argument) the whisper and piper language models.
  - whisper should use small.en by default
  - piper should use en_US-danny-low by default.

- create a task to initialize both whisper and piper with configured models.
  - arrange for these models to be cached in different directories somewhere in $HOME directory and not e.g. within a local tmp subdirectory.
    - allow the location for each directory be configurable e.g. by command-line switch
  - once the model is downloaded, it shouldn't have to be downloaded again.
  - the server log should be clear when it is starting to load a model and after it has completed that load.
  - both whisper and piper models should be initialized before chatterbox accepts new connections.

- create a task to confirm and test that chatterbox can handle several concurrent connections.

- research google search for whisper and piper libraries to determine if it is necessary to build some kind of mutex to prevent concurrent access to those model resources, or whether whisper and piper can efficiently process requests in parallel. create docs/assist-service-concurrency.md with any types, advice about contention across multiple connections from home assistant.

- create task to scan the entire source tree and change all variations of "chatterbox3b" to be just "chatterbox".  Currently, chatterbox is the name of the "brain server" which will implement wyoming events for interactions with ha.

- insert several tasks to verify that pytest tests continue to succeed, and focus on making scripts/chat-demo.sh better and better run the wyoming client to emulate ha connecting to and transmitting requests to chatterbox.

- Add general reminder to our project plan that the agent should use scripts/run-server.sh to restart or status the service, and should regularly consult the server log to see if there are any errors or to see the activity on the server.

Create this project plan now. Do not implement this plan yet.


# Background

In this "Second Brain" architecture, Home Assistant (HA) is the orchestrator (the Client) and your Python brain/hub is the provider (the Server).To test your brain server, you need to understand the Home Assistant ➔ Brain pattern. This connection is indeed persistent and initiated by Home Assistant. HA connects to your server's port (e.g., 10300 for STT or 10200 for TTS) and keeps that TCP socket open.📡 The Communication Pattern: HA as OrchestratorWhen a user speaks into the box3b, HA acts as a mediator. It receives audio from the satellite and then "re-broadcasts" it to your brain server.

1. The Speech-to-Text (STT) Pattern
When HA needs to transcribe audio, it reaches out to your brain server:Initiation: HA sends a transcribe event (specifying language/model)
.The Stream: HA immediately follows with audio-start, then a series of audio-chunk packets (the PCM audio it just got from the box3b).
The Signal: Once HA detects silence (VAD) or the satellite sends audio-stop, HA sends audio-stop to your brain server.
The Response (What your server sends back): Your brain server must process the audio and send a single transcript event back through that same persistent socket:JSON{"type": "transcript", "data": {"text": "What time is it?"}}

2. The Text-to-Speech (TTS) Pattern
Once the LLM generates a response, HA needs to turn it into audio:Initiation: HA sends a synthesize event containing the text.
The Stream (The Response from your server): Your server doesn't send one packet; it sends a stream back into the socket:audio-start: Initial metadata.audio-chunk: Multiple packets of PCM audio as they are generated.audio-stop: To signal the end of the voice response.🧪 What your Test Client needs to "Wait For"If you are writing a tool to test your brain server, your tool needs to emulate Home Assistant's behavior. Here are the specific events your test client should report on:Pipeline StageYour Test Client SendsYour Brain Server Sends Back (Wait for this)STT Testingaudio-start ➔ chunks ➔ audio-stoptranscript (Check if the text matches your .wav content).
LLM Testing - recognize (text) intent or handled (Check if the LLM understood the command).
TTS Testing - synthesize (text) audio-start ➔ chunks ➔ audio-stop.🛠️ Detailed "Response Packet" StructureYour brain server's response isn't just raw text or audio; it’s wrapped in the Wyoming JSONL format.

Example: The transcript response (from STT/Whisper):JSON{"type": "transcript", "data": {"text": "hello world"}, "payload_length": null}

Example: The audio-chunk response (from TTS/Piper):JSON{"type": "audio-chunk", "data": {"rate": 22050, "width": 2, "channels": 1}, "payload_length": 1024}

[1024 bytes of raw binary PCM data follows immediately]

🏁 Next Step for your Python BrainSince you are focusing on the server-side, you'll need to handle multiple concurrent sockets if you have more than one satellite, as HA will open a fresh connection for each "provider" entry in the Wyoming integration.
