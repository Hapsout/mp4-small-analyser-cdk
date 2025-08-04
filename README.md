# MP4 Small Analyser CDK

This AWS CDK Python project deploys infrastructure for analyzing small MP4 files.

## Repository

🔗 **GitHub**: [https://github.com/Hapsout/mp4-small-analyser-cdk](https://github.com/Hapsout/mp4-small-analyser-cdk)

The `cdk.json` file tells the CDK Toolkit how to execute your app.

## Getting Started

### Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js and npm (for AWS CDK CLI)
- Python 3.11+ and pip

### Setup

1. **Clone the repository**:

   ```bash
   git clone git@github.com:Hapsout/mp4-small-analyser-cdk.git
   cd mp4-small-analyser-cdk
   ```

2. **Create and activate virtual environment**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Linux/macOS
   # .venv\Scripts\activate.bat  # On Windows
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Bootstrap CDK** (first time only):
   ```bash
   cdk bootstrap
   ```

## Development

### Project Structure

```
mp4-small-analyser-cdk/
├── mp4_small_analyser_cdk/           # Main CDK stack
│   └── mp4_small_analyser_cdk_stack.py
├── tests/                            # Unit tests
├── app.py                           # CDK app entry point
├── cdk.json                         # CDK configuration
└── requirements.txt                 # Python dependencies
```

### Testing

Run unit tests:

```bash
pytest
```

### Synthesis and Deployment

Synthesize CloudFormation template:

```bash
cdk synth
```

Deploy to AWS:

```bash
cdk deploy
```

## Useful Commands

- `cdk ls` - List all stacks in the app
- `cdk synth` - Synthesize CloudFormation template
- `cdk deploy` - Deploy stack to AWS
- `cdk diff` - Compare deployed stack with current state
- `cdk destroy` - Remove stack from AWS
- `cdk docs` - Open CDK documentation

## Contributing

1. Create a feature branch from `main`
2. Make your changes and test them
3. Submit a pull request

---

Built with ❤️ using AWS CDK Python
