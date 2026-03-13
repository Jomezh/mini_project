import joblib
import m2cgen as m2c
import os

# 1. Load the model using joblib (matches your training script)
model_path = 'rf_model_33.pkl'

if not os.path.exists(model_path):
    print(f"Error: {model_path} not found in the current folder!")
else:
    print(f"Loading {model_path}...")
    model = joblib.load(model_path)

    # 2. Convert to Dart
    print("Converting to Dart (this may take a minute for 33 features)...")
    dart_code = m2c.export_to_dart(model)

    # 3. Save the output
    output_file = 'final_rf_model.dart'
    with open(output_file, 'w') as f:
        f.write(dart_code)

    print(f"Done! Created {output_file}")