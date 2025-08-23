#!/usr/bin/env python3
import os
import sys

print(f"Python path: {sys.path}")
print(f"Current working directory: {os.getcwd()}")
print(f"DISABLE_AI_PROCESSING env var: {os.getenv('DISABLE_AI_PROCESSING', 'NOT_SET')}")

# Test the conditional import
AI_DISABLED = os.getenv('DISABLE_AI_PROCESSING', 'false').lower() == 'true'
print(f"AI_DISABLED: {AI_DISABLED}")

if AI_DISABLED:
    print("AI is disabled - would import lightweight version")
    try:
        from app.services.ai.content_matcher_local import ContentMatcher
        print("Successfully imported lightweight ContentMatcher")
    except Exception as e:
        print(f"Error importing lightweight version: {e}")
else:
    print("AI is enabled - would import full version with face_recognition")
    try:
        import face_recognition
        print("face_recognition imported successfully")
    except Exception as e:
        print(f"Error importing face_recognition: {e}")