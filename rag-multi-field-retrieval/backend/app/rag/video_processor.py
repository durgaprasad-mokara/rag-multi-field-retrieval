"""
Video & Audio Processor for RAG Assistant.
Handles audio extraction with FFmpeg, Whisper speech-to-text with timestamp preservation,
noise and duplicate transcript cleaning, topic detection, and semantic chunking.
"""
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple

from langchain_core.documents import Document

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".flv"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def format_timestamp(seconds: float) -> str:
    """Format seconds (float) to MM:SS or HH:MM:SS string."""
    seconds = max(0.0, float(seconds))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def parse_timestamp_to_seconds(time_str: str) -> Optional[float]:
    """Parse string timestamp like '05:00', '5:00', '1:20:30', '5 minutes', or 'around 5 mins' into seconds."""
    if not time_str:
        return None
    clean = time_str.strip().lower()
    clean = re.sub(r"^(?:around|at|about|near|in)\s+", "", clean).strip()

    # Match "5 minutes", "5 min", "5 mins", "5m"
    min_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)\b", clean)
    if min_match:
        return float(min_match.group(1)) * 60.0

    # Match "90 seconds", "90s"
    sec_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b", clean)
    if sec_match:
        return float(sec_match.group(1))

    # Match HH:MM:SS or MM:SS
    col_match = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", clean)
    if col_match:
        h_or_m = float(col_match.group(1))
        m_or_s = float(col_match.group(2))
        s_opt = col_match.group(3)
        if s_opt is not None:
            return h_or_m * 3600.0 + m_or_s * 60.0 + float(s_opt)
        return h_or_m * 60.0 + m_or_s

    # Raw digits (default to seconds)
    if clean.isdigit():
        return float(clean)

    return None



def extract_audio_from_video(video_path: str, output_wav_path: Optional[str] = None) -> str:
    """
    Extract audio track from video file and convert to 16kHz mono WAV using ffmpeg.
    Returns path to the output WAV file.
    """
    if not output_wav_path:
        fd, output_wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

    ext = os.path.splitext(video_path)[1].lower()
    
    # If already a WAV file at 16kHz, we might still want to normalize, but check if ffmpeg is available
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",                   # Disable video recording
        "-acodec", "pcm_s16le",  # 16-bit PCM WAV
        "-ar", "16000",          # 16kHz sample rate for Whisper
        "-ac", "1",              # Mono channel
        output_wav_path,
    ]

    try:
        res = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return output_wav_path
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        # Fallback using pydub if ffmpeg CLI directly failed
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(video_path)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(output_wav_path, format="wav")
            return output_wav_path
        except Exception as pydub_err:
            raise RuntimeError(
                f"Failed to extract audio from video '{video_path}'. FFmpeg error: {e}. Pydub error: {pydub_err}"
            )


@lru_cache(maxsize=1)
def get_whisper_model():
    """
    Load Faster-Whisper model singleton on CPU with int8 quantization for ultra-fast transcription.
    """
    try:
        from faster_whisper import WhisperModel
        model_size = os.getenv("WHISPER_MODEL_SIZE", "base.en")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        return model
    except Exception as e:
        print(f"⚠️ Faster-Whisper initialization warning: {e}. Attempting fallback...")
        try:
            import whisper
            return whisper.load_model("base.en")
        except Exception as fallback_err:
            raise RuntimeError(f"Could not load Whisper speech-to-text model: {e} / {fallback_err}")


def transcribe_audio_file(audio_path: str) -> List[Dict[str, Any]]:
    """
    Transcribe an audio WAV file with timestamped segments.
    Returns list of dicts: [{"start": 0.0, "end": 2.5, "text": "..."}, ...]
    """
    model = get_whisper_model()
    segments_data: List[Dict[str, Any]] = []

    # Check if Faster-Whisper model
    if hasattr(model, "transcribe"):
        # Faster-Whisper
        try:
            segments, info = model.transcribe(
                audio_path,
                beam_size=5,
                word_timestamps=False,
                vad_filter=True,
            )
            for seg in segments:
                text = seg.text.strip()
                if text:
                    segments_data.append({
                        "start": float(seg.start),
                        "end": float(seg.end),
                        "text": text,
                    })
            return segments_data
        except Exception as e:
            print(f"Faster-whisper transcribe error: {e}")

    # Fallback for standard OpenAI whisper if present
    try:
        import whisper
        result = model.transcribe(audio_path)
        for seg in result.get("segments", []):
            text = seg.get("text", "").strip()
            if text:
                segments_data.append({
                    "start": float(seg.get("start", 0.0)),
                    "end": float(seg.get("end", 0.0)),
                    "text": text,
                })
        return segments_data
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")


