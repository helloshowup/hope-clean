"""Simplified Desktop UI for ShowupSquared Content Generator."""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import logging
import datetime
import json
import pandas as pd
import queue

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
REPO_ROOT = os.path.dirname(PARENT_DIR)

_PATHS = [
    CURRENT_DIR,
    PARENT_DIR,
    REPO_ROOT,
    os.path.join(REPO_ROOT, "showup-core"),
    os.path.join(REPO_ROOT, "showup-editor-ui"),
]

for _p in _PATHS:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Handle the ``showup_tools`` vs ``showup-tools`` directory name difference
import importlib.util


class ShowupToolsPathFinder:
    """Resolve imports for the ``showup_tools`` namespace."""

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if fullname == "showup_tools" or fullname.startswith("showup_tools."):
            parts = fullname.split(".")
            if len(parts) > 1:
                subpath = os.path.join(*parts[1:])
                filepath = os.path.join(REPO_ROOT, "showup-tools", subpath)
            else:
                filepath = os.path.join(REPO_ROOT, "showup-tools")

            if os.path.isdir(filepath):
                filename = os.path.join(filepath, "__init__.py")
                submodule_locations = [filepath]
            else:
                filename = filepath + ".py"
                submodule_locations = None

            if os.path.exists(filename):
                return importlib.util.spec_from_file_location(
                    fullname,
                    filename,
                    submodule_search_locations=submodule_locations,
                )
        return None


sys.meta_path.insert(0, ShowupToolsPathFinder)

from showup_core.core.log_utils import get_log_path
if os.name == 'nt':
    if not hasattr(sys.stdout, 'original_stream'):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        else:
            try:
                sys.stdout = open(sys.stdout.fileno(), mode='w', encoding=
                    'utf-8', buffering=1)
                sys.stderr = open(sys.stderr.fileno(), mode='w', encoding=
                    'utf-8', buffering=1)
            except Exception as e:
                print(f'Warning: Could not set UTF-8 encoding: {e}')
if not os.path.exists('logs'):
    try:
        os.makedirs('logs')
        print('Created logs directory')
    except Exception as e:
        print(f'ERROR: Failed to create logs directory: {str(e)}')
root_logger = logging.getLogger()
root_logger.handlers.clear()
logging.basicConfig(level=logging.INFO, format=
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(get_log_path('simplified_app'), encoding='utf-8'),
    logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('simplified_app')
required_directories = ['logs', 'templates', 'output', 'cache', 'archive',
    'data', 'test_data']
for directory in required_directories:
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f'Created required directory: {directory}')
    except Exception as e:
        error_msg = (
            f"Failed to create required directory '{directory}': {str(e)}")
        logging.critical(error_msg)
        print(f'CRITICAL ERROR: {error_msg}')
        sys.exit(1)
# Ensure all necessary modules are in the Python path
# This is required after code reorganization
try:
    # Add path to simplified_workflow module explicitly
    simplified_workflow_path = os.path.join(REPO_ROOT, 'simplified_workflow')
    if simplified_workflow_path not in sys.path:
        sys.path.insert(0, simplified_workflow_path)

    from simplified_workflow import run_workflow
    from simplified_workflow.csv_processor import read_csv
    logging.info('Successfully imported simplified_workflow')
except ImportError as e:
    error_msg = f'Could not import simplified_workflow: {str(e)}'
    logging.critical(error_msg)
    print(f'CRITICAL ERROR: {error_msg}')
    print(
        'The application cannot start due to missing simplified_workflow module.'
        )
    sys.exit(1)


