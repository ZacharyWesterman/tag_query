#!/usr/bin/env bash

# Create and activate a virtual environment
deactivate 2>/dev/null
[ -d venv ] || python3 -m venv venv || exit 1
source venv/bin/activate

python3 -m pip install --upgrade twine build

# Build the package
python3 -m build || exit 1

# Upload the package to PyPI
python3 -m twine upload --repository pypi dist/* || exit 1

# Print green success message
echo -e "\033[0;32mPackage built and uploaded successfully.\033[0m"
