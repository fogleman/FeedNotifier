import os
import cPickle as pickle

def load(path):
    tmp_path = '%s.tmp' % path
    bak_path = '%s.bak' % path
    for p in (path, bak_path, tmp_path):
        try:
            with open(p, 'rb') as file:
                return pickle.load(file)
        except Exception:
            pass
    raise Exception('Unable to load: %s' % path)
    
def save(path, data):
    tmp_path = '%s.tmp' % path
    bak_path = '%s.bak' % path
    # Write tmp file
    with open(tmp_path, 'wb') as file:
        pickle.dump(data, file, -1)
    # Copy existing file to bak file
    try:
        os.remove(bak_path)
    except Exception:
        pass
    try:
        os.rename(path, bak_path)
    except Exception:
        pass
    # Rename tmp file to actual file
    os.rename(tmp_path, path)
    # Remove bak file
    try:
        os.remove(bak_path)
    except Exception:
        pass
        