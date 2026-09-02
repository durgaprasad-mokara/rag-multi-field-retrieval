"""
Test Suite for Video Understanding in RAG Assistant.
Tests:
- Timestamp parsing & formatting
- Transcript cleaning & noise reduction
- Topic detection
- Smart video semantic chunking
- Video-grounded question answering (summaries, topics, timestamps, semantic search, anti-hallucination)
"""
from app.rag.video_processor import (
    format_timestamp,
    parse_timestamp_to_seconds,
    clean_transcript_text,
    detect_topic_from_text,
    chunk_transcript_segments,
)
from app.rag.chain import LocalGroundedChatModel, VIDEO_FALLBACK_MSG, FALLBACK_MSG


def test_timestamp_utils():
    """Verify timestamp formatting and parsing."""
    assert format_timestamp(0.0) == "00:00"
    assert format_timestamp(65.0) == "01:05"
    assert format_timestamp(3665.0) == "01:01:05"

    assert parse_timestamp_to_seconds("00:45") == 45.0
    assert parse_timestamp_to_seconds("05:00") == 300.0
    assert parse_timestamp_to_seconds("5 minutes") == 300.0
    assert parse_timestamp_to_seconds("2 mins") == 120.0
    assert parse_timestamp_to_seconds("01:10:00") == 4200.0


def test_transcript_cleaning():
    """Verify duplicate speech stutters and transcription noise are cleaned."""
    raw_text = "Today we we we are going to learn Python.... It is, it is very powerful."
    cleaned = clean_transcript_text(raw_text)
    assert "we we we" not in cleaned
    assert "we are going to learn Python" in cleaned
    assert "...." not in cleaned


def test_topic_detection():
    """Verify topic detection from transcript introductory patterns and keywords."""
    t1 = detect_topic_from_text("Let's talk about Python Functions and how to write them.")
    assert "Functions" in t1 or "Python Functions" in t1

    t2 = detect_topic_from_text("In this section we will cover Variables and Data Types.")
    assert "Variables" in t2

    t3 = detect_topic_from_text("Now let's understand Docker and Containerization for deployment.")
    assert "Docker" in t3 or "Container" in t3


def test_chunk_transcript_segments():
    """Verify smart semantic chunking preserves timestamps and generates structured chunks."""
    sample_segments = [
        {"start": 0.0, "end": 25.0, "text": "Welcome everyone. Introduction to Python programming."},
        {"start": 26.0, "end": 55.0, "text": "Python is a versatile high level programming language."},
        {"start": 60.0, "end": 95.0, "text": "Moving on to Python variables and data types."},
        {"start": 96.0, "end": 140.0, "text": "Variables store data values like integers, strings, and floats."},
        {"start": 260.0, "end": 310.0, "text": "Next topic is Python Functions. A function is a reusable block of code used to organize and execute specific tasks."},
        {"start": 590.0, "end": 640.0, "text": "Finally let's look at Python Classes and Object-Oriented Programming."},
    ]

    chunks = chunk_transcript_segments(sample_segments, target_duration_secs=50.0, filename="python_masterclass.mp4")
    assert len(chunks) >= 3
    for chk in chunks:
        assert "start_time" in chk
        assert "end_time" in chk
        assert "topic" in chk
        assert "content" in chk
        assert len(chk["content"]) > 0


def test_video_grounded_qa_local_model():
    """Test video-grounded question answering for summaries, topics, timestamps, and semantic search."""
    video_context = """\
[00:00–00:30] Topic: Introduction to Python
Welcome to the Python masterclass. We will cover the essentials from basics to advanced.

[00:31–01:20] Topic: Python Variables & Data Types
Variables store data values in Python. Common types include integers, floats, strings, and booleans.

[04:21–05:10] Topic: Python Functions
A function is a reusable block of code used to organize and execute specific tasks. You define a function using the def keyword.

[10:00–11:20] Topic: Python Classes & OOP
Classes allow creating custom types with methods and attributes.
"""

    model = LocalGroundedChatModel()

    # 1. Semantic query
    ans_functions = model._extract_exact_answer("What does the video explain about functions?", video_context)
    assert "reusable block of code" in ans_functions

    # 2. Topic list query
    ans_topics = model._extract_exact_answer("What topics are covered in this video?", video_context)
    assert "Introduction to Python" in ans_topics
    assert "Python Functions" in ans_topics

    # 3. Video summary query
    ans_summary = model._extract_exact_answer("Summarize the video.", video_context)
    assert "Introduction to Python" in ans_summary
    assert "Python Functions" in ans_summary

    # 4. Timestamp-specific query around 5 minutes (05:00)
    ans_timestamp = model._extract_exact_answer("What is discussed around 5 minutes?", video_context)
    assert "Functions" in ans_timestamp or "04:21" in ans_timestamp

    # 5. Anti-hallucination / absent topic query
    ans_absent = model._extract_exact_answer("What does the video say about Quantum Computing and Teleportation?", video_context)
    assert ans_absent == VIDEO_FALLBACK_MSG


if __name__ == "__main__":
    test_timestamp_utils()
    test_transcript_cleaning()
    test_topic_detection()
    test_chunk_transcript_segments()
    test_video_grounded_qa_local_model()
    print("✅ All video RAG tests passed successfully!")
