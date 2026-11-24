"""Import first: idle CPU priority, one thread (keeps the user's machine responsive)."""
import os
for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[k] = "1"
try:
    import psutil
    psutil.Process().nice(psutil.IDLE_PRIORITY_CLASS)
except Exception:
    pass
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
