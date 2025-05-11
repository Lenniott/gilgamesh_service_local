import os
import sys
import json
from app.downloaders import download_media_and_metadata
from app.scene_detection import extract_scene_cuts_and_frames, get_video_duration
from app.ocr_utils import ocr_image, EASYOCR_READER
from app.transcription import transcribe_audio
from app.video_processing import extract_and_downscale_scene, cleanup_temp_files
from app.utils import clean_text, resize_image_if_needed

DEFAULT_SCENE_THRESHOLD = 0.22

def process_url(url, threshold=DEFAULT_SCENE_THRESHOLD):
    result = download_media_and_metadata(url)
    print(result)

    video_files = [f for f in result['files'] if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
    image_files = [f for f in result['files'] if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    video_thumbnails = {}
    for video in video_files:
        base_name = os.path.splitext(video)[0]
        for img in image_files:
            if img.startswith(base_name):
                video_thumbnails[video] = img
                break

    print(f"\nFound {len(video_files)} videos and {len(image_files)} images")

    videos_output = []
    all_ocr_results = []
    all_transcript_segments = []

    for video_file in video_files:
        print(f"\nProcessing video: {video_file}")
        video_scenes = []
        video_ocr_results = []
        video_transcript_segments = []
        try:
            video_name = os.path.splitext(os.path.basename(video_file))[0]
            frames_dir = os.path.join(result['temp_dir'], 'frames', video_name)
            os.makedirs(frames_dir, exist_ok=True)
            thumbnail = None
            for img in image_files:
                if img.startswith(video_name):
                    thumbnail = img
                    break
            try:
                transcript = transcribe_audio(video_file)
                video_transcript_segments.extend(transcript)
            except Exception as e:
                print(f"Warning: Could not transcribe video {video_file}: {e}")
                transcript = []
            try:
                scene_cuts = extract_scene_cuts_and_frames(video_file, frames_dir, threshold=threshold)
                print('Scene cuts:', [t for t, _ in scene_cuts])
                print('Extracted frames:', [frame for _, frame in scene_cuts])
            except Exception as e:
                print(f"Warning: Could not extract scenes from video {video_file}: {e}")
                scene_cuts = []
            duration = get_video_duration(video_file)
            if not scene_cuts and thumbnail:
                onscreen_text = ocr_image(thumbnail)
                video_scenes.append({
                    'start': 0,
                    'end': duration if duration else 0,
                    'transcript': [],
                    'onscreenText': onscreen_text,
                    'thumbnail': thumbnail
                })
                video_ocr_results.append({'frame': thumbnail, 'ocr': onscreen_text})
            else:
                for i, (start, frame_path) in enumerate(scene_cuts):
                    end = scene_cuts[i+1][0] if i+1 < len(scene_cuts) else duration
                    scene_transcript = [
                        seg['text'] for seg in transcript
                        if not (seg['end'] <= start or (end is not None and seg['start'] >= end))
                    ]
                    onscreen_text = ocr_image(frame_path) if frame_path else ''
                    video_scenes.append({
                        'start': start,
                        'end': end,
                        'transcript': scene_transcript,
                        'onscreenText': onscreen_text
                    })
                    if frame_path:
                        video_ocr_results.append({'frame': frame_path, 'ocr': onscreen_text})
        except Exception as e:
            print(f"Error processing video {video_file}: {e}")
        videos_output.append({
            'video': video_file,
            'scenes': video_scenes,
            'transcript': video_transcript_segments,
            'ocr': video_ocr_results
        })
        all_ocr_results.extend(video_ocr_results)
        all_transcript_segments.extend(video_transcript_segments)

    used_thumbnails = set(video_thumbnails.values())
    remaining_images = [img for img in image_files if img not in used_thumbnails]
    images = []
    for image_file in remaining_images:
        print(f"\nProcessing image: {image_file}")
        try:
            ocr_text = ocr_image(image_file, reader=EASYOCR_READER)
            images.append({
                'link': result['link'],
                'text': ocr_text,
                'source': image_file
            })
            all_ocr_results.append({'image': image_file, 'ocr': ocr_text})
        except Exception as e:
            print(f"Error processing image {image_file}: {e}")

    videos_output_with_scene_files = []
    for video_entry in videos_output:
        video_path = video_entry['video']
        scenes = video_entry['scenes']
        for idx, scene in enumerate(scenes):
            start = scene['start']
            end = scene['end']
            try:
                scene_base64 = extract_and_downscale_scene(video_path, start, end, target_width=480)
            except Exception as e:
                print(f"Warning: Could not extract/downscale scene {idx+1} from {video_path}: {e}")
                scene_base64 = None
            scene['video_base64'] = scene_base64
        video_entry = {
            'scenes': video_entry['scenes'],
            'link': result['link'].split('?')[0].rstrip('/') + ('?img_index=' + video_path.split('_')[-1].split('.')[0] if '_UTC_' in video_path else '')
        }
        videos_output_with_scene_files.append(video_entry)

    output = {
        'link': result['link'],
        'tags': result['tags'],
        'description': result['description'],
        'source': result['source'],
        'videos': videos_output_with_scene_files,
        'images': images,
        'media_count': {
            'videos': len(video_files),
            'images': len(remaining_images)
        }
    }

    with open(os.path.join(result['temp_dir'], 'result.json'), 'w') as f:
        json.dump(output, f, indent=2)
    with open(os.path.join(result['temp_dir'], 'transcript.json'), 'w') as f:
        json.dump(all_transcript_segments, f, indent=2)
    with open(os.path.join(result['temp_dir'], 'scenes.json'), 'w') as f:
        json.dump(videos_output_with_scene_files, f, indent=2)
    with open(os.path.join(result['temp_dir'], 'ocr.json'), 'w') as f:
        json.dump(all_ocr_results, f, indent=2)

    print(f"\nSaved result to {os.path.join(result['temp_dir'], 'result.json')}")
    print(f"Saved transcript to {os.path.join(result['temp_dir'], 'transcript.json')}")
    print(f"Saved scenes to {os.path.join(result['temp_dir'], 'scenes.json')}")
    print(f"Saved ocr to {os.path.join(result['temp_dir'], 'ocr.json')}")

    return output

def process_and_cleanup(url, threshold=DEFAULT_SCENE_THRESHOLD):
    # Get the initial result with temp_dir
    initial_result = download_media_and_metadata(url)
    temp_dir = initial_result['temp_dir']  # Store temp_dir before processing
    
    # Process the URL
    result = process_url(url, threshold)
    
    # Clean up using the stored temp_dir
    cleanup_temp_files(temp_dir)
    
    return result

def main():
    if len(sys.argv) < 2:
        print('Usage: python media_utils.py <url> [threshold]')
        sys.exit(1)
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SCENE_THRESHOLD
    process_and_cleanup(sys.argv[1], threshold)

if __name__ == '__main__':
    main()