def clean_transcript_text(text: str) -> str:
    """
    Clean transcription noise, stutter, and duplicate phrases while preserving meaning.
    """
    if not text:
        return ""

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text.strip())

    # Fix repetitive speech stutters (e.g. "I, I, I think" or "we we we are" -> "we are")
    text = re.sub(r"\b([A-Za-z]+)(?:[,\s]+\1\b){2,}", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\b([A-Za-z]{2,})\s+\1\b", r"\1", text, flags=re.IGNORECASE)

    # Clean double punctuation
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r",{2,}", ",", text)

    return text.strip()


def detect_topic_from_text(text: str, fallback_topic: str = "General Discussion") -> str:
    """
    Extract or infer a concise topic/section name from segment text based on introductory patterns,
    keywords, and structural cues.
    """
    clean = text.strip()
    low = clean.lower()

    # Look for explicit introductory cues
    patterns = [
        r"(?:let's talk about|today we will discuss|introduction to|we are going to cover|moving on to|next topic is|first topic is|let's look at|understanding)\s+([A-Za-z0-9\s\-]{3,40})(?:\.|\,|$|\n)",
        r"(?:what is|how does|why use)\s+([A-Za-z0-9\s\-]{3,40})\??(?:\.|\,|$|\n)",
        r"(?:chapter|section|part)\s*(?:\d+)?\s*[:\-]?\s*([A-Za-z0-9\s\-]{3,40})(?:\.|\,|$|\n)",
    ]

    for pat in patterns:
        m = re.search(pat, clean, re.IGNORECASE)
        if m:
            topic_candidate = m.group(1).strip()
            # Clean trailing words
            topic_candidate = re.sub(r"\b(?:and|or|in|of|the|a)\b$", "", topic_candidate).strip()
            if 3 <= len(topic_candidate) <= 50:
                return topic_candidate.title()

    # Keyword based concept detection
    concept_map = [
        (["variable", "variables", "data types", "datatype", "strings", "integers"], "Variables & Data Types"),
        (["function", "functions", "arguments", "parameters", "return value"], "Functions & Methods"),
        (["class", "classes", "object", "objects", "oop", "inheritance"], "Object-Oriented Programming & Classes"),
        (["docker", "container", "containers", "dockerfile", "compose"], "Docker & Containerization"),
        (["database", "sql", "postgres", "query", "tables"], "Database & Storage"),
        (["api", "endpoint", "rest", "fastapi", "http"], "API & Web Services"),
        (["model", "machine learning", "neural network", "training", "deep learning"], "Machine Learning & AI"),
        (["install", "setup", "prerequisite", "getting started", "installation"], "Installation & Setup"),
        (["summary", "conclusion", "recap", "wrapping up", "in conclusion"], "Summary & Conclusion"),
        (["introduction", "overview", "welcome", "welcome to", "intro"], "Introduction & Overview"),
    ]

    for keywords, topic_name in concept_map:
        if any(re.search(r"\b" + re.escape(kw) + r"\b", low) for kw in keywords):
            return topic_name

    # Default to first sentence snippet capitalized or fallback
    first_few_words = " ".join(clean.split()[:4]).rstrip(".,:;?")
    if len(first_few_words) >= 4 and len(first_few_words) <= 30:
        return first_few_words.title()

    return fallback_topic


