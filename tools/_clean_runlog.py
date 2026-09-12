# -*- coding: utf-8 -*-
# Clean RUN_LOG.md: re-encode to UTF-8 only
raw = open('RUN_LOG.md', 'rb').read()
# Try to decode as UTF-8 with replacement, then re-encode
text = raw.decode('utf-8', errors='replace')
# Remove replacement character sequences and orphan control chars
import re
# Remove U+FFFD replacement chars
text = text.replace('\ufffd', '')
# Strip any UTF-16 sequences (zero-byte pairs) that might have leaked in
text = text.replace('\x00', '')
open('RUN_LOG.md', 'w', encoding='utf-8').write(text)
print(f'OK cleaned: {len(text)} chars, {len(text.encode("utf-8"))} bytes')

# Verify
verify = open('RUN_LOG.md', 'rb').read()
verify.decode('utf-8')  # Should not raise
print('UTF-8 verify OK')

# Count lines
lines = text.split('\n')
print(f'lines: {len(lines)}')

# Show last 10 lines
print('last 10 lines:')
for ln in lines[-10:]:
    print('  ', ln[:120])
