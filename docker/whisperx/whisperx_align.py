#!/usr/bin/env python3
"""
Simple wrapper to run whisper + whisperx alignment locally.
If whisperx is available, this script will transcribe and return JSON segments with start/end/text.
If required packages are missing it will exit with code 2 and print a helpful message.

Usage:
  python docker/whisperx/scripts/whisperx_align.py --audio path/to/audio.mp3 --output out.json

Output (stdout): JSON object { "segments": [ {"start": float, "end": float, "text": str}, ... ] }
"""
import sys
import json
import argparse
import os
import shutil

def err(msg):
    print(json.dumps({"error": msg}), file=sys.stderr)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--audio', required=True)
    p.add_argument('--output', required=False)
    p.add_argument('--require-gpu', action='store_true', help='Fail fast if a CUDA GPU is not available')
    args = p.parse_args()

    audio_path = args.audio
    if not os.path.exists(audio_path):
        err(f"audio not found: {audio_path}")
        sys.exit(2)

    # Robust ffmpeg detection:
    # 1) prefer an ffmpeg already on PATH, 2) try imageio_ffmpeg (provides a bundled binary),
    # 3) fallback to a small list of common locations.
    ffmpeg_exe = shutil.which('ffmpeg')
    if not ffmpeg_exe:
        try:
            # imageio-ffmpeg provides a portable ffmpeg binary and exposes its path
            import imageio_ffmpeg as iioff
            ffmpeg_exe = iioff.get_ffmpeg_exe()
        except Exception:
            ffmpeg_exe = None

    if ffmpeg_exe:
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
    else:
        # small set of common locations as a last resort (Windows + Unix)
        common = [
            os.path.expandvars(r"%LOCALAPPDATA%\\Programs\\Gyan\\ffmpeg\\bin"),
            r"C:\\ffmpeg\\bin",
            r"/usr/bin",
            r"/usr/local/bin",
        ]
        for p in common:
            if p and os.path.isdir(p) and shutil.which('ffmpeg', path=p):
                os.environ['PATH'] = p + os.pathsep + os.environ.get('PATH', '')
                ffmpeg_exe = shutil.which('ffmpeg')
                break
    if not shutil.which('ffmpeg'):
        # Not fatal here; whisper/whisperx will raise an error when attempting to load audio.
        print('[whisperx_align] warning: ffmpeg executable not found on PATH; audio loading may fail')

    try:
        import whisper
        import whisperx
    except Exception:
        err("Required python packages not found. Install whisper and whisperx. Example: pip install git+https://github.com/openai/whisper.git git+https://github.com/m-bain/whisperx@main")
        sys.exit(2)

    try:
        model = whisper.load_model('small')
        result = model.transcribe(audio_path)

        audio_load = whisperx.load_audio(audio_path)
        if isinstance(audio_load, (tuple, list)):
            if len(audio_load) >= 2:
                audio = audio_load[0]
                rate = audio_load[1]
            else:
                audio = audio_load[0]
                rate = 16000
        else:
            audio = audio_load
            rate = 16000

        try:
            import torch
            cuda_available = torch.cuda.is_available() and torch.cuda.device_count() > 0
            if cuda_available:
                device = torch.device('cuda:0')
            else:
                device = torch.device('cpu')
        except Exception:
            cuda_available = False
            device = torch.device('cpu')

        # If user requested GPU strictly, fail fast when GPU unavailable
        if args.require_gpu and not cuda_available:
            err('GPU required (--require-gpu) but no CUDA device is available')
            sys.exit(4)

        print(f"[whisperx_align] selected device: {device}")
        try:
            if str(device).startswith('cuda'):
                print(f"[whisperx_align] CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES')}")
                try:
                    import torch
                    print(f"[whisperx_align] torch.cuda.device_count()={torch.cuda.device_count()}")
                    if torch.cuda.device_count()>0:
                        print(f"[whisperx_align] torch.cuda.get_device_name(0)={torch.cuda.get_device_name(0)}")
                except Exception:
                    pass
        except Exception:
            pass

        try:
            model_a, metadata = whisperx.load_align_model(language_code=result.get('language', 'en'), device=device)
        except TypeError:
            try:
                model_a, metadata = whisperx.load_align_model(device, language_code=result.get('language', 'en'))
            except TypeError:
                model_a, metadata = whisperx.load_align_model(language_code=result.get('language', 'en'))

        try:
            try:
                model_a.to(device)
            except Exception:
                pass
        except Exception:
            pass

        # Try multiple align() call signatures to handle whisperx API differences.
        segs = result.get('segments', [])
        aligned = None

        def try_align_call(call_fn):
            try:
                return call_fn()
            except Exception as e:
                # propagate the exception for evaluation by caller
                raise

        align_attempts = [
            # common: (segments, model, metadata, audio, rate, device=...)
            lambda: whisperx.align(segs, model_a, metadata, audio, rate, device=device),
            # variant without rate param
            lambda: whisperx.align(segs, model_a, metadata, audio, device=device),
            # keyword-arg style used by some versions
            lambda: whisperx.align(transcript=segs, model=model_a, align_model_metadata=metadata, audio=audio, device=device),
            # older fallback: (segments, model, metadata, audio, rate)
            lambda: whisperx.align(segs, model_a, metadata, audio, rate),
        ]

        last_exc = None
        for attempt in align_attempts:
            try:
                aligned = attempt()
                break
            except Exception as e:
                last_exc = e
                # If it's a CUDA device error, break (we won't auto-fallback to CPU when GPU was expected)
                msg = str(e).lower()
                if 'invalid device ordinal' in msg or 'cannot access accelerator' in msg or 'cuda error' in msg:
                    last_exc = e
                    break
                # otherwise continue to next signature
                continue
        # If we failed due to CUDA errors and user required GPU, or any CUDA error occurred,
        # surface the error instead of silently falling back to CPU.
        if aligned is None:
            if last_exc is not None:
                msg = str(last_exc).lower()
                if 'invalid device ordinal' in msg or 'cannot access accelerator' in msg or 'cuda error' in msg:
                    err('CUDA error during alignment: ' + str(last_exc))
                    sys.exit(5)
                # otherwise re-raise the last exception for visibility
                raise last_exc
            else:
                raise RuntimeError('whisperx.align failed with unknown error')

        segments_out = []
        for seg in aligned.get('segments', []):
            seg_start = float(seg.get('start', 0.0))
            seg_end = float(seg.get('end', 0.0))
            text = seg.get('text', '').strip()
            if text:
                segments_out.append({"start": seg_start, "end": seg_end, "text": text})

        out = {"segments": segments_out}
        if args.output:
            with open(args.output, 'w', encoding='utf8') as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        err(f"whisper/whisperx error: {str(e)}\nTRACEBACK:\n{tb}")
        sys.exit(3)

if __name__ == '__main__':
    main()
