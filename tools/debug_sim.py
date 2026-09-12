import numpy as np
import pandas as pd
sim = np.load('data/processed/q3/q3_keyword_sim_matrix.npy')
print('shape:', sim.shape)
print('max:', sim.max(), 'min:', sim.min())
print('mean (off-diag):', sim[sim < 1].mean())
idx = np.where((sim >= 0.999) & (np.arange(909)[:, None] != np.arange(909)[None, :]))
print('# pairs ~1.0:', len(idx[0]))
pairs = []
for i, j in zip(*idx):
    pairs.append((i, j, sim[i,j]))
print('first 3 pairs:', pairs[:3])
prof = pd.read_pickle('data/processed/q3/q3_keyword_profiles.pkl')
for i, j, s in pairs[:3]:
    print('kw' + str(i) + ':', prof.iloc[i]['关键词'], 'kw' + str(j) + ':', prof.iloc[j]['关键词'])
    print('  cost:', prof.iloc[i]['kw_cost'], prof.iloc[j]['kw_cost'])
    print('  clicks:', prof.iloc[i]['kw_clicks'], prof.iloc[j]['kw_clicks'])
