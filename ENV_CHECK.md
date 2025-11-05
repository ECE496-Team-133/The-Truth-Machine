# How to Check Your Python Environment

## Quick Check Commands

### 1. Check which Python you're using:
```bash
which python
python --version
```

### 2. Check where packages are installed:
```bash
python -c "import sys; print(sys.executable)"
python -c "import sys; print(sys.path)"
```

### 3. Check if a package is installed:
```bash
python -m pip show fastapi
# or
python -c "import fastapi; print(fastapi.__file__)"
```

### 4. Install packages in the CURRENT Python:
```bash
# Always use this to install in the Python you're currently using:
python -m pip install package_name

# NOT just:
pip install package_name  # This might install in a different Python!
```

## Common Issues

### Problem: "No module named X" even after installing
**Solution**: You installed in a different Python environment than you're running.

**Fix**:
1. Check which Python you're using: `which python`
2. Install using that specific Python: `python -m pip install package_name`
3. Or use the full path: `/path/to/python -m pip install package_name`

### Problem: Conda vs System Python
If you see paths like:
- `/opt/homebrew/Caskroom/miniforge/base/bin/python` → Conda/miniforge Python
- `/usr/bin/python` or `/usr/local/bin/python` → System Python
- `/Library/Frameworks/Python.framework/...` → Homebrew Python

**Solution**: Always install packages in the Python you're actually using!

## For This Project

You're using: `/opt/homebrew/Caskroom/miniforge/base/bin/python` (Conda base environment)

To install packages:
```bash
python -m pip install -r requirements.txt
```

To verify FastAPI is installed:
```bash
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
```

