import json, re, subprocess, sys

video, wav, out = sys.argv[1:4]
target = 'I=-14:TP=-1.0:LRA=11'
p = subprocess.run(['ffmpeg', '-hide_banner', '-i', wav, '-af', f'loudnorm={target}:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True, check=True)
m = json.loads(re.findall(r'\{[^{}]+\}', p.stderr)[-1])
af = (f"loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                '-af', af, '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2', '-shortest', '-movflags', '+faststart', out], check=True)
r = subprocess.run(['ffmpeg', '-nostats', '-i', out, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True)
summary = r.stderr[r.stderr.rfind('Summary'):]
i = re.search(r'I:\s+(-?[\d.]+) LUFS', summary).group(1)
peak = re.search(r'Peak:\s+(-?[\d.]+) dBFS', summary).group(1)
print(f'loudness {i} LUFS, true peak {peak} dBFS')
