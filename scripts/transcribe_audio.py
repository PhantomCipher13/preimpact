import whisper
import json

print("Loading Whisper model...")
model = whisper.load_model("base")
print("Transcribing preimpact_audio.mp4...")
result = model.transcribe("preimpact_audio.mp4")

print("\n=== FULL TRANSCRIPT ===")
print(result["text"].strip())

print("\n=== SEGMENTS WITH TIMESTAMPS ===")
segments_data = []
for seg in result["segments"]:
    start = seg["start"]
    end = seg["end"]
    text = seg["text"].strip()
    print(f"[{start:05.2f}s -> {end:05.2f}s] {text}")
    segments_data.append({"start": start, "end": end, "text": text})

with open("scripts/transcript_timestamps.json", "w", encoding="utf-8") as f:
    json.dump(segments_data, f, indent=2)
print("\nSaved to scripts/transcript_timestamps.json")
