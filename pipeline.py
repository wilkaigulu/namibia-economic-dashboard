import subprocess

print("Downloading World Bank data...")

subprocess.run(
    ["python", "src/extract/world_bank.py"]
)

print("Standardizing datasets...")

subprocess.run(
    ["python", "src/transform/standardize.py"]
)

print("Validating datasets...")

subprocess.run(
    ["python", "src/validate/validate_data.py"]
)

print("Building warehouse...")

subprocess.run(
    ["python", "src/load/build_warehouse.py"]
)

print("Pipeline Complete")