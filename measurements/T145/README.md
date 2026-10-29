# T145 measurements

`candidates-slow-v1.txt`: the per-module times, slow tests on, of every module that checks page
bounds or the 90 % reserve, from a full local gate at T144's `7bfe7d2e` (32 cores, 8 jobs, all 129
modules in parallel). That run lacked `.cache/cloud.env` (offscreen Qt, dummy SDL), so five modules
failed on the WSLg display; their times are still the times they took, and with the environment
they pass. `LAYOUT_FIRST` takes the non-serial modules at 18 s or less: T110, T141, T134, T113,
395, T119, T121, T114, T107, T111, T105, T120. The longer ones (T115 and up, and T106, T108, T109
at 116 to 874 s) stay in the full batch, as do the SERIAL focus modules T138, T139, T140.

`before-89be1f37-v1.log`: the new gate's test stages (`check_tests`, 8 jobs, the automatic slow
choice off) on T144's unfixed `89be1f37` source, unpacked from `git archive`, with that environment.
The layout stage fails after 40.7 s naming `test_core_team_back_t141` and `test_core_team_t107`, and
the full batch does not start; Windows run 40785633279 reported the same two failures after about
an hour. Two full gates ran on the machine at the same time, so the time is an upper bound.