class SimplifiedContentGeneratorApp:
    """Simplified desktop application for ShowupSquared Content Generator"""

    def __init__(self, root, settings_path='user_settings.json',
        instance_id='default', output_dir='output'):
        """
        Initialize the application with root window
        
        Args:
            root: Tkinter root window
            settings_path: Path to settings file
            instance_id: Unique identifier for this application instance
            output_dir: Custom output directory for generated content
        """
        self.root = root
        self.root.title(
            f'ShowupSquared Simplified Content Generator - Instance: {instance_id}'
            )
        self.root.geometry('800x800')
        self.root.minsize(800, 800)
        self.bg_color = '#fdf6d3'
        self.root.configure(bg=self.bg_color)
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.log_update_interval = 100
        self.instance_id = instance_id
        self.csv_file_path = None
        self.learner_profile_path = None
        self.handbook_path = None
        self.settings_path = settings_path
        self.output_dir_var = tk.StringVar(value=output_dir)
        self.course_name = tk.StringVar(value='Photography Fundamentals')
        self.learner_profile = ''
        self.ui_settings = {}
        self.template_settings = {}
        self.template_dir_var = tk.StringVar()
        self.word_count = tk.StringVar(value='500')
        self.csv_data = []
        self.selected_modules = []
        self.available_modules = []
        self.token_limit = tk.StringVar(value='4000')
        self.model_var = tk.StringVar()
        self.initial_model_var = tk.StringVar()
        self.model_display_to_id = {}
        self.model_id_to_display = {}
        self.generation_running = False
        self.results = {}
        self.log_handler = None
        self.stdout_redirector = None
        self.stderr_redirector = None
        self.settings = self._load_settings()
        self._create_widgets()
        self._setup_logging()

    def _create_styles(self):
        """Create ttk styles for consistent background color"""
        style = ttk.Style()
        style.configure('BG.TFrame', background=self.bg_color)
        style.configure('BG.TLabel', background=self.bg_color)
        style.configure('BG.TLabelframe', background=self.bg_color)
        style.configure('BG.TLabelframe.Label', background=self.bg_color)
        border_color = '#e6dfc4'
        style.configure('BG.TLabelframe', bordercolor=border_color)

    def _create_widgets(self):
        """Create all UI widgets"""
        canvas_frame = ttk.Frame(self.root, style='BG.TFrame')
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self._create_styles()
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas = tk.Canvas(canvas_frame, bg=self.bg_color)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.config(command=canvas.yview)
        canvas.config(yscrollcommand=v_scrollbar.set)
        main_frame = ttk.Frame(canvas, padding=10, style='BG.TFrame')
        canvas_window = canvas.create_window((0, 0), window=main_frame,
            anchor=tk.NW)

        def configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width - 5)
            canvas.config(scrollregion=canvas.bbox('all'))
        canvas.bind('<Configure>', configure_canvas)

        def on_frame_configure(event):
            canvas.config(scrollregion=canvas.bbox('all'))
        main_frame.bind('<Configure>', on_frame_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        title_label = ttk.Label(main_frame, text=
            'ShowupSquared Simplified Content Generator', font=('Arial', 16,
            'bold'), style='BG.TLabel')
        title_label.pack(pady=10)
        description_label = ttk.Label(main_frame, text=
            'This application uses a simplified workflow that processes one content piece at a time through all steps.'
            , font=('Arial', 10), style='BG.TLabel')
        description_label.pack(pady=(0, 10))
        upload_frame = ttk.LabelFrame(main_frame, text='File Upload', style
            ='BG.TLabelframe')
        upload_frame.pack(fill=tk.X, pady=10, padx=5)
        csv_frame = ttk.Frame(upload_frame, style='BG.TFrame')
        csv_frame.pack(fill=tk.X, pady=5)
        ttk.Label(csv_frame, text='CSV File:', style='BG.TLabel').pack(side
            =tk.LEFT, padx=5)
        self.csv_path_var = tk.StringVar()
        ttk.Entry(csv_frame, textvariable=self.csv_path_var, width=50).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(csv_frame, text='Browse...', command=self._browse_csv).pack(
            side=tk.LEFT, padx=5)
        profile_frame = ttk.Frame(upload_frame, style='BG.TFrame')
        profile_frame.pack(fill=tk.X, pady=5)
        ttk.Label(profile_frame, text='Learner Profile:', style='BG.TLabel'
            ).pack(side=tk.LEFT, padx=5)
        self.profile_path_var = tk.StringVar()
        ttk.Entry(profile_frame, textvariable=self.profile_path_var, width=50
            ).pack(side=tk.LEFT, padx=5)
        ttk.Button(profile_frame, text='Browse...', command=self.
            _browse_profile).pack(side=tk.LEFT, padx=5)
        settings_frame = ttk.Frame(upload_frame, style='BG.TFrame')
        settings_frame.pack(fill=tk.X, pady=5)
        ttk.Label(settings_frame, text='Settings File:', style='BG.TLabel'
            ).pack(side=tk.LEFT, padx=5)
        self.settings_path_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.settings_path_var, width=50
            ).pack(side=tk.LEFT, padx=5)
        ttk.Button(settings_frame, text='Browse...', command=self.
            _browse_settings).pack(side=tk.LEFT, padx=5)
        course_frame = ttk.LabelFrame(main_frame, text='Course Information',
            style='BG.TLabelframe')
        course_frame.pack(fill=tk.X, pady=10, padx=5)
        course_name_frame = ttk.Frame(course_frame, style='BG.TFrame')
        course_name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(course_name_frame, text='Course Name:', style='BG.TLabel'
            ).pack(side=tk.LEFT, padx=5)
        ttk.Entry(course_name_frame, textvariable=self.course_name, width=50
            ).pack(side=tk.LEFT, padx=5)
        module_frame = ttk.LabelFrame(main_frame, text='Module Selection',
            style='BG.TLabelframe')
        module_frame.pack(fill=tk.X, pady=10, padx=5)
        ttk.Label(module_frame, text=
            'Select modules to process (leave empty to process all modules):',
            style='BG.TLabel').pack(anchor=tk.W, padx=5, pady=(5, 0))
        module_list_frame = ttk.Frame(module_frame, style='BG.TFrame')
        module_list_frame.pack(fill=tk.X, pady=5, padx=5)
        scrollbar = ttk.Scrollbar(module_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.module_listbox = tk.Listbox(module_list_frame, selectmode=tk.
            MULTIPLE, height=5, width=70)
        self.module_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.module_listbox.yview)
        self.module_listbox.config(yscrollcommand=scrollbar.set)
        module_button_frame = ttk.Frame(module_frame, style='BG.TFrame')
        module_button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(module_button_frame, text='Select All', command=self.
            _select_all_modules).pack(side=tk.LEFT, padx=5)
        ttk.Button(module_button_frame, text='Clear Selection', command=
            self._clear_module_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(module_button_frame, text='Refresh Modules', command=
            self._refresh_modules).pack(side=tk.LEFT, padx=5)
        template_settings_frame = ttk.LabelFrame(main_frame, text=
            'Template Settings', style='BG.TLabelframe')
        template_settings_frame.pack(fill=tk.X, pady=10, padx=5)
        word_count_frame = ttk.Frame(template_settings_frame, style='BG.TFrame'
            )
        word_count_frame.pack(fill=tk.X, pady=5)
        ttk.Label(word_count_frame, text='Default Word Count:', style='BG.TLabel'
            ).pack(side=tk.LEFT, padx=5)
        ttk.Entry(word_count_frame, textvariable=self.word_count, width=10
            ).pack(side=tk.LEFT, padx=5)
        ttk.Label(word_count_frame, text=
            '(Default target word count, can be overridden by Target_Word_Count in CSV)', style='BG.TLabel'
            ).pack(side=tk.LEFT, padx=5)
        token_limit_frame = ttk.Frame(template_settings_frame, style=
            'BG.TFrame')
        token_limit_frame.pack(fill=tk.X, pady=5)
        ttk.Label(token_limit_frame, text='Token Limit:', style='BG.TLabel'
            ).pack(side=tk.LEFT, padx=5)
        ttk.Entry(token_limit_frame, textvariable=self.token_limit, width=10
            ).pack(side=tk.LEFT, padx=5)
        ttk.Label(token_limit_frame, text=
            '(Maximum tokens for API request)', style='BG.TLabel').pack(side
            =tk.LEFT, padx=5)
            
        # Add template directory option
        template_dir_frame = ttk.Frame(template_settings_frame, style='BG.TFrame')
        template_dir_frame.pack(fill=tk.X, pady=5)
        ttk.Label(template_dir_frame, text='Template Directory:', style='BG.TLabel'
            ).pack(side=tk.LEFT, padx=5)
        ttk.Entry(template_dir_frame, textvariable=self.template_dir_var, width=50
            ).pack(side=tk.LEFT, padx=5)
        ttk.Button(template_dir_frame, text='Browse...', command=self._browse_template_dir
            ).pack(side=tk.LEFT, padx=5)
        ttk.Label(template_dir_frame, text=
            '(Directory containing content templates)', style='BG.TLabel').pack(side
            =tk.LEFT, padx=5)
        initial_model_frame = ttk.Frame(template_settings_frame, style=
            'BG.TFrame')
        initial_model_frame.pack(fill=tk.X, pady=5)
        ttk.Label(initial_model_frame, text='Initial Generation Model:',
            style='BG.TLabel').pack(side=tk.LEFT, padx=5)
        try:
            from showup_core.model_config import get_available_models, DEFAULT_MODEL
            models = get_available_models()
            model_display_names = [model['display_name'] for model in models]
            model_ids = [model['id'] for model in models]
            self.model_display_to_id = {model['display_name']: model['id'] for
                model in models}
            self.model_id_to_display = {model['id']: model['display_name'] for
                model in models}
            forced_model_id = 'claude-3-7-sonnet-20250219'
            default_display_name = self.model_id_to_display.get(
                forced_model_id, 'Claude 3.7 Sonnet'
            )
            self.model_var.set(default_display_name)
            # ensure settings reflect the forced model
            self.settings['selected_model'] = forced_model_id
            self._log(
                'Processing model forced to Claude 3.7 Sonnet during '
                'initialization'
            )
            default_initial_model = self.settings.get(
                'initial_generation_model', 'claude-3-haiku-20240307')
            default_initial_display_name = self.model_id_to_display.get(
                default_initial_model, 'Claude 3 Haiku')
            self.initial_model_var.set(default_initial_display_name)
        except Exception as e:
            self._log(f'Error loading model config: {str(e)}', level='ERROR')
            model_display_names = ['Claude 3.7 Sonnet', 'Claude 3.5 Sonnet',
                'Claude 3 Haiku', 'Claude 3 Opus']
            self.model_display_to_id = {'Claude 3.7 Sonnet':
                'claude-3-7-sonnet-20250219', 'Claude 3.5 Sonnet':
                'claude-3-5-sonnet-20240620', 'Claude 3 Haiku':
                'claude-3-haiku-20240307', 'Claude 3 Opus':
                'claude-3-opus-20240229'}
            self.model_id_to_display = {v: k for k, v in self.
                model_display_to_id.items()}
            forced_model_id = 'claude-3-7-sonnet-20250219'
            default_display_name = self.model_id_to_display.get(
                forced_model_id, 'Claude 3.7 Sonnet'
            )
            self.model_var.set(default_display_name)
            self.settings['selected_model'] = forced_model_id
            self._log(
                'Processing model forced to Claude 3.7 Sonnet during '
                'initialization (fallback)'
            )
            default_initial_model = self.settings.get(
                'initial_generation_model', 'claude-3-haiku-20240307')
            default_initial_display_name = self.model_id_to_display.get(
                default_initial_model, 'Claude 3 Haiku')
            self.initial_model_var.set(default_initial_display_name)
        self.initial_model_dropdown = ttk.Combobox(initial_model_frame,
            textvariable=self.initial_model_var, values=model_display_names,
            width=20, state='readonly')
        self.initial_model_dropdown.pack(side=tk.LEFT, padx=5)
        ttk.Label(initial_model_frame, text=
            '(Model used for initial 3 versions generation)', style='BG.TLabel'
            ).pack(side=tk.LEFT, padx=5)
        self.initial_model_dropdown.bind('<<ComboboxSelected>>', self.
            _on_initial_model_changed)
        model_selection_frame = ttk.Frame(template_settings_frame, style=
            'BG.TFrame')
        model_selection_frame.pack(fill=tk.X, pady=5)
        ttk.Label(model_selection_frame, text='Processing Steps Model:',
            style='BG.TLabel').pack(side=tk.LEFT, padx=5)
        self.model_dropdown = ttk.Combobox(model_selection_frame,
            textvariable=self.model_var, values=model_display_names, width=
            20, state='readonly')
        self.model_dropdown.pack(side=tk.LEFT, padx=5)
        ttk.Label(model_selection_frame, text=
            '(Model used for comparison, review, and finalization)', style=
            'BG.TLabel').pack(side=tk.LEFT, padx=5)
        self.model_dropdown.bind('<<ComboboxSelected>>', self._on_model_changed
            )
        self.model_dropdown.bind('<<ComboboxSelected>>', self._on_model_changed
            )
        self._log(
            'Processing steps will always use Claude 3.7 Sonnet regardless of '
            'UI selection'
        )
        template_type_frame = ttk.Frame(template_settings_frame, style=
            'BG.TFrame')
        template_type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(template_type_frame, text='Template Settings:', style=
            'BG.TLabel').pack(anchor=tk.W, padx=5)
        ttk.Label(template_type_frame, text=
            'Each template type can have different character and token limits.'
            , style='BG.TLabel').pack(anchor=tk.W, padx=5)
        handbook_frame = ttk.LabelFrame(main_frame, text=
            'Student Handbook Integration', style='BG.TLabelframe')
        handbook_frame.pack(fill=tk.X, pady=10, padx=5)
        self.use_handbook_var = tk.BooleanVar(value=False)
        handbook_checkbox_frame = ttk.Frame(handbook_frame, style='BG.TFrame')
        handbook_checkbox_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(handbook_checkbox_frame, text=
            'Pull relevant information from student handbook before generation'
            , variable=self.use_handbook_var).pack(side=tk.LEFT, padx=5)
        handbook_file_frame = ttk.Frame(handbook_frame, style='BG.TFrame')
        handbook_file_frame.pack(fill=tk.X, pady=5)
        ttk.Label(handbook_file_frame, text='Student Handbook File:', style
            ='BG.TLabel').pack(side=tk.LEFT, padx=5)
        self.handbook_path_var = tk.StringVar()
        output_dir_frame = ttk.LabelFrame(main_frame, text=
            'Output Settings', style='BG.TLabelframe')
        output_dir_frame.pack(fill=tk.X, pady=10, padx=5)
        output_dir_select_frame = ttk.Frame(output_dir_frame, style='BG.TFrame'
            )
        output_dir_select_frame.pack(fill=tk.X, pady=5)
        ttk.Label(output_dir_select_frame, text='Output Directory:', style=
            'BG.TLabel').pack(side=tk.LEFT, padx=5)
        self.output_dir_var = tk.StringVar(value='output')
        ttk.Entry(output_dir_select_frame, textvariable=self.output_dir_var,
            width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_dir_select_frame, text='Browse...', command=self.
            _browse_output_dir).pack(side=tk.LEFT, padx=5)
        ttk.Entry(handbook_file_frame, textvariable=self.handbook_path_var,
            width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(handbook_file_frame, text='Browse...', command=self.
            _browse_handbook).pack(side=tk.LEFT, padx=5)
        ttk.Label(handbook_frame, text=
            'This feature extracts relevant information from the student handbook based on the content outline'
            , style='BG.TLabel').pack(anchor=tk.W, padx=5, pady=(0, 5))
        ttk.Label(handbook_frame, text=
            'and includes it in the content generation process.', style=
            'BG.TLabel').pack(anchor=tk.W, padx=5, pady=(0, 5))
        output_dir_frame = ttk.LabelFrame(main_frame, text=
            'Output Directory', style='BG.TLabelframe')
        output_dir_frame.pack(fill=tk.X, pady=10, padx=5)
        dir_selection_frame = ttk.Frame(output_dir_frame, style='BG.TFrame')
        dir_selection_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dir_selection_frame, text='Save Generated Content To:',
            style='BG.TLabel').pack(side=tk.LEFT, padx=5)
        ttk.Entry(dir_selection_frame, textvariable=self.output_dir_var,
            width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(dir_selection_frame, text='Browse...', command=self.
            _browse_output_dir).pack(side=tk.LEFT, padx=5)
        ttk.Label(output_dir_frame, text=
            'The generated content will be saved to this directory. Subdirectories will be created automatically.'
            , style='BG.TLabel').pack(anchor=tk.W, padx=5, pady=(0, 5))
        profile_preview_frame = ttk.LabelFrame(main_frame, text=
            'Learner Profile Preview', style='BG.TLabelframe')
        profile_preview_frame.pack(fill=tk.X, pady=10, padx=5)
        self.profile_preview = scrolledtext.ScrolledText(profile_preview_frame,
            height=5)
        self.profile_preview.pack(fill=tk.X, pady=5, padx=5)
        action_frame = ttk.Frame(main_frame, style='BG.TFrame')
        action_frame.pack(fill=tk.X, pady=10, padx=5)
        self.generate_button = ttk.Button(action_frame, text=
            'Generate Content', command=self._generate_content)
        self.generate_button.pack(pady=10)
        progress_frame = ttk.LabelFrame(main_frame, text='Progress', style=
            'BG.TLabelframe')
        progress_frame.pack(fill=tk.X, pady=10, padx=5)
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.
            HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5, padx=5)
        self.status_label = ttk.Label(progress_frame, text='Ready', style=
            'BG.TLabel')
        self.status_label.pack(pady=5)
        self.status_label.pack(pady=5)
        results_frame = ttk.LabelFrame(main_frame, text='Results', style=
            'BG.TLabelframe')
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        self.results_text = scrolledtext.ScrolledText(results_frame, height=10)
        self.results_text.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        open_output_frame = ttk.Frame(main_frame, style='BG.TFrame')
        open_output_frame.pack(fill=tk.X, pady=5, padx=5)
        self.open_output_button = ttk.Button(open_output_frame, text=
            'Open Output Directory', command=self._open_output_directory)
        self.open_output_button.pack(side=tk.LEFT, padx=5)
        self.open_output_button.config(state=tk.DISABLED)
        log_frame = ttk.LabelFrame(main_frame, text='Log Output', style=
            'BG.TLabelframe')
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10,
            wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        self.log_text.config(state=tk.DISABLED)

    def _browse_csv(self):
        """Browse for CSV file"""
        self._log(f'Opening CSV file dialog in directory: {os.getcwd()}',
            level='DEBUG')
        self._log('Looking for CSV files with pattern: *.csv', level='DEBUG')
        csv_dir = os.path.join('data', 'input', 'csv')
        if os.path.exists(csv_dir):
            csv_files = [f for f in os.listdir(csv_dir) if f.lower().
                endswith('.csv')]
            self._log(f'Available CSV files in {csv_dir}: {csv_files}',
                level='DEBUG')
        filename = filedialog.askopenfilename(title='Select CSV File',
            filetypes=[('CSV files', '*.csv *.CSV'), ('All files', '*.*')],
            initialdir=
            'C:\\Users\\User\\Desktop\\ShowupSquaredV4\\data\\input\\csv')
        self._log(f'File dialog result: {filename}', level='DEBUG')
        if filename:
            self.csv_file_path = filename
            self.csv_path_var.set(filename)
            self._log(f'Selected CSV file: {filename}')
            self._process_csv()
        else:
            self._log('No CSV file selected or dialog cancelled', level='DEBUG'
                )

    def _browse_profile(self):
        """Browse for learner profile file"""
        self._log(f'Opening profile file dialog in directory: {os.getcwd()}',
            level='DEBUG')
        self._log('Looking for profile files with patterns: *.md, *.txt',
            level='DEBUG')
        profile_dir = os.path.join('data', 'input', 'csv')
        if os.path.exists(profile_dir):
            profile_files = [f for f in os.listdir(profile_dir) if f.lower(
                ).endswith('.md') or f.lower().endswith('.txt')]
            self._log(
                f'Available profile files in {profile_dir}: {profile_files}',
                level='DEBUG')
        filename = filedialog.askopenfilename(title=
            'Select Learner Profile', filetypes=[('Markdown files',
            '*.md *.MD'), ('Text files', '*.txt *.TXT'), ('All files',
            '*.*')], initialdir=
            'C:\\Users\\User\\Desktop\\ShowupSquaredV4\\data\\input\\learner_profiles'
            )
        self._log(f'Profile file dialog result: {filename}', level='DEBUG')
        if filename:
            self.learner_profile_path = filename
            self.profile_path_var.set(filename)
            self._log(f'Selected profile file: {filename}')
            self._process_profile()
        else:
            self._log('No profile file selected or dialog cancelled', level
                ='DEBUG')

    def _browse_handbook(self):
        """Browse for student handbook file"""
        filename = filedialog.askopenfilename(title=
            'Select Student Handbook File', filetypes=[('Text Files',
            '*.txt'), ('PDF Files', '*.pdf'), ('Markdown Files', '*.md'), (
            'All Files', '*.*')])
        if filename:
            self.handbook_path_var.set(filename)
            self._log(f'Selected student handbook file: {filename}')
            if not self.use_handbook_var.get():
                self.use_handbook_var.set(True)

    def _browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title='Select Output Directory')
        if directory:
            self.output_dir_var.set(directory)
            self._log(f'Selected output directory: {directory}')
            
    def _browse_template_dir(self):
        """Browse for template directory"""
        directory = filedialog.askdirectory(title='Select Template Directory')
        if directory:
            self.template_dir_var.set(directory)
            self._log(f'Selected template directory: {directory}')

    def _ensure_output_dirs(self, base_output_dir: str) ->None:
        """Ensure all necessary output directories exist
        
        Args:
            base_output_dir: The base output directory path
        """
        os.makedirs(base_output_dir, exist_ok=True)
        subdirs = ['generation_results', 'comparison_results',
            'review_results', 'final_content']
        for subdir in subdirs:
            full_path = os.path.join(base_output_dir, subdir)
            os.makedirs(full_path, exist_ok=True)
            self._log(f'Ensured directory exists: {full_path}')

    def _browse_settings(self):
        """Browse for settings file"""
        filename = filedialog.askopenfilename(title='Select Settings File',
            filetypes=[('JSON files', '*.json'), ('All files', '*.*')])
        if filename:
            self.settings_path = filename
            self.settings_path_var.set(filename)
            self._process_settings()

    def _process_csv(self):
        """Process selected CSV file and extract modules"""
        if not self.csv_file_path:
            self._log('No CSV file selected', level='WARNING')
            return
        try:
            self._log(f'Processing CSV file: {self.csv_file_path}')
            self.csv_data = read_csv(self.csv_file_path)
            if not self.csv_data:
                error_msg = 'Failed to load data from CSV'
                self._log(error_msg, level='ERROR')
                messagebox.showerror('CSV Error',
                    'Failed to load data from CSV. Please check the file format.'
                    )
                return
            self._extract_modules()
            self._log(f'Loaded {len(self.csv_data)} rows from CSV')
        except Exception as e:
            error_msg = f'Error processing CSV file: {str(e)}'
            self._log(error_msg, level='ERROR')
            messagebox.showerror('CSV Error', error_msg)

    def _extract_modules(self):
        """Extract unique modules from CSV data"""
        if not self.csv_data:
            return
        modules = set()
        for row in self.csv_data:
            module = row.get('Module', '')
            if module:
                modules.add(module)
        self.available_modules = sorted(list(modules))
        self.module_listbox.delete(0, tk.END)
        for module in self.available_modules:
            self.module_listbox.insert(tk.END, module)
        self._log(f'Found {len(self.available_modules)} modules in CSV')

    def _select_all_modules(self):
        """Select all modules in the listbox"""
        self.module_listbox.select_set(0, tk.END)

    def _clear_module_selection(self):
        """Clear module selection"""
        self.module_listbox.selection_clear(0, tk.END)

    def _refresh_modules(self):
        """Refresh module list from CSV"""
        if self.csv_file_path:
            self._process_csv()
        else:
            messagebox.showinfo('No CSV', 'Please select a CSV file first.')

    def _get_selected_modules(self):
        """Get list of selected modules"""
        selected_indices = self.module_listbox.curselection()
        selected_modules = [self.module_listbox.get(i) for i in
            selected_indices]
        return selected_modules

    def _process_profile(self):
        """Process selected learner profile file"""
        if not self.learner_profile_path:
            self._log('No learner profile file selected', level='WARNING')
            return
        try:
            self._log(
                f'Processing learner profile file: {self.learner_profile_path}'
                )
            with open(self.learner_profile_path, 'r', encoding='utf-8') as f:
                self.learner_profile = f.read().strip()
            self.profile_preview.delete(1.0, tk.END)
            self.profile_preview.insert(tk.END, self.learner_profile)
            self._log(
                f'Loaded learner profile ({len(self.learner_profile)} characters)'
                )
        except Exception as e:
            error_msg = f'Error processing learner profile file: {str(e)}'
            self._log(error_msg, level='ERROR')
            messagebox.showerror('Profile Error', error_msg)

    def _load_settings(self):
        """Load settings from settings file"""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            else:
                settings = {
                    'selected_model': 'claude-3-7-sonnet-20250219',
                    'initial_generation_model': 'claude-3-haiku-20240307',
                    'generation_settings': {
                        'max_tokens': 4000,
                        'temperature': 0.5,
                        'word_count': 500,
                    },
                }
                with open(self.settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2)
            # Force the processing model to Claude 3.7 Sonnet
            settings['selected_model'] = 'claude-3-7-sonnet-20250219'
            # Keep 'model' in sync for downstream modules
            settings['model'] = settings['selected_model']
            return settings
        except Exception as e:
            logger.error(f'Error loading settings: {str(e)}')
            return {}

    def _save_settings(self):
        """Save settings to settings file"""
        try:
            # Always persist the processing model as Claude 3.7 Sonnet
            self.settings['selected_model'] = 'claude-3-7-sonnet-20250219'
            self.settings['model'] = self.settings['selected_model']
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            logger.info(f'Settings saved successfully to {self.settings_path}')
        except Exception as e:
            logger.error(f'Error saving settings: {str(e)}')

    def _on_model_changed(self, event):
        """Handle model selection change."""
        forced_display = self.model_id_to_display.get(
            'claude-3-7-sonnet-20250219', 'Claude 3.7 Sonnet'
        )
        self.model_var.set(forced_display)
        self.settings['selected_model'] = 'claude-3-7-sonnet-20250219'
        self.settings['model'] = self.settings['selected_model']
        self._save_settings()
        self._log(
            f'Model selection overridden to {forced_display} '
            f'(claude-3-7-sonnet-20250219)'
        )
        logging.info(
            f'Model override applied: {forced_display} '
            f'(claude-3-7-sonnet-20250219)'
        )

    def _on_initial_model_changed(self, event):
        """Handle initial generation model selection change."""
        selected_display_name = self.initial_model_var.get()
        selected_model_id = self.model_display_to_id.get(selected_display_name)
        if selected_model_id:
            self.settings['initial_generation_model'] = selected_model_id
            self._save_settings()
            self._log(
                f'Changed initial generation model to {selected_display_name} ({selected_model_id})'
                )
            logging.info(
                f'User changed initial generation model to {selected_display_name} ({selected_model_id})'
                )

    def _process_settings(self):
        """Process selected settings file"""
        if not self.settings_path:
            self._log('No settings file selected', level='WARNING')
            return
        try:
            self._log(f'Processing settings file: {self.settings_path}')
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                self.ui_settings = json.load(f)
            if 'generation_settings' in self.ui_settings:
                gen_settings = self.ui_settings['generation_settings']
                if 'character_limit' in gen_settings:
                    self.word_count.set(str(gen_settings['character_limit']))
                    self._log(
                        f"Updated word count to {gen_settings['character_limit']} (from character_limit setting)"
                        )
                if 'word_count' in gen_settings:
                    self.word_count.set(str(gen_settings['word_count']))
                    self._log(
                        f"Updated word count to {gen_settings['word_count']}")
                if 'max_tokens' in gen_settings:
                    self.token_limit.set(str(gen_settings['max_tokens']))
                    self._log(
                        f"Updated token limit to {gen_settings['max_tokens']}")
                if 'template_settings' in self.ui_settings:
                    self.template_settings = self.ui_settings[
                        'template_settings']
                    self._log(
                        f'Loaded template-specific settings for {len(self.template_settings)} templates'
                        )
            # Ensure the processing model is always Claude 3.7 Sonnet
            self.ui_settings['selected_model'] = 'claude-3-7-sonnet-20250219'
            self.ui_settings['model'] = self.ui_settings['selected_model']
            self._log(
                'Selected model from settings overridden to Claude 3.7 Sonnet'
            )
            self._log(
                f'Loaded settings: {json.dumps(self.ui_settings, indent=2)}')
        except Exception as e:
            error_msg = f'Error processing settings file: {str(e)}'
            self._log(error_msg, level='ERROR')
            messagebox.showerror('Settings Error', error_msg)

    def _generate_content(self):
        """Start content generation process"""
        if self.generation_running:
            self._log('Generation already in progress', level='WARNING')
            return
        selected_modules = self._get_selected_modules()
        if not self.csv_file_path:
            messagebox.showwarning('Missing Input', 'Please select a CSV file')
            return
        if not self.learner_profile:
            messagebox.showwarning('Missing Input',
                'Please select a learner profile file')
            return
        course_name = self.course_name.get()
        if not course_name:
            messagebox.showwarning('Missing Input',
                'Please enter a course name')
            return
        selected_model_display = self.model_var.get()
        selected_model = self.model_display_to_id.get(selected_model_display,
            '')
        if selected_model != 'claude-3-7-sonnet-20250219':
            forced_display = self.model_id_to_display.get(
                'claude-3-7-sonnet-20250219', 'Claude 3.7 Sonnet'
            )
            self._log(
                'Selected model overridden to Claude 3.7 Sonnet',
                level='WARNING',
            )
            self.model_var.set(forced_display)
            selected_model = 'claude-3-7-sonnet-20250219'
        self.settings['selected_model'] = selected_model
        initial_model_display = self.initial_model_var.get()
        initial_model = self.model_display_to_id.get(initial_model_display, '')
        use_student_handbook = self.use_handbook_var.get()
        student_handbook_path = self.handbook_path_var.get(
            ) if use_student_handbook else ''
        if use_student_handbook and not os.path.exists(student_handbook_path):
            messagebox.showwarning('Invalid Handbook',
                'Please select a valid student handbook file or disable the feature'
                )
            return
        if selected_modules:
            confirm_message = (
                f"Generate content for course '{course_name}' using CSV file '{os.path.basename(self.csv_file_path)}' for selected modules: {', '.join(selected_modules)}?"
                )
        else:
            confirm_message = (
                f"Generate content for course '{course_name}' using CSV file '{os.path.basename(self.csv_file_path)}' for ALL modules?"
                )
        if not messagebox.askyesno('Confirm Generation', confirm_message):
            return
        self.generation_running = True
        self.generate_button.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self._update_status('Starting content generation...')
        self.results_text.delete(1.0, tk.END)
        output_dir = self.output_dir_var.get()
        if not output_dir:
            output_dir = 'output'
        self._ensure_output_dirs(output_dir)
        self._log(f'Using output directory: {output_dir}')
        self._log(
            'Processing steps will use Claude 3.7 Sonnet regardless of '
            'saved settings'
        )
        threading.Thread(
            target=self._run_generation,
            args=(selected_modules, None, use_student_handbook, student_handbook_path, output_dir),
            daemon=True,
        ).start()
        self._monitor_progress()

    def _run_generation(self, selected_modules=None, workflow_phase=None,
        use_student_handbook=False, student_handbook_path='', output_dir=
        'output'):
        """Run content generation in a separate thread with optional workflow phase"""
        try:
            self._log('Starting content generation process')
            self._log(f'Output directory: {output_dir}')
            self._update_status('Generating content...')
            self._update_progress(10, 'Initializing...')
            if selected_modules:
                self._log(
                    f'Filtering CSV data for selected modules: {selected_modules}'
                    )
                filtered_csv_path = self._create_filtered_csv(selected_modules)
                csv_path_to_use = filtered_csv_path
            else:
                csv_path_to_use = self.csv_file_path
            updated_settings = self.ui_settings.copy(
                ) if self.ui_settings else {}
            if 'generation_settings' not in updated_settings:
                updated_settings['generation_settings'] = {}
            updated_settings['generation_settings']['word_count'] = int(self
                .word_count.get())
            updated_settings['generation_settings']['character_limit'] = int(
                self.word_count.get())
            updated_settings['generation_settings']['max_tokens'] = int(self
                .token_limit.get())
            forced_model_id = 'claude-3-7-sonnet-20250219'
            forced_display = self.model_id_to_display.get(
                forced_model_id, 'Claude 3.7 Sonnet'
            )
            if self.model_var.get() != forced_display:
                self._log(
                    'Processing model overridden to Claude 3.7 Sonnet',
                    level='WARNING',
                )
                self.model_var.set(forced_display)
            updated_settings['selected_model'] = forced_model_id
            updated_settings['model'] = forced_model_id
            self.settings['selected_model'] = forced_model_id
            self.settings['model'] = forced_model_id
            initial_model_display = self.initial_model_var.get()
            initial_model_id = self.model_display_to_id.get(
                initial_model_display, 'claude-3-haiku-20240307')
            updated_settings['initial_generation_model'] = initial_model_id
            updated_settings['use_student_handbook'] = use_student_handbook
            updated_settings['student_handbook_path'] = student_handbook_path
            
            # Add template directory if specified
            template_dir = self.template_dir_var.get()
            if template_dir and os.path.exists(template_dir):
                updated_settings['template_directory'] = template_dir
                self._log(f'Using template directory: {template_dir}', level='INFO')
            if use_student_handbook:
                self._log(f'Using student handbook: {student_handbook_path}',
                    level='INFO')
            else:
                self._log('Student handbook extraction disabled', level='INFO')
            self._log(
                f"Using word count: {updated_settings['generation_settings']['word_count']} words"
                )
            self._log(
                f"Using token limit: {updated_settings['generation_settings']['max_tokens']} tokens"
                )
            self._log(f"Using model: {updated_settings['selected_model']}")
            self._log('DEBUG: About to call run_workflow', level='DEBUG')
            try:
                workflow_result = run_workflow(
                    csv_path=csv_path_to_use,
                    course_name=self.course_name.get(),
                    learner_profile=self.learner_profile,
                    ui_settings=updated_settings,
                    selected_modules=selected_modules,
                    instance_id=self.instance_id,
                    workflow_phase=workflow_phase,
                    output_dir=output_dir,
                    progress_queue=self.progress_queue,
                )
                self._log(
                    f'DEBUG: workflow_result type: {type(workflow_result).__name__}'
                    , level='DEBUG')
                if hasattr(workflow_result, '__await__'):
                    self._log(
                        'Result is a coroutine, creating isolated runner thread'
                        , level='INFO')
                    import concurrent.futures
                    result_future = concurrent.futures.Future()

                    def run_coroutine_in_isolated_thread():
                        try:
                            self._log('Starting isolated event loop thread',
                                level='INFO')
                            import asyncio
                            isolated_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(isolated_loop)
                            try:
                                actual_result = (isolated_loop.
                                    run_until_complete(workflow_result))
                                result_future.set_result(actual_result)
                                self._log(
                                    'Coroutine completed successfully in isolated thread'
                                    , level='INFO')
                            finally:
                                isolated_loop.close()
                                self._log('Isolated event loop closed',
                                    level='INFO')
                        except Exception as e:
                            self._log(f'Error in isolated thread: {str(e)}',
                                level='ERROR')
                            import traceback
                            self._log(f'Traceback: {traceback.format_exc()}',
                                level='ERROR')
                            result_future.set_exception(e)
                    import threading
                    isolated_thread = threading.Thread(target=
                        run_coroutine_in_isolated_thread, daemon=True)
                    isolated_thread.start()
                    try:
                        self._log('Waiting for result from isolated thread',
                            level='INFO')
                        self.results = result_future.result(timeout=3600)
                        self._log('Received result from isolated thread',
                            level='INFO')
                        self._log(
                            f'DIAGNOSTIC: Result type: {type(self.results).__name__}'
                            , level='DEBUG')
                        if isinstance(self.results, dict):
                            self._log(
                                f"DIAGNOSTIC: Result keys: {', '.join(self.results.keys())}"
                                , level='DEBUG')
                            phases_list = self.results.get('phases_completed',
                                [])
                            self._log(
                                f'DIAGNOSTIC: Phases completed from result: {phases_list}'
                                , level='INFO')
                            workflow_status = self.results.get('status',
                                'unknown')
                            self._log(
                                f'DIAGNOSTIC: Workflow status: {workflow_status}'
                                , level='INFO')
                            if 'processed_rows' in self.results:
                                row_count = len(self.results['processed_rows'])
                                completed_rows = sum(1 for r in self.
                                    results['processed_rows'] if r.get(
                                    'status') == 'completed')
                                self._log(
                                    f'DIAGNOSTIC: Processed {row_count} rows, {completed_rows} completed'
                                    , level='INFO')
                        if ('phases_completed' in self.results and 
                            'generate' in self.results['phases_completed']):
                            self._log('✅ GENERATION PHASE COMPLETED', level
                                ='INFO')
                            self._log(
                                f"DIAGNOSTIC: Next phases to run: {[p for p in ['generate', 'compare', 'review', 'finalize'] if p not in self.results.get('phases_completed', [])]}"
                                , level='INFO')
                    except concurrent.futures.TimeoutError:
                        self._log('Timeout waiting for coroutine result',
                            level='ERROR')
                        raise RuntimeError(
                            'Timeout waiting for workflow to complete')
                    except Exception as e:
                        self._log(f'Error from isolated thread: {str(e)}',
                            level='ERROR')
                        import traceback
                        self._log(
                            f'Traceback for isolated thread error: {traceback.format_exc()}'
                            , level='ERROR')
                        raise
                else:
                    self._log('Result is already resolved (not a coroutine)',
                        level='INFO')
                    self.results = workflow_result
            except Exception as workflow_e:
                self._log(f'ERROR in workflow execution: {str(workflow_e)}',
                    level='ERROR')
                import traceback
                self._log(f'Traceback: {traceback.format_exc()}', level='ERROR'
                    )
                raise workflow_e
            self._update_progress(100, 'Generation complete')
            self._update_status('Processing completed.')
            self._update_status(
                f"Generation complete. Output directory: {self.results.get('output_dir', 'unknown')}"
                )
            self._display_results(self.results)
            if 'output_dir' in self.results and os.path.exists(self.results
                ['output_dir']):
                self.open_output_button.config(state=tk.NORMAL)
            self._log('Content generation process completed successfully')
            if selected_modules and 'filtered_csv_path' in locals():
                try:
                    os.remove(filtered_csv_path)
                    self._log(
                        f'Removed temporary filtered CSV file: {filtered_csv_path}'
                        )
                except Exception as e:
                    self._log(
                        f'Error removing temporary filtered CSV file: {str(e)}'
                        , level='WARNING')
        except Exception as e:
            error_msg = f'Error generating content: {str(e)}'
            self._log(error_msg, level='ERROR')
            self._update_status(f'Error: {str(e)}')
            messagebox.showerror('Generation Error', error_msg)
        finally:
            self.generate_button.config(state=tk.NORMAL)
            self.generation_running = False

    def _create_filtered_csv(self, selected_modules):
        """Create a temporary CSV file with only the selected modules"""
        if not self.csv_data or not selected_modules:
            return self.csv_file_path
        filtered_data = [row for row in self.csv_data if row.get('Module',
            '') in selected_modules]
        if not filtered_data:
            self._log('No data found for selected modules', level='WARNING')
            return self.csv_file_path
        temp_dir = 'temp'
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filtered_csv_path = os.path.join(temp_dir,
            f'filtered_csv_{timestamp}.csv')
        try:
            columns = list(filtered_data[0].keys())
            df = pd.DataFrame(filtered_data)
            df.to_csv(filtered_csv_path, index=False)
            self._log(
                f'Created filtered CSV with {len(filtered_data)} rows for selected modules'
                )
            return filtered_csv_path
        except Exception as e:
            self._log(f'Error creating filtered CSV: {str(e)}', level='ERROR')
            return self.csv_file_path

    def _display_results(self, result):
        """Display generation results in the UI"""
        if not result:
            return
        self.results_text.delete(1.0, tk.END)
        summary = 'Generation Summary:\n'
        summary += f"Course: {result.get('course_name', 'unknown')}\n"
        summary += (
            f"CSV File: {os.path.basename(result.get('csv_path', 'unknown'))}\n"
            )
        summary += f"Output Directory: {result.get('output_dir', 'unknown')}\n"
        summary += f"Total Rows: {len(result.get('processed_rows', []))}\n"
        summary += f"Success: {result.get('success_count', 0)}\n"
        summary += f"Errors: {result.get('error_count', 0)}\n\n"
        summary += 'Processed Rows:\n'
        for i, row_result in enumerate(result.get('processed_rows', [])):
            status = row_result.get('status', 'unknown')
            module = row_result.get('module', 'unknown')
            lesson = row_result.get('lesson', 'unknown')
            step_number = row_result.get('step_number', 'unknown')
            step_title = row_result.get('step_title', 'unknown')
            summary += f"""{i + 1}. {module} > {lesson} > Step {step_number}: {step_title} - {status}
"""
            if status == 'error':
                summary += f"   Error: {row_result.get('error', 'unknown')}\n"
            elif status == 'completed':
                summary += (
                    f"   Output: {row_result.get('output_path', 'unknown')}\n")
        self.results_text.insert(tk.END, summary)

    def _open_output_directory(self):
        """Open the output directory in file explorer"""
        if not self.results or 'output_dir' not in self.results:
            messagebox.showinfo('No Output', 'No output directory available.')
            return
        output_dir = self.results['output_dir']
        if not os.path.exists(output_dir):
            messagebox.showinfo('Directory Not Found',
                f'Output directory not found: {output_dir}')
            return
        try:
            os.startfile(output_dir)
        except Exception as e:
            error_msg = f'Error opening output directory: {str(e)}'
            self._log(error_msg, level='ERROR')
            messagebox.showerror('Error', error_msg)

    def _update_progress(self, value, message=''):
        """Update progress bar and status message"""
        self.progress_bar['value'] = value
        if message:
            self._update_status(message)
        self.root.update_idletasks()

    def _update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def _log(self, message, level='INFO'):
        """Log a message with the specified level"""
        if level == 'INFO':
            logger.info(message)
        elif level == 'WARNING':
            logger.warning(message)
        elif level == 'ERROR':
            logger.error(message)
        elif level == 'DEBUG':
            logger.debug(message)

    def _setup_logging(self):
        """Set up custom log handler and stdout/stderr redirectors"""
        import codecs
        self.log_handler = UILogHandler(self.log_text, self.log_queue)
        self.log_handler.setLevel(logging.INFO)
        self.log_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.log_handler)
        utf8_stdout = codecs.getwriter('utf-8')(sys.stdout.buffer) if hasattr(
            sys.stdout, 'buffer') else sys.stdout
        utf8_stderr = codecs.getwriter('utf-8')(sys.stderr.buffer) if hasattr(
            sys.stderr, 'buffer') else sys.stderr
        self.stdout_redirector = StdoutRedirector(self.log_text, self.
            log_queue, utf8_stdout)
        sys.stdout = self.stdout_redirector
        self.stderr_redirector = StdoutRedirector(self.log_text, self.
            log_queue, utf8_stderr)
        sys.stderr = self.stderr_redirector
        self._update_log_display()
        logger.info(
            'Log display window initialized and ready with UTF-8 encoding')

    def _update_log_display(self):
        """Update the log display with any pending log messages"""
        while True:
            try:
                message = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message)
                self.log_text.see(tk.END)
                total_lines = int(self.log_text.index('end-1c').split('.')[0])
                if total_lines > 5000:
                    self.log_text.delete('1.0', f'{total_lines - 5000}.0')
                self.log_text.config(state=tk.DISABLED)
                self.log_queue.task_done()
            except queue.Empty:
                break
        self.root.after(self.log_update_interval, self._update_log_display)

    def _monitor_progress(self):
        """Monitor progress updates from worker threads"""
        def _loop():
            import time
            while self.generation_running or not self.progress_queue.empty():
                try:
                    value = self.progress_queue.get_nowait()
                    self.root.after(0, lambda v=value: self._update_progress(v))
                    self.progress_queue.task_done()
                except queue.Empty:
                    pass
                time.sleep(0.1)

        threading.Thread(target=_loop, daemon=True).start()

    def __del__(self):
        """Clean up resources when the application is closed"""
        if hasattr(self, 'stdout_redirector') and self.stdout_redirector:
            sys.stdout = self.stdout_redirector.original_stream
        if hasattr(self, 'stderr_redirector') and self.stderr_redirector:
            sys.stderr = self.stderr_redirector.original_stream
        if hasattr(self, 'log_handler') and self.log_handler:
            logging.getLogger().removeHandler(self.log_handler)


