import whisper

def transcribe_audio(audio_path: str, model_size: str = 'base'):
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    segments = [
        {'start': seg['start'], 'end': seg['end'], 'text': seg['text']}
        for seg in result['segments']
    ]
    return segments
