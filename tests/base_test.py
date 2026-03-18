import os
import unittest
from datetime import datetime
from src.core.llm import setup_logger
from src.core.log_viewer import generate_log_report

class BaseTestCase(unittest.TestCase):
    """Base test class that handles session logging setup."""
    
    @classmethod
    def setUpClass(cls):
        # Create a session directory for this test class
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cls.session_dir = os.path.join("logs", f"test_session_{cls.__name__}_{timestamp}")
        os.makedirs(cls.session_dir, exist_ok=True)
        
        # Setup LLM logger
        cls.llm_log_path = os.path.join(cls.session_dir, "llm_log.jsonl")
        setup_logger(cls.llm_log_path)
        print(f"\n📂 Test Session Logs: {cls.session_dir}")

    @classmethod
    def tearDownClass(cls):
        # Generate HTML report
        report_path = os.path.join(cls.session_dir, "report.html")
        if generate_log_report(cls.llm_log_path, report_path):
            print(f"📊 Generated Test Report: {report_path}")