class UILogHandler(logging.Handler):
    """Custom log handler that redirects logs to the UI text widget"""

    def __init__(self, text_widget, message_queue):
        super().__init__()
        self.text_widget = text_widget
        self.message_queue = message_queue

    def emit(self, record):
        """Process a log record and add it to the queue with UTF-8 encoding"""
        try:
            log_entry = self.format(record)
            if isinstance(log_entry, bytes):
                log_entry = log_entry.decode('utf-8', errors='replace')
            self.message_queue.put(log_entry + '\n')
        except Exception as e:
            safe_message = f'Error formatting log message: {str(e)}'
            self.message_queue.put(safe_message + '\n')


class StdoutRedirector:
    """Redirects stdout/stderr to the UI text widget"""

    def __init__(self, text_widget, message_queue, original_stream):
        self.text_widget = text_widget
        self.message_queue = message_queue
        self.original_stream = original_stream

    def write(self, message):
        """Write to both the original stream and the UI"""
        self.original_stream.write(message)
        if message.strip():
            self.message_queue.put(message)

    def flush(self):
        """Flush the stream"""
        self.original_stream.flush()


def run_app():
    """Run the application"""
    import argparse
    parser = argparse.ArgumentParser(description=
        'ShowupSquared Simplified Content Generator')
    parser.add_argument('--settings', help='Path to settings file', default
        ='user_settings.json')
    parser.add_argument('--log', help='Path to log file', default=
        'logs/simplified_app.log')
    parser.add_argument('--instance', help='Instance ID', default='default')
    parser.add_argument('--output-dir', help=
        'Custom output directory for generated content', default='output')
    args = parser.parse_args()
    if args.log != 'logs/simplified_app.log':
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                logging.root.removeHandler(handler)
        log_dir = os.path.dirname(args.log)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(args.log)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.root.addHandler(file_handler)
    root = tk.Tk()
    app = SimplifiedContentGeneratorApp(root, args.settings, args.instance,
        output_dir=args.output_dir)
    root.mainloop()


if __name__ == '__main__':
    run_app()
