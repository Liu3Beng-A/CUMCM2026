# -*- coding: utf-8 -*-
p = r'tools\verify_data_consistency_final.py'
content = open(p, 'r', encoding='utf-8').read()
content = content.replace("print('\u2705", "print('[OK]")
content = content.replace("print(f'\u274c", "print(f'[FAIL]")
open(p, 'w', encoding='utf-8').write(content)
print('fixed unicode')
