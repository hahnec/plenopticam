import matplotlib.pyplot as plt
import numpy as np
import os

s_arr = np.load('refo_metrics.npy')
s_list = s_arr.tolist()

# plot
fig, ax1 = plt.subplots()
ax1.set_title(s_list[0][0].split('_')[1])
ax2=ax1.twinx()

ax1.set_ylim(0, 1)
#ax2.set_ylim(0, 1)
ax2.set_ylim(0, 100)

# sharpness
ln3 = ax1.plot(range(len(s_list) // 2), s_arr[:len(s_list) // 2, 1].astype(np.float), c='r', label='Sharpness Lytro')
ln4 = ax1.plot(range(len(s_list) // 2), s_arr[len(s_list) // 2:, 1].astype(np.float), c='b', label='Sharpness Plenopticam')

# contrast
#ln1 = ax2.plot(range(len(s_list) // 2), s_arr[:len(s_list) // 2, 2].astype(np.float), c='k', label='Contrast Lytro')
#ln2 = ax2.plot(range(len(s_list) // 2), s_arr[len(s_list) // 2:, 2].astype(np.float), c='g', label='Contrast Plenopticam')

# BRISQUE
ln1 = ax2.plot(range(len(s_list) // 2), s_arr[:len(s_list) // 2, 3].astype(np.float), c='k', label='BRISQUE Lytro')
ln2 = ax2.plot(range(len(s_list) // 2), s_arr[len(s_list) // 2:, 3].astype(np.float), c='g', label='BRISQUE Plenopticam')

lns = ln1+ln2+ln3+ln4
labs = [l.get_label() for l in lns]
ax1.legend(lns, labs, loc='center')

ax1.set_ylabel('Sharpness $S$')
#ax2.set_ylabel('Contrast $C$')
ax2.set_ylabel('BRISQUE')

plt_fn = 'refocus_metric'
plt.savefig(os.path.join(os.getcwd(), plt_fn + '.png'))
plt.savefig(os.path.join(os.getcwd(), plt_fn + '.eps'))  # , metadata='eps'

plt.show()