# generates a linear interpolated fit for a LUT

import numpy as np
s1 = 0           # start point in um
e1 = 100      # end point in um
step1 = 0.010   # step in um
s2 = 0          # start in v
e2 = 10         # end in v

l1 = np.arange(s1, e1+step1, step1)
step2 = (e2-s2)/len(l1)
l2 = np.arange(s2, e2, step2)
l = np.zeros((len(l1), 2))
l[:, 0] = l2[:]
l[:, 1] = l1[:]
np.savetxt('interpolatedLUT.txt', l, header='volt um', delimiter=' ')
