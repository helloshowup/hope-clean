# Simplified Content Generator App

A streamlined desktop UI for ShowupSquared that processes educational content through a simplified workflow.

## Installation

### Prerequisites

- Python 3.7+
- Tkinter (usually bundled with Python)

### Setup

1. Create a virtual environment:

```bash
python -m venv venv
```

1. Activate the virtual environment:

   - Windows:

   ```bash
   venv\Scripts\activate
   ```

   - macOS/Linux:

   ```bash
   source venv/bin/activate
   ```

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

Execute the batch file to start the application:

```bash
run_simplified_app.bat
```

Alternatively, you can run the Python script directly:

```bash
python simplified_app.py
```

### Testing

To run the unit tests locally:

```bash
pytest
```

## Features

- Simplified desktop interface for content generation
- CSV-based content processing
- Support for learner profiles and student handbooks
- Configurable output settings
- Logging and error handling
- Optional template directory setting for custom content templates

### Template Directory

You can choose a folder containing your own markdown templates. In the UI this
is saved as the `template_directory` setting. If omitted, the app loads the
default template from the repository's `templates/` folder.
