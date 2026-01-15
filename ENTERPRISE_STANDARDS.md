# Enterprise Standards - Complete Implementation Guide for MT5 AI/ML Trading Bot

## Table of Contents
1. [Code Quality & Standards](#1-code-quality--standards)
2. [Testing Infrastructure](#2-testing-infrastructure)
3. [Documentation](#3-documentation)
4. [Project Configuration](#4-project-configuration)
5. [Git Workflow & Organization](#5-git-workflow--organization)
6. [Security](#6-security)
7. [Project Structure](#7-project-structure)
8. [Development Tools](#8-development-tools)
9. [Performance & Monitoring](#9-performance--monitoring)
10. [Dependency Management](#10-dependency-management)
11. [API Documentation](#11-api-documentation)
12. [Quality Metrics](#12-quality-metrics)
13. [Automation](#13-automation)
14. [Contributing Guidelines](#14-contributing-guidelines)
15. [Release Checklist](#15-release-checklist)

***

## 1. Code Quality & Standards

### A. Linting & Formatting

**Tools to Implement:**
```bash
# Install required tools
pip install black pylint flake8 isort autopep8 pycodestyle pydocstyle
```

**Configuration Files:**

`.flake8`
```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,.venv,build,dist
ignore = E203,W503
per-file-ignores = 
    __init__.py:F401
count = True
statistics = True
```

`setup.cfg`
```ini
[flake8]
max-line-length = 100

[isort]
profile = black
multi_line_mode = 3
include_trailing_comma = True
force_grid_wrap = 0
use_parentheses = True
ensure_newline_before_comments = True
line_length = 100

[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=src --cov-report=html --cov-report=term-missing --verbose
```

`pyproject.toml`
```toml
[tool.black]
line-length = 100
target-version = ['py39', 'py310', 'py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.venv
  | build
  | dist
)/
'''

[tool.pylint.messages_control]
disable = [
    "C0111",  # missing-docstring
    "C0103",  # invalid-name
]

[tool.pylint.format]
max-line-length = 100

[tool.pylint.basic]
good-names = ["i", "j", "k", "ex", "Run", "_"]
```

**.pre-commit-config.yaml**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: debug-statements
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100']
        additional_dependencies: ['flake8-docstrings']

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-ll', '-r', 'src/']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        args: ['--ignore-missing-imports']
        additional_dependencies: ['types-all']
```

### B. Type Safety

**Type Hints Throughout Codebase:**

```python
# Example: src/models/ppo_trader.py
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from stable_baselines3 import PPO

class PPOTrader:
    """PPO-based trading agent for XAUUSD.
    
    Attributes:
        model: The PPO model instance
        feature_size: Dimensionality of feature space
        action_space_size: Number of possible actions
    """
    
    def __init__(
        self, 
        feature_size: int = 140,
        action_space_size: int = 3,
        learning_rate: float = 3e-4
    ) -> None:
        """Initialize PPO trader.
        
        Args:
            feature_size: Number of input features
            action_space_size: Size of action space
            learning_rate: PPO learning rate
            
        Raises:
            ValueError: If feature_size <= 0 or action_space_size < 2
        """
        if feature_size <= 0:
            raise ValueError("feature_size must be positive")
        if action_space_size < 2:
            raise ValueError("action_space_size must be at least 2")
            
        self.feature_size: int = feature_size
        self.action_space_size: int = action_space_size
        self.model: Optional[PPO] = None
        
    def train(
        self, 
        data: np.ndarray,
        steps: int = 1000000,
        batch_size: int = 64
    ) -> Dict[str, float]:
        """Train PPO model on historical data.
        
        Args:
            data: Training data array of shape (timesteps, features)
            steps: Number of training steps
            batch_size: Training batch size
            
        Returns:
            Dictionary with training metrics (loss, reward, etc.)
            
        Raises:
            ValueError: If data shape is invalid
            RuntimeError: If training fails
        """
        if data.shape[1] != self.feature_size:
            raise ValueError(
                f"Expected {self.feature_size} features, "
                f"got {data.shape[1]}"
            )
        # Implementation...
        return {}
    
    def predict(
        self, 
        observation: np.ndarray,
        deterministic: bool = True
    ) -> Tuple[int, Optional[np.ndarray]]:
        """Generate trading action from observation.
        
        Args:
            observation: Current market observation
            deterministic: If True, use greedy policy
            
        Returns:
            Tuple of (action, hidden_state)
        """
        # Implementation...
        return 0, None
```

**mypy Configuration & Strict Type Checking:**

`mypy.ini`
```ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
strict_equality = True
```

### C. Code Documentation

**Google-style Docstrings:**

```python
def calculate_sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.02
) -> float:
    """Calculate Sharpe ratio of trading returns.
    
    The Sharpe ratio is a measure of risk-adjusted return, calculated as:
    (mean_return - risk_free_rate) / std_dev_return
    
    Args:
        returns: Array of periodic returns (e.g., daily returns)
        risk_free_rate: Annual risk-free rate (default: 0.02 for 2%)
        
    Returns:
        The calculated Sharpe ratio (higher is better, >2 is excellent)
        
    Raises:
        ValueError: If returns array is empty or risk_free_rate is negative
        
    Examples:
        >>> returns = np.array([0.01, 0.02, -0.01, 0.03])
        >>> sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        >>> print(f"Sharpe Ratio: {sharpe:.2f}")
        Sharpe Ratio: 1.25
        
    Note:
        Assumes returns are in the same frequency as risk_free_rate.
        For daily returns, annualize by multiplying by sqrt(252).
        
    See Also:
        calculate_max_drawdown: Another important risk metric
    """
    if len(returns) == 0:
        raise ValueError("Returns array cannot be empty")
    if risk_free_rate < 0:
        raise ValueError("Risk-free rate cannot be negative")
        
    excess_returns = returns - (risk_free_rate / 252)  # Daily equivalent
    return np.mean(excess_returns) / np.std(excess_returns)
```

***

## 2. Testing Infrastructure

### A. Unit Testing

`tests/conftest.py`
```python
import pytest
import numpy as np
from pathlib import Path

@pytest.fixture
def sample_market_data() -> np.ndarray:
    """Generate sample XAUUSD market data."""
    np.random.seed(42)
    return np.random.randn(1000, 140)  # 1000 timesteps, 140 features

@pytest.fixture
def sample_returns() -> np.ndarray:
    """Generate sample trading returns."""
    np.random.seed(42)
    return np.random.normal(0.001, 0.02, 252)  # Daily returns for 1 year

@pytest.fixture
def temp_model_path(tmp_path) -> Path:
    """Create temporary path for model files."""
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    return model_dir

@pytest.fixture
def mock_mt5_connection(monkeypatch):
    """Mock MT5 connection."""
    class MockMT5:
        def __init__(self):
            self.connected = True
        def connect(self, *args, **kwargs):
            return True
        def disconnect(self):
            self.connected = False
        def get_rates(self, *args, **kwargs):
            return np.random.randn(100, 140)
    
    return MockMT5()
```

`tests/unit/test_models.py`
```python
import pytest
import numpy as np
from src.models.ppo_trader import PPOTrader
from src.models.feature_engineer import FeatureEngineer

class TestPPOTrader:
    """Test suite for PPO trader model."""
    
    def test_initialization(self):
        """Test PPOTrader initialization."""
        trader = PPOTrader(feature_size=140, action_space_size=3)
        assert trader.feature_size == 140
        assert trader.action_space_size == 3
        
    def test_invalid_feature_size(self):
        """Test that invalid feature size raises error."""
        with pytest.raises(ValueError):
            PPOTrader(feature_size=-1)
            
    def test_train_shape_validation(self, sample_market_data):
        """Test that train validates input shape."""
        trader = PPOTrader(feature_size=140)
        invalid_data = np.random.randn(100, 50)  # Wrong feature dim
        
        with pytest.raises(ValueError):
            trader.train(invalid_data)
            
    def test_predict_output_shape(self, sample_market_data):
        """Test that predict returns correct shape."""
        trader = PPOTrader(feature_size=140)
        # Setup mock model...
        observation = sample_market_data[0]
        action, hidden = trader.predict(observation)
        
        assert isinstance(action, (int, np.integer))
        assert action in [0, 1, 2]  # Valid actions
```

`tests/unit/test_utils.py`
```python
import pytest
import numpy as np
from src.utils.metrics import calculate_sharpe_ratio, calculate_max_drawdown

class TestMetrics:
    """Test trading performance metrics."""
    
    def test_sharpe_ratio_positive(self, sample_returns):
        """Test Sharpe ratio calculation with positive returns."""
        sharpe = calculate_sharpe_ratio(sample_returns)
        assert isinstance(sharpe, float)
        
    def test_sharpe_ratio_empty_input(self):
        """Test Sharpe ratio with empty array."""
        with pytest.raises(ValueError):
            calculate_sharpe_ratio(np.array([]))
            
    def test_max_drawdown_calculation(self, sample_returns):
        """Test maximum drawdown calculation."""
        cumulative = np.cumprod(1 + sample_returns) - 1
        drawdown = calculate_max_drawdown(cumulative)
        
        assert drawdown <= 0
        assert abs(drawdown) <= 1  # Max 100% loss
```

### B. Integration Testing

`tests/integration/test_mt5_integration.py`
```python
import pytest
from src.trading.mt5_connector import MT5Connector

class TestMT5Integration:
    """Integration tests for MT5 platform."""
    
    @pytest.mark.integration
    def test_mt5_connection(self, mock_mt5_connection):
        """Test MT5 connection establishment."""
        connector = MT5Connector()
        assert connector.connect(mock_mt5_connection)
        
    @pytest.mark.integration
    def test_data_fetching(self, mock_mt5_connection):
        """Test historical data fetching."""
        connector = MT5Connector(mock_mt5_connection)
        data = connector.fetch_ohlcv("XAUUSD", "M5", 1000)
        
        assert data is not None
        assert len(data) > 0
        
    @pytest.mark.integration
    def test_order_placement(self, mock_mt5_connection):
        """Test order placement."""
        connector = MT5Connector(mock_mt5_connection)
        order_id = connector.place_order(
            symbol="XAUUSD",
            action="BUY",
            volume=0.1,
            price=None  # Market order
        )
        
        assert order_id is not None
        assert isinstance(order_id, int)
```

### C. CI/CD Pipeline

`.github/workflows/tests.yml`
```yaml
name: Tests & Code Quality

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8
      run: |
        flake