def chunk_transcript_segments(
    segments: List[Dict[str, Any]],
    target_duration_secs: float = 45.0,
    max_duration_secs: float = 90.0,
    filename: str = "video.mp4",
) -> List[Dict[str, Any]]:
    """
    Perform smart semantic chunking on timestamped transcript segments.
    Groups segments into logical topic-aware windows with start/end timestamps.
    """
    if not segments:
        return []

    chunks: List[Dict[str, Any]] = []
    current_texts: List[str] = []
    chunk_start_sec = segments[0]["start"]
    current_end_sec = segments[0]["end"]
    chunk_index = 0

    for i, seg in enumerate(segments):
        seg_text = clean_transcript_text(seg.get("text", ""))
        if not seg_text:
            continue

        seg_start = seg.get("start", current_end_sec)
        seg_end = seg.get("end", seg_start + 2.0)

        duration = seg_end - chunk_start_sec

        # Check if new topic indicator or target duration reached
        has_topic_cue = any(
            seg_text.lower().startswith(cue)
            for cue in ["now let's", "next,", "moving on", "in conclusion", "to summarize", "chapter", "another"]
        )

        if (duration >= target_duration_secs or (duration >= 20.0 and has_topic_cue) or duration >= max_duration_secs) and current_texts:
            # Emit current chunk
            chunk_content = " ".join(current_texts)
            chunk_topic = detect_topic_from_text(chunk_content)
            start_formatted = format_timestamp(chunk_start_sec)
            end_formatted = format_timestamp(current_end_sec)

            chunks.append({
                "chunk_index": chunk_index,
                "start_seconds": chunk_start_sec,
                "end_seconds": current_end_sec,
                "start_time": start_formatted,
                "end_time": end_formatted,
                "topic": chunk_topic,
                "content": chunk_content,
                "timestamp_label": f"{start_formatted}–{end_formatted}",
            })
            chunk_index += 1

            # Start new chunk
            current_texts = [seg_text]
            chunk_start_sec = seg_start
            current_end_sec = seg_end
        else:
            current_texts.append(seg_text)
            current_end_sec = seg_end

    # Emit final trailing chunk
    if current_texts:
        chunk_content = " ".join(current_texts)
        chunk_topic = detect_topic_from_text(chunk_content)
        start_formatted = format_timestamp(chunk_start_sec)
        end_formatted = format_timestamp(current_end_sec)

        chunks.append({
            "chunk_index": chunk_index,
            "start_seconds": chunk_start_sec,
            "end_seconds": current_end_sec,
            "start_time": start_formatted,
            "end_time": end_formatted,
            "topic": chunk_topic,
            "content": chunk_content,
            "timestamp_label": f"{start_formatted}–{end_formatted}",
        })

    return chunks


def process_video_file(file_path: str) -> List[Document]:
    """
    Full pipeline to process a video or audio file:
    1. Extract audio to WAV (FFmpeg).
    2. Transcribe speech to text with timestamps (Whisper).
    3. Clean transcript text.
    4. Smart chunk into topic-aware semantic blocks.
    5. Return list of LangChain Document objects with timestamp and topic metadata.
    """
    filename = os.path.basename(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    temp_wav = None
    try:
        if ext in VIDEO_EXTENSIONS:
            temp_wav = extract_audio_from_video(file_path)
            audio_target = temp_wav
        else:
            # Direct audio file
            audio_target = file_path

        # Transcribe
        segments = transcribe_audio_file(audio_target)
        if not segments:
            raise ValueError(f"No speech content detected in '{filename}'.")

        # Chunk transcript
        semantic_chunks = chunk_transcript_segments(segments, filename=filename)

        documents: List[Document] = []
        for chk in semantic_chunks:
            # Build text content prefixed with timestamp and topic for clear context
            header_prefix = f"[{chk['start_time']}–{chk['end_time']}] Topic: {chk['topic']}\n"
            full_page_content = f"{header_prefix}{chk['content']}"

            doc = Document(
                page_content=full_page_content,
                metadata={
                    "source": file_path,
                    "filename": filename,
                    "document_name": filename,
                    "is_video": True,
                    "video_id": filename,
                    "chunk_id": chk["chunk_index"],
                    "chunk_index": chk["chunk_index"],
                    "start_time": chk["start_time"],
                    "end_time": chk["end_time"],
                    "start_seconds": chk["start_seconds"],
                    "end_seconds": chk["end_seconds"],
                    "topic": chk["topic"],
                    "section": chk["topic"],
                    "source_reference": f"{filename} ({chk['timestamp_label']})",
                }
            )
            documents.append(doc)

        return documents

    finally:
        # Cleanup temporary WAV file
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except Exception:
                pass
