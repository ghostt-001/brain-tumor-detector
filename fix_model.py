"""
Run this ONCE to patch final_model.h5 for Keras compatibility.
Place in your project folder and run: python fix_model.py
"""

import h5py
import json
import shutil
import os

MODEL_PATH = "final_model.h5"

if not os.path.exists("final_model_backup.h5"):
    shutil.copy(MODEL_PATH, "final_model_backup.h5")
    print("Backup saved as final_model_backup.h5")
else:
    # Always restore from backup so we patch the original clean file
    shutil.copy("final_model_backup.h5", MODEL_PATH)
    print("Restored from backup, patching fresh copy...")

# Keys not supported in older/newer Keras depending on version
REMOVE_KEYS = {'optional', 'quantization_config', 'registered_name', 'module'}

with h5py.File(MODEL_PATH, 'r+') as f:
    model_config = f.attrs.get('model_config')
    if isinstance(model_config, bytes):
        model_config = model_config.decode('utf-8')

    config = json.loads(model_config)

    def fix_layer(obj):
        if isinstance(obj, dict):
            # Fix batch_shape -> batch_input_shape
            if 'batch_shape' in obj:
                obj['batch_input_shape'] = obj.pop('batch_shape')

            # Remove all unsupported keys
            for key in REMOVE_KEYS:
                obj.pop(key, None)

            # Fix DTypePolicy -> plain string
            if 'dtype' in obj and isinstance(obj['dtype'], dict):
                if obj['dtype'].get('class_name') == 'DTypePolicy':
                    obj['dtype'] = obj['dtype'].get('config', {}).get('name', 'float32')

            # Fix initializers — remove 'module' and 'registered_name' from nested dicts
            for key in list(obj.keys()):
                obj[key] = fix_layer(obj[key])

        elif isinstance(obj, list):
            return [fix_layer(item) for item in obj]

        return obj

    fixed = fix_layer(config)
    f.attrs['model_config'] = json.dumps(fixed).encode('utf-8')

print("Model patched successfully!")
print("Now run: python app.py")
